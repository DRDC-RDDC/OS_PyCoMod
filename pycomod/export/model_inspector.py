"""Model inspection utilities with sub-model support.

Compatible with Bokeh 2.4.1 and Python 3.9.7.
"""

import inspect
from typing import Dict, Any, Optional, Set, List
import numpy as np

from ..elements import Pool, Parameter, Equation, Flow, Step, Impulse, VirtualBuildingBlock, Process, Delay, Time, TimeStep, Date
from ..model import Model


def inspect_model(model: Model) -> Dict[str, Any]:
    """Extract model structure including sub-models, flattened into a single namespace.

    Sub-model elements are prefixed with the sub-model variable name(s)
    separated by ``__``.  For example, sub-model ``m``'s pool ``P`` becomes
    ``m__P``; nested ``m1.m2.P`` becomes ``m1__m2__P``.

    Returns a dict with keys: pools, parameters, equations, flows,
    outputs, si_outputs, run_params, element_map, submodel_names,
    display_names.
    """
    init_data = model._get_init_df()

    run_df = init_data['run']
    run_params = {
        't': _safe_scalar(run_df['t'].iloc[0]),
        'date': str(run_df['date'].iloc[0]),
        'tunit': str(run_df['tunit'].iloc[0]),
        'dt': _safe_scalar(run_df['dt'].iloc[0]),
        'end': _safe_scalar(run_df['end'].iloc[0]),
        'reps': int(run_df['reps'].iloc[0]),
    }

    identity_map = _build_identity_map(model, '')

    pools: Dict[str, Any] = {}
    parameters: Dict[str, Any] = {}
    equations: Dict[str, Any] = {}
    flows: Dict[str, Any] = {}
    element_map: Dict[str, str] = {}
    submodel_names: Set[str] = set()
    display_names: Dict[str, str] = {}

    _collect_elements_recursive(
        model, '', identity_map,
        pools, parameters, equations, flows,
        element_map, submodel_names, display_names,
    )

    outputs = _flatten_outputs(model, '')
    si_outputs = [name for name, info in equations.items()
                  if info['type'] in ('step', 'impulse')]

    processes = _collect_processes(model, '')

    return {
        'pools': pools,
        'parameters': parameters,
        'equations': equations,
        'flows': flows,
        'processes': processes,
        'outputs': outputs,
        'si_outputs': si_outputs,
        'run_params': run_params,
        'element_map': element_map,
        'submodel_names': submodel_names,
        'display_names': display_names,
    }


# ---------------------------------------------------------------------------
# Identity map: id(obj) -> qualified flat name
# ---------------------------------------------------------------------------

def _build_identity_map(model: Model, prefix: str) -> Dict[int, str]:
    """Recursively map ``id(obj)`` to qualified flat name for every element."""
    result: Dict[int, str] = {}
    available = getattr(model, '_available', {})

    for name, obj in available.items():
        if name.startswith('_'):
            continue
        flat = (prefix + '__' + name) if prefix else name

        if isinstance(obj, Model):
            result.update(_build_identity_map(obj, flat))
        elif isinstance(obj, VirtualBuildingBlock):
            target = getattr(obj, '_target', None)
            if target is not None:
                result[id(target)] = flat
            result[id(obj)] = flat
        elif hasattr(obj, 'value'):
            result[id(obj)] = flat

    return result


def _find_name_by_identity(element, identity_map: Dict[int, str]) -> Optional[str]:
    if element is None:
        return None
    if isinstance(element, VirtualBuildingBlock):
        target = getattr(element, '_target', None)
        if target is not None:
            name = identity_map.get(id(target))
            if name is not None:
                return name
    return identity_map.get(id(element))


# ---------------------------------------------------------------------------
# Recursive element collection
# ---------------------------------------------------------------------------

def _collect_elements_recursive(
    model: Model,
    prefix: str,
    identity_map: Dict[int, str],
    pools: Dict[str, Any],
    parameters: Dict[str, Any],
    equations: Dict[str, Any],
    flows: Dict[str, Any],
    element_map: Dict[str, str],
    submodel_names: Set[str],
    display_names: Dict[str, str],
):
    available = getattr(model, '_available', {})

    for name, obj in available.items():
        if name.startswith('_'):
            continue

        flat = (prefix + '__' + name) if prefix else name
        dotted = flat.replace('__', '.')

        if isinstance(obj, Model):
            submodel_names.add(name)
            _collect_elements_recursive(
                obj, flat, identity_map,
                pools, parameters, equations, flows,
                element_map, submodel_names, display_names,
            )

        elif isinstance(obj, Pool):
            pools[flat] = _make_pool_entry(flat, obj(), obj)
            element_map[flat] = 'pool'
            if flat != dotted:
                display_names[flat] = dotted

        elif isinstance(obj, Parameter):
            parameters[flat] = _make_entry(flat, obj())
            element_map[flat] = 'parameter'
            if flat != dotted:
                display_names[flat] = dotted

        elif isinstance(obj, Step):
            equations[flat] = _make_step_entry(flat, obj)
            element_map[flat] = 'equation'
            if flat != dotted:
                display_names[flat] = dotted

        elif isinstance(obj, Impulse):
            equations[flat] = _make_impulse_entry(flat, obj)
            element_map[flat] = 'equation'
            if flat != dotted:
                display_names[flat] = dotted

        elif isinstance(obj, Equation):
            equations[flat] = _make_equation_entry(flat, obj, 'equation')
            element_map[flat] = 'equation'
            if flat != dotted:
                display_names[flat] = dotted

        elif isinstance(obj, Flow):
            flows[flat] = _make_flow_entry(flat, obj, identity_map)
            element_map[flat] = 'flow'
            if flat != dotted:
                display_names[flat] = dotted


