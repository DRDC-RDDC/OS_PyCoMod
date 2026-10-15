"""Tests for pycomod.export.model_inspector."""

import pytest
from pycomod.export.model_inspector import inspect_model


class TestInspectModelBasic:
    """Tests with the simple SIR model."""

    def test_returns_all_required_keys(self, simple_sir):
        result = inspect_model(simple_sir)
        expected_keys = {
            'pools', 'parameters', 'equations', 'flows', 'processes',
            'outputs', 'si_outputs', 'run_params', 'element_map',
            'submodel_names', 'display_names',
        }
        assert expected_keys == set(result.keys())

    def test_pools(self, simple_sir):
        pools = inspect_model(simple_sir)['pools']
        assert set(pools.keys()) == {'S', 'I', 'R'}
        assert pools['S']['init_value'] == 950
        assert pools['I']['init_value'] == 50
        assert pools['R']['init_value'] == 0

        pool = pools['S']
        assert pool['name'] == 'S'
        assert pool['type'] in ('int', 'float')
        assert pool['is_vector'] is False
        assert pool['shape'] is None
        assert 'allow_negative' in pool

    def test_parameters(self, simple_sir):
        params = inspect_model(simple_sir)['parameters']
        assert params['b']['init_value'] == pytest.approx(0.3)
        assert params['g']['init_value'] == pytest.approx(0.1)

    def test_equations(self, simple_sir):
        equations = inspect_model(simple_sir)['equations']
        assert equations['N']['type'] == 'equation'
        assert equations['N']['func_info']['source'] is not None

    def test_flows(self, simple_sir):
        flows = inspect_model(simple_sir)['flows']
        assert flows['Fsi']['src'] == 'S'
        assert flows['Fsi']['dest'] == 'I'
        assert flows['Fir']['src'] == 'I'
        assert flows['Fir']['dest'] == 'R'
        assert flows['Fsi']['stochastic'] is True
        assert flows['Fir']['stochastic'] is True
        assert 'lambda' in flows['Fsi']['rate_func']['source']
        assert flows['Fsi']['rate_func']['is_lambda'] is True

    def test_metadata(self, simple_sir):
        result = inspect_model(simple_sir)
        assert result['outputs'] == ['S', 'I', 'R', 'N']
        assert result['si_outputs'] == []
        assert result['submodel_names'] == set()
        assert result['processes'] == {}

        em = result['element_map']
        assert em['S'] == 'pool'
        assert em['N'] == 'equation'
        assert em['b'] == 'parameter'
        assert em['Fsi'] == 'flow'

    def test_run_params(self, simple_sir):
        rp = inspect_model(simple_sir)['run_params']
        for key in ('dt', 'end', 'reps', 'date', 'tunit'):
            assert key in rp
        assert rp['dt'] > 0
        assert rp['end'] > 0


class TestInspectModelStepImpulse:

    def test_step_and_impulse_equations(self, sir_step_impulse):
        result = inspect_model(sir_step_impulse)
        equations = result['equations']

        eq_b = equations['b']
        assert eq_b['type'] == 'step'
        assert eq_b['values'] == [0.3, 0.05, 0.2]
        assert eq_b['times'] == [0, 30, 60]
        assert eq_b['default'] == 0.3

        eq_vax = equations['vax']
        assert eq_vax['type'] == 'impulse'
        assert eq_vax['values'] == [50, 100]
        assert eq_vax['times'] == [20, 45]

        assert 'b' in result['si_outputs']
        assert 'vax' in result['si_outputs']
        assert equations['N']['type'] == 'equation'


class TestInspectModelSubmodels:

    def test_flattened_elements(self, two_region_sir):
        result = inspect_model(two_region_sir)
        pools = result['pools']
        for prefix in ('r1', 'r2'):
            for var in ('S', 'I', 'R'):
                assert '%s__%s' % (prefix, var) in pools

        params = result['parameters']
        assert 'migration_rate' in params
        assert params['migration_rate']['init_value'] == pytest.approx(0.01)
        assert params['r1__b']['init_value'] == pytest.approx(0.3)

    def test_submodel_metadata(self, two_region_sir):
        result = inspect_model(two_region_sir)
        assert {'r1', 'r2'} <= result['submodel_names']
        assert result['display_names']['r1__S'] == 'r1.S'
        assert result['display_names']['r2__I'] == 'r2.I'

        outputs = result['outputs']
        for prefix in ('r1', 'r2'):
            for var in ('S', 'I', 'R'):
                assert '%s__%s' % (prefix, var) in outputs

    def test_cross_model_flow_and_element_map(self, two_region_sir):
        result = inspect_model(two_region_sir)
        flows = result['flows']
        assert flows['F_r1_to_r2']['src'] == 'r1__I'
        assert flows['F_r1_to_r2']['dest'] == 'r2__I'

        em = result['element_map']
        assert em['r1__S'] == 'pool'
        assert em['r1__Fsi'] == 'flow'
        assert em['r2__g'] == 'parameter'


class TestInspectModelProcesses:

    def test_processes(self, process_model):
        procs = inspect_model(process_model)['processes']
        assert 'attend' in procs and 'scheduler' in procs

        assert procs['attend']['start_type'] is None
        assert procs['scheduler']['start_type'] == 'time'
        assert procs['scheduler']['start_value'] == 2

        assert 'def attend' in procs['attend']['source']
        assert 'def scheduler' in procs['scheduler']['source']
        assert procs['attend']['priority'] == 0


class TestInspectModelMinimal:

    def test_single_pool_and_flow(self, minimal_model):
        result = inspect_model(minimal_model)
        assert result['pools']['X']['init_value'] == 10
        assert result['flows']['Fx']['src'] == 'X'
        assert result['flows']['Fx']['dest'] is None


class TestInspectModelWaitTypes:

    def test_date_start(self, wait_types_model):
        procs = inspect_model(wait_types_model)['processes']
        assert procs['p_date']['start_type'] == 'date'
        assert procs['p_date']['start_value'] == '2025-03-01'

    def test_condition_start(self, wait_types_model):
        procs = inspect_model(wait_types_model)['processes']
        assert procs['p_cond']['start_type'] == 'condition'
        assert 'A <= 50' in procs['p_cond']['start_value']

    def test_time_start_still_works(self, wait_types_model):
        procs = inspect_model(wait_types_model)['processes']
        assert procs['p_waits']['start_type'] == 'time'
        assert procs['p_waits']['start_value'] == 0
