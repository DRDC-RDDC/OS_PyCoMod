"""JavaScript callbacks for Bokeh UI components."""

from bokeh.models import CustomJS
from .template_loader import get_loader


class BokehCallbackGenerator:
    def __init__(self, ui_generator):
        self.ui_generator = ui_generator
        self.model_structure = ui_generator.model_structure
        self.template_loader = get_loader()

    def attach_all_callbacks(self):
        self._attach_reset_callback()
        self._attach_save_inputs_callback()
        self._attach_load_inputs_callback()

    def _build_common_args(self):
        """Build the args dict shared by save/load callbacks."""
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

    def _attach_reset_callback(self):
        args = self._build_common_args()

        run_params = self.model_structure['run_params']

        # Build reset lines for model input widgets
        input_resets = []
        for name, widget in self.ui_generator.input_widgets.items():
            input_resets.append(
                '    input_%s.value = %s;' % (name, widget.value)
            )

        # Map tunit back to the Select label used in the UI
        tunit_str = str(run_params.get('tunit', '1 days'))
        tunit_map = {
            'D': 'Days', 'days': 'Days', '1 days': 'Days',
            'M': 'Months', 'months': 'Months',
            'Y': 'Years', 'years': 'Years',
            'h': 'Hours', 'hours': 'Hours',
        }
        default_tunit = tunit_map.get(tunit_str, 'Days')

        # Strip time component from date if present
        date_str = str(run_params.get('date', ''))
        if ' ' in date_str:
            date_str = date_str.split(' ')[0]

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

        callback = CustomJS(args=args, code=callback_code)
        self.ui_generator.control_buttons['reset'].js_on_click(callback)

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


def attach_callbacks(ui_generator):
    callback_gen = BokehCallbackGenerator(ui_generator)
    callback_gen.attach_all_callbacks()
