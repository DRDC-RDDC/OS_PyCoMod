// Save Inputs Callback
try {
    // Collect all inputs
    const inputs = {
{{INPUT_COLLECTION}}
        "date": date_input.value,
        "tunit": tunit_select.value,
        "duration": duration_input.value,
        "dt": dt_input.value,
        "xaxis": xaxis_select.value,
        "yaxis_label": yaxis_label_input.value,
        "mode": mode_select.value,
        "reps": reps_input.value
    };

    // Convert to JSON
    const json_string = JSON.stringify(inputs, null, 2);

    // Create blob and download
    const blob = new Blob([json_string], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'model_inputs.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    message_div.text = '<div style="background-color: #d4edda; padding: 10px; border: 1px solid #c3e6cb;"><b>Messages:</b> Inputs saved to model_inputs.json</div>';

} catch (error) {
    message_div.text = `<div style="background-color: #f8d7da; padding: 10px; border: 1px solid #f5c6cb;"><b>Error:</b> ${error.message}</div>`;
    console.error('Save inputs error:', error);
}
