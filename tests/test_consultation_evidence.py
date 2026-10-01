"""Primary-source inspection does not mistake citation location for support."""
# qualify: platform

import copy

import pytest

from attune_harness.consultation_evidence import assessment, claims, lines


def record():
    return {'checkpoint_digest': 'before', 'contract': {'snapshot': {'digest': 'snapshot',
            'files': {'x.py': {'text': 'first\r\nactual assignment\r\nthird\r\n'}}}},
            'answers': [{'round': 0, 'participant': 'critic', 'answer': {'evidence': [
                {'path': 'x.py', 'line': 2, 'detail': 'False claim: this line proves total isolation'}]}}]}


def test_false_in_range_claim_is_unchecked_and_can_be_rejected_without_rewriting_answer():
    value = record()
    original = copy.deepcopy(value['answers'])
    row = claims(value)[0]
    assert row['support'] == 'unchecked'
    assert row['source'] == [{'line': 1, 'text': 'first'}, {'line': 2, 'text': 'actual assignment'},
                             {'line': 3, 'text': 'third'}]
    decision = assessment(value, 0, 'critic', 0, 'rejected', 'The frozen line does not support isolation')
    value['citation_assessments'] = [decision]
    assert claims(value)[0]['support'] == 'rejected'
    assert value['answers'] == original and decision['authority'] == 'advisory_host_assessment'
    assert decision['prior_checkpoint'] == 'before' and decision['snapshot_digest'] == 'snapshot'


@pytest.mark.parametrize('text,expected', [('', ['']), ('a\n', ['a']), ('a\r\nb', ['a', 'b']),
                                         ('a\vb\u2028c', ['a\vb\u2028c']), ('a\r', ['a\r'])])
def test_editor_line_numbering_preserves_control_content(text, expected):
    assert lines(text) == expected


@pytest.mark.parametrize('args', [(True, 'critic', 0, 'supported'), (0, 'unknown', 0, 'supported'),
                                 (0, 'critic', True, 'supported'), (0, 'critic', 1, 'supported'),
                                 (0, 'critic', 0, 'approve')])
def test_invalid_host_selector_or_decision_refuses(args):
    with pytest.raises(ValueError):
        assessment(record(), *args, 'Host note')


