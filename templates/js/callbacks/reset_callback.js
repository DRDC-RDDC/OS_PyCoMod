try {
  {{INPUT_RESETS}}

  date_input.value = '{{DEFAULT_DATE}}'
  tunit_select.value = '{{DEFAULT_TUNIT}}'
  duration_input.value = {{DEFAULT_DURATION}}
  dt_input.value = {{DEFAULT_DT}}
  xaxis_select.value = 'Dates'
  yaxis_label_input.value = 'Value'
  mode_select.value = 'Single'
  reps_input.value = {{DEFAULT_REPS}}
  reps_input.disabled = true
  interval_input.value = {{DEFAULT_INTERVAL}}
  interval_input.disabled = true
  png_resolution_input.value = {{DEFAULT_PNG_RESOLUTION}}

  message_div.text = '<div style="background-color: #d4edda; padding: 10px; border: 1px solid #c3e6cb;"><b>Messages:</b> All inputs reset to defaults</div>'
} catch (error) {
  message_div.text = `<div style="background-color: #f8d7da; padding: 10px; border: 1px solid #f5c6cb;"><b>Error:</b> ${error.message}</div>`
  console.error('Reset error:', error)
}
