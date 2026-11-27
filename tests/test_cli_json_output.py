"""Check that JSON reports survive redirection to a narrow text stream.

# qualify: platform
"""

import io
import json
import sys

import pytest

from attune_harness.cli import main


@pytest.mark.parametrize('encoding', ['cp1252', 'ascii', 'utf-8'])
def test_redirected_verification_preserves_unicode_and_exit_status(tmp_path, monkeypatch, encoding):
    document = tmp_path / 'guide-東京-🪁.md'
    document.write_text('[reference](missing.md)', encoding='utf-8')
    context = tmp_path / 'context.json'
    context.write_text('{"schema_version":1,"project_root":"."}', encoding='utf-8')
    saved = tmp_path / 'result.json'
    buffer = io.BytesIO()
    with io.TextIOWrapper(buffer, encoding=encoding, errors='strict', write_through=True) as stream:
        with monkeypatch.context() as output:
            output.setattr(sys, 'stdout', stream)
            code = main(['verify', str(document), '--context', str(context), '--output', str(saved)])
        wire = buffer.getvalue()

    assert code == 1
    result = json.loads(wire.decode(encoding))
    assert result['status'] == 'refuted'
    assert result == json.loads(saved.read_text(encoding='utf-8'))
    assert document.name in result['artifacts']['document']['path']
    if encoding == 'utf-8':
        assert document.name.encode('utf-8') in wire


def test_redirected_code_config_retains_usable_project_path(tmp_path, monkeypatch):
    project = tmp_path / 'project-東京'
    project.mkdir()
    buffer = io.BytesIO()
    with io.TextIOWrapper(buffer, encoding='cp1252', errors='strict', write_through=True) as stream:
        with monkeypatch.context() as output:
            output.setattr(sys, 'stdout', stream)
            code = main(['code-config', '--repo', str(project), '--index-dir', str(tmp_path / 'index')])
        wire = buffer.getvalue()

    assert code == 0
    assert json.loads(wire)['roots'][0]['path'] == str(project.resolve())
