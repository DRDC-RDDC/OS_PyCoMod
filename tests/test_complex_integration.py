"""Integration test with a complex model combining all features.

The model has:
- Multi-layer submodels (Outer -> Middle -> Inner)
- Process / discrete event definitions
- Step functions
- Impulse functions
- Regular equations and flows (including stochastic and cross-submodel)
- Parameters at every level
"""

import pytest
from pathlib import Path

import pycomod as pcm
from pycomod.export.model_inspector import inspect_model
from pycomod.export.code_translator import CodeTranslator
from pycomod.export.js_simulation_engine import generate_js_engine
from pycomod.export.html_export import export_to_html


# -----------------------------------------------------------------------
# Model definitions
# -----------------------------------------------------------------------

class InnerSIR(pcm.Model):
    def build(self, s0=900, i0=100, r0=0):
        S = self.pool(s0)
        I = self.pool(i0)
        R = self.pool(r0)
        N = self.equation(lambda: S + I + R)
        g = self.parameter(0.1)
        b = self.step(values=[0.3, 0.05, 0.2], times=[0, 30, 60], default=0.3)
        vax = self.impulse(values=[20, 40], times=[15, 45])
        Fsi = self.flow(lambda: b * S * I / N, src=S, dest=I, stochastic=True)
        Fir = self.flow(lambda: g * I, src=I, dest=R)
        Fvax = self.flow(lambda: vax, src=S, dest=R)
        self.set_available(locals(), output=(S, I, R))


class MiddleRegion(pcm.Model):
    def build(self, s0=900, i0=100):
        sir = self.submodel(InnerSIR(s0, i0, 0))
        treat_rate = self.parameter(5)
        treat_interval = self.parameter(7)

        @self.process(start=self.wait_time(3))
        def treat():
            while True:
                if sir.I >= treat_rate:
                    sir.I.remove(treat_rate)
                    sir.R.add(treat_rate)
                yield self.wait_delay(treat_interval)

        self.set_available(locals(), output=(sir,))


class TopModel(pcm.Model):
    def build(self):
        regionA = self.submodel(MiddleRegion(900, 100))
        regionB = self.submodel(MiddleRegion(800, 200))
        migration = self.parameter(0.01)
        total_I = self.equation(lambda: regionA.sir.I + regionB.sir.I)
        total_S = self.equation(lambda: regionA.sir.S + regionB.sir.S)
        F_AB = self.flow(
            lambda: migration * regionA.sir.I,
            src=regionA.sir.I, dest=regionB.sir.I,
        )
        self.set_available(
            locals(), output=(regionA, regionB, total_I, total_S)
        )


@pytest.fixture
def complex_model():
    return TopModel()


def _run_model(model, end=30):
    init = model.get_init()
    init['run']['end'] = [end]
    model.set_init(init)
    model._run()
    return model._output


# -----------------------------------------------------------------------
# 1. Python model simulation
# -----------------------------------------------------------------------

class TestModelSimulationOutput:

    def test_output_structure(self, complex_model):
        out = _run_model(complex_model, end=30)
        assert out is not None
        for key in ('regionA', 'regionB', 'total_I', 'total_S'):
            assert key in out
        sir_a = out['regionA']['sir']
        for var in ('S', 'I', 'R'):
            assert var in sir_a

    def test_initial_values_and_conservation(self, complex_model):
        out = _run_model(complex_model, end=10)
        sir_a = out['regionA']['sir']
        sir_b = out['regionB']['sir']
        assert sir_a['S']['values'][0] == pytest.approx(900.0)
        assert sir_a['I']['values'][0] == pytest.approx(100.0)
        assert sir_b['S']['values'][0] == pytest.approx(800.0)
        assert sir_b['I']['values'][0] == pytest.approx(200.0)

        pop = (
            sir_a['S']['values'][0]
            + sir_a['I']['values'][0]
            + sir_a['R']['values'][0]
            + sir_b['S']['values'][0]
            + sir_b['I']['values'][0]
            + sir_b['R']['values'][0]
        )
        assert pop == pytest.approx(2000.0)

        assert out['total_I']['values'][0] == pytest.approx(300.0)
        assert out['total_S']['values'][0] == pytest.approx(1700.0)

    def test_dynamics_and_time_axis(self, complex_model):
        out = _run_model(complex_model, end=30)
        sir_a = out['regionA']['sir']
        assert sir_a['S']['values'][-1] < sir_a['S']['values'][0]
        assert sir_a['R']['values'][-1] > 0

        assert len(sir_a['S']['values']) == 31
        assert sir_a['S']['times'][0] == 0
        assert sir_a['S']['times'][-1] == 30


