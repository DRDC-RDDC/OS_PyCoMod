"""Export a PyCoMod model to a standalone interactive HTML tool."""

from __future__ import annotations

import base64
import re
from pathlib import Path

from bokeh.io import output_file, save

from ..model import Model
from .model_inspector import inspect_model
from .code_translator import CodeTranslator
from .js_simulation_engine import generate_js_engine
from .bokeh_ui_generator import BokehUIGenerator
from .bokeh_compat import BOKEH_2, get_save_resources
from .bokeh_callbacks import attach_callbacks

_SVG_DIR = Path(__file__).resolve().parent.parent.parent / \
                "assets" / "SVG Files"


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
        Name of the output HTML file.
    path : str
        Directory where the HTML file will be written.
    title : str
        Title displayed at the top of the HTML tool.
    help_text : str
        Help text shown in the Help tab. Supports basic Markdown.

    Returns
    -------
    str
        Absolute path to the generated HTML file.
    """
    out_dir = Path(path).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    output_filepath = out_dir / filename

    structure = inspect_model(model)

    translator = CodeTranslator(
        element_map=structure['element_map'],
        submodel_names=structure['submodel_names'],
    )
    translated_code = {}

    for name, info in structure.get('equations', {}).items():
        source = info.get('func_info', {}).get('source')
        if source:
            prefix = '__'.join(name.split('__')[:-1])
            result = translator.translate_lambda(source, context_prefix=prefix)
            translated_code[name] = (
                result['javascript'] if result['success'] else '0'
            )

    for name, info in structure.get('flows', {}).items():
        source = info.get('rate_func', {}).get('source')
        if source:
            prefix = '__'.join(name.split('__')[:-1])
            result = translator.translate_lambda(source, context_prefix=prefix)
            translated_code[name] = (
                result['javascript'] if result['success'] else '0'
            )

        when_info = info.get('when')
        if when_info is not None:
            when_source = when_info.get('source')
            if when_source:
                # when= lambda may share a source line with rate_func; extract
                # just its portion
                when_match = re.search(
                    r'when\s*=\s*(lambda\b.*)$', when_source
                )
                if when_match:
                    when_source = when_match.group(1)
                prefix = '__'.join(name.split('__')[:-1])
                result = translator.translate_lambda(
                    when_source, context_prefix=prefix)
                translated_code[name + '__when'] = (
                    result['javascript'] if result['success'] else 'true'
                )

    process_names = set(structure.get('processes', {}).keys())
    for name, info in structure.get('processes', {}).items():
        source = info.get('source')
        if source:
            prefix = '__'.join(name.split('__')[:-1])
            result = translator.translate_process(
                source, process_names=process_names, context_prefix=prefix)
            if result['success']:
                info['js_body'] = result['javascript']

    js_engine = generate_js_engine(structure, translated_code)

    ui_generator = BokehUIGenerator(
        model_structure=structure,
        title=title,
        help_text=help_text,
    )
    layout = ui_generator.generate_layout()

    attach_callbacks(ui_generator, js_engine)

    output_file(str(output_filepath), title=title)
    _resources = get_save_resources()
    if _resources is not None:
        save(layout, resources=_resources)
    else:
        save(layout)

    _post_process_html(str(output_filepath), title=title)

    return str(output_filepath)


def _logo_img(svg_name: str, css_class: str, alt: str) -> str:
    """Return an inline base64 <img> tag for a banner logo, or '' if absent."""
    b64 = _load_svg_b64(svg_name)
    if not b64:
        return ''
    return ('<img class="bnr-logo %s" alt="%s" '
            'src="data:image/svg+xml;base64,%s">' % (css_class, alt, b64))


def _build_header_html(title: str) -> str:
    """Return the DRDC banner HTML inserted at the top of the page body."""
    fip = _logo_img("Defence Identifier (FIP).svg", "bnr-fip",
                    "National Defence")
    crest = _logo_img("Defence Crest.svg", "bnr-crest",
                      "Department of National Defence crest")
    drdc = _logo_img("DRDC Identifier.svg", "bnr-drdc",
                     "Defence Research and Development Canada")
    banner_text = ("ASSISTANT DEPUTY MINISTER "
                   "(DEFENCE RESEARCH AND DEVELOPMENT CANADA)")

    return (
        f"""
        <div class="bnr">
            <!-- The three colour strips -->
            <div class="bnr-rb bnr-rb-1">
                {fip}
                <div class="bnr-title">
                    {title}
                </div>
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


def _decode_script_entities(html: str) -> str:
    # Bokeh HTML-encodes > and < inside JSON script tags; the browser won't
    # decode them there, breaking operators like >=.
    def _decode(m):
        content = m.group(1)
        content = (
            content.replace('&gt;', '>')
            .replace('&lt;', '<')
            .replace('&amp;', '&')
        )
        return '<script type="application/json"' + content + '</script>'

    return re.sub(
        r'<script type="application/json"(.*?)</script>',
        _decode,
        html,
        flags=re.DOTALL,
    )


def _insert_outside_scripts(html: str, tag: str, replacement: str) -> str:
    """Replace the first *tag* that is not inside a <script> element.

    The inline BokehJS bundle contains strings such as "</head><body>",
    which a plain str.replace would also modify.
    """
    scripts = [m.span() for m in
               re.finditer(r'<script\b.*?</script>', html, flags=re.DOTALL)]
    for m in re.finditer(re.escape(tag), html):
        if not any(a <= m.start() < b for a, b in scripts):
            return html[:m.start()] + replacement + html[m.end():]
    return html


def _post_process_html(html_filename: str, title: str = '') -> bool:
    with open(html_filename, "r", encoding="utf-8") as f:
        html_content = f.read()

    if "<body>" not in html_content or "</head>" not in html_content:
        return False

    html_content = _decode_script_entities(html_content)

    css_path = (Path(__file__).resolve().parent.parent.parent
                / "templates" / "css" / "styles.css")
    with open(css_path, "r", encoding="utf-8") as f:
        css_rules = f.read()
    if BOKEH_2:
        css_rules += """
/* Bokeh 2.x overrides - allow scrolling since stretch_both doesn't work */
body {
  overflow: auto !important;
  height: auto !important;
  min-height: 100vh;
}
.bk-root {
  overflow: visible !important;
}
"""
    # Bokeh uses Shadow DOMs for widgets, so this stylesheet won't reach them.
    # Style Bokeh widgets via their "stylesheets" property instead.
    css = f"\n    <style>\n{css_rules}    </style>"
    html_content = _insert_outside_scripts(
        html_content, "</head>", css + "\n  </head>")

    header_html = _build_header_html(title)
    html_content = _insert_outside_scripts(
        html_content, "<body>", "<body>\n" + header_html)

    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(html_content)

    return True
