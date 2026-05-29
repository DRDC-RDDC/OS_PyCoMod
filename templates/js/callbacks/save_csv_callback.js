// Save Output Data as CSV
try {
    const data = plot_source.data;
    const time = data['time'] || [];

    if (time.length === 0) {
        message_div.text = '<div style="background-color: #fff3cd; padding: 10px; border: 1px solid #ffeeba;"><b>Messages:</b> No simulation data to save. Run the simulation first.</div>';
        return;
    }

    const outputs = {{OUTPUTS_JSON}};
    const is_mc = mode_select.value === 'Monte Carlo';

    // Build header row
    const headers = ['time', 'date'];
    for (const name of outputs) {
        if (is_mc) {
            headers.push(name + '_mc_median', name + '_mc_p_low', name + '_mc_p_high');
        } else {
            headers.push(name);
        }
    }

    // Compute date strings for each timestep
    const tunit_ms_map = { Hours: 3600000, Days: 86400000, Months: 2628000000, Years: 31557600000 };
    const tunit_ms = tunit_ms_map[tunit_select.value] || 86400000;
    let dates;
    if (xaxis_select.value === 'Dates' && date_input.value) {
        const start_ms = new Date(date_input.value + 'T00:00:00').getTime();
        dates = time.map(t => new Date(start_ms + t * tunit_ms).toISOString().slice(0, 10));
    } else {
        dates = time.map(() => '');
    }

    // Build CSV rows
    const rows = [headers.join(',')];
    for (let i = 0; i < time.length; i++) {
        const row = [time[i], dates[i]];
        for (const name of outputs) {
            if (is_mc) {
                row.push(
                    (data[name + '_mc_median'] || [])[i] ?? '',
                    (data[name + '_mc_p_low']  || [])[i] ?? '',
                    (data[name + '_mc_p_high'] || [])[i] ?? ''
                );
            } else {
                row.push((data[name] || [])[i] ?? '');
            }
        }
        rows.push(row.join(','));
    }

    const csv_content = rows.join('\n');

    if (window.showSaveFilePicker) {
        (async () => {
            try {
                const handle = await window.showSaveFilePicker({
                    suggestedName: 'simulation_output.csv',
                    types: [{ description: 'CSV Files', accept: { 'text/csv': ['.csv'] } }],
                });
                const writable = await handle.createWritable();
                await writable.write(csv_content);
                await writable.close();
                message_div.text = '<div style="background-color: #d4edda; padding: 10px; border: 1px solid #c3e6cb;"><b>Messages:</b> CSV saved successfully.</div>';
            } catch (err) {
                if (err.name !== 'AbortError') {
                    message_div.text = `<div style="background-color: #f8d7da; padding: 10px; border: 1px solid #f5c6cb;"><b>Error:</b> ${err.message}</div>`;
                }
            }
        })();
    } else {
        // Fallback for browsers without File System Access API
        const blob = new Blob([csv_content], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'simulation_output.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        message_div.text = '<div style="background-color: #d4edda; padding: 10px; border: 1px solid #c3e6cb;"><b>Messages:</b> CSV download started.</div>';
    }

} catch (error) {
    message_div.text = `<div style="background-color: #f8d7da; padding: 10px; border: 1px solid #f5c6cb;"><b>Error:</b> ${error.message}</div>`;
}