# -----------------------------------------------------------------------
# 2. Model inspector
# -----------------------------------------------------------------------

class TestComplexModelInspection:

    @pytest.fixture
    def structure(self, complex_model):
        return inspect_model(complex_model)

    def test_pools_and_parameters(self, structure):
        pools = structure['pools']
        for prefix in ('regionA__sir', 'regionB__sir'):
            for var in ('S', 'I', 'R'):
                assert '%s__%s' % (prefix, var) in pools

        params = structure['parameters']
        assert params['migration']['init_value'] == pytest.approx(0.01)
        assert params['regionA__treat_rate']['init_value'] == pytest.approx(
            5.0)
        assert params['regionA__sir__g']['init_value'] == pytest.approx(0.1)

    def test_equations(self, structure):
        equations = structure['equations']
        assert equations['regionA__sir__b']['type'] == 'step'
        assert equations['regionA__sir__b']['values'] == [0.3, 0.05, 0.2]
        assert equations['regionA__sir__vax']['type'] == 'impulse'
        assert equations['regionA__sir__vax']['values'] == [20, 40]
        assert equations['total_I']['type'] == 'equation'
        assert equations['regionA__sir__N']['type'] == 'equation'

    def test_flows(self, structure):
        flows = structure['flows']
        assert flows['F_AB']['src'] == 'regionA__sir__I'
        assert flows['F_AB']['dest'] == 'regionB__sir__I'
        assert flows['regionA__sir__Fsi']['stochastic'] is True
        assert flows['regionA__sir__Fir']['stochastic'] is False

    def test_processes(self, structure):
        procs = structure['processes']
        assert procs['regionA__treat']['start_type'] == 'time'
        assert procs['regionA__treat']['start_value'] == 3
        assert 'def treat' in procs['regionA__treat']['source']

    def test_metadata(self, structure):
        assert {'regionA', 'regionB', 'sir'} <= structure['submodel_names']
        assert structure['display_names']['regionA__sir__S'] == 'regionA.sir.S'
        assert 'regionA__sir__S' in structure['outputs']
        assert 'total_I' in structure['outputs']
        assert 'regionA__sir__b' in structure['si_outputs']

        em = structure['element_map']
        assert em['regionA__sir__S'] == 'pool'
        assert em['migration'] == 'parameter'
        assert em['total_I'] == 'equation'
        assert em['F_AB'] == 'flow'


# -----------------------------------------------------------------------
# 3. Code translation
# -----------------------------------------------------------------------

class TestComplexCodeTranslation:

    @pytest.fixture
    def structure(self, complex_model):
        return inspect_model(complex_model)

    @pytest.fixture
    def translator(self, structure):
        return CodeTranslator(
            element_map=structure['element_map'],
            submodel_names=structure['submodel_names'],
        )

    def test_equations_and_flows_translate(self, structure, translator):
        eq = structure['equations']['total_I']
        r = translator.translate_lambda(eq['func_info']['source'])
        assert (
            r['success']
            and "elements['regionA__sir__I'].value" in r['javascript']
        )

        flow = structure['flows']['F_AB']
        r = translator.translate_lambda(flow['rate_func']['source'])
        assert (
            r['success'] and "elements['migration'].value" in r['javascript']
        )

        eq_n = structure['equations']['regionA__sir__N']
        r = translator.translate_lambda(
            eq_n['func_info']['source'], context_prefix='regionA__sir')
        assert r['success']
        for el in ('regionA__sir__S', 'regionA__sir__I', 'regionA__sir__R'):
            assert "elements['%s'].value" % el in r['javascript']

    def test_all_elements_translate_successfully(self, structure, translator):
        for name, info in structure['equations'].items():
            source = info.get('func_info', {}).get('source')
            if source and info['type'] == 'equation':
                prefix = '__'.join(name.split('__')[:-1])
                r = translator.translate_lambda(source, context_prefix=prefix)
                assert r['success'], 'Equation %s failed: %s' % (
                    name, r['errors'])

        for name, info in structure['flows'].items():
            source = info.get('rate_func', {}).get('source')
            if source:
                prefix = '__'.join(name.split('__')[:-1])
                r = translator.translate_lambda(source, context_prefix=prefix)
                assert r['success'], 'Flow %s failed: %s' % (name, r['errors'])

        process_names = set(structure['processes'].keys())
        for name, info in structure['processes'].items():
            source = info.get('source')
            if source:
                prefix = '__'.join(name.split('__')[:-1])
                r = translator.translate_process(
                    source, process_names=process_names, context_prefix=prefix)
                assert r['success'], 'Process %s failed: %s' % (
                    name, r['errors'])


