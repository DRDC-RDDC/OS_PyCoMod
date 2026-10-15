try {
  const mode = mode_select.value

  message_div.text = '<div style="background-color: #e8f4f8; padding: 10px; border: 1px solid #b8d4e8;"><b>Messages:</b> Running simulation...</div>'

  const raw_date = (date_input.value || '').trim()
  if (raw_date !== '') {
    const date_rx = /^\d{4}-\d{2}-\d{2}$/
    let date_err = null
    if (!date_rx.test(raw_date)) {
      date_err = `Start Date must be in YYYY-MM-DD format (e.g. 2026-01-15). Got: "${raw_date}"`
    } else {
      const dp = raw_date.split('-')
      const y = parseInt(dp[0]); const m = parseInt(dp[1]); const d = parseInt(dp[2])
      const chk = new Date(Date.UTC(y, m - 1, d))
      if (chk.getUTCFullYear() !== y || chk.getUTCMonth() !== m - 1 || chk.getUTCDate() !== d) {
        date_err = `Start Date "${raw_date}" is not a valid calendar date. Month must be 01-12 and day must be valid for that month.`
      }
    }
    if (date_err) {
      message_div.text = `<div style="background-color: #f8d7da; padding: 10px; border: 1px solid #f5c6cb;"><b>Error:</b> ${date_err}</div>`
      return
    }
  }

  const inputs = {
    {{INPUT_COLLECTION}}
  }

  const run_params = {
    t_start: 0,
    t_end: duration_input.value,
    dt: dt_input.value,
    reps: reps_input.value,
    interval: interval_input.value || 50,
    date: raw_date || null,
    tunit: tunit_select.value || 'Days',
    outputs: {{OUTPUTS_JSON}}
  }

  const start_time = performance.now()
  const has_stochastic = {{HAS_STOCHASTIC}}

  // Precompute x-axis values as final values (ms timestamps or plain numbers) so
  // changing tunit/date forces Bokeh to re-render with correct tick labels without Reset.
  const tunit_ms_map = { Hours: 3600000, Days: 86400000, Months: 2628000000, Years: 31557600000 }
  const tunit_ms = tunit_ms_map[tunit_select.value] || 86400000
  const use_dates = xaxis_select.value === 'Dates'
  let start_ms = 0
  if (use_dates && raw_date !== '') {
    const dp = raw_date.split('-')
    start_ms = Date.UTC(parseInt(dp[0]), parseInt(dp[1]) - 1, parseInt(dp[2]))
  }

  function convert_time (t_arr) {
    if (use_dates) {
      return t_arr.map(function (t) { return start_ms + t * tunit_ms })
    }
    return t_arr
  }

  if (plot_figure && plot_figure.left && plot_figure.left[0]) {
    plot_figure.left[0].axis_label = yaxis_label_input.value || 'Value'
  }
  if (xaxis_formatter && plot_figure && plot_figure.below && plot_figure.below[0]) {
    if (use_dates) {
      xaxis_formatter.code = 'const d = new Date(tick); return d.toISOString().slice(0, 10);'
      plot_figure.below[0].axis_label = 'Date'
    } else {
      xaxis_formatter.code = 'return String(tick);'
      plot_figure.below[0].axis_label = 'Time (' + tunit_select.value.toLowerCase() + ')'
    }
  }

  if (mode === 'Monte Carlo') {
    const result = window.PyCoModSimulation.run_simulation_mc(inputs, run_params)
    const elapsed = (performance.now() - start_time).toFixed(1)

    const plot_data = { time: convert_time(result.time) }
    for (const name of run_params.outputs) {
      const mc = result.mc_outputs[name]
      const median = mc ? mc.median : []
      const p_low = mc ? mc.p_low : median.slice()
      const p_high = mc ? mc.p_high : median.slice()
      // Keep single-run column at matching length (renderer is hidden)
      plot_data[name] = median.slice()
      plot_data[name + '_mc_median'] = median
      plot_data[name + '_mc_p_low'] = p_low
      plot_data[name + '_mc_p_high'] = p_high
    }

    {{SINGLE_HIDE_CODE}}
    {{MC_SHOW_CODE}}

    plot_source.data = plot_data
    if (!has_stochastic) {
      message_div.text = `<div style="background-color: #fff3cd; padding: 10px; border: 1px solid #ffc107;"><b>Warning:</b> Monte Carlo completed (${run_params.reps} runs, ${elapsed} ms) but no stochastic flows are defined — all replications produced identical results. Set stochastic=True on one or more flows to enable variability.</div>`
    } else {
      message_div.text = `<div style="background-color: #d4edda; padding: 10px; border: 1px solid #c3e6cb;"><b>Messages:</b> Monte Carlo (${run_params.reps} runs, ${run_params.interval}% interval) completed in ${elapsed} ms</div>`
    }
  } else {
    const result = window.PyCoModSimulation.run_simulation(inputs, run_params)
    const elapsed = (performance.now() - start_time).toFixed(1)

    const plot_data = { time: convert_time(result.time) }
    for (const name of run_params.outputs) {
      const vals = result.outputs[name] || []
      // Keep MC columns at matching length (renderers are hidden)
      const placeholder = new Array(vals.length).fill(0)
      plot_data[name] = vals
      plot_data[name + '_mc_median'] = placeholder
      plot_data[name + '_mc_p_low'] = placeholder
      plot_data[name + '_mc_p_high'] = placeholder
    }

    {{MC_HIDE_CODE}}
    {{SINGLE_SHOW_CODE}}

    plot_source.data = plot_data
    message_div.text = `<div style="background-color: #d4edda; padding: 10px; border: 1px solid #c3e6cb;"><b>Messages:</b> Simulation completed in ${elapsed} ms</div>`
  }
} catch (error) {
  message_div.text = `<div style="background-color: #f8d7da; padding: 10px; border: 1px solid #f5c6cb;"><b>Error:</b> ${error.message}</div>`
  console.error('Simulation error:', error)
}
