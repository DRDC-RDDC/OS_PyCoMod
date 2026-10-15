"""Template loading and rendering utilities."""

from pathlib import Path
from typing import Dict, Any, Optional
import re


class TemplateLoader:
    """Load and render templates from the templates directory."""

    def __init__(self, templates_dir: Optional[Path] = None):
        """Use *templates_dir*, or the package templates directory."""
        if templates_dir is None:
            module_dir = Path(__file__).parent
            templates_dir = module_dir.parent.parent / 'templates'

        self.templates_dir = Path(templates_dir)

        if not self.templates_dir.exists():
            raise FileNotFoundError(
                f"Templates directory not found: {self.templates_dir}"
            )

    def load_template(self, template_path: str) -> str:
        """Return the raw text of a template file."""
        full_path = self.templates_dir / template_path

        if not full_path.exists():
            raise FileNotFoundError(f"Template not found: {full_path}")

        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()

    def render_template(self, template_path: str,
                        variables: Optional[Dict[str, Any]] = None) -> str:
        """Return a template with its placeholders filled in."""
        template = self.load_template(template_path)

        if variables is None:
            return template

        def replace_var(match):
            var_name = match.group(1)
            if var_name in variables:
                return str(variables[var_name])
            else:
                return match.group(0)

        rendered = re.sub(r'\{\{(\w+)\}\}', replace_var, template)
        return rendered

    def load_js_template(self, template_name: str) -> str:
        """Return a raw template from templates/js."""
        return self.load_template(f'js/{template_name}')

    def render_js_template(self, template_name: str,
                           variables: Optional[Dict[str, Any]] = None) -> str:
        """Return a rendered template from templates/js."""
        return self.render_template(f'js/{template_name}', variables)

    def load_html_template(self, template_name: str) -> str:
        """Return a raw template from templates/html."""
        return self.load_template(f'html/{template_name}')

    def render_html_template(
        self, template_name: str, variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """Return a rendered template from templates/html."""
        return self.render_template(f'html/{template_name}', variables)

    def load_js_callback(self, callback_name: str) -> str:
        """Return a raw template from templates/js/callbacks."""
        return self.load_template(f'js/callbacks/{callback_name}')

    def render_js_callback(self, callback_name: str,
                           variables: Optional[Dict[str, Any]] = None) -> str:
        """Return a rendered template from templates/js/callbacks."""
        return self.render_template(f'js/callbacks/{callback_name}', variables)


_default_loader = None


def get_loader() -> TemplateLoader:
    """Return the shared module-level TemplateLoader."""
    global _default_loader
    if _default_loader is None:
        _default_loader = TemplateLoader()
    return _default_loader


def load_template(template_path: str) -> str:
    """Return a raw template (shared loader)."""
    return get_loader().load_template(template_path)


def render_template(template_path: str,
                    variables: Optional[Dict[str, Any]] = None) -> str:
    """Return a rendered template (shared loader)."""
    return get_loader().render_template(template_path, variables)


def load_js_template(template_name: str) -> str:
    """Return a raw JS template (shared loader)."""
    return get_loader().load_js_template(template_name)


def render_js_template(template_name: str,
                       variables: Optional[Dict[str, Any]] = None) -> str:
    """Return a rendered JS template (shared loader)."""
    return get_loader().render_js_template(template_name, variables)


def load_html_template(template_name: str) -> str:
    """Return a raw HTML template (shared loader)."""
    return get_loader().load_html_template(template_name)


def render_html_template(template_name: str,
                         variables: Optional[Dict[str, Any]] = None) -> str:
    """Return a rendered HTML template (shared loader)."""
    return get_loader().render_html_template(template_name, variables)


def load_js_callback(callback_name: str) -> str:
    """Return a raw JS callback template (shared loader)."""
    return get_loader().load_js_callback(callback_name)


def render_js_callback(callback_name: str,
                       variables: Optional[Dict[str, Any]] = None) -> str:
    """Return a rendered JS callback template (shared loader)."""
    return get_loader().render_js_callback(callback_name, variables)