# -----------------------------------------------------------------------
# 4. JS engine
# -----------------------------------------------------------------------

class TestComplexJSEngine:

    @pytest.fixture
    def engine(self, complex_model):
        structure = inspect_model(complex_model)
        translator = CodeTranslator(
            element_map=structure['element_map'],
            submodel_names=structure['submodel_names'],
        )
        translated = {}
        for name, info in structure.get('equations', {}).items():
            source = info.get('func_info', {}).get('source')
            if source:
                prefix = '__'.join(name.split('__')[:-1])
                r = translator.translate_lambda(source, context_prefix=prefix)
                translated[name] = r['javascript'] if r['success'] else '0'
        for name, info in structure.get('flows', {}).items():
            source = info.get('rate_func', {}).get('source')
            if source:
                prefix = '__'.join(name.split('__')[:-1])
                r = translator.translate_lambda(source, context_prefix=prefix)
                translated[name] = r['javascript'] if r['success'] else '0'

        process_names = set(structure.get('processes', {}).keys())
        for name, info in structure.get('processes', {}).items():
            source = info.get('source')
            if source:
                prefix = '__'.join(name.split('__')[:-1])
                r = translator.translate_process(
                    source, process_names=process_names, context_prefix=prefix)
                if r['success']:
                    info['js_body'] = r['javascript']

        return generate_js_engine(structure, translated)

    def test_engine_contains_all_elements(self, engine):
        assert isinstance(engine, str) and len(engine) > 5000

        for name in ['regionA__sir__S', 'regionA__sir__I', 'regionB__sir__S']:
            assert "elements['%s']" % name in engine
        for name in ['migration', 'regionA__treat_rate', 'regionA__sir__g']:
            assert "elements['%s']" % name in engine

        assert 'new Step' in engine
        assert 'new Impulse' in engine
        assert "elements['F_AB']" in engine

    def test_engine_infrastructure(self, engine):
        for expected in ('run_simulation', 'PyCoModSimulation', 'class Pool',
                         'class Flow', 'class Process', 'new Process',
                         'function*', 'processes.push', 'new Time(3)'):
            assert expected in engine


# -----------------------------------------------------------------------
# 5. Full HTML export
# -----------------------------------------------------------------------

class TestComplexHTMLExport:

    def test_full_export(self, complex_model, tmp_path):
        output = export_to_html(
            model=complex_model,
            filename='complex_test.html',
            path=str(tmp_path),
            title='Complex Integration Test',
            help_text='# Complex Model\nAll features combined.',
        )
        assert Path(output).exists()
        content = Path(output).read_text(encoding='utf-8')
        assert len(content) > 50_000

        assert 'Complex Integration Test' in content
        assert 'Complex Model' in content
        assert '<style>' in content
        assert 'bnr' in content

        for name in ['regionA__sir__S', 'regionB__sir__I']:
            assert name in content
        assert 'regionA.sir.S' in content
        assert 'new Step' in content
        assert 'new Impulse' in content
        assert 'new Process' in content
        assert 'run_simulation' in content
        assert 'PyCoModSimulation' in content


# -----------------------------------------------------------------------
# 6. Manual verification
# -----------------------------------------------------------------------

