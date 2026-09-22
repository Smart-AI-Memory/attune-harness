"""Real attune-verify boundary behavior and CLI evidence preservation."""

import hashlib
import json
from pathlib import Path

import pytest

from attune_harness.cli import main
from attune_harness.features import FeatureUnavailable
from attune_harness.verification import verify_document


@pytest.fixture
def project(tmp_path):
    (tmp_path/'target.md').write_text('Reference document.', encoding='utf-8')
    context = tmp_path/'context.json'
    context.write_text(json.dumps({'schema_version':1, 'project_root':'.'}), encoding='utf-8')
    document = tmp_path/'guide.md'
    document.write_text('[reference](target.md)', encoding='utf-8')
    return document, context


@pytest.mark.parametrize('content,status,claims', [
    ('[reference](target.md)', 'verified', 1),
    ('[missing](absent.md)', 'refuted', 1),
    ('[remote](https://example.com)', 'unknown', 1),
    ('Ordinary prose without a supported claim.', 'unknown', 0),
])
def test_real_strict_results_and_evidence(project, content, status, claims):
    document, context = project
    document.write_text(content, encoding='utf-8')
    result = verify_document(document, context)
    assert result['status'] == status
    assert result['passed'] is (status == 'verified')
    assert result['result']['coverage']['total'] == claims
    assert result['artifacts']['document']['sha256'] == hashlib.sha256(content.encode()).hexdigest()
    if claims:
        assert result['result']['claims'][0]['status'] == status
        assert result['result']['claims'][0]['evidence']


def test_nested_document_resolves_links_from_document_directory(project):
    document, context = project
    nested = document.parent/'docs'
    nested.mkdir()
    document = nested/'guide.md'
    document.write_text('[reference](../target.md)', encoding='utf-8')
    assert verify_document(document, context)['status'] == 'verified'


@pytest.mark.parametrize('content,exit_code,status', [('[reference](target.md)',0,'verified'),('[x](missing)',1,'refuted'),('No claims.',1,'unknown')])
def test_cli_writes_same_report_as_stdout(project, capsys, content, exit_code, status):
    document, context = project
    document.write_text(content, encoding='utf-8')
    output = document.parent/'report.json'
    assert main(['verify',str(document),'--context',str(context),'--output',str(output)]) == exit_code
    printed = json.loads(capsys.readouterr().out)
    assert printed == json.loads(output.read_text())
    assert printed['status'] == status


def test_missing_dependency_is_actionable_even_without_input_files(tmp_path, monkeypatch, capsys):
    import attune_harness.features as features
    def absent(_):
        raise features.PackageNotFoundError()
    monkeypatch.setattr(features, 'version', absent)
    output = tmp_path/'unavailable.json'
    assert main(['verify','missing.md','--context','missing.json','--output',str(output)]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result['status'] == 'unavailable'
    assert result['error']['detail'] == 'attune-verify is missing; reinstall with: pip install --force-reinstall attune-harness'
    assert json.loads(output.read_text()) == result


def test_wrong_dependency_version_never_invokes_library(project, monkeypatch):
    monkeypatch.setattr('attune_harness.features.version', lambda _: '0.5.0')
    with pytest.raises(FeatureUnavailable, match='unsupported'):
        verify_document(*project)


@pytest.mark.parametrize('payload', [{},[],{'schema_version':True},{'schema_version':2}])
def test_invalid_manifest_schema(project, payload):
    document, context = project
    context.write_text(json.dumps(payload), encoding='utf-8')
    with pytest.raises(ValueError, match='schema_version'):
        verify_document(document, context)


def test_outside_document_rejected(project, tmp_path):
    document, context = project
    root = tmp_path/'declared'
    root.mkdir()
    context.write_text(json.dumps({'schema_version':1,'project_root':'declared'}),encoding='utf-8')
    with pytest.raises(ValueError, match='outside'):
        verify_document(document, context)


def test_changed_context_and_malformed_library_result_fail(project, monkeypatch):
    import attune_verify
    document, context = project
    original = attune_verify.verify
    def change(content, ctx):
        value = original(content, ctx)
        context.write_text('{}',encoding='utf-8')
        return value
    monkeypatch.setattr(attune_verify, 'verify', change)
    with pytest.raises(ValueError, match='changed'):
        verify_document(document, context)
    context.write_text('{"schema_version":1}',encoding='utf-8')
    monkeypatch.setattr(attune_verify, 'verify', lambda *_: {'ok':True})
    with pytest.raises(TypeError, match='invalid result'):
        verify_document(document, context)


def test_cli_refuses_input_overwrite_before_call(project, monkeypatch, capsys):
    document, context = project
    original = context.read_bytes()
    monkeypatch.setattr('attune_harness.verification.verify_document', lambda *_: pytest.fail('operation ran'))
    assert main(['verify',str(document),'--context',str(context),'--output',str(context)]) == 2
    assert context.read_bytes() == original
    assert json.loads(capsys.readouterr().out)['status'] == 'failed'


def test_cli_runtime_and_report_write_errors_are_not_success(project, monkeypatch, capsys):
    import attune_harness.cli as cli
    monkeypatch.setattr(cli,'write_report',lambda *_: (_ for _ in ()).throw(OSError('disk full')))
    assert main(['verify',str(project[0]),'--context',str(project[1]),'--output',str(project[0].parent/'out.json')]) == 2
    assert 'Report write failed' in json.loads(capsys.readouterr().out)['error']['detail']
    project[0].unlink()
    assert main(['verify',str(project[0]),'--context',str(project[1])]) == 2
    assert json.loads(capsys.readouterr().out)['status'] == 'failed'


def test_no_argument_cli_preserves_demo(capsys):
    assert main([]) == 0
    assert json.loads(capsys.readouterr().out)['status'] == 'verified'
