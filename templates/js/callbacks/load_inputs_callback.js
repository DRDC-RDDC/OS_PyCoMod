// Load Inputs Callback
try {
    // Create file input element
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';

    input.onchange = function(e) {
        const file = e.target.files[0];
        const reader = new FileReader();

        reader.onload = function(event) {
            try {
                const inputs = JSON.parse(event.target.result);

                // Load all inputs
{{INPUT_ASSIGNMENTS}}
                if (inputs.date !== undefined) date_input.value = inputs.date;
                if (inputs.tunit !== undefined) tunit_select.value = inputs.tunit;
                if (inputs.duration !== undefined) duration_input.value = inputs.duration;
                if (inputs.dt !== undefined) dt_input.value = inputs.dt;
                if (inputs.xaxis !== undefined) xaxis_select.value = inputs.xaxis;
                if (inputs.yaxis_label !== undefined) yaxis_label_input.value = inputs.yaxis_label;
                if (inputs.mode !== undefined) mode_select.value = inputs.mode;
                if (inputs.reps !== undefined) reps_input.value = inputs.reps;

                message_div.text = '<div style="background-color: #d4edda; padding: 10px; border: 1px solid #c3e6cb;"><b>Messages:</b> Inputs loaded successfully</div>';

            } catch (error) {
                message_div.text = `<div style="background-color: #f8d7da; padding: 10px; border: 1px solid #f5c6cb;"><b>Error:</b> Invalid JSON file - ${error.message}</div>`;
                console.error('Parse error:', error);
            }
        };

        reader.readAsText(file);
    };

    input.click();

} catch (error) {
    message_div.text = `<div style="background-color: #f8d7da; padding: 10px; border: 1px solid #f5c6cb;"><b>Error:</b> ${error.message}</div>`;
    console.error('Load inputs error:', error);
}
