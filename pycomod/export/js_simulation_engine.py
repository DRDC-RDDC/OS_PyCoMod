"""Generates JavaScript simulation engine code for browser execution."""

import re
from typing import Dict, Any
from .template_loader import get_loader
from .code_translator import CodeTranslator


class JavaScriptSimulationEngine:
    """Assemble the browser-side simulation engine for one model."""

    def __init__(
        self, model_structure: Dict[str, Any], translated_code: Dict[str, str]
    ):
        """Store the model structure and translated code."""
        self.model_structure = model_structure
        self.translated_code = translated_code
        self.template_loader = get_loader()

    def generate_engine(self) -> str:
        """Return the complete JavaScript engine source."""
        js_parts = [
            self.template_loader.load_js_template('header.js'),
            self.template_loader.load_js_template('element_classes.js'),
            self._generate_element_initialization(),
            self.template_loader.load_js_template('simulation_loop.js'),
            self.template_loader.load_js_template('public_api.js'),
        ]
        return '\n\n'.join(p.strip('\n') for p in js_parts) + '\n'

    def _generate_element_initialization(self) -> str:
        pools = self.model_structure['pools']
        parameters = self.model_structure['parameters']
        equations = self.model_structure.get('equations', {})
        flows = self.model_structure.get('flows', {})

        pool_init = []
        for name, info in pools.items():
            init_val = info['init_value']
            allow_neg = info.get('allow_negative', False)
            pool_init.append(
                "elements['%s'] = new Pool('%s', "
                "inputs['%s'] !== undefined ? inputs['%s'] : %s, %s)"
                % (name, name, name, name, init_val, str(allow_neg).lower())
            )

        param_init = []
        for name, info in parameters.items():
            init_val = info['init_value']
            param_init.append(
                "elements['%s'] = new Parameter('%s', "
                "inputs['%s'] !== undefined ? inputs['%s'] : %s)"
                % (name, name, name, name, init_val)
            )

        eq_init = []
        for name, info in equations.items():
            init_val = info['init_value']
            eq_type = info['type']

            if eq_type == 'step':
                default_vals = info['values']
                default_times = info['times']
                default_default = info['default']
                eq_init.append(
                    "elements['%s'] = new Step('%s', "
                    "_parse_csv(inputs['%s_values'], %s), "
                    "_parse_csv(inputs['%s_times'], %s), "
                    "inputs['%s_default'] !== undefined "
                    "? inputs['%s_default'] : %s)"
                    % (
                        name,
                        name,
                        name,
                        default_vals,
                        name,
                        default_times,
                        name,
                        name,
                        default_default,
                    )
                )
            elif eq_type == 'impulse':
                default_vals = info['values']
                default_times = info['times']
                eq_init.append(
                    "elements['%s'] = new Impulse('%s', "
                    "_parse_csv(inputs['%s_values'], %s), "
                    "_parse_csv(inputs['%s_times'], %s))"
                    % (name, name,
                       name, default_vals,
                       name, default_times)
                )
            elif eq_type == 'equation':
                js_expr = self.translated_code.get(name, '0')
                eq_init.append(
                    "elements['%s'] = new Equation('%s', %s, () => %s)"
                    % (name, name, init_val, js_expr)
                )

        flow_init = []
        for name, info in flows.items():
            src = info['src']
            dest = info['dest']
            discrete = info.get('discrete', False)
            stochastic = info.get('stochastic', False)
            variance_value = info.get('variance_value', None)
            js_expr = self.translated_code.get(name, '0')
            src_ref = "elements['%s']" % src if src else 'null'
            dest_ref = "elements['%s']" % dest if dest else 'null'
            variance_js = str(
                variance_value) if variance_value is not None else 'null'

            when_js = 'null'
            when_info = info.get('when')
            if when_info is not None:
                when_expr = self.translated_code.get(name + '__when', 'true')
                when_js = '() => %s' % when_expr

            limit_value = info.get('limit')
            limit_js = str(limit_value) if limit_value is not None else 'null'

            flow_init.append(
                "elements['%s'] = new Flow('%s', () => %s, "
                "%s, %s, %s, %s, %s, %s, %s)"
                % (
                    name,
                    name,
                    js_expr,
                    src_ref,
                    dest_ref,
                    str(discrete).lower(),
                    str(stochastic).lower(),
                    variance_js,
                    when_js,
                    limit_js,
                )
            )

        process_init = self._generate_process_initialization()

        # Generated lines sit under a 2-space-indented placeholder.
        def block(lines):
            return '\n  '.join('\n'.join(lines).split('\n'))

        rendered = self.template_loader.render_js_template(
            'element_initialization.js',
            {
                'POOL_INITIALIZATION': block(pool_init),
                'PARAMETER_INITIALIZATION': block(param_init),
                'EQUATION_INITIALIZATION': block(eq_init),
                'FLOW_INITIALIZATION': block(flow_init),
                'PROCESS_INITIALIZATION': block(process_init),
            }
        )
        return _standard_style(rendered)

    def _translate_condition_start(self, cond_source, process_name):
        prefix = '__'.join(process_name.split('__')[:-1])
        translator = CodeTranslator(
            self.model_structure.get('element_map', {}),
            self.model_structure.get('submodel_names', set()),
        )
        result = translator.translate_lambda(
            cond_source, context_prefix=prefix)
        if result['success']:
            return '() => %s' % result['javascript']
        return '() => false'

    def _generate_process_initialization(self):
        processes = self.model_structure.get('processes', {})
        lines = []
        for name, info in processes.items():
            start_js = 'null'
            start_type = info.get('start_type')
            start_value = info.get('start_value')
            if start_type == 'delay':
                start_js = 'new Delay(%s)' % start_value
            elif start_type == 'time':
                start_js = 'new Time(%s)' % start_value
            elif start_type == 'timestep':
                start_js = 'new Delay(%s * sim_context.dt)' % start_value
            elif start_type == 'date':
                start_js = 'new DateMarker("%s")' % start_value
            elif start_type == 'condition':
                cond_js = self._translate_condition_start(start_value, name)
                start_js = 'new ConditionStart(%s)' % cond_js

            js_body = info.get('js_body')
            if not js_body:
                continue
            priority = info.get('priority', 0)

            lines.append("const %s_routine = %s" % (name, js_body))
            lines.append(
                "const %s = new Process(%s_routine, "
                "{ start: %s, priority: %s, parent: sim_context })"
                % (name, name, start_js, priority)
            )
            lines.append("processes.push(%s)" % name)
            lines.append("")

        return lines


def _standard_style(js: str) -> str:
    """Tidy generated JS for StandardJS: dot notation, no extra blank lines."""
    js = re.sub(r"\b(elements|inputs)\['([A-Za-z_$][\w$]*)'\]", r"\1.\2", js)
    js = '\n'.join(line.rstrip() for line in js.split('\n'))
    js = re.sub(r'\n{3,}', '\n\n', js)
    js = re.sub(r'\{\n\n', '{\n', js)
    return re.sub(r'\n\n(\s*\})', r'\n\1', js)


def generate_js_engine(model_structure: Dict[str, Any],
                       translated_code: Dict[str, str]) -> str:
    """Return the JavaScript engine for a model structure."""
    engine = JavaScriptSimulationEngine(model_structure, translated_code)
    return engine.generate_engine()
