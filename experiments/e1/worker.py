"""Disposable E1 worker, always executed with -I against installed packages."""
import argparse
import hashlib
import importlib.metadata
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def setup(cell, spec):
    import attune_harness
    from attune_harness.review_contract import review_form, load_registry
    corpus = cell / 'project'
    corpus.mkdir()
    document = {'broken-link': '[Quartz](missing.md)', 'unsupported-prose': 'No supported claims.'}.get(
        spec['variant'], '[Quartz retention policy](reference.md)')
    (corpus / 'guide.md').write_text(document, encoding='utf-8')
    (corpus / 'reference.md').write_text('Quartz retention policy fixture reference.', encoding='utf-8')
    write(cell / 'context.json', {'schema_version': 1, 'project_root': 'project'})
    roster = {'schema_version': 1, 'participants': {}}
    for name in ('alpha', 'gamma'):
        fault = spec['interruption'] if name == spec['from'] else 'none'
        roster['participants'][name] = {'adapter': 'command', 'tools': [], 'max_turns': 1,
            'max_tool_calls': 0, 'timeout': 5,
            'command': [sys.executable, '-I', str(HERE / 'peer.py'), str(cell), fault]}
    roster['participants']['reviewer'] = {'adapter': 'deterministic', 'tools': ['retrieve', 'verify'],
                                        'max_turns': 3, 'max_tool_calls': 2}
    config = cell / 'config.json'
    write(config, roster)
    submission = review_form(load_registry(config))['submission']
    submission.update(accepted=True, answers={
        'objective': 'Review local evidence. Preserve constraints; never repeat an uncertain request effect.',
        'query': 'nonmatchingzzzz' if spec['variant'] == 'no-results' else 'quartz retention policy',
        'document': 'project/guide.md', 'context': 'context.json', 'corpus': 'project',
        'lead': spec['from'], 'reviewer': 'reviewer'})
    write(cell / 'request.json', submission)
    package = Path(attune_harness.__file__).parent
    write(cell / 'runtime.json', {'python': sys.executable, 'harness': str(package),
        'versions': {name: importlib.metadata.version(name) for name in
                     ('attune-harness', 'attune-forms', 'attune-verify', 'attune-rag')},
        'sources': {p.name: sha(p) for p in sorted(package.glob('*.py'))}})


def produce(cell, spec):
    from attune_harness.review import review
    from attune_harness.review_store import RunStore
    save = RunStore.save

    def crash_after_save(store, record):
        save(store, record)
        events = record['events']
        if events and events[-1]['kind'] == 'participant_turn':
            target = {'prepared': 'prepared', 'saved-result': 'completed'}.get(spec['interruption'])
            if target and events[-1]['phase'] == target:
                os._exit(71)

    RunStore.save = crash_after_save  # Disposable fault injection, no installed-file edit.
    result = review(cell / 'request.json', cell / 'config.json', cell / 'run', allow_external=True)
    assert spec['interruption'] == 'lost-ack' and result['status'] == 'failed'
    write(cell / 'producer-result.json', result)


def packet_fields(cell):
    record = read(cell / 'before.json')
    event = record['events'][-1]
    return {'goal': record['accepted']['submission']['answers']['objective'],
        'acceptance_criteria': json.dumps(record['accepted']['submission'], sort_keys=True),
        'scope_assumptions': record['requirement_revision'],
        'current_state': json.dumps({'record_path': record['record_path'], 'sha256': sha(cell / 'before.json'),
            'event': {k: event[k] for k in ('event_id', 'phase', 'state', 'effect_class')},
            'completion': 'unverified; continuation required'}, sort_keys=True),
        'next_action': 'Inspect evidence; reconcile uncertain effects before continuing with ' + read(cell / 'spec.json')['to']}


def pack(cell):
    from attune.handoff import packet
    protocol = read(HERE / 'protocol.json')
    assert importlib.metadata.version('attune-ai') == protocol['baseline_attune_ai']
    assert sha(Path(packet.__file__)) == protocol['baseline_packet_sha256']
    fields = packet_fields(cell)
    assert packet.check_caps(fields) is None
    result = packet.write_packet(cell, 'experiment',
        {'schema_version': 1, 'provenance': 'experiment assertions only; no Git verification'},
        packet.assemble_sections(fields))
    assert result['ok'], result
    write(cell / 'packet-runtime.json', {'python': sys.executable, 'attune_ai': importlib.metadata.version('attune-ai'),
        'module': packet.__file__, 'sha256': sha(Path(packet.__file__)), 'public_facade_exercised': False})


def unpack(cell):
    from attune.handoff import packet
    meta, sections = packet.parse((cell / 'docs/handoffs/experiment.md').read_text(encoding='utf-8'))
    write(cell / 'outcome.json', {'status': 'operator_required', 'sections': sections, 'meta': meta,
        'accepted': json.loads(sections['acceptance_criteria']), 'requirement_revision': sections['scope_assumptions'],
        'document_outcome': None, 'human_repair_seconds': None, 'model_correctness': None})


def recover(cell, spec):
    from attune_harness.recovery import resume_review, transfer_lead, reconcile_review, UnresolvedOperation
    from attune_harness.review_store import read_record
    run, request, config = cell / 'run', cell / 'request.json', cell / 'config.json'
    record = read_record(run)
    steps = []
    if spec['interruption'] == 'lost-ack':
        for action in ('resume', 'transfer'):
            try:
                if action == 'resume':
                    resume_review(run, request, config, record['checkpoint_digest'], allow_external=True)
                else:
                    transfer_lead(run, record['checkpoint_digest'], spec['to'], 'Local comparison')
            except UnresolvedOperation as exc:
                steps.append({'action': action, 'status': 'blocked', 'detail': str(exc)})
            else:
                raise AssertionError('Uncertain effects were not blocked')
        event = record['events'][-1]
        record = reconcile_review(run, record['checkpoint_digest'], event['event_id'],
                                  reply_file=cell / (event['request_digest'] + '.reply.json'))
        steps.append({'action': 'operator_reply_reconciliation', 'status': record['status']})
    elif spec['interruption'] == 'prepared':
        record = resume_review(run, request, config, record['checkpoint_digest'], allow_external=True, max_operations=1)
        steps.append({'action': 'finish_prepared_operation', 'status': record['status']})
    record = transfer_lead(run, record['checkpoint_digest'], spec['to'], 'Local comparison')
    steps.append({'action': 'transfer', 'status': record['status']})
    result = resume_review(run, request, config, record['checkpoint_digest'], allow_external=True)
    write(cell / 'outcome.json', {'status': result['status'], 'accepted': result['accepted']['submission'],
        'requirement_revision': result['requirement_revision'], 'document_outcome': result.get('document_outcome'),
        'steps': steps, 'human_repair_seconds': None, 'model_correctness': None})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('setup', 'produce', 'pack', 'unpack', 'recover'))
    parser.add_argument('--cell', type=Path, required=True)
    args = parser.parse_args()
    cell = args.cell.absolute()
    spec = read(cell / 'spec.json')
    if args.action in ('pack', 'unpack'):
        {'pack': pack, 'unpack': unpack}[args.action](cell)
    else:
        {'setup': setup, 'produce': produce, 'recover': recover}[args.action](cell, spec)
