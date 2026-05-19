"""JavaScript callbacks for Bokeh UI components."""

from bokeh.models import CustomJS
from .template_loader import get_loader


class BokehCallbackGenerator:
    def __init__(self, ui_generator, js_engine: str = ''):
        self.ui_generator = ui_generator
        self.js_engine = js_engine
        self.model_structure = ui_generator.model_structure
        self.template_loader = get_loader()

    def attach_all_callbacks(self):
        self._attach_run_callback()
        self._attach_reset_callback()
        self._attach_output_toggle_callback()
        self._attach_save_inputs_callback()
        self._attach_load_inputs_callback()

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
        }
        if self.ui_generator.xaxis_formatter is not None:
            args['xaxis_formatter'] = self.ui_generator.xaxis_formatter
        if self.ui_generator.plot_figure is not None:
            args['plot_figure'] = self.ui_generator.plot_figure
        for name, widget in self.ui_generator.input_widgets.items():
            args['input_%s' % name] = widget
        outputs = self.model_structure.get('outputs', [])
        for name in outputs:
            if name in self.ui_generator.line_renderers:
                args['single_line_%s' % name] = self.ui_generator.line_renderers[name]
            if name in self.ui_generator.mc_band_renderers:
                args['mc_band_%s' % name] = self.ui_generator.mc_band_renderers[name]
            if name in self.ui_generator.mc_mean_renderers:
                args['mc_mean_%s' % name] = self.ui_generator.mc_mean_renderers[name]
        return args

    def _attach_run_callback(self):
        args = self._build_common_args()
        args['plot_source'] = self.ui_generator.plot_source

        outputs = self.model_structure.get('outputs', [])
        outputs_json = str(outputs).replace("'", '"')

        input_collection = []
        for name in self.ui_generator.input_widgets.keys():
            input_collection.append('        %s: input_%s.value,' % (name, name))

        single_hide = ['        single_line_%s.visible = false;' % n for n in outputs if n in self.ui_generator.line_renderers]
        single_show = ['        single_line_%s.visible = true;' % n for n in outputs if n in self.ui_generator.line_renderers]
        mc_hide = []
        mc_show = []
        for n in outputs:
            if n in self.ui_generator.mc_band_renderers:
                mc_hide.append('        mc_band_%s.visible = false;' % n)
                mc_show.append('        mc_band_%s.visible = true;' % n)
            if n in self.ui_generator.mc_mean_renderers:
                mc_hide.append('        mc_mean_%s.visible = false;' % n)
                mc_show.append('        mc_mean_%s.visible = true;' % n)

        callback_code = self.template_loader.render_js_callback(
            'run_callback.js',
            {
                'INPUT_COLLECTION': '\n'.join(input_collection),
                'OUTPUTS_JSON': outputs_json,
                'SINGLE_HIDE_CODE': '\n'.join(single_hide),
                'SINGLE_SHOW_CODE': '\n'.join(single_show),
                'MC_HIDE_CODE': '\n'.join(mc_hide),
                'MC_SHOW_CODE': '\n'.join(mc_show),
            }
        )

        callback = CustomJS(
            args=args,
            code=self.js_engine + '\n\n' + callback_code,
        )
        self.ui_generator.control_buttons['run_model'].js_on_click(callback)

    def _attach_reset_callback(self):
        args = self._build_common_args()
        if self.ui_generator.plot_source is not None:
            args['plot_source'] = self.ui_generator.plot_source

        run_params = self.model_structure['run_params']

        input_resets = []
        for name, widget in self.ui_generator.input_widgets.items():
            input_resets.append('    input_%s.value = %s;' % (name, widget.value))

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

        outputs = self.model_structure.get('outputs', [])
        clear_data_lines = ['    const clear_data = { time: [] };']
        for name in outputs:
            clear_data_lines.append("    clear_data['%s'] = [];" % name)
            clear_data_lines.append("    clear_data['%s_mc_median'] = [];" % name)
            clear_data_lines.append("    clear_data['%s_mc_p_low'] = [];" % name)
            clear_data_lines.append("    clear_data['%s_mc_p_high'] = [];" % name)
        if self.ui_generator.plot_source is not None:
            clear_data_lines.append('    plot_source.data = clear_data;')
        if self.ui_generator.plot_figure is not None:
            clear_data_lines.append('    plot_figure.reset.emit();')

        # Reset renderers to single-mode visibility
        for name in outputs:
            if name in self.ui_generator.line_renderers:
                clear_data_lines.append('    single_line_%s.visible = true;' % name)
            if name in self.ui_generator.mc_band_renderers:
                clear_data_lines.append('    mc_band_%s.visible = false;' % name)
            if name in self.ui_generator.mc_mean_renderers:
                clear_data_lines.append('    mc_mean_%s.visible = false;' % name)

        callback_code = self.template_loader.render_js_callback(
            'reset_callback.js',
            {
                'INPUT_RESETS': '\n'.join(input_resets),
                'DEFAULT_DATE': date_str,
                'DEFAULT_TUNIT': default_tunit,
                'DEFAULT_DURATION': float(run_params['end']),
                'DEFAULT_DT': float(run_params['dt']),
                'DEFAULT_REPS': int(run_params['reps']),
                'DEFAULT_INTERVAL': 50,
            }
        )

        full_code = callback_code.rstrip() + '\n\n// Clear plot\n' + '\n'.join(clear_data_lines)

        callback = CustomJS(args=args, code=full_code)
        self.ui_generator.control_buttons['reset'].js_on_click(callback)

    def _attach_output_toggle_callback(self):
        outputs = self.model_structure.get('outputs', [])
        if not outputs or self.ui_generator.output_checkboxes is None:
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

        toggle_lines = ['    const is_mc = mode_select.value === "Monte Carlo";']
        for i, name in enumerate(outputs):
            toggle_lines.append('    const checked_%s = checkboxes.active.includes(%d);' % (name, i))
            if name in self.ui_generator.line_renderers:
                toggle_lines.append('    single_line_%s.visible = !is_mc && checked_%s;' % (name, name))
            if name in self.ui_generator.mc_band_renderers:
                toggle_lines.append('    mc_band_%s.visible = is_mc && checked_%s;' % (name, name))
            if name in self.ui_generator.mc_mean_renderers:
                toggle_lines.append('    mc_mean_%s.visible = is_mc && checked_%s;' % (name, name))

        callback_code = self.template_loader.render_js_callback(
            'output_toggle_callback.js',
            {'TOGGLE_CODE': '\n'.join(toggle_lines)}
        )

        callback = CustomJS(args=args, code=callback_code)
        self.ui_generator.output_checkboxes.js_on_change('active', callback)

    def _attach_save_inputs_callback(self):
        args = self._build_common_args()

        input_collection = []
        for name in self.ui_generator.input_widgets.keys():
            input_collection.append('        "%s": input_%s.value,' % (name, name))

        callback_code = self.template_loader.render_js_callback(
            'save_inputs_callback.js',
            {'INPUT_COLLECTION': '\n'.join(input_collection)}
        )

        callback = CustomJS(args=args, code=callback_code)
        self.ui_generator.control_buttons['save_inputs'].js_on_click(callback)

    def _attach_load_inputs_callback(self):
        args = self._build_common_args()

        input_assignments = []
        for name in self.ui_generator.input_widgets.keys():
            input_assignments.append(
                '                if (inputs.%s !== undefined) input_%s.value = inputs.%s;'
                % (name, name, name)
            )

        callback_code = self.template_loader.render_js_callback(
            'load_inputs_callback.js',
            {'INPUT_ASSIGNMENTS': '\n'.join(input_assignments)}
        )

        callback = CustomJS(args=args, code=callback_code)
        self.ui_generator.control_buttons['load_inputs'].js_on_click(callback)


def attach_callbacks(ui_generator, js_engine: str = ''):
    callback_gen = BokehCallbackGenerator(ui_generator, js_engine)
    callback_gen.attach_all_callbacks()
