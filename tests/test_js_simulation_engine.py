"""Tests for pycomod.export.js_simulation_engine."""

import pytest
from pycomod.export.model_inspector import inspect_model
from pycomod.export.code_translator import CodeTranslator
from pycomod.export.html_export import translate_structure
from pycomod.export.js_simulation_engine import (
    JavaScriptSimulationEngine, generate_js_engine,
)


def _build_translated_code(structure):
    """Helper: translate all equations/flows for a model structure."""
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
    return translated


def _generate(model):
    structure = inspect_model(model)
    translated = _build_translated_code(structure)
    return generate_js_engine(structure, translated), structure


class TestGenerateEngineSimpleSIR:

    def test_engine_structure(self, simple_sir):
        engine, _ = _generate(simple_sir)
        assert isinstance(engine, str) and len(engine) > 0
        assert 'PyCoMod' in engine
        for cls in ('class Pool', 'class Parameter',
                    'class Equation', 'class Flow'):
            assert cls in engine
        assert 'run_simulation' in engine
        assert 'PyCoModSimulation' in engine

    def test_engine_element_initialization(self, simple_sir):
        engine, _ = _generate(simple_sir)
        for el in ("elements.S", "elements.I", "elements.R",
                   "elements.b", "elements.g", "elements.N",
                   "elements.Fsi", "elements.Fir"):
            assert el in engine
        for constructor in ('new Pool', 'new Parameter',
                            'new Equation', 'new Flow'):
            assert constructor in engine

    def test_stochastic_and_allow_negative_flags(self, simple_sir):
        engine, _ = _generate(simple_sir)
        assert 'true' in engine
        assert 'false' in engine


class TestGenerateEngineStepImpulse:

    def test_step_and_impulse_init(self, sir_step_impulse):
        engine, _ = _generate(sir_step_impulse)
        assert 'new Step' in engine
        assert '_parse_csv' in engine
        assert 'new Impulse' in engine


class TestGenerateEngineSubmodels:

    def test_submodel_and_cross_model_elements(self, two_region_sir):
        engine, _ = _generate(two_region_sir)
        assert "elements.r1__S" in engine
        assert "elements.r2__S" in engine
        assert "elements.migration_rate" in engine
        assert "elements.F_r1_to_r2" in engine


class TestGenerateEngineProcesses:

    def test_process_init_and_start_time(self, process_model):
        structure = inspect_model(process_model)
        translator = CodeTranslator(
            element_map=structure['element_map'],
            submodel_names=structure['submodel_names'],
        )
        translated = _build_translated_code(structure)
        process_names = set(structure.get('processes', {}).keys())
        for name, info in structure.get('processes', {}).items():
            source = info.get('source')
            if source:
                prefix = '__'.join(name.split('__')[:-1])
                r = translator.translate_process(
                    source, process_names=process_names, context_prefix=prefix)
                if r['success']:
                    info['js_body'] = r['javascript']

        engine = generate_js_engine(structure, translated)
        assert 'new Process' in engine
        assert 'function * (' in engine
        assert 'processes.push' in engine
        assert 'new Time(2)' in engine


class TestJavaScriptSimulationEngineClass:

    def test_constructor_and_generate(self, simple_sir):
        structure = inspect_model(simple_sir)
        translated = _build_translated_code(structure)
        engine_obj = JavaScriptSimulationEngine(structure, translated)
        assert engine_obj.model_structure is structure
        assert engine_obj.translated_code is translated
        assert isinstance(engine_obj.generate_engine(), str)


class TestGenerateEngineMinimal:

    def test_flow_with_no_dest(self, minimal_model):
        engine, _ = _generate(minimal_model)
        assert 'null' in engine
        assert "elements.Fx" in engine


class TestGenerateEngineWaitTypes:

    def test_date_and_condition_start_markers(self, wait_types_model):
        engine, _ = _generate(wait_types_model)
        assert 'DateMarker' in engine
        assert 'ConditionStart' in engine

    def test_helper_functions_present(self, wait_types_model):
        engine, _ = _generate(wait_types_model)
        for fn in ('wait_step', 'wait_date', 'wait_condition',
                   'wait_message', 'send_message',
                   'wait_any', 'wait_all', 'wait_sequence'):
            assert fn in engine, f'{fn} not found in engine'

    def test_message_infrastructure(self, wait_types_model):
        engine, _ = _generate(wait_types_model)
        assert 'messages' in engine
        assert 'MessageWait' in engine


class TestGenerateEngineFeatureModel:
    """Flow variants, sub-processes and Monte Carlo statistics."""

    @staticmethod
    def _engine(model):
        structure = inspect_model(model)
        return generate_js_engine(structure, translate_structure(structure))

    def test_flow_variants(self, feature_model):
        engine = self._engine(feature_model)
        assert "new Pool('leak__P'" in engine
        assert "new Pool('N', inputs.N !== undefined ? inputs.N : 0, true)" \
            in engine
        # discrete flow from the integer pool into the connected Sink pool
        assert 'elements.leak__P, elements.Sink, true' in engine
        assert ', 0.5, null, null)' in engine                       # variance
        assert '() => sim_context.sim_time <= 5, null)' in engine   # when
        assert ', null, 3)' in engine                                # limit

    def test_sub_processes(self, feature_model):
        engine = self._engine(feature_model)
        assert 'yield sub.call(1)' in engine
        assert 'sub.call(2).start()' in engine
        assert 'sub.call(3).start(wait_delay(1))' in engine

    def test_monte_carlo(self, feature_model, run_js):
        engine = self._engine(feature_model)
        out = run_js(engine + (
            "\nconst r = run_simulation_mc({}, {t_end: 10, dt: 1, reps: 20,"
            " interval: 50, outputs: ['A']})"
            "\nconsole.log(JSON.stringify(r.mc_outputs.A))"))
        assert len(out['median']) == 11
        assert all(lo <= m <= hi for lo, m, hi in
                   zip(out['p_low'], out['median'], out['p_high']))
        assert out['p_high'][-1] > out['p_low'][-1]  # stochastic spread
