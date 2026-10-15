try {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.json'

  input.onchange = function (e) {
    const file = e.target.files[0]
    const reader = new FileReader()

    reader.onload = function (event) {
      try {
        const inputs = JSON.parse(event.target.result)

        {{INPUT_ASSIGNMENTS}}
        if (inputs._sim_date !== undefined) date_input.value = inputs._sim_date
        if (inputs._sim_tunit !== undefined) tunit_select.value = inputs._sim_tunit
        if (inputs._sim_duration !== undefined) duration_input.value = inputs._sim_duration
        if (inputs._sim_dt !== undefined) dt_input.value = inputs._sim_dt
        if (inputs._sim_xaxis !== undefined) xaxis_select.value = inputs._sim_xaxis
        if (inputs._sim_yaxis_label !== undefined) yaxis_label_input.value = inputs._sim_yaxis_label
        if (inputs._sim_mode !== undefined) mode_select.value = inputs._sim_mode
        if (inputs._sim_reps !== undefined) reps_input.value = inputs._sim_reps
        if (inputs._sim_interval !== undefined) interval_input.value = inputs._sim_interval

        message_div.text = '<div style="background-color: #d4edda; padding: 10px; border: 1px solid #c3e6cb;"><b>Messages:</b> Inputs loaded successfully</div>'
      } catch (error) {
        message_div.text = `<div style="background-color: #f8d7da; padding: 10px; border: 1px solid #f5c6cb;"><b>Error:</b> Invalid JSON file - ${error.message}</div>`
        console.error('Parse error:', error)
      }
    }

    reader.readAsText(file)
  }

  input.click()
} catch (error) {
  message_div.text = `<div style="background-color: #f8d7da; padding: 10px; border: 1px solid #f5c6cb;"><b>Error:</b> ${error.message}</div>`
  console.error('Load inputs error:', error)
}
