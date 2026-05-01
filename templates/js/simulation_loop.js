// ============================================================================
// Main Simulation Loop
// ============================================================================

function run_simulation(inputs, run_params) {
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
                elements[name].update(dt);
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
