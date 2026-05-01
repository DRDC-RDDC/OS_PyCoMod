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
        }
        for name, widget in self.ui_generator.input_widgets.items():
            args['input_%s' % name] = widget
        return args

    def _attach_run_callback(self):
        args = {
            'plot_source': self.ui_generator.plot_source,
            'message_div': self.ui_generator.message_div,
            'mode_select': self.ui_generator.mode_select,
            'duration_input': self.ui_generator.duration_input,
            'dt_input': self.ui_generator.dt_input,
            'reps_input': self.ui_generator.reps_input,
        }
        for name, widget in self.ui_generator.input_widgets.items():
            args['input_%s' % name] = widget

        outputs = self.model_structure.get('outputs', [])
        outputs_json = str(outputs).replace("'", '"')

        input_collection = []
        for name in self.ui_generator.input_widgets.keys():
            input_collection.append('        %s: input_%s.value,' % (name, name))

        callback_code = self.template_loader.render_js_callback(
            'run_callback.js',
            {
                'INPUT_COLLECTION': '\n'.join(input_collection),
                'OUTPUTS_JSON': outputs_json,
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
        if self.ui_generator.plot_source is not None:
            clear_data_lines.append('    plot_source.data = clear_data;')

        callback_code = self.template_loader.render_js_callback(
            'reset_callback.js',
            {
                'INPUT_RESETS': '\n'.join(input_resets),
                'DEFAULT_DATE': date_str,
                'DEFAULT_TUNIT': default_tunit,
                'DEFAULT_DURATION': float(run_params['end']),
                'DEFAULT_DT': float(run_params['dt']),
                'DEFAULT_REPS': int(run_params['reps']),
            }
        )

        full_code = callback_code.rstrip() + '\n\n// Clear plot\n' + '\n'.join(clear_data_lines)

        callback = CustomJS(args=args, code=full_code)
        self.ui_generator.control_buttons['reset'].js_on_click(callback)

    def _attach_output_toggle_callback(self):
        outputs = self.model_structure.get('outputs', [])
        if not outputs or self.ui_generator.output_checkboxes is None:
            return

        args = {'checkboxes': self.ui_generator.output_checkboxes}
        for name, renderer in self.ui_generator.line_renderers.items():
            args['line_%s' % name] = renderer

        toggle_lines = []
        for i, name in enumerate(outputs):
            toggle_lines.append('    line_%s.visible = checkboxes.active.includes(%d);' % (name, i))

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
