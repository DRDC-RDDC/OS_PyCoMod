"""Tests for pycomod.export.code_translator."""

import pytest
from pycomod.export.code_translator import CodeTranslator


@pytest.fixture
def translator():
    element_map = {
        'S': 'pool', 'I': 'pool', 'R': 'pool',
        'N': 'equation', 'b': 'parameter', 'g': 'parameter',
        'Fsi': 'flow', 'Fir': 'flow',
    }
    return CodeTranslator(element_map=element_map)


@pytest.fixture
def submodel_translator():
    element_map = {
        'r1__S': 'pool', 'r1__I': 'pool', 'r1__R': 'pool',
        'r1__N': 'equation', 'r1__b': 'parameter', 'r1__g': 'parameter',
        'r2__S': 'pool', 'r2__I': 'pool', 'r2__R': 'pool',
        'r2__N': 'equation', 'r2__b': 'parameter', 'r2__g': 'parameter',
        'migration_rate': 'parameter',
        'F_r1_to_r2': 'flow',
    }
    return CodeTranslator(element_map=element_map, submodel_names={'r1', 'r2'})


@pytest.fixture
def process_translator():
    element_map = {
        'W': 'pool', 'C': 'pool', 'P': 'pool', 'F': 'pool',
        'duration': 'parameter', 'passRate': 'parameter',
        'maxLoad': 'parameter', 'minLoad': 'parameter',
        'startInt': 'parameter',
    }
    return CodeTranslator(element_map=element_map)


class TestTranslateLambdaBasic:

    def test_element_references_and_arithmetic(self, translator):
        result = translator.translate_lambda("lambda: b * S * I / N")
        assert result['success'] is True
        js = result['javascript']
        for el in ('b', 'S', 'N'):
            assert "elements['%s'].value" % el in js

        assert 'python_source' in result
        assert 'warnings' in result
        assert 'errors' in result

    def test_constant_lambda(self):
        t = CodeTranslator()
        result = t.translate_lambda("lambda: 42")
        assert result['success'] is True
        assert '42' in result['javascript']

    def test_self_accessors_and_callable_elements(self, translator):
        r1 = translator.translate_lambda("lambda: self.t() * b")
        assert r1['success'] and 'sim_time' in r1['javascript']

        r2 = translator.translate_lambda("lambda: self.dt() * g")
        assert r2['success'] and 'dt' in r2['javascript']

        r3 = translator.translate_lambda("lambda: self.S()")
        assert r3['success'] and "elements['S'].value" in r3['javascript']

        r4 = translator.translate_lambda("lambda: S()")
        assert r4['success'] and "elements['S'].value" in r4['javascript']


class TestTranslateLambdaOperators:

    def test_math_operators(self, translator):
        r1 = translator.translate_lambda("lambda: S ** 2")
        assert r1['success'] and 'Math.pow' in r1['javascript']

        r2 = translator.translate_lambda("lambda: S // 10")
        assert r2['success'] and 'Math.floor' in r2['javascript']

    def test_logical_operators(self, translator):
        r1 = translator.translate_lambda("lambda: 1 if S and I else 0")
        assert r1['success'] and '&&' in r1['javascript']

        r2 = translator.translate_lambda("lambda: 1 if S or I else 0")
        assert r2['success'] and '||' in r2['javascript']

        r3 = translator.translate_lambda("lambda: 1 if not S else 0")
        assert r3['success'] and '!' in r3['javascript']


class TestTranslateLambdaNumpy:

    def test_numpy_functions_and_constants(self, translator):
        r1 = translator.translate_lambda("lambda: np.sqrt(S)")
        assert r1['success'] and 'Math.sqrt' in r1['javascript']

        r2 = translator.translate_lambda("lambda: np.exp(b)")
        assert r2['success'] and 'Math.exp' in r2['javascript']

        r3 = translator.translate_lambda("lambda: np.pi * S")
        assert r3['success'] and 'Math.PI' in r3['javascript']


class TestTranslateLambdaSubmodels:

    def test_dotted_and_prefix_resolution(self, submodel_translator):
        r1 = submodel_translator.translate_lambda("lambda: r1.I")
        assert r1['success'] and "elements['r1__I'].value" in r1['javascript']

        r2 = submodel_translator.translate_lambda("lambda: self.r1.S")
        assert r2['success'] and "elements['r1__S'].value" in r2['javascript']

        r3 = submodel_translator.translate_lambda(
            "lambda: S + I + R", context_prefix='r1')
        assert r3['success']
        for el in ('r1__S', 'r1__I', 'r1__R'):
            assert "elements['%s'].value" % el in r3['javascript']


