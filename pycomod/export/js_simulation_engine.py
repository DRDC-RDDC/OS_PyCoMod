"""Generates JavaScript simulation engine code for browser execution."""

from typing import Dict, Any
from .template_loader import get_loader


class JavaScriptSimulationEngine:
    def __init__(self, model_structure: Dict[str, Any], translated_code: Dict[str, str]):
        self.model_structure = model_structure
        self.translated_code = translated_code
        self.template_loader = get_loader()

    def generate_engine(self) -> str:
        js_parts = [
            self.template_loader.load_js_template('header.js'),
            self.template_loader.load_js_template('element_classes.js'),
            self._generate_element_initialization(),
            self.template_loader.load_js_template('simulation_loop.js'),
            self.template_loader.load_js_template('public_api.js'),
        ]
        return '\n\n'.join(js_parts)

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
                "    elements.%s = new Pool('%s', inputs.%s !== undefined ? inputs.%s : %s, %s);"
                % (name, name, name, name, init_val, str(allow_neg).lower())
            )

        param_init = []
        for name, info in parameters.items():
            init_val = info['init_value']
            param_init.append(
                "    elements.%s = new Parameter('%s', inputs.%s !== undefined ? inputs.%s : %s);"
                % (name, name, name, name, init_val)
            )

        eq_init = []
        for name, info in equations.items():
            init_val = info['init_value']
            eq_type = info['type']

            if eq_type == 'equation':
                js_expr = self.translated_code.get(name, '0')
                eq_init.append(
                    "    elements.%s = new Equation('%s', %s, () => %s);"
                    % (name, name, init_val, js_expr)
                )
            else:
                eq_init.append(
                    "    elements.%s = new Equation('%s', %s, () => 0);"
                    % (name, name, init_val)
                )

        flow_init = []
        for name, info in flows.items():
            src = info['src']
            dest = info['dest']
            discrete = info.get('discrete', False)
            js_expr = self.translated_code.get(name, '0')
            src_ref = 'elements.%s' % src if src else 'null'
            dest_ref = 'elements.%s' % dest if dest else 'null'
            flow_init.append(
                "    elements.%s = new Flow('%s', () => %s, %s, %s, %s);"
                % (name, name, js_expr, src_ref, dest_ref, str(discrete).lower())
            )

        return self.template_loader.render_js_template(
            'element_initialization.js',
            {
                'POOL_INITIALIZATION': '\n'.join(pool_init),
                'PARAMETER_INITIALIZATION': '\n'.join(param_init),
                'EQUATION_INITIALIZATION': '\n'.join(eq_init),
                'FLOW_INITIALIZATION': '\n'.join(flow_init),
            }
        )


def generate_js_engine(model_structure: Dict[str, Any],
                       translated_code: Dict[str, str]) -> str:
    engine = JavaScriptSimulationEngine(model_structure, translated_code)
    return engine.generate_engine()
