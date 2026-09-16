"""Documentation must separate declarations, prose, and reviewer opinion."""

from dataclasses import replace
import json

import pytest

from attune_harness.documentation import (
    Claim, api_claims, changed_sources, generate, main,
)


@pytest.fixture
def project(tmp_path):
    (tmp_path / 'api.py').write_text(
        'raise RuntimeError("must never execute")\n'
        'async def fetch(key: str, /, *, limit=3) -> bytes:\n'
        '    """Guaranteed to never fail (untrusted docstring)."""\n'
        '    return b""\n'
        'class Client:\n'
        '    pass\n'
        'def _private(): pass\n'
    )
    (tmp_path / 'test_api.py').write_text('def test_example(): pass\n')
    return tmp_path


def test_static_reference_without_importing_or_trusting_docstrings(project):
    doc = generate(project, 'api.py', tests=('test_api.py',))
    assert doc.status == 'verified'
    assert [f.claim.symbol for f in doc.findings] == ['fetch', 'Client']
    assert doc.findings[0].claim.value == 'async def fetch(key: str, /, *, limit=3) -> bytes'
    assert 'Guaranteed' not in doc.markdown()
    assert 'api.py#L2-L4' in doc.markdown()
    assert len(doc.to_dict()['sources']) == 2


@pytest.mark.parametrize('change,status', [
    ({'symbol': 'invented'}, 'refuted'),
    ({'value': 'async def fetch(key)'}, 'refuted'),
    ({'path': 'unselected.py'}, 'refuted'),
    ({'start': 0}, 'refuted'),
    ({'end': 999}, 'refuted'),
    ({'start': 3}, 'refuted'),
    ({'kind': 'behavior', 'value': 'Never raises an exception'}, 'unknown'),
    ({'kind': 'symbol', 'value': 'fetch is always correct'}, 'refuted'),
])
def test_false_or_unsupported_claims_cannot_pass(project, change, status):
    def author(evidence):
        return (replace(api_claims(evidence)[0], **change),)

    doc = generate(project, 'api.py', author=author,
                   reviewer=lambda evidence, findings: 'I approve everything')
    assert doc.status == status
    assert doc.reviewer_notes == 'I approve everything'
    assert 'advisory, unverified' in doc.markdown()


def test_same_snapshot_and_changed_tests_require_review(project):
    seen = []

    def author(evidence):
        seen.append(evidence)
        (project / 'api.py').write_text('def replacement(): pass\n')
        return api_claims(evidence)

    def reviewer(evidence, findings):
        assert evidence is seen[0]
        assert findings[0].claim.symbol == 'fetch'
        return 'Snapshot reviewed'

    doc = generate(project, 'api.py', tests=('test_api.py',), author=author, reviewer=reviewer)
    assert changed_sources(project, doc) == ('api.py',)
    (project / 'test_api.py').unlink()
    assert changed_sources(project, doc) == ('api.py', 'test_api.py')


def test_unchanged_sources_and_empty_module(project):
    doc = generate(project, 'api.py')
    assert changed_sources(project, doc) == ()
    (project / 'empty.py').write_text('# nothing public\n')
    assert generate(project, 'empty.py').status == 'unknown'


@pytest.mark.parametrize('path', ['../escape.py', '/tmp/escape.py'])
def test_outside_paths_rejected(project, path):
    with pytest.raises(ValueError):
        generate(project, path)


def test_symlink_escape_rejected(project, tmp_path_factory):
    other = tmp_path_factory.mktemp('outside') / 'other.py'
    other.write_text('def secret(): pass\n')
    (project / 'link.py').symlink_to(other)
    with pytest.raises(ValueError):
        generate(project, 'link.py')


@pytest.mark.parametrize('author', [lambda s: [], lambda s: ('invented',)])
def test_invalid_author_protocol_fails(project, author):
    with pytest.raises((TypeError, ValueError)):
        generate(project, 'api.py', author=author)


def test_reviewer_failure_propagates_without_retry(project):
    calls = []

    def reviewer(*args):
        calls.append(1)
        raise RuntimeError('offline')

    with pytest.raises(RuntimeError, match='offline'):
        generate(project, 'api.py', reviewer=reviewer)
    assert calls == [1]


def test_duplicate_declarations_do_not_claim_runtime_resolution(project):
    (project / 'api.py').write_text('def f(): pass\ndef f(x): pass\n')
    with pytest.raises(ValueError, match='Ambiguous'):
        generate(project, 'api.py')


def test_cli_prints_portable_bundle(project, monkeypatch, capsys):
    monkeypatch.setattr('sys.argv', ['documentation', 'api.py', '--root', str(project)])
    main()
    bundle = json.loads(capsys.readouterr().out)
    assert bundle['receipt']['status'] == 'verified'
    assert 'fetch' in bundle['markdown']