class TestTranslateLambdaErrors:

    def test_invalid_inputs(self, translator):
        r1 = translator.translate_lambda("def foo(): return 1")
        assert r1['success'] is False and len(r1['errors']) > 0

        r2 = translator.translate_lambda("")
        assert r2['success'] is False


class TestTranslateProcess:

    def test_generator_with_pool_ops(self, process_translator):
        source = """
def attend(n):
    W.remove(n)
    C.add(n)
    yield self.wait_delay(duration)
    C.remove(n)
"""
        result = process_translator.translate_process(source)
        assert result['success'] is True
        js = result['javascript']
        assert 'function*' in js
        assert 'yield' in js
        assert 'wait_delay' in js
        assert '-=' in js
        assert '+=' in js

    def test_wait_types(self, process_translator):
        r1 = process_translator.translate_process("""
def proc():
    yield self.wait_delay(10)
""")
        assert r1['success'] and 'wait_delay(10)' in r1['javascript']

        r2 = process_translator.translate_process("""
def proc():
    yield self.wait_time(5)
""")
        assert r2['success'] and 'wait_time(5)' in r2['javascript']

    def test_control_flow(self, process_translator):
        r1 = process_translator.translate_process("""
def scheduler():
    while True:
        yield self.wait_delay(10)
""")
        assert r1['success'] and 'while (true)' in r1['javascript']

        r2 = process_translator.translate_process("""
def proc():
    if W >= 10:
        W.remove(10)
    yield self.wait_delay(1)
""")
        assert r2['success'] and 'if (' in r2['javascript']

        r3 = process_translator.translate_process("""
def proc():
    for x in items:
        yield self.wait_delay(x)
""")
        assert r3['success'] and 'for (const' in r3['javascript']

    def test_process_calls_other_process(self, process_translator):
        result = process_translator.translate_process("""
def scheduler():
    attend(10).start()
    yield self.wait_delay(5)
""", process_names={'attend', 'scheduler'})
        assert result['success'] is True
        assert 'attend.call(10)' in result['javascript']
        assert '.start()' in result['javascript']

    def test_builtins(self, process_translator):
        r1 = process_translator.translate_process("""
def proc(n):
    x = round(n * 0.8)
    y = min(10, 20)
    z = max(5, 3)
    w = int(W)
    yield self.wait_delay(1)
""")
        assert r1['success']
        js = r1['javascript']
        assert 'Math.round' in js
        assert 'Math.min' in js
        assert 'Math.max' in js
        assert 'Math.floor' in js

    def test_comparison_and_equality(self, process_translator):
        r1 = process_translator.translate_process("""
def proc():
    if W >= 10:
        pass
    if W == 0:
        pass
    yield self.wait_delay(1)
""")
        assert r1['success']
        assert '>=' in r1['javascript']
        assert '===' in r1['javascript']

    def test_assignments(self, process_translator):
        result = process_translator.translate_process("""
def proc():
    x = 5
    x += 5
    yield self.wait_delay(x)
""")
        assert result['success']
        assert 'let x = 5' in result['javascript']
        assert '+= 5' in result['javascript']

    def test_return_break_continue(self, process_translator):
        r1 = process_translator.translate_process("""
def proc():
    return
""")
        assert r1['success'] and 'return;' in r1['javascript']

        r2 = process_translator.translate_process("""
def proc():
    while True:
        if W == 0:
            break
        yield self.wait_delay(1)
        continue
""")
        assert r2['success']
        assert 'break;' in r2['javascript']
        assert 'continue;' in r2['javascript']

    def test_boolean_and_ternary(self, process_translator):
        result = process_translator.translate_process("""
def proc():
    x = True
    y = False
    z = 10 if W > 5 else 0
    yield self.wait_delay(1)
""")
        assert result['success']
        js = result['javascript']
        assert 'true' in js
        assert 'false' in js
        assert '?' in js and ':' in js

    def test_math_ops_in_process(self, process_translator):
        result = process_translator.translate_process("""
def proc():
    x = W ** 2
    y = W // 3
    yield self.wait_delay(1)
""")
        assert result['success']
        assert 'Math.pow' in result['javascript']
        assert 'Math.floor' in result['javascript']

    def test_decorators_stripped(self, process_translator):
        r1 = process_translator.translate_process("""@self.process
def attend(n):
    yield self.wait_delay(5)
""")
        assert r1['success'] and 'function*' in r1['javascript']

        r2 = process_translator.translate_process(
            """@self.process(start=self.wait_time(2))
def scheduler():
    yield self.wait_delay(10)
"""
        )
        assert r2['success'] and 'function*' in r2['javascript']

    def test_element_and_sim_references(self, process_translator):
        result = process_translator.translate_process("""
def proc():
    x = W + C
    t = self.t()
    step = self.dt()
    yield self.wait_delay(1)
""")
        assert result['success']
        js = result['javascript']
        assert "elements['W'].value" in js
        assert "elements['C'].value" in js
        assert 'sim_context.sim_time' in js
        assert 'sim_context.dt' in js

    def test_unary_and_boolean_ops(self, process_translator):
        result = process_translator.translate_process("""
def proc():
    if not W:
        pass
    x = -W
    if W > 0 and C < 10:
        pass
    yield self.wait_delay(1)
""")
        assert result['success']
        js = result['javascript']
        assert '!(' in js
        assert '(-' in js
        assert '&&' in js

    def test_no_function_found(self, process_translator):
        result = process_translator.translate_process("x = 5")
        assert result['success'] is False and len(result['errors']) > 0

    def test_list_subscript_pass(self, process_translator):
        result = process_translator.translate_process("""
def proc():
    x = [1, 2, 3]
    y = items[0]
    pass
""")
        assert result['success']
        assert '[1, 2, 3]' in result['javascript']
        assert 'items[0]' in result['javascript']

    def test_if_elif_else(self, process_translator):
        result = process_translator.translate_process("""
def proc():
    if W > 10:
        x = 1
    elif W > 5:
        x = 2
    else:
        x = 3
    yield self.wait_delay(1)
""")
        assert result['success']
        assert (
            '} else {' in result['javascript']
            or '} else' in result['javascript']
        )


