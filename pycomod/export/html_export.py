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

_SVG_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "SVG Files"


def _load_svg_b64(filename: str) -> str | None:
    p = _SVG_DIR / filename
    if not p.exists():
        return None
    return base64.b64encode(p.read_bytes()).decode('utf-8')


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
    _default_banner = _pkg_dir.parent.parent / "assets" / "all_elements_banner.svg"
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
    _post_process_html(str(output_filepath), title=title)

    return str(output_filepath)


def _build_header_html(title: str, banner_image_path: str | None) -> str:
    """Build the banner header HTML. All styling is handled by the injected stylesheet."""
    fip_b64   = _load_svg_b64("Defence Identifier (FIP).svg")
    crest_b64 = _load_svg_b64("Defence Crest.svg")
    drdc_b64  = _load_svg_b64("DRDC Identifier.svg")

    fip   = f'<img class="bnr-logo bnr-fip" src="data:image/svg+xml;base64,{fip_b64}">'     if fip_b64   else ''
    crest = f'<img class="bnr-logo bnr-crest" src="data:image/svg+xml;base64,{crest_b64}">' if crest_b64 else ''
    drdc  = f'<img class="bnr-logo bnr-drdc" src="data:image/svg+xml;base64,{drdc_b64}">'   if drdc_b64  else ''
    banner_text = "ASSISTANT DEPUTY MINISTER (DEFENCE RESEARCH AND DEVELOPMENT CANADA)"

    return (
        f"""
        <div class="bnr">
            <!-- The three colour strips -->
            <div class="bnr-rb bnr-rb-1">
                {fip}
            </div>
            <div class="bnr-rb bnr-rb-2">
                <div class="bnr-txt">
                    {banner_text}
                </div>
            </div>
            <div class="bnr-rb bnr-rb-3"></div>

            <!-- Crest/DRDC column, positioned to the right -->
            <div class="bnr-right-col">
                {crest}
                {drdc}
            </div>
        </div>
        """
    )


def _post_process_html(html_filename: str, title: str = '',
                       banner_image_path: str | None = None) -> bool:
    """Inject header and custom CSS into the generated HTML file."""
    with open(html_filename, "r", encoding="utf-8") as f:
        html_content = f.read()

    if "<body>" not in html_content or "</head>" not in html_content:
        return False

    css_path = Path(__file__).resolve().parent.parent.parent / "templates" / "css" / "styles.css"
    with open(css_path, "r", encoding="utf-8") as f:
        css_rules = f.read()
    css = f"\n    <style>\n{css_rules}    </style>"
    # Keep in mind that Bokeh uses Shadow DOMs for its widgets so this won't apply to them.
    # If you want to style Bokeh widgets, apply the CSS using their "stylesheets" property
    html_content = html_content.replace("</head>", css + "\n  </head>")

    header_html = _build_header_html(title, banner_image_path)
    html_content = html_content.replace("<body>", "<body>\n" + header_html)

    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(html_content)

    return True
