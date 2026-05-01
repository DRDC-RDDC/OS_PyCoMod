// Run Model Callback (Single Run only)
try {
    const mode = mode_select.value;

    if (mode === 'Monte Carlo') {
        message_div.text = '<div style="background-color: #fff3cd; padding: 10px; border: 1px solid #ffeeba;"><b>Messages:</b> Monte Carlo mode is not yet supported in this export. Please select Single run mode.</div>';
        return;
    }

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
        outputs: {{OUTPUTS_JSON}}
    };

    const start_time = performance.now();
    const result = window.PyCoModSimulation.run_simulation(inputs, run_params);
    const elapsed = (performance.now() - start_time).toFixed(1);

    // Update plot data
    const plot_data = { time: result.time };
    for (const name of run_params.outputs) {
        if (result.outputs[name]) {
            plot_data[name] = result.outputs[name];
        }
    }
    plot_source.data = plot_data;

    message_div.text = `<div style="background-color: #d4edda; padding: 10px; border: 1px solid #c3e6cb;"><b>Messages:</b> Simulation completed in ${elapsed} ms</div>`;

} catch (error) {
    message_div.text = `<div style="background-color: #f8d7da; padding: 10px; border: 1px solid #f5c6cb;"><b>Error:</b> ${error.message}</div>`;
    console.error('Simulation error:', error);
}