class TestCodeTranslatorInit:

    def test_defaults_and_custom_map(self):
        t = CodeTranslator()
        assert t.element_map == {}
        assert t.submodel_names == set()
        assert t.numpy_to_js['np.sqrt'] == 'Math.sqrt'

        t2 = CodeTranslator(element_map={'X': 'pool'})
        assert t2.element_map == {'X': 'pool'}


class TestTranslateProcessNewWaitTypes:
    """Tests for all new wait type translations in process bodies."""

    def test_wait_step(self, process_translator):
        r = process_translator.translate_process("""
def proc():
    yield self.wait_step(5)
""")
        assert r['success'] and 'wait_step(5)' in r['javascript']

    def test_wait_sim_start(self, process_translator):
        r = process_translator.translate_process("""
def proc():
    yield self.wait_sim_start()
""")
        assert r['success'] and 'wait_sim_start()' in r['javascript']

    def test_wait_date(self, process_translator):
        r = process_translator.translate_process("""
def proc():
    yield self.wait_date("2025-06-15")
""")
        assert r['success'] and 'wait_date(' in r['javascript']

    def test_wait_condition(self, process_translator):
        r = process_translator.translate_process("""
def proc():
    yield self.wait_condition(lambda: W > 10)
""")
        assert r['success']
        js = r['javascript']
        assert 'wait_condition(' in js
        assert '=>' in js

    def test_send_and_wait_message(self, process_translator):
        r = process_translator.translate_process("""
def proc():
    self.send_message("go", 5)
    val = yield self.wait_message("go")
""")
        assert r['success']
        js = r['javascript']
        assert 'send_message(' in js
        assert 'wait_message(' in js
        assert 'let val = yield' in js

    def test_wait_any(self, process_translator):
        r = process_translator.translate_process("""
def proc():
    yield self.wait_any(self.wait_delay(10), self.wait_delay(20))
""")
        assert r['success'] and 'wait_any(' in r['javascript']

    def test_wait_all(self, process_translator):
        r = process_translator.translate_process("""
def proc():
    yield self.wait_all(self.wait_delay(5), self.wait_delay(8))
""")
        assert r['success'] and 'wait_all(' in r['javascript']

    def test_wait_sequence(self, process_translator):
        r = process_translator.translate_process("""
def proc():
    yield self.wait_sequence(self.wait_delay(3), self.wait_delay(4))
""")
        assert r['success'] and 'wait_sequence(' in r['javascript']
