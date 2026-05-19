// Run Model Callback
try {
    const mode = mode_select.value;

    message_div.text = '<div style="background-color: #e8f4f8; padding: 10px; border: 1px solid #b8d4e8;"><b>Messages:</b> Running simulation...</div>';

    // Collect model inputs
    const inputs = {
{{INPUT_COLLECTION}}
    };

    // Collect run parameters
    const run_params = {
        t_start: 0,
        t_end: duration_input.value,
        dt: dt_input.value,
        reps: reps_input.value,
        interval: interval_input.value || 50,
        outputs: {{OUTPUTS_JSON}}
    };

    const start_time = performance.now();

    if (mode === 'Monte Carlo') {
        const result = window.PyCoModSimulation.run_simulation_mc(inputs, run_params);
        const elapsed = (performance.now() - start_time).toFixed(1);

        const plot_data = { time: result.time };
        for (const name of run_params.outputs) {
            const mc = result.mc_outputs[name];
            const median = mc ? mc.median : [];
            const p_low  = mc ? mc.p_low  : median.slice();
            const p_high = mc ? mc.p_high : median.slice();
            // Keep single-run column at matching length (renderer is hidden)
            plot_data[name]                = median.slice();
            plot_data[name + '_mc_median'] = median;
            plot_data[name + '_mc_p_low']  = p_low;
            plot_data[name + '_mc_p_high'] = p_high;
        }

{{SINGLE_HIDE_CODE}}
{{MC_SHOW_CODE}}

        plot_source.data = plot_data;
        message_div.text = `<div style="background-color: #d4edda; padding: 10px; border: 1px solid #c3e6cb;"><b>Messages:</b> Monte Carlo (${run_params.reps} runs, ${run_params.interval}% interval) completed in ${elapsed} ms</div>`;

    } else {
        const result = window.PyCoModSimulation.run_simulation(inputs, run_params);
        const elapsed = (performance.now() - start_time).toFixed(1);

        const plot_data = { time: result.time };
        for (const name of run_params.outputs) {
            const vals = result.outputs[name] || [];
            // Keep MC columns at matching length (renderers are hidden)
            const placeholder = new Array(vals.length).fill(0);
            plot_data[name]                = vals;
            plot_data[name + '_mc_median'] = placeholder;
            plot_data[name + '_mc_p_low']  = placeholder;
            plot_data[name + '_mc_p_high'] = placeholder;
        }

{{MC_HIDE_CODE}}
{{SINGLE_SHOW_CODE}}

        plot_source.data = plot_data;
        message_div.text = `<div style="background-color: #d4edda; padding: 10px; border: 1px solid #c3e6cb;"><b>Messages:</b> Simulation completed in ${elapsed} ms</div>`;
    }

    // Apply y-axis label
    if (plot_figure && plot_figure.left && plot_figure.left[0]) {
        plot_figure.left[0].axis_label = yaxis_label_input.value || 'Value';
    }

    // Apply x-axis formatting
    if (xaxis_formatter && plot_figure && plot_figure.below && plot_figure.below[0]) {
        if (xaxis_select.value === 'Dates') {
            const start_ms = new Date(date_input.value + 'T00:00:00').getTime();
            const tunit_ms_map = {Hours: 3600000, Days: 86400000, Months: 2628000000, Years: 31557600000};
            const tunit_ms = tunit_ms_map[tunit_select.value] || 86400000;
            xaxis_formatter.code = `const d = new Date(${start_ms} + tick * ${tunit_ms}); return d.toISOString().slice(0, 10);`;
            plot_figure.below[0].axis_label = 'Date';
        } else {
            xaxis_formatter.code = 'return String(tick);';
            plot_figure.below[0].axis_label = 'Time (' + tunit_select.value.toLowerCase() + ')';
        }
    }

} catch (error) {
    message_div.text = `<div style="background-color: #f8d7da; padding: 10px; border: 1px solid #f5c6cb;"><b>Error:</b> ${error.message}</div>`;
    console.error('Simulation error:', error);
}
