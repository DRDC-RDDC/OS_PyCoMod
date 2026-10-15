"""Bokeh version compatibility layer.

Centralizes all Bokeh 2.4.x / 3.x import differences and helper
wrappers so the rest of the export pipeline stays clean.

Bokeh 2.4.1 (Python 3.9.7) lacks:
  - ScrollBox             (3.0+)
  - ImportedStyleSheet    (3.0+)
  - CustomJSTickFormatter (3.0+, was FuncTickFormatter in 2.x)
  - TabPanel              (3.0+, was Panel in 2.x)
  - stylesheets kwarg     (3.0+)
"""

from __future__ import annotations

import bokeh

# ---- version detection ------------------------------------------------

_ver = tuple(int(x) for x in bokeh.__version__.split(".")[:2])
BOKEH_MAJOR = _ver[0]
BOKEH_2 = BOKEH_MAJOR < 3


# ---- conditional imports ----------------------------------------------

# TabPanel (3.x) vs Panel (2.x)
try:
    from bokeh.models import TabPanel
except ImportError:
    # type: ignore[attr-defined]
    from bokeh.models.widgets import Panel as TabPanel

# CustomJSTickFormatter (3.x) vs FuncTickFormatter (2.x)
try:
    from bokeh.models import CustomJSTickFormatter
except ImportError:
    # type: ignore[attr-defined]
    from bokeh.models import FuncTickFormatter as CustomJSTickFormatter

# ScrollBox -- Bokeh 3.0+ only
try:
    from bokeh.models import ScrollBox
except ImportError:
    ScrollBox = None  # type: ignore[assignment,misc]

# ImportedStyleSheet -- Bokeh 3.0+ only
try:
    from bokeh.models import ImportedStyleSheet
except ImportError:
    ImportedStyleSheet = None  # type: ignore[assignment,misc]

# InlineStyleSheet -- Bokeh 3.0+ only
try:
    from bokeh.models import InlineStyleSheet
except ImportError:
    InlineStyleSheet = None  # type: ignore[assignment,misc]


# ---- helper wrappers --------------------------------------------------

def make_scrollable(child, **kwargs):
    """Wrap *child* in a ScrollBox when available, otherwise return it as-is.

    On Bokeh 2.4.x the content is rendered without a scroll container;
    the layout still works, it just won't scroll independently.
    """
    if ScrollBox is not None:
        return ScrollBox(child=child, **kwargs)
    return child


def make_stylesheet(css_path):
    """Create an InlineStyleSheet from *css_path*; return None on 2.4.x.

    The CSS text is embedded in the HTML so the file works on other machines
    (an ImportedStyleSheet with a file:// URL only resolves locally).
    """
    if InlineStyleSheet is not None:
        with open(css_path, "r", encoding="utf-8") as f:
            return InlineStyleSheet(css=f.read())
    return None


def make_div(css=None, **kwargs):
    """Create a Div, attaching *css* as a stylesheet on 3.x.

    On 2.4.x the stylesheet kwarg does not exist, so it is omitted and
    the CSS file referenced by *css* is injected via inline ``<style>``
    instead (see ``_inject_inline_css``).
    """
    from bokeh.models import Div
    if css is not None:
        kwargs["stylesheets"] = [css]
    return Div(**kwargs)


def get_save_resources():
    """Return INLINE resources so the HTML works offline (no CDN)."""
    from bokeh.resources import INLINE
    return INLINE


def inject_inline_css(html: str, css_path: str) -> str:
    """On Bokeh 2.4.x, prepend the stylesheet content as an inline <style>.

    On Bokeh 3.x this is a no-op because ImportedStyleSheet handles it.
    """
    if not BOKEH_2:
        return html
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            css_text = f.read()
        return "<style>\n" + css_text + "\n</style>\n" + html
    except FileNotFoundError:
        return html
