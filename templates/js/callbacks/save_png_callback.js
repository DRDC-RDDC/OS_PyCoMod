try {
  let src_canvas = null

  // Strategy 1: walk Bokeh.index to find a PlotView that has a canvas_view.
  // Bokeh.index may be a plain object or a Map depending on the version.
  try {
    const root_views = (Bokeh.index instanceof Map)
      ? [...Bokeh.index.values()]
      : Object.values(Bokeh.index)

    function _find_canvas_view (view) {
      if (!view) return null
      if (view.canvas_view) return view.canvas_view
      const children = view.child_views
      if (!children) return null
      const vals = (children instanceof Map) ? [...children.values()] : Object.values(children)
      for (const child of vals) {
        const found = _find_canvas_view(child)
        if (found) return found
      }
      return null
    }

    for (const root_view of root_views) {
      const cv = _find_canvas_view(root_view)
      if (!cv) continue
      const primary = cv.primary
      if (primary && primary.el instanceof HTMLCanvasElement) {
        src_canvas = primary.el
      } else if (cv.el instanceof HTMLCanvasElement) {
        src_canvas = cv.el
      } else if (cv.el && cv.el.querySelector) {
        src_canvas = cv.el.querySelector('canvas')
      }
      if (src_canvas) break
    }
  } catch (_) {}

  // Strategy 2: pick the largest canvas that is not an event overlay.
  if (!src_canvas) {
    const candidates = Array.from(document.querySelectorAll('canvas'))
      .filter(c => c.width > 0 && c.height > 0 && !c.classList.contains('bk-canvas-events'))
    if (candidates.length > 0) {
      src_canvas = candidates.reduce((a, b) => (a.width * a.height >= b.width * b.height) ? a : b)
    }
  }

  // Strategy 3: any canvas at all as a last resort
  if (!src_canvas) {
    src_canvas = document.querySelector('canvas')
  }

  if (!src_canvas) {
    message_div.text = '<div style="background-color: #f8d7da; padding: 10px; border: 1px solid #f5c6cb;"><b>Error:</b> Could not locate plot canvas. Ensure the simulation has been run.</div>'
    return
  }

  const target_width = Math.round(png_resolution_input.value || 1600)
  if (target_width < 1200 || target_width > 1920) {
    message_div.text = '<div style="background-color: #fff3cd; padding: 10px; border: 1px solid #ffeeba;"><b>Messages:</b> PNG width must be between 1200 and 1920 px.</div>'
    return
  }
  const scale_factor = target_width / src_canvas.width
  const target_height = Math.round(src_canvas.height * scale_factor)

  const out_canvas = document.createElement('canvas')
  out_canvas.width = target_width
  out_canvas.height = target_height
  const ctx = out_canvas.getContext('2d')
  ctx.imageSmoothingEnabled = true
  ctx.imageSmoothingQuality = 'high'
  ctx.drawImage(src_canvas, 0, 0, target_width, target_height)

  out_canvas.toBlob(blob => {
    if (!blob) {
      message_div.text = '<div style="background-color: #f8d7da; padding: 10px; border: 1px solid #f5c6cb;"><b>Error:</b> Could not generate PNG image.</div>'
      return
    }

    if (window.showSaveFilePicker) {
      (async () => {
        try {
          const handle = await window.showSaveFilePicker({
            suggestedName: 'simulation_output.png',
            types: [{ description: 'PNG Image', accept: { 'image/png': ['.png'] } }]
          })
          const writable = await handle.createWritable()
          await writable.write(blob)
          await writable.close()
          message_div.text = `<div style="background-color: #d4edda; padding: 10px; border: 1px solid #c3e6cb;"><b>Messages:</b> PNG saved (${target_width} \xd7 ${target_height} px).</div>`
        } catch (err) {
          if (err.name !== 'AbortError') {
            message_div.text = `<div style="background-color: #f8d7da; padding: 10px; border: 1px solid #f5c6cb;"><b>Error:</b> ${err.message}</div>`
          }
        }
      })()
    } else {
      // Fallback for browsers without File System Access API
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'simulation_output.png'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      message_div.text = `<div style="background-color: #d4edda; padding: 10px; border: 1px solid #c3e6cb;"><b>Messages:</b> PNG download started (${target_width} \xd7 ${target_height} px).</div>`
    }
  }, 'image/png')
} catch (error) {
  message_div.text = `<div style="background-color: #f8d7da; padding: 10px; border: 1px solid #f5c6cb;"><b>Error:</b> ${error.message}</div>`
}
