"""Export PyCoMod models to standalone interactive HTML tools.

Compatible with Bokeh 2.4.1 and Python 3.9.7.

This module provides the public ``export_to_html`` function which converts a
PyCoMod model into a self-contained HTML file with:

* DRDC banner image at the top of the UI
* Editable model inputs (pool initial values, parameters)
* Editable run inputs (duration, time-step, run mode, repetitions)
* Save / Load buttons for persisting inputs to a JSON text file
"""

from pathlib import Path

from bokeh.io import output_file, save

from ..model import Model
from .model_inspector import inspect_model
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

    # Step 2 – Build Bokeh UI layout ------------------------------------------
    ui_generator = BokehUIGenerator(
        model_structure=structure,
        title=title,
        help_text=help_text,
        banner_image_path=banner_image_path,
    )
    layout = ui_generator.generate_layout()

    # Step 3 – Attach JavaScript callbacks (save/load inputs) -----------------
    attach_callbacks(ui_generator)

    # Step 4 – Write HTML file ------------------------------------------------
    output_file(str(output_filepath), title=title)
    save(layout)

    # Step 5 – Post-process (inject custom CSS) -------------------------------
    _post_process_html(str(output_filepath))

    return str(output_filepath)


def _post_process_html(html_filename: str) -> bool:
    """Inject custom CSS for banner and input styling."""
    with open(html_filename, "r", encoding="utf-8") as f:
        html_content = f.read()

    if "</head>" not in html_content:
        return False

    injections = """
    <style>
      .bk-input-group label { font-size: 15px !important; font-weight: 500; }
      .bk-input { font-size: 14px !important; }
      .bk-btn { font-size: 14px !important; }
      .bk-tabs-header .bk-tab { font-size: 15px !important; }
      .pycomod-banner > div { height: 100% !important; width: 100% !important;
                              padding: 0 !important; margin: 0 !important; line-height: 0; }
      .pycomod-banner > div > div { height: 100% !important; width: 100% !important; }
    </style>"""

    html_content = html_content.replace("</head>", injections + "\n  </head>")

    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(html_content)

    return True
