"""Tests for pycomod.export.html_export (integration)."""

import os
import pytest
from pathlib import Path
from pycomod.export.html_export import (
    export_to_html,
    _decode_script_entities,
    _build_header_html,
    _post_process_html,
)


class TestDecodeScriptEntities:

    def test_decodes_entities_inside_json_scripts(self):
        html = ('<script type="application/json">'
                'x &gt;= 5 &amp;&amp; y &lt; 10</script>')
        result = _decode_script_entities(html)
        assert 'x >= 5 && y < 10' in result

    def test_does_not_decode_outside_json_scripts(self):
        html = '<div>&gt;</div><script type="application/json">&gt;</script>'
        result = _decode_script_entities(html)
        assert '<div>&gt;</div>' in result

        regular = '<script>var x = 5 &gt; 3;</script>'
        assert '&gt;' in _decode_script_entities(regular)

    def test_multiline_and_empty_scripts(self):
        multiline = ('<script type="application/json">'
                     '\n{\n  "a": "b &gt; c"\n}\n</script>')
        assert '"b > c"' in _decode_script_entities(multiline)

        empty = '<script type="application/json"></script>'
        assert '<script type="application/json"' in _decode_script_entities(
            empty)


class TestBuildHeaderHtml:

    def test_returns_header_with_title(self):
        result = _build_header_html('My Model')
        assert isinstance(result, str)
        assert 'My Model' in result
        assert 'bnr' in result
        assert 'bnr-title' in result


class TestPostProcessHtml:

    def test_injects_header_css_and_decodes_entities(self, tmp_path):
        html_file = tmp_path / 'test.html'
        html_file.write_text(
            '<html><head></head><body>'
            '<script type="application/json">x &gt;= 5</script>'
            '</body></html>',
            encoding='utf-8',
        )
        assert _post_process_html(str(html_file), title='Test') is True
        content = html_file.read_text(encoding='utf-8')
        assert '<style>' in content
        assert 'bnr' in content
        assert 'x >= 5' in content

    def test_returns_false_for_malformed_html(self, tmp_path):
        html_file = tmp_path / 'bad.html'
        html_file.write_text('<div>no body tag</div>', encoding='utf-8')
        assert _post_process_html(str(html_file), title='Test') is False


class TestExportToHtmlIntegration:

    def test_simple_sir_export(self, simple_sir, tmp_path):
        output = export_to_html(
            model=simple_sir,
            filename='test_sir.html',
            path=str(tmp_path),
            title='My SIR Model',
            help_text='# Custom Help\nSome description here.',
        )
        assert Path(output).exists()
        assert os.path.isabs(output)
        assert output.endswith('test_sir.html')

        content = Path(output).read_text(encoding='utf-8')
        assert len(content) > 1000
        assert 'My SIR Model' in content
        assert 'PyCoMod' in content
        assert 'run_simulation' in content
        assert '<style>' in content
        assert 'Custom Help' in content

    def test_creates_nested_output_directory(self, simple_sir, tmp_path):
        nested = tmp_path / 'sub' / 'dir'
        output = export_to_html(
            model=simple_sir, filename='test.html', path=str(nested),
        )
        assert Path(output).exists()

    def test_step_impulse_model_export(self, sir_step_impulse, tmp_path):
        output = export_to_html(
            model=sir_step_impulse, filename='test_si.html',
            path=str(tmp_path), title='Step Impulse Test',
        )
        content = Path(output).read_text(encoding='utf-8')
        assert 'new Step' in content
        assert 'new Impulse' in content

    def test_submodel_export(self, two_region_sir, tmp_path):
        output = export_to_html(
            model=two_region_sir, filename='test_sub.html',
            path=str(tmp_path), title='Sub-model Test',
        )
        content = Path(output).read_text(encoding='utf-8')
        assert 'r1__S' in content
        assert 'r2__S' in content

    def test_process_model_export(self, process_model, tmp_path):
        output = export_to_html(
            model=process_model, filename='test_proc.html',
            path=str(tmp_path), title='Process Test',
        )
        content = Path(output).read_text(encoding='utf-8')
        assert 'new Process' in content
        assert 'function * (' in content

    def test_minimal_model_export(self, minimal_model, tmp_path):
        output = export_to_html(
            model=minimal_model, filename='test_min.html', path=str(tmp_path),
        )
        assert Path(output).exists()

    def test_feature_model_export(self, feature_model, tmp_path):
        output = export_to_html(
            model=feature_model, filename='test_feat.html', path=str(tmp_path),
        )
        content = Path(output).read_text(encoding='utf-8')
        assert 'yield sub.call(1)' in content
        assert 'sub.call(2).start()' in content
        assert 'sub.call(3).start(wait_delay(1))' in content