def test_real_saved_cli_inspection_and_rejection_never_dispatch_or_rewrite_model(tmp_path, capsys):
    import json
    import sys
    from attune_harness import consultation as c
    from attune_harness.cli import main

    root = tmp_path / 'source'
    root.mkdir()
    (root / 'x.py').write_bytes(b'first\r\nactual assignment\r\nthird\r\n')
    script, calls = tmp_path / 'seat.py', tmp_path / 'calls'
    script.write_text('import hashlib,json,pathlib,sys\n'
                      'raw=sys.stdin.read()\n'
                      f'with pathlib.Path({str(calls)!r}).open("ab") as calls: calls.write(b"called\\n")\n'
                      f'answer={record()["answers"][0]["answer"]!r}\n'
                      'answer.update(verdict="recommend",summary="Inspect the claim")\n'
                      'print(json.dumps({"version":1,"request_digest":hashlib.sha256(raw.encode()).hexdigest(),'
                      '"text":json.dumps(answer)}))\n', encoding='utf-8')
    cfg = {'schema_version': 1, 'question': 'Inspect', 'author': {'provider': 'codex', 'model': 'gpt-6'},
           'participants': {'critic': {'adapter': 'command', 'identity': {'provider': 'fixture', 'model': 'fixture'},
                                      'timeout': 3, 'command': [sys.executable, str(script)]}}, 'rounds': 1}
    directory = tmp_path / 'run'
    prepared = c.prepare('source-review', root, ['x.py'], cfg, directory)
    completed = c.run(directory, prepared['contract_digest'], allow_external=True)
    completed = c.load(directory)  # Compare the persisted JSON forms, including argv arrays.
    original_answers, original_events = copy.deepcopy(completed['answers']), copy.deepcopy(completed['events'])
    (root / 'x.py').write_bytes(b'changed checkout')
    before = (directory / 'record.json').read_bytes()
    assert main(['source-review', 'evidence', str(directory)]) == 0
    view = json.loads(capsys.readouterr().out)
    assert view['claims'][0]['source'][1]['text'] == 'actual assignment'
    assert view['claims'][0]['support'] == 'unchecked'
    assert (directory / 'record.json').read_bytes() == before
    common = ['source-review', 'assess-citation', str(directory), '--round', '0', '--participant', 'critic',
              '--citation', '0', '--decision', 'rejected', '--note', 'This line does not prove isolation']
    assert main([*common, '--checkpoint', 'stale']) == 2
    capsys.readouterr()
    assert (directory / 'record.json').read_bytes() == before
    assert main([*common, '--checkpoint', completed['checkpoint_digest']]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['answers'] == original_answers and result['events'] == original_events
    assert c.inspect_evidence(directory)['claims'][0]['support'] == 'rejected'
    with pytest.raises(ValueError, match='Terminal'):
        c.run(directory, prepared['contract_digest'], allow_external=True)
    assert calls.read_bytes() == b'called\n'


def test_assessment_bound_and_writer_lease_refuse(tmp_path):
    from attune_harness import consultation as c
    from attune_harness.review_store import RunStore

    root = tmp_path / 'source'
    root.mkdir()
    (root / 'x.py').write_text('x=1\n')
    cfg = {'schema_version': 1, 'question': 'Inspect', 'author': {'provider': 'codex', 'model': 'gpt-6'},
           'participants': {'critic': {'adapter': 'command', 'identity': {'provider': 'fixture', 'model': 'fixture'},
                                      'timeout': 3, 'command': ['unused']}}, 'rounds': 1}
    directory = tmp_path / 'run'
    prepared = c.prepare('source-review', root, ['x.py'], cfg, directory)
    with RunStore(directory, existing=True).lease():
        with pytest.raises(OSError, match='busy'):
            c.assess_citation(directory, prepared['checkpoint_digest'], 0, 'critic', 0, 'rejected', 'No support')
    value = record()
    value['citation_assessments'] = [{}] * 128
    with pytest.raises(ValueError, match='bound'):
        assessment(value, 0, 'critic', 0, 'rejected', 'No support')


def test_assessed_answer_survives_cancellation_during_saved_replay(tmp_path, monkeypatch):
    from threading import Event
    from attune_harness import consultation as c
    from test_consultation import prepared, completed

    _, directory, initial = prepared(tmp_path, 'roundtable')
    calls = []
    def dispatch(*args):
        calls.append(1)
        result = completed()
        result['answer']['evidence'] = [{'path': 'x.py', 'line': 1, 'detail': 'Claim'}]
        return result
    paused = c.run(directory, initial['contract_digest'], allow_external=True,
                   max_operations=2, dispatcher=dispatch)
    second = paused['answers'][1]
    assessed = c.assess_citation(directory, paused['checkpoint_digest'], second['round'],
                                second['participant'], 0, 'rejected', 'No support')
    saved_answers, saved_events = copy.deepcopy(assessed['answers']), copy.deepcopy(assessed['events'])
    cancel = Event()
    original = c.RecoveryCursor.perform
    def replay_then_cancel(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        cancel.set()
        return result
    monkeypatch.setattr(c.RecoveryCursor, 'perform', replay_then_cancel)
    c.run(directory, initial['contract_digest'], allow_external=True, cancel=cancel, dispatcher=dispatch)
    retained = c.load(directory)
    assert retained['status'] == 'cancelled'
    assert retained['answers'] == saved_answers and retained['events'] == saved_events
    assert retained['citation_assessments'] == assessed['citation_assessments']
    assert c.inspect_evidence(directory)['claims'][1]['support'] == 'rejected'
    assert len(calls) == 2
