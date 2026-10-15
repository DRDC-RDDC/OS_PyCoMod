"""Attach CustomJS callbacks to the widgets of the generated UI."""

from bokeh.models import CustomJS
from .template_loader import get_loader

# Setting renderer.muted from JS doesn't restyle the legend (it only updates
# on click); a change on a legend item makes it re-render all entries.
_LEGEND_REFRESH = (
    'if (legend.items.length > 0) legend.items[0].change.emit()'
)


# Generated JS follows StandardJS: no semicolons, single quotes, 2-space
# indent. Lines are emitted unindented and aligned by _block().

def _block(lines, indent):
    """Join JS lines for a placeholder that sits *indent* spaces deep."""
    return ('\n' + ' ' * indent).join(lines)


def _js_str(value):
    """Return *value* as a single-quoted JS string literal."""
    return "'%s'" % str(value).replace('\\', '\\\\').replace("'", "\\'")


def _js_list(names):
    """Return a JS array literal of single-quoted strings."""
    return '[%s]' % ', '.join(_js_str(n) for n in names)


class BokehCallbackGenerator:
    """Wire the Run, Reset, Save/Load, CSV, PNG and toggle callbacks."""

    def __init__(self, ui_generator, js_engine: str = ''):
        """Store the UI generator and the JS engine source."""
        self.ui_generator = ui_generator
        self.js_engine = js_engine
        self.model_structure = ui_generator.model_structure
        self.template_loader = get_loader()

    def _get_all_outputs(self):
        outputs = self.model_structure.get('outputs', [])
        si_outputs = self.model_structure.get('si_outputs', [])
        return outputs + si_outputs

    def attach_all_callbacks(self):
        """Attach every callback to its widget."""
        self._attach_run_callback()
        self._attach_reset_callback()
        self._attach_output_toggle_callback()
        self._attach_save_inputs_callback()
        self._attach_load_inputs_callback()
        self._attach_save_csv_callback()
        self._attach_save_png_callback()

    def _build_common_args(self):
        args = {
            'message_div': self.ui_generator.message_div,
            'date_input': self.ui_generator.date_input,
            'tunit_select': self.ui_generator.tunit_select,
            'duration_input': self.ui_generator.duration_input,
            'dt_input': self.ui_generator.dt_input,
            'xaxis_select': self.ui_generator.xaxis_select,
            'yaxis_label_input': self.ui_generator.yaxis_label_input,
            'mode_select': self.ui_generator.mode_select,
            'reps_input': self.ui_generator.reps_input,
            'interval_input': self.ui_generator.interval_input,
            'png_resolution_input': self.ui_generator.png_resolution_input,
        }
        if self.ui_generator.xaxis_formatter is not None:
            args['xaxis_formatter'] = self.ui_generator.xaxis_formatter
        if self.ui_generator.plot_figure is not None:
            args['plot_figure'] = self.ui_generator.plot_figure
        for name, widget in self.ui_generator.input_widgets.items():
            args['input_%s' % name] = widget
        for name in self._get_all_outputs():
            if name in self.ui_generator.line_renderers:
                args['single_line_%s' % name] = (
                    self.ui_generator.line_renderers[name]
                )
            if name in self.ui_generator.mc_band_renderers:
                args['mc_band_%s' % name] = (
                    self.ui_generator.mc_band_renderers[name]
                )
            if name in self.ui_generator.mc_mean_renderers:
                args['mc_mean_%s' % name] = (
                    self.ui_generator.mc_mean_renderers[name]
                )
        return args

    def _attach_run_callback(self):
        args = self._build_common_args()
        args['plot_source'] = self.ui_generator.plot_source
        if self.ui_generator.output_checkboxes is not None:
            args['checkboxes'] = self.ui_generator.output_checkboxes

        all_outputs = self._get_all_outputs()
        outputs_json = _js_list(all_outputs)

        input_collection = []
        for name in self.ui_generator.input_widgets.keys():
            input_collection.append('%s: input_%s.value,' % (name, name))

        single_hide = []
        single_show = []
        mc_hide = []
        mc_show = []
        for i, n in enumerate(all_outputs):
            chk = 'checkboxes.active.includes(%d)' % i
            if n in self.ui_generator.line_renderers:
                single_hide.append('single_line_%s.visible = false' % n)
                single_show.append('single_line_%s.visible = %s' % (n, chk))
            if n in self.ui_generator.mc_band_renderers:
                mc_hide.append('mc_band_%s.visible = false' % n)
                mc_show.append('mc_band_%s.visible = %s' % (n, chk))
            if n in self.ui_generator.mc_mean_renderers:
                mc_hide.append('mc_mean_%s.visible = false' % n)
                mc_show.append('mc_mean_%s.visible = %s' % (n, chk))

        has_stochastic = any(
            info.get('stochastic', False)
            for info in self.model_structure.get('flows', {}).values()
        )

        callback_code = self.template_loader.render_js_callback(
            'run_callback.js',
            {
                'INPUT_COLLECTION': _block(input_collection, 4).rstrip(','),
                'OUTPUTS_JSON': outputs_json,
                'HAS_STOCHASTIC': 'true' if has_stochastic else 'false',
                'SINGLE_HIDE_CODE': _block(single_hide, 4),
                'SINGLE_SHOW_CODE': _block(single_show, 4),
                'MC_HIDE_CODE': _block(mc_hide, 4),
                'MC_SHOW_CODE': _block(mc_show, 4),
            }
        )

        callback = CustomJS(
            args=args,
            code=self.js_engine.rstrip('\n') + '\n\n' + callback_code
        )
        self.ui_generator.control_buttons['run_model'].js_on_click(callback)

    def _attach_reset_callback(self):
        args = self._build_common_args()
        if self.ui_generator.plot_source is not None:
            args['plot_source'] = self.ui_generator.plot_source

        run_params = self.model_structure['run_params']

        input_resets = []
        for name, widget in self.ui_generator.input_widgets.items():
            val = widget.value
            if isinstance(val, str):
                input_resets.append(
                    'input_%s.value = %s' % (name, _js_str(val)))
            else:
                input_resets.append('input_%s.value = %s' % (name, val))

        tunit_str = str(run_params.get('tunit', '1 days'))
        tunit_map = {
            'D': 'Days', 'days': 'Days', '1 days': 'Days',
            'M': 'Months', 'months': 'Months',
            'Y': 'Years', 'years': 'Years',
            'h': 'Hours', 'hours': 'Hours',
        }
        default_tunit = tunit_map.get(tunit_str, 'Days')

        date_str = str(run_params.get('date', ''))
        if ' ' in date_str:
            date_str = date_str.split(' ')[0]

        all_outputs = self._get_all_outputs()
        n_primary = self.ui_generator.n_primary_outputs
        clear_data_lines = ['const clear_data = { time: [] }']
        for name in all_outputs:
            clear_data_lines.append('clear_data.%s = []' % name)
            clear_data_lines.append('clear_data.%s_mc_median = []' % name)
            clear_data_lines.append('clear_data.%s_mc_p_low = []' % name)
            clear_data_lines.append('clear_data.%s_mc_p_high = []' % name)
        if self.ui_generator.plot_source is not None:
            clear_data_lines.append('plot_source.data = clear_data')
        if self.ui_generator.plot_figure is not None:
            clear_data_lines.append('plot_figure.reset.emit()')
        if self.ui_generator.output_checkboxes is not None:
            args['checkboxes'] = self.ui_generator.output_checkboxes
            clear_data_lines.append(
                'checkboxes.active = %s'
                % list(self.ui_generator.output_checkboxes.active)
            )

        for i, name in enumerate(all_outputs):
            is_si = i >= n_primary
            # Also clear legend mute state (legend click_policy='mute')
            if name in self.ui_generator.line_renderers:
                clear_data_lines.append(
                    'single_line_%s.visible = %s'
                    % (name, 'false' if is_si else 'true')
                )
                clear_data_lines.append('single_line_%s.muted = false' % name)
            if name in self.ui_generator.mc_band_renderers:
                clear_data_lines.append('mc_band_%s.visible = false' % name)
                clear_data_lines.append('mc_band_%s.muted = false' % name)
            if name in self.ui_generator.mc_mean_renderers:
                clear_data_lines.append('mc_mean_%s.visible = false' % name)
                clear_data_lines.append('mc_mean_%s.muted = false' % name)
        if self.ui_generator.legend is not None:
            args['legend'] = self.ui_generator.legend
            clear_data_lines.append(_LEGEND_REFRESH)

        callback_code = self.template_loader.render_js_callback(
            'reset_callback.js',
            {
                'INPUT_RESETS': _block(input_resets, 2),
                'DEFAULT_DATE': date_str,
                'DEFAULT_TUNIT': default_tunit,
                'DEFAULT_DURATION': float(run_params['end']),
                'DEFAULT_DT': float(run_params['dt']),
                'DEFAULT_REPS': int(run_params['reps']),
                'DEFAULT_INTERVAL': 50,
                'DEFAULT_PNG_RESOLUTION': 1600,
            }
        )

        full_code = (callback_code.rstrip() + '\n\n// Clear plot\n'
                     + '\n'.join(clear_data_lines))
        callback = CustomJS(args=args, code=full_code)
        self.ui_generator.control_buttons['reset'].js_on_click(callback)

    def _attach_output_toggle_callback(self):
        all_outputs = self._get_all_outputs()
        if not all_outputs or self.ui_generator.output_checkboxes is None:
            return

        args = {
            'checkboxes': self.ui_generator.output_checkboxes,
            'mode_select': self.ui_generator.mode_select,
        }
        for name, renderer in self.ui_generator.line_renderers.items():
            args['single_line_%s' % name] = renderer
        for name, renderer in self.ui_generator.mc_band_renderers.items():
            args['mc_band_%s' % name] = renderer
        for name, renderer in self.ui_generator.mc_mean_renderers.items():
            args['mc_mean_%s' % name] = renderer

        toggle_lines = ["const is_mc = mode_select.value === 'Monte Carlo'"]
        for i, name in enumerate(all_outputs):
            toggle_lines.append(
                'const checked_%s = checkboxes.active.includes(%d)'
                % (name, i)
            )
            if name in self.ui_generator.line_renderers:
                toggle_lines.append(
                    'single_line_%s.visible = !is_mc && checked_%s'
                    % (name, name)
                )
            if name in self.ui_generator.mc_band_renderers:
                toggle_lines.append(
                    'mc_band_%s.visible = is_mc && checked_%s'
                    % (name, name)
                )
            if name in self.ui_generator.mc_mean_renderers:
                toggle_lines.append(
                    'mc_mean_%s.visible = is_mc && checked_%s'
                    % (name, name)
                )

        callback_code = self.template_loader.render_js_callback(
            'output_toggle_callback.js',
            {'TOGGLE_CODE': _block(toggle_lines, 0)}
        )

        callback = CustomJS(args=args, code=callback_code)
        self.ui_generator.output_checkboxes.js_on_change('active', callback)

    def _attach_save_inputs_callback(self):
        args = self._build_common_args()

        input_collection = []
        for name in self.ui_generator.input_widgets.keys():
            input_collection.append('%s: input_%s.value,' % (name, name))

        callback_code = self.template_loader.render_js_callback(
            'save_inputs_callback.js',
            {'INPUT_COLLECTION': _block(input_collection, 4)}
        )

        callback = CustomJS(args=args, code=callback_code)
        self.ui_generator.control_buttons['save_inputs'].js_on_click(callback)

    def _attach_load_inputs_callback(self):
        args = self._build_common_args()

        input_assignments = []
        for name in self.ui_generator.input_widgets.keys():
            input_assignments.append(
                'if (inputs.%s !== undefined) input_%s.value = inputs.%s'
                % (name, name, name)
            )

        callback_code = self.template_loader.render_js_callback(
            'load_inputs_callback.js',
            {'INPUT_ASSIGNMENTS': _block(input_assignments, 8)}
        )

        callback = CustomJS(args=args, code=callback_code)
        self.ui_generator.control_buttons['load_inputs'].js_on_click(callback)

    def _attach_save_csv_callback(self):
        args = self._build_common_args()
        if self.ui_generator.plot_source is not None:
            args['plot_source'] = self.ui_generator.plot_source

        all_outputs = self._get_all_outputs()
        outputs_json = _js_list(all_outputs)

        callback_code = self.template_loader.render_js_callback(
            'save_csv_callback.js',
            {'OUTPUTS_JSON': outputs_json}
        )

        callback = CustomJS(args=args, code=callback_code)
        self.ui_generator.control_buttons['save_csv'].js_on_click(callback)

    def _attach_save_png_callback(self):
        args = self._build_common_args()
        callback_code = self.template_loader.render_js_callback(
            'save_png_callback.js')
        callback = CustomJS(args=args, code=callback_code)
        self.ui_generator.control_buttons['save_png'].js_on_click(callback)


def attach_callbacks(ui_generator, js_engine: str = ''):
    """Attach all callbacks for *ui_generator* using *js_engine*."""
    BokehCallbackGenerator(ui_generator, js_engine).attach_all_callbacks()
