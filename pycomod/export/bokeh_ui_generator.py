"""Interactive Bokeh UI generation for PyCoMod models.

Compatible with Bokeh 2.4.1 and Python 3.9.7.
"""

import base64
import re
from typing import Dict, Any, Optional, List
from pathlib import Path

from bokeh.layouts import column, row
from bokeh.models import (
    Div, Button, CustomJS, NumericInput, Select, Tabs, TextInput,
    CheckboxGroup, ColumnDataSource, ScrollBox, ImportedStyleSheet,
)
from bokeh.plotting import figure

# Bokeh 2.4.x uses Panel; Bokeh 3.x renamed it to TabPanel
try:
    from bokeh.models import TabPanel as _TabPanel
except ImportError:
    from bokeh.models.widgets import Panel as _TabPanel

from .template_loader import get_loader

_COLORS = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
]


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

        self.input_widgets: Dict[str, Any] = {}
        self.control_buttons: Dict[str, Any] = {}
        self.message_div = None
        self.tabs = None

        # Plot components
        self.plot_figure = None
        self.plot_source: Optional[ColumnDataSource] = None
        self.line_renderers: Dict[str, Any] = {}
        self.output_checkboxes = None
        
        css_path = Path(__file__).resolve().parent.parent.parent / "templates" / "css" / "styles.css"
        self.css = ImportedStyleSheet(url=css_path.as_uri())

    def generate_layout(self):
        self._create_model_input_panel()
        self._create_run_input_panel()
        self._create_control_panel()
        self._create_plot_panel()
        self._create_message_panel()
        self._create_tabs()

        left_panel = column(
            self.tabs,
            self.control_panel,
            sizing_mode='stretch_both',
            min_width=320,
            max_width=450,
        )

        # This margin makes space for the banner's overhang on the right side
        right_panel = column(
            self.plot_panel,
            sizing_mode='stretch_both',
            margin=(0, 160, 0, 0),
        )

        main_content = row(
            left_panel,
            right_panel,
            sizing_mode='stretch_both',
        )

        return column(
            main_content,
            self.message_div,
            sizing_mode='stretch_both',
            margin=(0, 0, 0, 0),
        )

    def _create_model_input_panel(self):
        model_input_panel = column(sizing_mode='stretch_width', margin=(0,20,0,20))

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

            model_input_panel.children.extend([pools_header] + pool_widgets)

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

            model_input_panel.children.extend([params_header] + param_widgets)
        self.model_input_panel = ScrollBox(child=model_input_panel, vertical_scrollbar='auto', width_policy='max')

    def _create_run_input_panel(self):
        run_input_panel = column(sizing_mode='stretch_both', margin=(0,20,0,20))

        run_header = Div(text='<h3>Run Configuration</h3>')
        run_params = self.model_structure['run_params']

        date_str = run_params.get('date', '')
        if ' ' in str(date_str):
            date_str = str(date_str).split(' ')[0]
        self.date_input = TextInput(
            title='Start Date (YYYY-MM-DD)',
            value=str(date_str),
            width=360,
        )

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

        self.mode_select.js_on_change('value', CustomJS(
            args={'reps_input': self.reps_input},
            code='reps_input.disabled = (cb_obj.value !== "Monte Carlo");',
        ))

        run_input_panel.children.extend([
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
        
        self.run_input_panel = ScrollBox(child=run_input_panel, vertical_scrollbar='auto', width_policy='max')

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

        self.control_panel = column(
            Div(text='<hr>'),
            row(self.run_model_button, self.reset_button),
            row(self.save_inputs_button, self.load_inputs_button),
            sizing_mode='stretch_width',
        )

    def _create_plot_panel(self):
        outputs: List[str] = self.model_structure.get('outputs', [])

        self.plot_figure = figure(
            title='Model Output',
            x_axis_label='Time',
            y_axis_label='Value',
            width=800,
            height=500,
            sizing_mode='stretch_both',
            tools='pan,wheel_zoom,box_zoom,reset,save',
            active_drag='pan',
            active_scroll='wheel_zoom',
        )

        initial_data: Dict[str, list] = {'time': []}
        for name in outputs:
            initial_data[name] = []

        self.plot_source = ColumnDataSource(data=initial_data)

        for i, name in enumerate(outputs):
            line = self.plot_figure.line(
                x='time',
                y=name,
                source=self.plot_source,
                line_width=2,
                line_color=_COLORS[i % len(_COLORS)],
                legend_label=name,
                visible=True,
            )
            self.line_renderers[name] = line

        if outputs:
            self.plot_figure.legend.click_policy = 'hide'
            self.plot_figure.legend.location = 'top_right'

            self.output_checkboxes = CheckboxGroup(
                labels=outputs,
                active=list(range(len(outputs))),
                inline=True,
            )
            checkbox_row = column(
                Div(text='<b>Show/Hide Outputs:</b>'),
                self.output_checkboxes,
            )
        else:
            self.output_checkboxes = None
            checkbox_row = Div(text='<i>No outputs defined</i>')

        self.plot_panel = column(
            self.plot_figure,
            checkbox_row,
            sizing_mode='stretch_both',
        )

    def _create_message_panel(self):
        message_html = self.template_loader.load_html_template('message_panel.html')
        self.message_div = Div(text=message_html, sizing_mode='stretch_width', stylesheets=[self.css])

    def _create_tabs(self):
        inputs_tab = _TabPanel(
            child=self.model_input_panel,
            title='Inputs',
        )

        advanced_tab = _TabPanel(
            child=self.run_input_panel,
            title='Advanced',
        )

        if self.help_text:
            help_html = '<div style="padding: 10px;">%s</div>' % self._markdown_to_html(self.help_text)
        else:
            help_html = self.template_loader.load_html_template('help_content.html')

        help_content = Div(text=help_html)
        help_content = ScrollBox(child=help_content, sizing_mode='stretch_width', width_policy='max')
        help_tab = _TabPanel(
            child=help_content,
            title='Help',
        )

        self.tabs = Tabs(tabs=[inputs_tab, advanced_tab, help_tab], sizing_mode='stretch_both')

    def _markdown_to_html(self, markdown_text: str) -> str:
        html = markdown_text

        html = html.replace('### ', '<h4>').replace('\n', '</h4>\n', 1)
        html = html.replace('## ', '<h3>').replace('\n', '</h3>\n', 1)
        html = html.replace('# ', '<h2>').replace('\n', '</h2>\n', 1)

        html = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', html)
        html = re.sub(r'\*(.+?)\*', r'<i>\1</i>', html)

        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'((?:<li>.+</li>\n?)+)', r'<ul>\1</ul>', html)

        html = re.sub(r'\n\n', '</p><p>', html)
        html = '<p>%s</p>' % html

        return html
