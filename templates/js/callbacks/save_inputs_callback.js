try {
  const inputs = {
{{INPUT_COLLECTION}}
      "_sim_date": date_input.value,
      "_sim_tunit": tunit_select.value,
      "_sim_duration": duration_input.value,
      "_sim_dt": dt_input.value,
      "_sim_xaxis": xaxis_select.value,
      "_sim_yaxis_label": yaxis_label_input.value,
      "_sim_mode": mode_select.value,
      "_sim_reps": reps_input.value,
      "_sim_interval": interval_input.value
  };

  const json_string = JSON.stringify(inputs, null, 2);
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
