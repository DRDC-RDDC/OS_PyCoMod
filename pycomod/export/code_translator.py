"""Translates Python lambda functions and generator processes to JavaScript."""

import ast
import re
import textwrap
from typing import Dict, Any, Optional, Set, List


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

    # ------------------------------------------------------------------
    # Process (generator function) translation
    # ------------------------------------------------------------------

    def translate_process(self, source: str, process_names: Set[str] = None,
                          context_prefix: str = '') -> Dict[str, Any]:
        """Translate a Python generator function to a JavaScript generator.

        Parameters
        ----------
        source : str
            Full Python source of the process function (including ``def``).
        process_names : set of str
            Names of other processes in the model, so calls like
            ``attend_serial(n).start()`` can be recognised.
        context_prefix : str
            Sub-model prefix for resolving element names.

        Returns
        -------
        dict with keys ``javascript``, ``success``, ``errors``.
        """
        result = {
            'python_source': source,
            'javascript': None,
            'success': False,
            'errors': [],
        }

        try:
            # Strip decorator lines before parsing
            lines = source.splitlines()
            func_start = 0
            for i, line in enumerate(lines):
                stripped = line.lstrip()
                if stripped.startswith('def '):
                    func_start = i
                    break
            source = '\n'.join(lines[func_start:])
            source = textwrap.dedent(source)
            tree = ast.parse(source)

            func_node = None
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_node = node
                    break

            if func_node is None:
                result['errors'].append('No function definition found')
                return result

            visitor = _ProcessJSVisitor(
                element_map=self.element_map,
                submodel_names=self.submodel_names,
                process_names=process_names or set(),
                context_prefix=context_prefix,
                numpy_to_js=self.numpy_to_js,
            )
            js_body = visitor.translate_function(func_node)
            result['javascript'] = js_body
            result['success'] = True

        except Exception as e:
            result['errors'].append('Process translation error: %s' % str(e))

        return result


