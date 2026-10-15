"""Pure public-data tests; no proof/helper/native code is imported or executed."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('merge_inputs', ROOT / 'experiments/platform/check_windows_saved_store_merge_inputs_v1.py')
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)
BASE, HEAD, MERGE = 'a' * 40, 'b' * 40, 'c' * 40
HEADER = f'tree {"d" * 40}\nparent {BASE}\nparent {HEAD}\nauthor public\n\npublic message\n'.encode()
CONTEXT = dict(event='pull_request', sha=MERGE, head=HEAD, base=BASE)


def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def test_raw_header_keeps_parents_even_if_graph_is_shallow():
    assert check.parents(HEADER) == [BASE, HEAD]


@pytest.mark.parametrize('event,sha,head,base,actual,parents', [
    ('pull_request', MERGE, HEAD, BASE, HEAD, [BASE, HEAD]),
    ('pull_request', MERGE, HEAD, BASE, MERGE, [HEAD, BASE]),
    ('pull_request', MERGE, HEAD, BASE, MERGE, []),
    ('pull_request', MERGE, '', BASE, MERGE, [BASE, HEAD]),
    ('pull_request', MERGE, HEAD, '', MERGE, [BASE, HEAD]),
    ('workflow_dispatch', MERGE, HEAD, BASE, MERGE, [BASE, HEAD]),
    ('push', '', '', '', MERGE, [BASE]),
])
def test_provenance_refuses_wrong_checkout_or_context(event, sha, head, base, actual, parents):
    with pytest.raises(ValueError):
        check.provenance(event, sha, head, base, actual, parents)


def test_push_context_uses_actual_event_commit():
    assert check.provenance('push', HEAD, '', '', HEAD, [BASE])['actual_checkout'] == HEAD


def test_literal_driver_binding_is_data_not_execution():
    assert check.native_binding(b"raise RuntimeError('must not execute')\nNATIVE_SHA = '" + b'0' * 64 + b"'\n") == '0' * 64


@pytest.fixture
def source_tree(tmp_path, monkeypatch):
    values = {}
    for path in check.PINS:
        p = tmp_path / path; p.parent.mkdir(parents=True, exist_ok=True)
        raw = ("NATIVE_SHA = '" + '0' * 64 + "'\n").encode() if 'combined_driver' in path else ('public fixture ' + path).encode()
        p.write_bytes(raw); values[path] = raw
    monkeypatch.setattr(check, 'PINS', {p: hashlib.sha256(raw).hexdigest() for p, raw in values.items()})

    def reader(repo, *args):
        if args == ('rev-parse', 'HEAD'):
            return (MERGE + '\n').encode()
        if args == ('cat-file', 'commit', 'HEAD'):
            return HEADER
        assert args[0] == 'rev-parse' and args[1].startswith('HEAD:')
        return (blob(values[args[1][5:]]) + '\n').encode()
    return tmp_path, values, reader


def test_positive_source_identity_remains_cold_only(source_tree):
    repo, _, reader = source_tree; out = repo / 'report.json'
    assert check.execute(repo, out, CONTEXT, reader) == 0
    report = json.loads(out.read_text()); assert len(report['sources']) == 7
    assert report['status'] == 'merge_sources_verified_for_cold_control_only'
    assert report['historical_driver_matches_current_native'] is False
    for key in ['account_fixture_invoked', 'accounts_or_credentials_created', 'gui_objects_created',
                'native_methods_invoked', 'proof_invoked', 'future_account_readiness', 'production_port_allowed']:
        assert report[key] is False


@pytest.mark.parametrize('path', list(check.PINS))
def test_each_actual_source_mutation_refuses_and_retains_all_rows(source_tree, path):
    repo, _, reader = source_tree; target = repo / path
    target.write_bytes(target.read_bytes() + b'\n')
    out = repo / 'report.json'; assert check.execute(repo, out, CONTEXT, reader) == 1
    report = json.loads(out.read_text()); assert report['status'] == 'merge_sources_refused'
    assert len(report['sources']) == 7
    assert next(r for r in report['sources'] if r['path'] == path)['matched'] is False


def test_checkout_refusal_still_writes_context_and_expected_pins(source_tree):
    repo, _, reader = source_tree; out = repo / 'report.json'
    assert check.execute(repo, out, {**CONTEXT, 'sha': HEAD}, reader) == 1
    report = json.loads(out.read_text()); assert report['provenance']['actual_checkout'] == MERGE
    assert len(report['expected_sources']) == 7


def test_existing_report_is_preserved(source_tree):
    repo, _, reader = source_tree; out = repo / 'report.json'; out.write_bytes(b'prior evidence')
    with pytest.raises(ValueError):
        check.execute(repo, out, CONTEXT, reader)
    assert out.read_bytes() == b'prior evidence'


def test_head_blob_mismatch_refuses_even_with_expected_file_bytes(source_tree):
    repo, _, _ = source_tree; path = next(iter(check.PINS))
    assert check.observe_file(repo, path, check.PINS[path], lambda _: '0' * 40)['matched'] is False


def test_missing_file_has_typed_failure_without_message(tmp_path):
    row = check.observe_file(tmp_path, 'public-missing.py', '0' * 64, lambda _: HEAD)
    assert row['matched'] is False and row['failure_type'] == 'FileNotFoundError'
    assert 'message' not in row
