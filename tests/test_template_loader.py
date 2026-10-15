"""Tests for pycomod.export.template_loader."""

import pytest
from pathlib import Path
from pycomod.export.template_loader import TemplateLoader, get_loader


@pytest.fixture
def loader():
    return get_loader()


class TestTemplateLoaderInit:

    def test_default_templates_dir(self, loader):
        assert loader.templates_dir.exists()
        assert loader.templates_dir.name == 'templates'

    def test_custom_templates_dir(self, tmp_path):
        (tmp_path / 'js').mkdir()
        (tmp_path / 'js' / 'test.js').write_text('hello')
        tl = TemplateLoader(templates_dir=tmp_path)
        assert tl.templates_dir == tmp_path

    def test_invalid_dir_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            TemplateLoader(templates_dir=tmp_path / 'nonexistent')


class TestTemplateLoading:

    def test_load_js_templates(self, loader):
        header = loader.load_js_template('header.js')
        assert 'PyCoMod' in header

        classes = loader.load_js_template('element_classes.js')
        assert 'class Pool' in classes
        assert 'class Flow' in classes

        loop = loader.load_js_template('simulation_loop.js')
        assert 'run_simulation' in loop

        api = loader.load_js_template('public_api.js')
        assert 'PyCoModSimulation' in api

    def test_load_html_and_callback(self, loader):
        assert len(loader.load_html_template('message_panel.html')) > 0
        assert len(loader.load_js_callback('run_callback.js')) > 0

    def test_load_nonexistent_raises(self, loader):
        with pytest.raises(FileNotFoundError):
            loader.load_template('nonexistent.txt')


class TestTemplateRendering:

    def test_render_replaces_variables(self, loader):
        content = loader.load_js_template('element_initialization.js')
        assert '{{POOL_INITIALIZATION}}' in content

        rendered = loader.render_js_template(
            'element_initialization.js',
            {
                'POOL_INITIALIZATION': '// pools here',
                'PARAMETER_INITIALIZATION': '// params here',
                'EQUATION_INITIALIZATION': '// eqs here',
                'FLOW_INITIALIZATION': '// flows here',
                'PROCESS_INITIALIZATION': '// procs here',
            }
        )
        assert '{{POOL_INITIALIZATION}}' not in rendered
        assert '// pools here' in rendered
        assert '// procs here' in rendered

    def test_render_preserves_unknown_vars_and_no_vars(self, loader):
        rendered = loader.render_js_template(
            'header.js', {'NONEXISTENT': 'val'})
        assert 'PyCoMod' in rendered

        content = loader.load_js_template('header.js')
        assert content == loader.render_js_template('header.js')

    def test_render_callback(self, loader):
        rendered = loader.render_js_callback(
            'reset_callback.js',
            {
                'INPUT_RESETS': '// reset code',
                'DEFAULT_DATE': '2020-01-01',
                'DEFAULT_TUNIT': 'Days',
                'DEFAULT_DURATION': 100.0,
                'DEFAULT_DT': 1.0,
                'DEFAULT_REPS': 100,
                'DEFAULT_INTERVAL': 50,
                'DEFAULT_PNG_RESOLUTION': 1600,
            }
        )
        assert '// reset code' in rendered
        assert '2020-01-01' in rendered


class TestModuleLevelFunctions:

    def test_get_loader_singleton_and_module_functions(self):
        assert get_loader() is get_loader()

        from pycomod.export.template_loader import (
            load_js_template,
            render_js_template,
        )

        assert 'PyCoMod' in load_js_template('header.js')
        assert 'PyCoMod' in render_js_template('header.js')