class DeterministicInnerSIR(pcm.Model):
    def build(self, s0=900, i0=100, r0=0):
        S = self.pool(s0)
        I = self.pool(i0)
        R = self.pool(r0)
        N = self.equation(lambda: S + I + R)
        g = self.parameter(0.1)
        b = self.step(values=[0.3, 0.05, 0.2], times=[0, 30, 60], default=0.3)
        vax = self.impulse(values=[20, 40], times=[15, 45])
        Fsi = self.flow(lambda: b * S * I / N, src=S, dest=I)
        Fir = self.flow(lambda: g * I, src=I, dest=R)
        Fvax = self.flow(lambda: vax, src=S, dest=R)
        self.set_available(locals(), output=(S, I, R))


class DeterministicMiddleRegion(pcm.Model):
    def build(self, s0=900, i0=100):
        sir = self.submodel(DeterministicInnerSIR(s0, i0, 0))
        treat_rate = self.parameter(5)
        treat_interval = self.parameter(7)

        @self.process(start=self.wait_time(3))
        def treat():
            while True:
                if sir.I >= treat_rate:
                    sir.I.remove(treat_rate)
                    sir.R.add(treat_rate)
                yield self.wait_delay(treat_interval)

        self.set_available(locals(), output=(sir,))


class DeterministicTopModel(pcm.Model):
    def build(self):
        regionA = self.submodel(DeterministicMiddleRegion(900, 100))
        regionB = self.submodel(DeterministicMiddleRegion(800, 200))
        migration = self.parameter(0.01)
        total_I = self.equation(lambda: regionA.sir.I + regionB.sir.I)
        total_S = self.equation(lambda: regionA.sir.S + regionB.sir.S)
        F_AB = self.flow(
            lambda: migration * regionA.sir.I,
            src=regionA.sir.I, dest=regionB.sir.I,
        )
        self.set_available(
            locals(), output=(regionA, regionB, total_I, total_S)
        )


def _resample_by_time(values, times):
    import numpy as np
    resampled = {}
    for i, t in enumerate(times):
        resampled[int(t)] = values[i]
    max_t = int(times[-1])
    return np.array([resampled[t] for t in range(max_t + 1)])


def _collect_values(output, prefix=''):
    flat = {}
    for key, val in output.items():
        name = ('%s.%s' % (prefix, key)) if prefix else key
        if isinstance(val, dict) and 'values' in val:
            flat[name] = _resample_by_time(val['values'], val['times'])
        elif isinstance(val, dict):
            flat.update(_collect_values(val, name))
    return flat


def print_reference_values(output, time_points, label=''):
    flat = _collect_values(output)
    names = sorted(flat.keys())
    col_w = max(len(n) for n in names) + 2
    hdr = 'Name'.ljust(col_w) + ''.join(('t=%-8s' % t) for t in time_points)
    print()
    if label:
        print('=== %s ===' % label)
    print(hdr)
    print('-' * len(hdr))
    for name in names:
        vals = flat[name]
        row = name.ljust(col_w)
        for t in time_points:
            row += ('%-10.4f' %
                    vals[t]) if 0 <= t < len(vals) else '%-10s' % 'N/A'
        print(row)
    print()


class TestManualVerification:
    """Run with ``pytest tests/test_complex_integration.py -k manual -s``"""

    def test_manual_export_and_print(self, tmp_path):
        end = 90
        model = DeterministicTopModel()
        out = _run_model(model, end=end)

        time_points = [0, 10, 20, 30, 45, 60, end]
        print_reference_values(
            out,
            time_points,
            label='Python reference values (end=%d, dt=1, deterministic)'
            % end,
        )

        html_path = export_to_html(
            model=DeterministicTopModel(),
            filename='manual_verify.html',
            path=str(tmp_path),
            title='Manual Verification — Deterministic Complex Model',
            help_text=(
                '# Manual Verification\n'
                'Run the model with **Duration=%d**, **dt=1**, '
                '**Single** mode, then compare the plot values '
                'against the reference table printed by the test.\n\n'
                'All flows are deterministic — the JS output should '
                'match the Python reference values exactly.' % end
            ),
        )
        print('HTML exported to: %s' % html_path)
