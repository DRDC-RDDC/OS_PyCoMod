"""Interactive Bokeh UI generation for PyCoMod models.

Compatible with Bokeh 2.4.1 and Python 3.9.7.
"""

import base64
from typing import Dict, Any, Optional
from pathlib import Path

from bokeh.layouts import column, row
from bokeh.models import Div, Button, CustomJS, NumericInput, Select, Tabs, TextInput

# Bokeh 2.4.x uses Panel; Bokeh 3.x renamed it to TabPanel
try:
    from bokeh.models import TabPanel as _TabPanel
except ImportError:
    from bokeh.models.widgets import Panel as _TabPanel
from .template_loader import get_loader


class BokehUIGenerator:
    def __init__(self, model_structure: Dict[str, Any],
                 title: str = 'PyCoMod Model',
                 help_text: str = '',
                 banner_image_path: Optional[str] = None):
        self.model_structure = model_structure
        self.title = title
        self.help_text = help_text
        self.banner_image_path = banner_image_path
        self.template_loader = get_loader()

        self.input_widgets = {}
        self.control_buttons = {}
        self.message_div = None
        self.tabs = None

    def generate_layout(self):
        self._create_model_input_panel()
        self._create_run_input_panel()
        self._create_control_panel()
        self._create_message_panel()
        self._create_tabs()

        main_panel = column(
            self.tabs,
            self.control_panel,
            sizing_mode='stretch_both',
        )

        full_layout = column(
            main_panel,
            self.message_div,
            sizing_mode='stretch_both',
            margin=(0, 0, 0, 0),
        )

        return full_layout

    def _create_model_input_panel(self):
        """Create the Model Inputs panel (pools + parameters)."""
        self.model_input_panel = column(sizing_mode='stretch_width')

        if self.model_structure['pools']:
            pools_header = Div(text='<h3>Pools (Initial Values)</h3>')
            pool_widgets = []

            for name, info in self.model_structure['pools'].items():
                if info['is_vector']:
                    widget = Div(text='<b>%s:</b> Vector (shape: %s)' % (name, info['shape']))
                else:
                    widget = NumericInput(
                        title=name,
                        value=float(info['init_value']),
                        mode='float' if info['type'] == 'float' else 'int',
                        width=360,
                    )
                    self.input_widgets[name] = widget
                pool_widgets.append(widget)

            self.model_input_panel.children.extend([pools_header] + pool_widgets)

        if self.model_structure['parameters']:
            params_header = Div(text='<h3>Parameters</h3>')
            param_widgets = []

            for name, info in self.model_structure['parameters'].items():
                if info['is_vector']:
                    widget = Div(text='<b>%s:</b> Vector (shape: %s)' % (name, info['shape']))
                else:
                    widget = NumericInput(
                        title=name,
                        value=float(info['init_value']),
                        mode='float' if info['type'] == 'float' else 'int',
                        width=360,
                    )
                    self.input_widgets[name] = widget
                param_widgets.append(widget)

            self.model_input_panel.children.extend([params_header] + param_widgets)

    def _create_run_input_panel(self):
        """Create the Run Inputs panel (Advanced tab)."""
        self.run_input_panel = column(sizing_mode='stretch_width')

        run_header = Div(text='<h3>Run Configuration</h3>')
        run_params = self.model_structure['run_params']

        # --- Start date ---
        date_str = run_params.get('date', '')
        # Strip time component if present (e.g. "2026-03-25 00:00:00" -> "2026-03-25")
        if ' ' in str(date_str):
            date_str = str(date_str).split(' ')[0]
        self.date_input = TextInput(
            title='Start Date (YYYY-MM-DD)',
            value=str(date_str),
            width=360,
        )

        # --- Time unit ---
        # Parse tunit string like "1 days" -> "D"
        tunit_str = str(run_params.get('tunit', '1 days'))
        tunit_map = {
            'D': 'Days', 'days': 'Days', '1 days': 'Days',
            'M': 'Months', 'months': 'Months',
            'Y': 'Years', 'years': 'Years',
            'h': 'Hours', 'hours': 'Hours',
        }
        current_tunit = tunit_map.get(tunit_str, 'Days')
        self.tunit_select = Select(
            title='Time Unit',
            value=current_tunit,
            options=['Hours', 'Days', 'Months', 'Years'],
            width=360,
        )

        # --- Duration and time step ---
        self.duration_input = NumericInput(
            title='Duration (time units)',
            value=float(run_params['end']),
            mode='float',
            width=360,
        )

        self.dt_input = NumericInput(
            title='Time Step (dt)',
            value=float(run_params['dt']),
            mode='float',
            width=360,
        )

        # --- Plot settings ---
        self.xaxis_select = Select(
            title='Plot X-Axis Labels',
            value='Dates',
            options=['Dates', 'Time Units'],
            width=360,
        )

        self.yaxis_label_input = TextInput(
            title='Plot Y-Axis Label',
            value='Value',
            width=360,
        )

        # --- Monte Carlo ---
        self.mode_select = Select(
            title='Run Mode',
            value='Single',
            options=['Single', 'Monte Carlo'],
            width=360,
        )

        self.reps_input = NumericInput(
            title='Monte Carlo Repetitions',
            value=int(run_params['reps']),
            mode='int',
            width=300,
            disabled=True,
        )

        # Toggle reps_input enabled/disabled when mode changes
        self.mode_select.js_on_change('value', CustomJS(
            args={'reps_input': self.reps_input},
            code='reps_input.disabled = (cb_obj.value !== "Monte Carlo");',
        ))

        self.run_input_panel.children.extend([
            run_header,
            self.date_input,
            self.tunit_select,
            self.duration_input,
            self.dt_input,
            self.xaxis_select,
            self.yaxis_label_input,
            self.mode_select,
            self.reps_input,
        ])

    def _create_control_panel(self):
        self.run_model_button = Button(
            label='Run Model',
            button_type='success',
            width=150,
        )

        self.reset_button = Button(
            label='Reset',
            button_type='warning',
            width=150,
        )

        self.save_inputs_button = Button(
            label='Save Inputs',
            button_type='primary',
            width=150,
        )

        self.load_inputs_button = Button(
            label='Load Inputs',
            button_type='primary',
            width=150,
        )

        self.control_buttons = {
            'run_model': self.run_model_button,
            'reset': self.reset_button,
            'save_inputs': self.save_inputs_button,
            'load_inputs': self.load_inputs_button,
        }

        top_buttons_row = row(self.run_model_button, self.reset_button)
        bottom_buttons_row = row(self.save_inputs_button, self.load_inputs_button)

        self.control_panel = column(
            Div(text='<hr>'),
            top_buttons_row,
            bottom_buttons_row,
            sizing_mode='stretch_width',
        )

    def _create_message_panel(self):
        message_html = self.template_loader.load_html_template('message_panel.html')
        self.message_div = Div(text=message_html, sizing_mode='stretch_width')

    def _create_tabs(self):
        # Tab 1: Model Inputs (pools + parameters)
        inputs_tab = _TabPanel(
            child=self.model_input_panel,
            title='Inputs',
        )

        # Tab 2: Run Inputs (Advanced)
        advanced_tab = _TabPanel(
            child=self.run_input_panel,
            title='Advanced',
        )

        # Tab 3: Help
        if self.help_text:
            help_html = '<div style="padding: 10px;">%s</div>' % self._markdown_to_html(self.help_text)
        else:
            help_html = self.template_loader.load_html_template('help_content.html')

        help_content = Div(text=help_html, sizing_mode='stretch_width')
        help_tab = _TabPanel(
            child=help_content,
            title='Help',
        )

        self.tabs = Tabs(tabs=[inputs_tab, advanced_tab, help_tab])

    def _markdown_to_html(self, markdown_text: str) -> str:
        html = markdown_text

        html = html.replace('### ', '<h4>').replace('\n', '</h4>\n', 1)
        html = html.replace('## ', '<h3>').replace('\n', '</h3>\n', 1)
        html = html.replace('# ', '<h2>').replace('\n', '</h2>\n', 1)

        import re
        html = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', html)
        html = re.sub(r'\*(.+?)\*', r'<i>\1</i>', html)

        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'((?:<li>.+</li>\n?)+)', r'<ul>\1</ul>', html)

        html = re.sub(r'\n\n', '</p><p>', html)
        html = '<p>%s</p>' % html

        return html
