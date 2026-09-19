"""Freshness of a historical assessment after its separately accepted repair.

Only completed, proposal-bound replacements contribute to the expected view.
This never changes the assessment or makes its historical index current again.
"""

import copy
from pathlib import Path

from .features import read_text
from .repair import decode_patch, sha
from .review_contract import digest, parse_json, validate_registry

PROFILE = 'completed-assessment-effects-v1'


def completed_patches(record):
    """Use the actual worker result, including at pause/replay summary boundaries."""
    plan = record['request']['repair']['scope']
    run = record.get('execution', {})
    events = run.get('events', [])
    replacements = [e for e in events if e['kind'] == 'replacement']
    if not replacements:
        return {}
    assignment = run['recovery']['assignments']['assessor']
    workers = [e for e in events if e['kind'] == 'participant_turn'
               and e.get('participant_id') == assignment['participant_id']
               and e.get('attempt_id') == assignment['attempt_id']]
    if len(workers) != 1:
        raise ValueError('Repair effects lack a unique assigned worker result')
    worker = workers[0]
    action = worker.get('result', {}).get('action', {})
    if (worker['state'] != 'completed' or worker['phase'] != 'completed'
            or worker['operation_key'] != assignment['attempt_id'] + ':turn:0'
            or action.get('kind') != 'final'):
        raise ValueError('Repair effects require a completed final worker result')
    proposal = decode_patch(action['text'], plan)['replacements']
    if len(replacements) > len(proposal):
        raise ValueError('Repair effects exceed the worker proposal')
    completed = {}
    for index, event in enumerate(replacements):
        item = proposal[index]
        if (events.index(event) <= events.index(worker)
                or event['operation_key'] != 'replace:' + item['path']
                or event.get('patch') != item or event.get('plan_digest') != digest(plan)
                or event.get('effect_class') != 'file_replacement'):
            raise ValueError('Repair effect differs from its ordered worker proposal')
        if event['state'] != 'completed':
            if index != len(replacements) - 1:
                raise ValueError('Repair effect follows an unresolved replacement')
            continue
        raw = item['text'].encode('utf-8')
        expected = dict(path=item['path'], before_sha256=item['before_sha256'],
                        after_sha256=sha(raw), bytes=len(raw))
        if event['phase'] != 'completed' or event.get('result') != expected:
            raise ValueError('Repair result differs from its exact replacement bytes')
        completed[str(Path(plan['root']) / item['path'])] = item
    return completed


def index_identity(selection):
    """Freeze the valid publication at handoff time, not assessment-time vectors."""
    if selection is None:
        return None
    from .voyage_index import read_generation, table_rows
    directory, metadata = read_generation(selection['config'], selection['generation'])
    table_rows(directory, metadata)
    return dict(selection_digest=digest(selection),
                publication_sha256=sha((directory / 'published.json').read_bytes()),
                receipt_sha256=sha((directory / 'build-receipt.json').read_bytes()),
                metadata_digest=digest(metadata))


def check_registry(request):
    """Check exact config and normal participant/extension rules without retrieval."""
    path = Path(request['config']['path'])
    raw = read_text(path, 131072)
    registry = parse_json(raw)
    if (registry != request['registry']
            or sha(raw.encode('utf-8')) != request['config']['sha256']):
        raise ValueError('Stale registry for effect-aware assessment handoff')
    plain = {k: v for k, v in registry.items() if k != 'retrieval'}
    validate_registry(plain, path, minimum_participants=1)


def _after(original, path, patches):
    patch = patches.get(str(path))
    if patch is None:
        return original
    if patch['before_sha256'] != original:
        raise ValueError('Repair preimage differs from original assessment evidence')
    return sha(patch['text'].encode('utf-8'))


def check_index(selection, frozen, patches):
    from .voyage_index import read_generation
    from .voyage_sources import snapshot
    if index_identity(selection) != frozen:
        raise ValueError('Historical assessment index publication changed')
    cfg = selection['config']
    _, metadata = read_generation(cfg, selection['generation'])
    expected = copy.deepcopy(metadata['manifest'])
    actual, _ = snapshot({**cfg, 'allow_overlays': True})
    selections = {(e['repo_id'], e['path']): e['selection'] for e in actual['files']}
    roots = {r['repo_id']: Path(r['path']) for r in cfg['roots']}
    for entry in expected['files']:
        path = roots[entry['repo_id']] / entry['path']
        patch = patches.get(str(path))
        if patch is None:
            continue
        entry['sha256'] = _after(entry['sha256'], path, patches)
        raw = patch['text'].encode('utf-8')
        entry['bytes'] = len(raw)
        if entry['selection'] != 'untracked':
            # The full checkout freezes modes/Git metadata and the journal fixes
            # exact replacement bytes. Let Git classify those bytes with its
            # conversion/mode rules; raw HEAD equality misses those semantics.
            entry['selection'] = selections.get((entry['repo_id'], entry['path']))
    if actual != expected:
        raise ValueError('Assessment repository differs from original plus repaired bytes')


def check_fresh(assessment, repair_record, frozen_index):
    """Validate original evidence against only journaled repair effects."""
    request = assessment['request']
    repair_request = repair_record['request']
    check_registry(request)
    check_registry(repair_request)
    selected = request['registry'].get('retrieval')
    other = repair_request['registry'].get('retrieval')
    if other is not None and other != selected:
        raise ValueError('Effect-aware repair requires the same retrieval selection')
    patches = completed_patches(repair_record)
    expected = copy.deepcopy(request['evidence'])
    for name in ('document', 'context'):
        if name in expected:
            item = expected[name]
            item['sha256'] = _after(item['sha256'], Path(item['path']), patches)
    retrieval = expected.get('retrieval')
    from .task_contract import evidence
    answers = copy.deepcopy(request['answers'])
    registry = request['registry']
    if retrieval and retrieval['mode'] == 'voyage':
        if frozen_index is None:
            raise ValueError('Missing frozen historical index identity')
        check_index(selected, frozen_index, patches)
        # Local document/context checks stay live. The historical index was
        # checked separately and is never used for a new retrieval here.
        answers['corpus'] = None
        registry = {k: v for k, v in registry.items() if k != 'retrieval'}
        expected.pop('retrieval')
    elif retrieval and retrieval['mode'] == 'keyword':
        for name, original in list(retrieval['sources'].items()):
            retrieval['sources'][name] = _after(original, Path(retrieval['root']) / name, patches)
    actual = evidence(Path(request['project_root']), Path(assessment['record_path']).parent,
                      answers, registry)
    if actual != expected:
        raise ValueError('Assessment evidence differs from original plus repaired bytes')
