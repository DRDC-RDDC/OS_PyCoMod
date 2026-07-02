"""Translates Python lambda functions to JavaScript."""

import re
from typing import Dict, Any, Optional, Set


class CodeTranslator:
    def __init__(self, element_map: Dict[str, str] = None,
                 submodel_names: Set[str] = None):
        self.element_map = element_map or {}
        self.submodel_names = submodel_names or set()

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

    def translate_lambda(self, source: str,
                         context_prefix: str = '') -> Dict[str, Any]:
        """Translate a Python lambda to JavaScript.

        Parameters
        ----------
        source : str
            Python source containing the lambda.
        context_prefix : str
            The ``__``-separated prefix of the element this lambda belongs
            to.  For example, if translating the equation ``r1__N``, pass
            ``"r1"`` so that bare names like ``S`` resolve to ``r1__S``.
        """
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

            result['javascript'] = self._translate_expression(
                lambda_body, context_prefix)
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

    def _resolve_name(self, bare_name: str, context_prefix: str) -> Optional[str]:
        """Resolve a bare name to a flat element-map key.

        Tries ``context_prefix + '__' + bare_name`` first, then falls
        back to the bare name itself.
        """
        if context_prefix:
            prefixed = context_prefix + '__' + bare_name
            if prefixed in self.element_map:
                return prefixed
        if bare_name in self.element_map:
            return bare_name
        return None

    def _translate_expression(self, expr: str,
                              context_prefix: str = '') -> str:
        js_expr = expr

        # --- built-in time accessors ---
        js_expr = js_expr.replace('self.t()', 'sim_time')
        js_expr = js_expr.replace('self.date()', 'sim_date')
        js_expr = js_expr.replace('self.dt()', 'dt')

        # --- numpy → Math ---
        for np_func, js_func in self.numpy_to_js.items():
            js_expr = js_expr.replace(np_func, js_func)

        js_expr = self._translate_power_operator(js_expr)
        js_expr = self._translate_integer_division(js_expr)

        # --- Python logical operators ---
        js_expr = js_expr.replace(' and ', ' && ')
        js_expr = js_expr.replace(' or ', ' || ')
        js_expr = re.sub(r'\bnot\s+', '!', js_expr)

        # --- sub-model dotted references: self.m.P  /  m.P  /  m.P() ---
        js_expr = self._translate_submodel_references(js_expr)

        # --- self.element() references ---
        def _replace_self_ref(match):
            name = match.group(1)
            if name in self.submodel_names:
                return match.group(0)
            resolved = self._resolve_name(name, context_prefix)
            if resolved is not None:
                return "elements['%s'].value" % resolved
            return "elements['%s'].value" % name

        js_expr = re.sub(r'self\.(\w+)\(\)', _replace_self_ref, js_expr)

        # --- callable element references: P() ---
        protected_functions = {
            'sqrt', 'exp', 'log', 'log10', 'pow', 'floor', 'ceil', 'round',
            'min', 'max', 'sin', 'cos', 'tan', 'abs',
        }

        def replace_element(match):
            name = match.group(1)
            if name in protected_functions:
                return match.group(0)
            resolved = self._resolve_name(name, context_prefix)
            if resolved is not None:
                return "elements['%s'].value" % resolved
            return match.group(0)

        js_expr = re.sub(r'\b(\w+)\(\)', replace_element, js_expr)

        # --- bare name references ---
        # Build a priority-ordered mapping: context-local names first, then
        # root-level names.
        bare_replacements: Dict[str, str] = {}
        if context_prefix:
            cp = context_prefix + '__'
            for flat_name in self.element_map:
                if flat_name.startswith(cp):
                    local = flat_name[len(cp):]
                    if '__' not in local:
                        bare_replacements[local] = flat_name
        for flat_name in self.element_map:
            if '__' not in flat_name and flat_name not in bare_replacements:
                bare_replacements[flat_name] = flat_name

        for local_name, flat_name in bare_replacements.items():
            pattern = (r"(?<!elements\[')(?<!Math\.)(?<!\.)\b"
                       + re.escape(local_name)
                       + r"\b(?!\.value)(?!\.)")
            js_expr = re.sub(pattern,
                             "elements['%s'].value" % flat_name,
                             js_expr)

        return js_expr

    def _translate_submodel_references(self, expr: str) -> str:
        """Translate ``self.m.P``, ``m.P``, or ``m.P()`` to ``elements['m__P'].value``."""
        if not self.submodel_names:
            return expr

        sm_pattern = '|'.join(
            re.escape(n)
            for n in sorted(self.submodel_names, key=len, reverse=True)
        )
        pattern = r'(?:self\.)?\b(' + sm_pattern + r')((?:\.\w+)+)(?:\(\))?'

        def _replace(match):
            chain = match.group(1) + match.group(2)
            flat_name = chain.replace('.', '__')
            if flat_name in self.element_map:
                return "elements['%s'].value" % flat_name
            return match.group(0)

        return re.sub(pattern, _replace, expr)

    def _translate_integer_division(self, expr: str) -> str:
        return re.sub(r'(\w+)\s*//\s*(\w+)', r'Math.floor(\1 / \2)', expr)

    def _translate_power_operator(self, expr: str) -> str:
        return re.sub(r'(\w+(?:\.\w+)?)\s*\*\*\s*(\w+(?:\.\w+)?)',
                      r'Math.pow(\1, \2)', expr)
