"""Audit retained local review evidence and aggregate explicit blinded judgments."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from statistics import median

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
LABEL = 'Local model review (unverified proposal):\n'


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def grade_check(grade, text, oracle):
    require(set(grade) == {'detected', 'unsupported', 'uncertainty_preserved', 'rationale'}, 'Grade fields differ')
    detected = grade['detected']
    require(isinstance(detected, list) and all(isinstance(x, str) for x in detected), 'Invalid detections')
    require(len(set(detected)) == len(detected) and set(detected) <= set(oracle['critical_issues']), 'Unknown/duplicate issue')
    require(type(grade['uncertainty_preserved']) is bool, 'Uncertainty judgment must be boolean')
    require(isinstance(grade['rationale'], str) and bool(grade['rationale'].strip()), 'Missing rationale')
    require(isinstance(grade['unsupported'], list), 'Unsupported findings must be a list')
    for finding in grade['unsupported']:
        require(set(finding) == {'quote', 'reason'}, 'Unsupported finding fields differ')
        require(isinstance(finding['quote'], str) and bool(finding['quote'].strip())
                and finding['quote'] in text, 'Unsupported quote is not exact')
        require(isinstance(finding['reason'], str) and bool(finding['reason'].strip()), 'Missing finding reason')
    require(len({x['quote'] for x in grade['unsupported']}) == len(grade['unsupported']), 'Duplicate unsupported quote')


def aggregate(rows, oracle):
    """Rows include every planned trial, including failed or unrun trials."""
    require(len({r['trial_id'] for r in rows}) == len(rows), 'Duplicate trial')
    scored = []
    for row in rows:
        case = oracle[row['case_id']]
        require(row['arm'] in ('single', 'harness'), 'Unknown arm')
        expected = 1 if row['arm'] == 'single' else 2
        narratives = row['narratives']
        require(len(narratives) <= expected, 'Too many narratives')
        for item in narratives:
            grade_check(item['grade'], item['text'], case)
        complete = row['status'] == 'completed' and len(narratives) == expected
        detected = {issue for item in narratives for issue in item['grade']['detected']}
        missing = sorted(set(case['critical_issues']) - detected)
        unsupported = sum(len(item['grade']['unsupported']) for item in narratives)
        preserved = complete and all(item['grade']['uncertainty_preserved'] for item in narratives)
        scored.append({**row, 'family': case['family'], 'complete': complete,
            'critical_opportunities': len(case['critical_issues']), 'critical_misses': missing,
            'unsupported_assertions': unsupported,
            'uncertainty_required': case['require_uncertainty'], 'uncertainty_preserved': preserved,
            'pass': complete and not missing and not unsupported and (not case['require_uncertainty'] or preserved),
            'narrative_words': sum(len(item['text'].split()) for item in narratives)})
    summaries = {}
    for arm in ('single', 'harness'):
        trials = [r for r in scored if r['arm'] == arm]
        if not trials:
            continue
        summaries[arm] = {'planned': len(trials), 'completed': sum(r['complete'] for r in trials),
            'passed': sum(r['pass'] for r in trials),
            'critical_opportunities': sum(r['critical_opportunities'] for r in trials),
            'critical_misses': sum(len(r['critical_misses']) for r in trials),
            'unsupported_assertions': sum(r['unsupported_assertions'] for r in trials),
            'ambiguous_opportunities': sum(r['uncertainty_required'] for r in trials),
            'ambiguous_preserved': sum(r['uncertainty_required'] and r['uncertainty_preserved'] for r in trials),
            'narratives': sum(len(r['narratives']) for r in trials),
            'total_narrative_words': sum(r['narrative_words'] for r in trials),
            'families': {family: {'passed': sum(r['pass'] for r in trials if r['family'] == family),
                                  'planned': sum(r['family'] == family for r in trials)}
                         for family in ('clean', 'defective', 'ambiguous')}}
        for metric in ('elapsed_seconds', 'input_tokens', 'output_tokens', 'narrative_words'):
            values = [r[metric] for r in trials if r.get(metric) is not None]
            summaries[arm]['median_' + metric] = median(values) if values else None
        summaries[arm]['correction_instances'] = summaries[arm]['critical_misses'] + summaries[arm]['unsupported_assertions']
    return {'arms': summaries, 'trials': scored, 'human_review_time': 'unmeasured'}


def audit_generation(record, trial, narrative, document, reference):
    """Check exact prompt, generation identity, evidence access and delivered text."""
    from attune_harness.ollama_review import SYSTEM, SCHEMA, OPTIONS, projected_evidence
    from attune_harness.review_contract import digest
    protocol = trial['protocol']; role = narrative['role']
    if trial['arm'] == 'harness':
        return audit_grounded(record, trial, narrative, document, reference)
    seed = trial['seed'] + (1 if role == 'reviewer' else 0)
    require(record['status'] == 'completed', 'Delivered narrative lacks completed generation')
    require(record['model_pin'] == protocol['model_pin'], 'Model pin differs')
    require(record['system'] == SYSTEM and record['seed'] == seed, 'System/seed differs')
    require(record['options'] == {**OPTIONS, 'num_predict': protocol['max_output_tokens']}, 'Options differ')
    prompt = json.loads(record['prompt'])
    require(prompt['objective'] == protocol['objective'] and prompt['document'] == document, 'Objective/document differs')
    if trial['arm'] == 'single':
        require(set(prompt) == {'objective', 'document', 'reference_material'}, 'Baseline prompt fields differ')
        require(prompt['reference_material'] == [reference], 'Baseline reference differs')
    else:
        request = record['request']; turn = request['turn']
        require(request['request_digest'] == digest(turn), 'Turn digest differs')
        require(turn['role'] == role and turn['query'] == protocol['query'], 'Role/query differs')
        require(prompt == projected_evidence(turn), 'Harness prompt projection differs')
        require([item['action']['name'] for item in turn['history']] == ['retrieve', 'verify'], 'Evidence tools differ')
        sources = turn['history'][0]['result']['sources']
        matching = [s for s in sources if s['path'] == 'reference.md']
        require(len(matching) == 1 and matching[0]['excerpt'] == reference['text'], 'Complete reference not retrieved')
        for source in sources:
            require(source['path'] in ('guide.md', 'reference.md'), 'Unexpected source in prompt')
            require(source['sha256'] == sha(Path(trial['corpus'])/source['path']), 'Retrieved source hash differs')
    generation = record['generation']; payload = record['generation_request']
    require(payload == {'model': protocol['model_pin']['name'], 'system': SYSTEM, 'prompt': record['prompt'],
        'format': SCHEMA, 'stream': False, 'keep_alive': '5m', 'truncate': False, 'shift': False,
        'options': {**record['options'], 'seed': seed}}, 'Generation request differs')
    require(generation['done'] is True and generation['done_reason'] == 'stop', 'Incomplete generation')
    require(generation['local_identity'] == {'model': protocol['model_pin']['name'],
        **{k: protocol['model_pin'][k] for k in ('digest', 'server_version')}}, 'Generation identity differs')
    require(json.loads(generation['response']) == record['response'], 'Raw response differs')
    require(narrative['text'] == LABEL + record['response']['review'], 'Delivered narrative differs')
    accounting = record['context_accounting']
    require(accounting['kind'] == 'model_tokens' and accounting['remaining_after_reserves'] >= 0, 'Invalid token accounting')
    require(accounting['input_units'] == generation['prompt_eval_count'], 'Input token drift')


def audit_grounded(record, trial, narrative, document, reference):
    from attune_harness.grounded_review import project, render, SYSTEM, SCHEMA
    from attune_harness.ollama_review import OPTIONS
    from attune_harness.review_contract import digest
    protocol = trial['protocol']; turn = record['request']['turn']
    seed = trial['seed'] + (1 if narrative['role'] == 'reviewer' else 0)
    require(record['status'] == 'completed' and record['output_contract'] == 'grounded-v1', 'Strict contract absent')
    require(turn['role'] == narrative['role'] and record['seed'] == seed, 'Role/seed differs')
    require(record['request']['request_digest'] == digest(turn), 'Turn digest differs')
    require(turn['document'] == document and turn['objective'] == protocol['objective'], 'Input differs')
    require(json.loads(record['prompt']) == project(turn), 'Grounded prompt differs')
    require([h['action']['name'] for h in turn['history']] == ['retrieve', 'verify'], 'Tool history differs')
    refs = project(turn)['references']
    require(len(refs) == 1 and refs[0]['path'] == 'reference.md' and refs[0]['text'] == reference['text'], 'Reference access differs')
    require(refs[0]['sha256'] == sha(Path(reference['path'])), 'Reference hash differs')
    options = {**OPTIONS, 'num_predict': protocol['max_output_tokens']}
    require(record['system'] == SYSTEM and record['options'] == options, 'Runtime differs')
    require(record['generation_request'] == {'model': protocol['model_pin']['name'], 'system': SYSTEM,
        'prompt': record['prompt'], 'format': SCHEMA, 'stream': False, 'keep_alive': '5m',
        'truncate': False, 'shift': False, 'options': {**options, 'seed': seed}}, 'Payload differs')
    generation = record['generation']
    require(generation['done'] is True and generation['done_reason'] == 'stop', 'Generation incomplete')
    require(generation['local_identity'] == {'model': protocol['model_pin']['name'],
        **{k: protocol['model_pin'][k] for k in ('digest', 'server_version')}}, 'Generation identity differs')
    require(json.loads(generation['response']) == record['response'], 'Raw response differs')
    require(render(record['response'], turn) == narrative['text'], 'Rendered narrative differs')
    accounting = record['context_accounting']
    require(accounting['kind'] == 'model_tokens' and accounting['remaining_after_reserves'] >= 0, 'Context reserve differs')
    require(accounting['input_units'] == generation['prompt_eval_count'], 'Token count differs')


def audit_and_score(output, grades_path):
    # Import the frozen runner explicitly: no package or source-path assumptions.
    spec = importlib.util.spec_from_file_location('review_quality_runner', HERE/'run.py')
    runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
    runner.verify_freeze(output)
    for name, expected in read(output/'blind-freeze.json').items():
        require(sha(output/name) == expected, 'Blind artifact changed')
    packet, mapping, grades = read(output/'blind-packet.json'), read(output/'blind-mapping.json'), read(grades_path)
    require(len({p['id'] for p in packet}) == len(packet), 'Duplicate blinded ID')
    require(set(grades) == set(mapping) == {p['id'] for p in packet}, 'Missing/extra blinded grades')
    for item in packet:
        mapped = mapping[item['id']]
        require({k: mapped[k] for k in ('case_id', 'text', 'text_sha256')} == {k: item[k] for k in ('case_id', 'text', 'text_sha256')}, 'Blind mapping differs')
        require(runner.text_sha(item['text']) == item['text_sha256'], 'Narrative hash differs')
    lookup = {(m['trial_id'], m['narrative_index']): key for key, m in mapping.items()}
    require(len(lookup) == len(mapping), 'Duplicate narrative mapping')
    plan = read(output/'plan.json'); protocol = read(HERE/'protocol.json'); oracle = read(HERE/'oracle.json')
    expected = {(case, arm, repeat) for case in protocol['cases'] for arm in (protocol['arms'] if case in protocol['fresh_cases'] else ['harness']) for repeat in range(protocol['repeats'])}
    require(len(plan) == len(expected) and {(t['case_id'], t['arm'], t['repeat']) for t in plan} == expected, 'Scheduled trials differ')
    rows, receipts, used_ids = [], [], set()
    for index, trial in enumerate(plan):
        require(trial['protocol'] == protocol, 'Trial protocol differs')
        require(trial['seed'] == protocol['base_seed'] + protocol['cases'].index(trial['case_id'])*100 + trial['repeat']*2, 'Trial seed differs')
        path = output/f'{index:03}'/'result.json'
        result = read(path) if path.exists() else {'status': 'unrun', 'narratives': [], 'generation_records': []}
        if path.exists():
            require(all(result[k] == trial[k] for k in ('trial_id', 'case_id', 'arm', 'repeat')), 'Trial identity differs')
        items = []
        corpus = Path(trial['corpus'])
        document = {'path': str(corpus/'guide.md'), 'text': (corpus/'guide.md').read_text()}
        reference = {'path': str(corpus/'reference.md'), 'text': (corpus/'reference.md').read_text()}
        records = [read(p) for p in result['generation_records']]
        for record in records:
            require(record['model_pin'] == protocol['model_pin'], 'Receipt model pin differs')
            if record['status'] == 'failed' and trial['arm'] == 'harness' and record.get('generation'):
                # Retained invalid output must still fail the frozen strict contract.
                from attune_harness.grounded_review import render
                try:
                    render(json.loads(record['generation']['response']), record['request']['turn'])
                except (ValueError, TypeError, KeyError):
                    pass
                else:
                    require(False, 'Failed output unexpectedly satisfies strict contract')
        receipts.extend(result['generation_records'])
        for n, narrative in enumerate(result['narratives']):
            key = lookup.get((trial['trial_id'], n)); require(key is not None, 'Ungraded delivered narrative')
            used_ids.add(key); mapped = mapping[key]
            require(mapped['result_sha256'] == sha(path) and mapped['case_id'] == trial['case_id'], 'Result hash/identity differs')
            text = narrative['text'].removeprefix(LABEL)
            require(mapped['text'] == text, 'Mapped text differs')
            candidates = [r for r in records if r.get('seed') == trial['seed'] + (narrative['role'] == 'reviewer')]
            require(len(candidates) == 1, 'Missing/duplicate generation for narrative')
            audit_generation(candidates[0], trial, narrative, document, reference)
            items.append({'blind_id': key, 'role': narrative['role'], 'text': text, 'grade': grades[key]})
        roles = [n['role'] for n in result['narratives']]
        require(len(set(roles)) == len(roles), 'Duplicate narrative role')
        if result['status'] == 'completed':
            require(set(roles) == ({'single'} if trial['arm'] == 'single' else {'lead', 'reviewer'}), 'Completed trial lacks roles')
            require(len(records) == len(roles), 'Completed trial generation count differs')
        rows.append({**{k: trial[k] for k in ('trial_id', 'case_id', 'arm', 'repeat')},
            'status': result['status'], 'narratives': items,
            **{k: result.get(k) for k in ('elapsed_seconds', 'input_tokens', 'output_tokens')}})
    require(used_ids == set(mapping), 'Orphaned grades')
    require(len(set(receipts)) == len(receipts) <= protocol['max_generations'], 'Generation count differs')
    summary = aggregate(rows, oracle); harness = summary['arms']['harness']
    complete = all(arm['completed'] == arm['planned'] for arm in summary['arms'].values())
    acceptance = protocol['acceptance']
    passed = (harness['completed'] == acceptance['completed_harness_trials']
        and harness['critical_opportunities'] == acceptance['critical_opportunities']
        and harness['critical_misses'] == acceptance['critical_misses']
        and harness['unsupported_assertions'] == acceptance['unsupported_assertions']
        and harness['ambiguous_preserved'] == acceptance['ambiguous_trials_preserving_uncertainty'])
    observed = all((output/f'{i:03}'/'result.json').exists() for i in range(len(plan)))
    summary.update(disposition='inconclusive' if not observed else 'pass' if passed else 'revise',
        audit='passed', generation_records=len(receipts), grades_sha256=sha(grades_path),
        freeze_sha256=sha(output/'freeze.json'), grading='Codex blinded narrative judgment in the existing session; no independent human replication')
    (output/'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--grades', type=Path, required=True)
    args = parser.parse_args()
    summary = audit_and_score(args.output.absolute(), args.grades.absolute())
    print(json.dumps({k: v for k, v in summary.items() if k != 'trials'}, indent=2))
