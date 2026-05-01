"""Translates Python lambda functions to JavaScript."""

import re
from typing import Dict, Any, Optional


class CodeTranslator:
    def __init__(self, element_map: Dict[str, str] = None):
        self.element_map = element_map or {}

        self.numpy_to_js = {
            'np.sqrt': 'Math.sqrt',
            'np.pow': 'Math.pow',
            'np.exp': 'Math.exp',
            'np.log': 'Math.log',
            'np.log10': 'Math.log10',
            'np.abs': 'Math.abs',
            'np.floor': 'Math.floor',
            'np.ceil': 'Math.ceil',
            'np.round': 'Math.round',
            'np.min': 'Math.min',
            'np.max': 'Math.max',
            'np.sin': 'Math.sin',
            'np.cos': 'Math.cos',
            'np.tan': 'Math.tan',
            'np.asin': 'Math.asin',
            'np.acos': 'Math.acos',
            'np.atan': 'Math.atan',
            'np.atan2': 'Math.atan2',
            'np.pi': 'Math.PI',
            'np.e': 'Math.E',
        }

    def translate_lambda(self, source: str) -> Dict[str, Any]:
        result = {
            'python_source': source,
            'javascript': None,
            'success': False,
            'warnings': [],
            'errors': [],
        }

        try:
            source = source.strip()
            lambda_body = self._extract_lambda_body(source)
            if not lambda_body:
                result['errors'].append('Could not extract lambda body')
                return result

            result['javascript'] = self._translate_expression(lambda_body)
            result['success'] = True

        except Exception as e:
            result['errors'].append('Translation error: %s' % str(e))

        return result

    def _extract_lambda_body(self, source: str) -> Optional[str]:
        patterns = [
            r'lambda\s*:\s*([^,\)]+)',
            r'lambda\s+\w+\s*:\s*([^,\)]+)',
            r'lambda\s+\w+\s*,\s*\w+\s*:\s*([^,\)]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, source)
            if match:
                body = match.group(1)
                body = self._balance_parentheses(body, source[match.end():])
                return body.strip()

        return None

    def _balance_parentheses(self, initial_body: str, remaining: str) -> str:
        open_count = initial_body.count('(')
        close_count = initial_body.count(')')

        if open_count == close_count:
            return initial_body

        body = initial_body
        for char in remaining:
            if char == '(':
                open_count += 1
                body += char
            elif char == ')':
                close_count += 1
                body += char
                if open_count == close_count:
                    break
            elif char == ',' and open_count == close_count:
                break
            else:
                body += char

        return body

    def _translate_expression(self, expr: str) -> str:
        js_expr = expr

        js_expr = js_expr.replace('self.t()', 'sim_time')
        js_expr = js_expr.replace('self.date()', 'sim_date')
        js_expr = js_expr.replace('self.dt()', 'dt')

        for np_func, js_func in self.numpy_to_js.items():
            js_expr = js_expr.replace(np_func, js_func)

        js_expr = self._translate_power_operator(js_expr)
        js_expr = self._translate_integer_division(js_expr)

        js_expr = js_expr.replace(' and ', ' && ')
        js_expr = js_expr.replace(' or ', ' || ')
        js_expr = re.sub(r'\bnot\s+', '!', js_expr)

        js_expr = re.sub(r'self\.(\w+)\(\)', r'elements.\1.value', js_expr)

        protected_functions = [
            'sqrt', 'exp', 'log', 'log10', 'pow', 'floor', 'ceil', 'round',
            'min', 'max', 'sin', 'cos', 'tan', 'abs',
        ]

        def replace_element(match):
            name = match.group(1)
            if name in protected_functions:
                return match.group(0)
            if name in self.element_map:
                return 'elements.%s.value' % name
            return match.group(0)

        js_expr = re.sub(r'\b(\w+)\(\)', replace_element, js_expr)

        for elem_name in self.element_map.keys():
            pattern = r'(?<!elements\.)(?<!Math\.)(?<!\.)\b' + elem_name + r'\b(?!\.value)(?!\.)'
            js_expr = re.sub(pattern, 'elements.%s.value' % elem_name, js_expr)

        return js_expr

    def _translate_integer_division(self, expr: str) -> str:
        return re.sub(r'(\w+)\s*//\s*(\w+)', r'Math.floor(\1 / \2)', expr)

    def _translate_power_operator(self, expr: str) -> str:
        return re.sub(r'(\w+(?:\.\w+)?)\s*\*\*\s*(\w+(?:\.\w+)?)', r'Math.pow(\1, \2)', expr)
