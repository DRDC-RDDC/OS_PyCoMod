"""Model inspection utilities using _get_init_df().

Compatible with Bokeh 2.4.1 and Python 3.9.7.
"""

from typing import Dict, Any
import numpy as np

from ..elements import Pool, Parameter
from ..model import Model


def inspect_model(model: Model) -> Dict[str, Any]:
    """Extract model structure using _get_init_df().

    Returns a dict with keys: pools, parameters, run_params.
    Each pool/parameter entry has: name, init_value, type, is_vector, shape.
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

    model_df = init_data.get('model')
    if model_df is not None:
        for col in model_df.columns:
            if col == 'out':
                continue

            obj = available.get(col)
            if obj is None:
                continue

            # Get the first non-None value
            values = model_df[col].dropna().tolist()
            init_value = values[0] if values else 0

            if isinstance(obj, Pool):
                pools[col] = _make_entry(col, init_value)
            elif isinstance(obj, Parameter):
                parameters[col] = _make_entry(col, init_value)

    return {
        'pools': pools,
        'parameters': parameters,
        'run_params': run_params,
    }


def _make_entry(name, init_value):
    """Build a pool/parameter info dict."""
    is_vec = isinstance(init_value, np.ndarray)
    return {
        'name': name,
        'init_value': init_value,
        'type': _get_value_type(init_value),
        'is_vector': is_vec,
        'shape': init_value.shape if is_vec else None,
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
    """Convert numpy scalar to Python scalar."""
    if isinstance(val, (np.integer,)):
        return int(val)
    elif isinstance(val, (np.floating,)):
        return float(val)
    return val
