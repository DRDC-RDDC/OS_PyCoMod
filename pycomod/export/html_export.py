"""Export PyCoMod models to standalone interactive HTML tools.

Compatible with Bokeh 2.4.1 and Python 3.9.7.

This module provides the public ``export_to_html`` function which converts a
PyCoMod model into a self-contained HTML file with:

* DRDC banner image at the top of the UI
* Editable model inputs (pool initial values, parameters)
* Editable run inputs (duration, time-step, run mode, repetitions)
* Save / Load buttons for persisting inputs to a JSON text file
* Interactive plot for single-run simulation results
"""

import base64
from pathlib import Path

from bokeh.io import output_file, save

from ..model import Model
from .model_inspector import inspect_model
from .code_translator import CodeTranslator
from .js_simulation_engine import generate_js_engine
from .bokeh_ui_generator import BokehUIGenerator
from .bokeh_callbacks import attach_callbacks


def export_to_html(
    model: Model,
    filename: str = "model_output.html",
    path: str = ".",
    title: str = "PyCoMod Model",
    help_text: str = "",
) -> str:
    """Export a PyCoMod model to a standalone interactive HTML tool.

    Parameters
    ----------
    model : pycomod.Model
        An instantiated PyCoMod model (must have been built).
    filename : str
        Name of the output HTML file (e.g. ``"sir_model.html"``).
    path : str
        Directory where the HTML file will be written.  Defaults to the
        current working directory.
    title : str
        Title displayed at the top of the HTML tool.
    help_text : str
        Help / description text shown in the *Help* tab of the HTML tool.
        Basic Markdown formatting (headings, bold, italic, lists) is
        supported.

    Returns
    -------
    str
        Absolute path to the generated HTML file.
    """

    # Resolve DRDC banner path ------------------------------------------------
    _pkg_dir = Path(__file__).resolve().parent
    _default_banner = _pkg_dir.parent.parent / "assets" / "drdc_banner.jpg"
    banner_image_path = str(_default_banner) if _default_banner.exists() else None

    # Resolve output path -----------------------------------------------------
    out_dir = Path(path).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    output_filepath = out_dir / filename

    # Step 1 – Inspect model structure ----------------------------------------
    structure = inspect_model(model)

    # Step 2 – Translate lambda functions to JavaScript -----------------------
    translator = CodeTranslator(structure['element_map'])
    translated_code = {}

    for name, info in structure.get('equations', {}).items():
        func_info = info.get('func_info', {})
        source = func_info.get('source')
        if source:
            result = translator.translate_lambda(source)
            translated_code[name] = result['javascript'] if result['success'] else '0'

    for name, info in structure.get('flows', {}).items():
        func_info = info.get('rate_func', {})
        source = func_info.get('source')
        if source:
            result = translator.translate_lambda(source)
            translated_code[name] = result['javascript'] if result['success'] else '0'

    # Step 3 – Generate JavaScript simulation engine --------------------------
    js_engine = generate_js_engine(structure, translated_code)

    # Step 4 – Build Bokeh UI layout ------------------------------------------
    ui_generator = BokehUIGenerator(
        model_structure=structure,
        title=title,
        help_text=help_text,
        banner_image_path=banner_image_path,
    )
    layout = ui_generator.generate_layout()

    # Step 5 – Attach JavaScript callbacks ------------------------------------
    attach_callbacks(ui_generator, js_engine)

    # Step 6 – Write HTML file ------------------------------------------------
    output_file(str(output_filepath), title=title)
    save(layout)

    # Step 7 – Post-process (inject header + custom CSS) ---------------------
    _post_process_html(str(output_filepath), title=title,
                       banner_image_path=banner_image_path)

    return str(output_filepath)


def _build_header_html(title: str, banner_image_path: str | None) -> str:
    """Build the header HTML with title and optional banner image."""
    if banner_image_path and Path(banner_image_path).exists():
        with open(banner_image_path, 'rb') as f:
            image_data = f.read()
        encoded = base64.b64encode(image_data).decode('utf-8')
        ext = Path(banner_image_path).suffix.lower()
        mime_type = 'image/jpeg' if ext in ['.jpg', '.jpeg'] else 'image/png'
        banner_section = (
            '<div style="flex:1 1 auto; overflow:hidden; line-height:0; min-width:0;">'
            f'<img src="data:{mime_type};base64,{encoded}"'
            ' style="display:block; width:100%; height:100%; object-fit:cover; object-position:center; margin:0; padding:0;">'
            '</div>'
        )
    else:
        banner_section = '<div style="flex:1 1 auto;"></div>'

    return (
        '<div style="display:flex; align-items:stretch; width:100%;'
        ' background-color:#f0f0f0; border-bottom:2px solid #003366;'
        ' box-sizing:border-box; margin:0; padding:0;">'
        '<div style="flex:0 0 auto; padding:4px 15px; display:flex; align-items:center;">'
        f'<h1 style="margin:0; padding:0; color:#003366; font-family:Arial,sans-serif;'
        f' white-space:nowrap;">{title}</h1>'
        '</div>'
        f'{banner_section}'
        '</div>'
    )


def _post_process_html(html_filename: str, title: str = '',
                       banner_image_path: str | None = None) -> bool:
    """Inject header and custom CSS into the generated HTML file."""
    with open(html_filename, "r", encoding="utf-8") as f:
        html_content = f.read()

    if "<body>" not in html_content or "</head>" not in html_content:
        return False

    css = """
    <style>
      html, body { margin: 0; padding: 0; width: 100%; }
      .bk-input-group label { font-size: 15px !important; font-weight: 500; }
      .bk-input { font-size: 14px !important; }
      .bk-btn { font-size: 14px !important; }
      .bk-tabs-header .bk-tab { font-size: 15px !important; }
    </style>"""
    html_content = html_content.replace("</head>", css + "\n  </head>")

    header_html = _build_header_html(title, banner_image_path)
    html_content = html_content.replace("<body>", "<body>\n" + header_html)

    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(html_content)

    return True
