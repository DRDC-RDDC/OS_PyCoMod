"""Model inspection utilities using _get_init_df().

Compatible with Bokeh 2.4.1 and Python 3.9.7.
"""

import inspect
from typing import Dict, Any, Optional
import numpy as np

from ..elements import Pool, Parameter, Equation, Flow, Step, Impulse
from ..model import Model


def inspect_model(model: Model) -> Dict[str, Any]:
    """Extract model structure including equations, flows, and outputs.

    Returns a dict with keys: pools, parameters, equations, flows,
    outputs, run_params, element_map.
    """
    init_data = model._get_init_df()

    # --- Run parameters from the 'run' DataFrame ---
    run_df = init_data['run']
    run_params = {
        't': _safe_scalar(run_df['t'].iloc[0]),
        'date': str(run_df['date'].iloc[0]),
        'tunit': str(run_df['tunit'].iloc[0]),
        'dt': _safe_scalar(run_df['dt'].iloc[0]),
        'end': _safe_scalar(run_df['end'].iloc[0]),
        'reps': int(run_df['reps'].iloc[0]),
    }

    # --- Model inputs from the 'model' DataFrame ---
    available = getattr(model, '_available', {})

    pools = {}
    parameters = {}
    equations = {}
    flows = {}
    element_map = {}

    model_df = init_data.get('model')
    if model_df is not None:
        for col in model_df.columns:
            if col == 'out':
                continue

            obj = available.get(col)
            if obj is None:
                continue

            values = model_df[col].dropna().tolist()
            init_value = values[0] if values else 0

            if isinstance(obj, Pool):
                pools[col] = _make_pool_entry(col, init_value, obj)
                element_map[col] = 'pool'
            elif isinstance(obj, Parameter):
                parameters[col] = _make_entry(col, init_value)
                element_map[col] = 'parameter'

    # --- Extract equations and flows from _available ---
    for name, obj in available.items():
        if name.startswith('_') or name in pools or name in parameters:
            continue

        if isinstance(obj, (Step, Impulse)):
            equations[name] = _make_equation_entry(name, obj, 'step' if isinstance(obj, Step) else 'impulse')
            element_map[name] = 'equation'
        elif isinstance(obj, Equation):
            equations[name] = _make_equation_entry(name, obj, 'equation')
            element_map[name] = 'equation'
        elif isinstance(obj, Flow):
            flows[name] = _make_flow_entry(name, obj, available)
            element_map[name] = 'flow'

    # --- Outputs ---
    outputs = list(model.out) if model.out else []

    return {
        'pools': pools,
        'parameters': parameters,
        'equations': equations,
        'flows': flows,
        'outputs': outputs,
        'run_params': run_params,
        'element_map': element_map,
    }


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


def _make_equation_entry(name, obj, eq_type):
    func = obj.eq_func
    func_info = _extract_func_info(func)
    return {
        'name': name,
        'type': eq_type,
        'init_value': getattr(obj, 'init_value', 0),
        'func_info': func_info,
    }


def _make_flow_entry(name, obj, available):
    func_info = _extract_func_info(obj.rate_func)
    src_name = _find_name(obj.src, available) if obj.src is not None else None
    dest_name = _find_name(obj.dest, available) if obj.dest is not None else None
    return {
        'name': name,
        'rate_func': func_info,
        'src': src_name,
        'dest': dest_name,
        'discrete': getattr(obj, 'discrete', False),
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


def _find_name(element, available) -> Optional[str]:
    for name, obj in available.items():
        if obj is element and not name.startswith('_'):
            return name
    return None


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