class _ProcessJSVisitor:
    """AST visitor that converts a Python generator function to JS."""

    def __init__(self, element_map, submodel_names, process_names,
                 context_prefix, numpy_to_js):
        self.element_map = element_map
        self.submodel_names = submodel_names
        self.process_names = process_names
        self.context_prefix = context_prefix
        self.numpy_to_js = numpy_to_js

    def translate_function(self, node: ast.FunctionDef) -> str:
        params = [arg.arg for arg in node.args.args if arg.arg != 'self']
        body_lines = []
        for stmt in node.body:
            body_lines.extend(self._visit_stmt(stmt, indent=1))
        body = '\n'.join(body_lines)
        return 'function*(%s) {\n%s\n}' % (', '.join(params), body)

    def _indent(self, level: int) -> str:
        return '    ' * level

    # ------------------------------------------------------------------
    # Statement visitors
    # ------------------------------------------------------------------

    def _visit_stmt(self, node, indent: int) -> List[str]:
        if isinstance(node, ast.Expr):
            expr_js = self._visit_expr(node.value)
            if isinstance(node.value, ast.Yield):
                return ['%syield %s;' % (self._indent(indent), self._yield_value(node.value))]
            return ['%s%s;' % (self._indent(indent), expr_js)]

        elif isinstance(node, ast.Assign):
            targets = [self._visit_expr(t) for t in node.targets]
            value = self._visit_expr(node.value)
            if isinstance(node.value, ast.Yield):
                return ['%s%s = yield %s;' % (self._indent(indent), targets[0], self._yield_value(node.value))]
            lines = []
            for t in targets:
                lines.append('%slet %s = %s;' % (self._indent(indent), t, value))
            return lines

        elif isinstance(node, ast.AugAssign):
            target = self._visit_expr(node.target)
            value = self._visit_expr(node.value)
            op = self._binop_symbol(node.op)
            return ['%s%s %s= %s;' % (self._indent(indent), target, op, value)]

        elif isinstance(node, ast.Return):
            if node.value is None:
                return ['%sreturn;' % self._indent(indent)]
            return ['%sreturn %s;' % (self._indent(indent), self._visit_expr(node.value))]

        elif isinstance(node, ast.If):
            lines = []
            test = self._visit_expr(node.test)
            lines.append('%sif (%s) {' % (self._indent(indent), test))
            for stmt in node.body:
                lines.extend(self._visit_stmt(stmt, indent + 1))
            if node.orelse:
                if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                    lines.append('%s} else' % self._indent(indent))
                    lines.extend(self._visit_stmt(node.orelse[0], indent))
                else:
                    lines.append('%s} else {' % self._indent(indent))
                    for stmt in node.orelse:
                        lines.extend(self._visit_stmt(stmt, indent + 1))
                    lines.append('%s}' % self._indent(indent))
            else:
                lines.append('%s}' % self._indent(indent))
            return lines

        elif isinstance(node, ast.While):
            lines = []
            test = self._visit_expr(node.test)
            lines.append('%swhile (%s) {' % (self._indent(indent), test))
            for stmt in node.body:
                lines.extend(self._visit_stmt(stmt, indent + 1))
            lines.append('%s}' % self._indent(indent))
            return lines

        elif isinstance(node, ast.For):
            target = self._visit_expr(node.target)
            iter_expr = self._visit_expr(node.iter)
            lines = []
            lines.append('%sfor (const %s of %s) {' % (self._indent(indent), target, iter_expr))
            for stmt in node.body:
                lines.extend(self._visit_stmt(stmt, indent + 1))
            lines.append('%s}' % self._indent(indent))
            return lines

        elif isinstance(node, ast.Break):
            return ['%sbreak;' % self._indent(indent)]

        elif isinstance(node, ast.Continue):
            return ['%scontinue;' % self._indent(indent)]

        elif isinstance(node, ast.Pass):
            return []

        return ['%s/* untranslated: %s */' % (self._indent(indent), type(node).__name__)]

    # ------------------------------------------------------------------
    # Expression visitors
    # ------------------------------------------------------------------

    def _visit_expr(self, node) -> str:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return 'true' if node.value else 'false'
            return repr(node.value)

        elif isinstance(node, ast.Name):
            return self._resolve_element_name(node.id)

        elif isinstance(node, ast.BinOp):
            left = self._visit_expr(node.left)
            right = self._visit_expr(node.right)
            op = self._binop_symbol(node.op)
            if isinstance(node.op, ast.Pow):
                return 'Math.pow(%s, %s)' % (left, right)
            if isinstance(node.op, ast.FloorDiv):
                return 'Math.floor(%s / %s)' % (left, right)
            return '(%s %s %s)' % (left, op, right)

        elif isinstance(node, ast.UnaryOp):
            operand = self._visit_expr(node.operand)
            if isinstance(node.op, ast.Not):
                return '!(%s)' % operand
            elif isinstance(node.op, ast.USub):
                return '(-%s)' % operand
            elif isinstance(node.op, ast.UAdd):
                return '(+%s)' % operand
            return operand

        elif isinstance(node, ast.BoolOp):
            op = ' && ' if isinstance(node.op, ast.And) else ' || '
            parts = [self._visit_expr(v) for v in node.values]
            return '(%s)' % op.join(parts)

        elif isinstance(node, ast.Compare):
            parts = [self._visit_expr(node.left)]
            for op, comparator in zip(node.ops, node.comparators):
                parts.append(self._cmpop_symbol(op))
                parts.append(self._visit_expr(comparator))
            return '(%s)' % ' '.join(parts)

        elif isinstance(node, ast.Call):
            return self._visit_call(node)

        elif isinstance(node, ast.Attribute):
            return self._visit_attribute(node)

        elif isinstance(node, ast.Subscript):
            value = self._visit_expr(node.value)
            slice_val = self._visit_expr(node.slice)
            return '%s[%s]' % (value, slice_val)

        elif isinstance(node, ast.IfExp):
            test = self._visit_expr(node.test)
            body = self._visit_expr(node.body)
            orelse = self._visit_expr(node.orelse)
            return '(%s ? %s : %s)' % (test, body, orelse)

        elif isinstance(node, ast.Yield):
            return 'yield %s' % self._yield_value(node)

        elif isinstance(node, ast.Tuple) or isinstance(node, ast.List):
            elts = [self._visit_expr(e) for e in node.elts]
            return '[%s]' % ', '.join(elts)

        return '/* ? %s */' % type(node).__name__

    def _yield_value(self, node: ast.Yield) -> str:
        if node.value is None:
            return ''
        return self._visit_expr(node.value)

    def _visit_call(self, node: ast.Call) -> str:
        args = [self._visit_expr(a) for a in node.args]

        # self.wait_delay(x) → wait_delay(x)
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id == 'self':
                method = node.func.attr
                if method == 'wait_delay':
                    return 'wait_delay(%s)' % ', '.join(args)
                elif method == 'wait_time':
                    return 'wait_time(%s)' % ', '.join(args)
                elif method == 't':
                    return 'sim_context.sim_time'
                elif method == 'dt':
                    return 'sim_context.dt'

        # pool.add(x) / pool.remove(x)
        if isinstance(node.func, ast.Attribute):
            obj = node.func.value
            method = node.func.attr
            if isinstance(obj, ast.Name) and method in ('add', 'remove'):
                el_ref = self._resolve_element_name(obj.id)
                if method == 'add':
                    return '(%s += %s)' % (el_ref, args[0])
                else:
                    return '(%s -= %s)' % (el_ref, args[0])
            # process_name(args).start()
            if method == 'start' and isinstance(obj, ast.Call):
                inner = self._visit_call(obj)
                return '%s.start()' % inner

        # other_process(n) → other_process.call(n)
        if isinstance(node.func, ast.Name) and node.func.id in self.process_names:
            return '%s.call(%s)' % (node.func.id, ', '.join(args))

        # Built-in function mapping
        func_name = self._visit_expr(node.func)
        builtin_map = {
            'round': 'Math.round',
            'int': 'Math.floor',
            'float': 'Number',
            'abs': 'Math.abs',
            'min': 'Math.min',
            'max': 'Math.max',
            'len': '__len__',
        }
        for py_name, js_name in builtin_map.items():
            if func_name == py_name:
                if js_name == '__len__':
                    return '%s.length' % args[0] if args else '0'
                return '%s(%s)' % (js_name, ', '.join(args))

        # numpy
        for np_func, js_func in self.numpy_to_js.items():
            if func_name == np_func.replace('np.', 'np_'):
                return '%s(%s)' % (js_func, ', '.join(args))

        return '%s(%s)' % (func_name, ', '.join(args))

    def _visit_attribute(self, node: ast.Attribute) -> str:
        # self.X() style references handled in _visit_call
        if isinstance(node.value, ast.Name) and node.value.id == 'self':
            return self._resolve_element_name(node.attr)
        value = self._visit_expr(node.value)
        return '%s.%s' % (value, node.attr)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_element_name(self, name: str) -> str:
        if self.context_prefix:
            prefixed = self.context_prefix + '__' + name
            if prefixed in self.element_map:
                return "elements['%s'].value" % prefixed
        if name in self.element_map:
            return "elements['%s'].value" % name
        return name

    def _binop_symbol(self, op) -> str:
        ops = {
            ast.Add: '+', ast.Sub: '-', ast.Mult: '*', ast.Div: '/',
            ast.Mod: '%', ast.Pow: '**', ast.FloorDiv: '//',
            ast.BitAnd: '&', ast.BitOr: '|', ast.BitXor: '^',
            ast.LShift: '<<', ast.RShift: '>>',
        }
        return ops.get(type(op), '?')

    def _cmpop_symbol(self, op) -> str:
        ops = {
            ast.Eq: '===', ast.NotEq: '!==', ast.Lt: '<', ast.LtE: '<=',
            ast.Gt: '>', ast.GtE: '>=',
        }
        return ops.get(type(op), '?')
