// ============================================================================
// Main Simulation Loop
// ============================================================================

function run_simulation(inputs, run_params, stochastic_enabled) {
    const elements = initialize_elements(inputs);
    PyCoMod.elements = elements;

    for (const name in elements) {
        elements[name].reset();
    }

    const t_start = run_params.t_start || 0;
    const t_end = run_params.t_end || 100;
    const dt = run_params.dt || 1;
    const n_steps = Math.floor((t_end - t_start) / dt);

    let sim_time = t_start;
    const time_hist = [t_start];

    for (let step = 0; step < n_steps; step++) {
        sim_time += dt;

        for (const name in elements) {
            if (elements[name] instanceof Equation) {
                elements[name].update(dt);
            }
        }

        for (const name in elements) {
            if (elements[name] instanceof Flow) {
                elements[name].update(dt, stochastic_enabled);
            }
        }

        for (const name in elements) {
            if (elements[name] instanceof Pool) {
                elements[name].update(dt);
            }
        }

        for (const name in elements) {
            elements[name].save_hist();
        }

        time_hist.push(sim_time);
    }

    return {
        time: time_hist,
        elements: elements,
        outputs: extract_outputs(elements, run_params.outputs)
    };
}

function extract_outputs(elements, output_names) {
    const outputs = {};

    if (!output_names || output_names.length === 0) {
        for (const name in elements) {
            outputs[name] = elements[name].get_history();
        }
    } else {
        for (const name of output_names) {
            if (elements[name]) {
                outputs[name] = elements[name].get_history();
            }
        }
    }

    return outputs;
}

// ============================================================================
// Monte Carlo Simulation
// ============================================================================

function run_simulation_mc(inputs, run_params) {
    const reps = run_params.reps || 100;
    const interval = run_params.interval || 90;
    const outputs = run_params.outputs || [];

    const all_runs = {};
    for (const name of outputs) {
        all_runs[name] = [];
    }
    let time_hist = null;

    for (let rep = 0; rep < reps; rep++) {
        const result = run_simulation(inputs, run_params, true);
        if (time_hist === null) {
            time_hist = result.time;
        }
        for (const name of outputs) {
            if (result.outputs[name]) {
                all_runs[name].push(result.outputs[name]);
            }
        }
    }

    const mc_outputs = {};
    for (const name of outputs) {
        mc_outputs[name] = _compute_statistics(all_runs[name], interval);
    }

    return { time: time_hist, mc_outputs: mc_outputs };
}

function _percentile(sorted_values, pct) {
    const n = sorted_values.length;
    if (n === 0) return 0;
    const idx = (pct / 100) * (n - 1);
    const lo = Math.floor(idx);
    const hi = Math.ceil(idx);
    if (lo === hi) return sorted_values[lo];
    return sorted_values[lo] + (idx - lo) * (sorted_values[hi] - sorted_values[lo]);
}

function _compute_statistics(runs, interval) {
    if (!runs || runs.length === 0) {
        return { median: [], p_low: [], p_high: [] };
    }

    interval = interval || 90;
    const pct_low  = (100 - interval) / 2;
    const pct_high = 100 - pct_low;

    const n_steps = runs[0].length;
    const median = new Array(n_steps);
    const p_low  = new Array(n_steps);
    const p_high = new Array(n_steps);

    for (let t = 0; t < n_steps; t++) {
        const values = runs.map(run => run[t]).sort((a, b) => a - b);
        median[t] = _percentile(values, 50);
        p_low[t]  = _percentile(values, pct_low);
        p_high[t] = _percentile(values, pct_high);
    }

    return { median, p_low, p_high };
}