# ---------------------------------------------------------------------------
# Output flattening
# ---------------------------------------------------------------------------

def _flatten_outputs(model: Model, prefix: str) -> List[str]:
    """Expand sub-model entries in the output list into flat element names."""
    available = getattr(model, '_available', {})
    result: List[str] = []

    for name in (model.out or []):
        flat = (prefix + '__' + name) if prefix else name
        obj = available.get(name)
        if isinstance(obj, Model):
            result.extend(_flatten_outputs(obj, flat))
        else:
            result.append(flat)

    return result


# ---------------------------------------------------------------------------
# Entry builders (unchanged signatures)
# ---------------------------------------------------------------------------

def _make_pool_entry(name, init_value, obj):
    entry = _make_entry(name, init_value)
    entry['allow_negative'] = getattr(obj, 'allow_neg', False)
    return entry


def _make_entry(name, init_value):
    is_vec = isinstance(init_value, np.ndarray)
    return {
        'name': name,
        'init_value': init_value,
        'type': _get_value_type(init_value),
        'is_vector': is_vec,
        'shape': init_value.shape if is_vec else None,
    }


def _get_closure_vars(func):
    if func.__closure__ is None:
        return {}
    return dict(zip(func.__code__.co_freevars,
                     [c.cell_contents for c in func.__closure__]))


def _resolve_array(val):
    if isinstance(val, Parameter):
        val = val()
    if hasattr(val, 'tolist'):
        return val.tolist()
    return [float(v) for v in val]


def _make_step_entry(name, obj):
    cv = _get_closure_vars(obj.eq_func)
    values = _resolve_array(cv['values'])
    times = _resolve_array(cv['times'])
    default = float(cv.get('default', 0))
    return {
        'name': name,
        'type': 'step',
        'init_value': default,
        'values': values,
        'times': times,
        'default': default,
        'func_info': _extract_func_info(obj.eq_func),
    }


def _make_impulse_entry(name, obj):
    cv = _get_closure_vars(obj.eq_func)
    values = _resolve_array(cv['values'])
    times = _resolve_array(cv['times'])
    return {
        'name': name,
        'type': 'impulse',
        'init_value': 0,
        'values': values,
        'times': times,
        'func_info': _extract_func_info(obj.eq_func),
    }


def _make_equation_entry(name, obj, eq_type):
    func = obj.eq_func
    func_info = _extract_func_info(func)
    return {
        'name': name,
        'type': eq_type,
        'init_value': getattr(obj, 'init_value', 0),
        'func_info': func_info,
    }


def _make_flow_entry(name, obj, identity_map):
    func_info = _extract_func_info(obj.rate_func)
    src_name = _find_name_by_identity(obj.src, identity_map)
    dest_name = _find_name_by_identity(obj.dest, identity_map)

    variance_value = None
    variance_func = getattr(obj, 'variance', None)
    if variance_func is not None:
        try:
            variance_value = float(variance_func())
        except Exception:
            pass

    return {
        'name': name,
        'rate_func': func_info,
        'src': src_name,
        'dest': dest_name,
        'discrete': getattr(obj, 'discrete', False),
        'stochastic': getattr(obj, 'stochastic', False),
        'variance_value': variance_value,
    }


def _extract_func_info(func) -> Dict[str, Any]:
    source = None
    try:
        source = inspect.getsource(func).strip()
    except (OSError, TypeError):
        pass
    return {
        'source': source,
        'is_lambda': getattr(func, '__name__', '') == '<lambda>',
    }


def _get_value_type(value):
    if isinstance(value, np.ndarray):
        return 'array[%s]' % value.dtype
    elif isinstance(value, (int, np.integer)):
        return 'int'
    elif isinstance(value, (float, np.floating)):
        return 'float'
    elif isinstance(value, str):
        return 'str'
    else:
        return type(value).__name__


def _safe_scalar(val):
    if isinstance(val, (np.integer,)):
        return int(val)
    elif isinstance(val, (np.floating,)):
        return float(val)
    return val


# ---------------------------------------------------------------------------
# Process collection
# ---------------------------------------------------------------------------

def _collect_processes(model: Model, prefix: str) -> Dict[str, Any]:
    """Extract process definitions from a model and its sub-models."""
    processes: Dict[str, Any] = {}

    for i, proc in enumerate(getattr(model, '_processes', [])):
        name = getattr(proc.routine, '__name__', 'proc_%d' % i)
        flat = (prefix + '__' + name) if prefix else name

        start_type = None
        start_value = None
        if proc.start is not None:
            if isinstance(proc.start, Time):
                start_type = 'time'
                start_value = proc.start.time
            elif isinstance(proc.start, Delay):
                start_type = 'delay'
                start_value = proc.start.delay
            elif isinstance(proc.start, TimeStep):
                start_type = 'timestep'
                start_value = proc.start.steps

        source = None
        try:
            source = inspect.getsource(proc.routine).strip()
        except (OSError, TypeError):
            pass

        processes[flat] = {
            'name': flat,
            'start_type': start_type,
            'start_value': _safe_scalar(start_value) if start_value is not None else None,
            'priority': proc.priority,
            'source': source,
        }

    for sub_name, sub_model in _iter_submodels(model):
        sub_prefix = (prefix + '__' + sub_name) if prefix else sub_name
        processes.update(_collect_processes(sub_model, sub_prefix))

    return processes


def _iter_submodels(model: Model):
    """Yield (name, sub_model) pairs from a model's _available dict."""
    available = getattr(model, '_available', {})
    for name, obj in available.items():
        if isinstance(obj, Model):
            yield name, obj
