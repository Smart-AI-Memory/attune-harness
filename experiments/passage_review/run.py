"""Frozen dev7 passage-review trial with a dev5 baseline on fresh cases."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def text_sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def worker(envelope, output):
    # This branch runs with the selected interpreter and -I, outside source imports.
    from attune_harness.llama_tokens import LlamaTokenizer
    from attune_harness.ollama import LocalModel, ModelPin, parse
    from attune_harness.ollama_review import SYSTEM, SCHEMA, OPTIONS
    from attune_harness.review import review
    from attune_harness.review_contract import digest, fields, load_registry, review_form
    from attune_harness.review_participants import decode_action
    trial = read(envelope); protocol = trial['protocol']; output.mkdir()
    corpus = Path(trial['corpus']); document = corpus/'guide.md'
    context = output/'context.json'; write(context, {'schema_version': 1, 'project_root': str(corpus)})
    started = time.monotonic()
    result = {'trial_id': trial['trial_id'], 'case_id': trial['case_id'], 'arm': trial['arm'],
              'repeat': trial['repeat'], 'status': 'prepared', 'narratives': [], 'generation_records': []}
    write(output/'result.json', result)
    try:
        if trial['arm'] == 'single':
            pin = ModelPin(**protocol['model_pin'])
            model = LocalModel(pin, tokenizer=LlamaTokenizer(trial['tokenizer_file'], pin))
            prompt = json.dumps({'objective': protocol['objective'],
                'document': {'path': str(document), 'text': document.read_text()},
                'reference_material': [{'path': str(corpus/'reference.md'), 'text': (corpus/'reference.md').read_text()}]},
                ensure_ascii=False, separators=(',', ':'))
            options = {**OPTIONS, 'num_predict': protocol['max_output_tokens']}
            saved = {'status': 'prepared', 'prompt': prompt, 'system': SYSTEM, 'options': options,
                     'seed': trial['seed'], 'model_pin': protocol['model_pin']}
            record_path = output/'generation.json'; write(record_path, saved)
            result['generation_records'] = [str(record_path)]
            try:
                saved['status'] = 'dispatching'; write(record_path, saved)
                generated = model.generate(prompt, system=SYSTEM, schema=SCHEMA, seed=trial['seed'], options=options)
                value = parse(generated['response']); fields(value, ('review',))
                if not isinstance(value['review'], str) or not value['review'].strip():
                    raise ValueError('Review must contain nonempty text')
                action = {'kind': 'final', 'text': 'Local model review (unverified proposal):\n' + value['review']}
                raw = json.dumps({'schema_version': 1, 'request_digest': digest(trial), 'action': action}, ensure_ascii=False)
                decode_action(raw, digest(trial))
                saved.update(status='completed', generation=generated, response=value)
                result['narratives'] = [{'role': 'single', 'text': action['text']}]
            except Exception as exc:
                saved.update(status='failed', error=str(exc), generation=model.last_response)
                raise
            finally:
                saved.update(generation_request=model.last_request, generation_attempted=model.generation_attempted,
                             context_accounting=model.last_context_accounting)
                write(record_path, saved)
        else:
            pin = protocol['model_pin']; generations = output/'generations'; generations.mkdir()
            command = [sys.executable, '-I', '-m', 'attune_harness.ollama_review', '--model', pin['name'],
                '--digest', pin['digest'], '--server-version', pin['server_version'], '--receipts', str(generations),
                '--max-output-tokens', str(protocol['max_output_tokens']), '--tokenizer-file', trial['tokenizer_file'], '--grounded-passages']
            config = output/'participants.json'
            write(config, {'schema_version': 1, 'participants': {role: {
                'adapter': 'command', 'command': command + ['--seed', str(trial['seed'] + offset)],
                'tools': ['retrieve', 'verify'], 'max_turns': 3, 'max_tool_calls': 2, 'timeout': 75}
                for role, offset in [('lead', 0), ('reviewer', 1)]}})
            request = output/'request.json'; submission = review_form(load_registry(config))['submission']
            submission.update(accepted=True, answers={'objective': protocol['objective'], 'query': protocol['query'],
                'document': str(document), 'context': str(context), 'corpus': str(corpus), 'lead': 'lead', 'reviewer': 'reviewer'})
            write(request, submission)
            record = review(request, config, output/'review', allow_external=True)
            result.update(workflow_status=record['status'], document_outcome=record.get('document_outcome'),
                          verification=record.get('verification'), events=record['events'])
            result['generation_records'] = [str(p) for p in sorted(generations.glob('*/record.json'))]
            result['narratives'] = [{'role': role, 'text': item['text']} for role, item in record['participants'].items()
                                   if isinstance(item.get('text'), str)]
            if record['status'] != 'completed':
                raise RuntimeError('Harness workflow did not complete: ' + str(record.get('error')))
            if len(result['narratives']) != 2 or any(item['tool_calls'] != 2 for item in record['participants'].values()):
                raise ValueError('Harness did not deliver both independent evidence reviews')
        result['status'] = 'completed'
    except Exception as exc:
        result.update(status='failed', error={'type': type(exc).__name__, 'detail': str(exc)})
    finally:
        result['elapsed_seconds'] = time.monotonic() - started
        # A failed Harness invocation may have persisted its generation before returning.
        if trial['arm'] == 'harness':
            result['generation_records'] = [str(p) for p in sorted((output/'generations').glob('*/record.json'))]
        result['input_tokens'] = result['output_tokens'] = 0
        for name in result['generation_records']:
            generation = read(name).get('generation') or {}
            result['input_tokens'] += generation.get('prompt_eval_count', 0)
            result['output_tokens'] += generation.get('eval_count', 0)
        write(output/'result.json', result)


def verify_freeze(output):
    frozen = read(output/'freeze.json')
    for name, expected in frozen['sources'].items():
        if sha(ROOT/name) != expected:
            raise ValueError('Frozen source changed: ' + name)
    for name, expected in frozen['inputs'].items():
        if sha(output/name) != expected:
            raise ValueError('Frozen trial input changed: ' + name)
    if sha(frozen['tokenizer_file']) != frozen['tokenizer_sha256']:
        raise ValueError('Frozen tokenizer changed')
    return frozen


def prepare(python, profile, output):
    output = output.resolve()
    protocol, cases = read(HERE/'protocol.json'), read(HERE/'cases.json')
    output.mkdir(parents=True, exist_ok=False)
    identity_code = ('import json,hashlib,pathlib,importlib.metadata as m,attune_harness; '
        'print(json.dumps(dict(version=m.version("attune-harness"),location=attune_harness.__file__,sources={'
        '"attune_harness/"+p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in pathlib.Path(attune_harness.__file__).parent.glob("*.py")})))')
    identity = json.loads(subprocess.check_output([str(python), '-I', '-c', identity_code], cwd=output, text=True))
    artifact = read(ROOT/'docs/receipts/passage-review/artifact.json')
    assert identity['version'] == protocol['package_version'] and identity['sources'] == artifact['installed']['sources']
    assert sha(artifact['wheel']) == protocol['wheel_sha256']
    write(output/'installed.json', identity)
    baseline = json.loads(subprocess.check_output([str(ROOT/'.venv-token-accounting/bin/python'), '-I', '-c', identity_code], cwd=output, text=True))
    old_artifact = read(ROOT/'docs/receipts/token-accounting/artifact.json')
    assert baseline['version'] == '0.1.0.dev5' and baseline['sources'] == old_artifact['installed']['sources']
    write(output/'baseline-installed.json', baseline)
    if [case['id'] for case in cases] != protocol['cases']:
        raise ValueError('Case list differs from protocol')
    # Offline validation only; a malformed or unqualified profile fails before calls.
    check_code = ('import json,sys; from attune_harness.llama_tokens import LlamaTokenizer; '
        'from attune_harness.ollama import ModelPin; '
        't=LlamaTokenizer(sys.argv[1], ModelPin(**json.loads(sys.argv[2]))); '
        'print(json.dumps(t.identity))')
    profile_identity = json.loads(subprocess.check_output([str(python), '-I', '-c', check_code,
        str(profile), json.dumps(protocol['model_pin'])], cwd=output, text=True))
    write(output/'tokenizer-identity.json', profile_identity)
    envelopes = []
    for index, case in enumerate(cases):
        corpus = output/'cases'/case['id']; corpus.mkdir(parents=True)
        (corpus/'guide.md').write_text(case['document']); (corpus/'reference.md').write_text(case['reference'])
        for repeat in range(protocol['repeats']):
            for arm in (protocol['arms'] if case['id'] in protocol['fresh_cases'] else ['harness']):
                envelopes.append({'trial_id': f"{case['id']}.{arm}.{repeat}", 'case_id': case['id'], 'arm': arm,
                    'repeat': repeat, 'seed': protocol['base_seed'] + index*100 + repeat*2,
                    'corpus': str(corpus), 'tokenizer_file': str(profile), 'protocol': protocol, 'python': str(python) if arm == 'harness' else str(ROOT/'.venv-token-accounting/bin/python')})
    random.Random(protocol['order_seed']).shuffle(envelopes)
    (output/'envelopes').mkdir()
    for i, envelope in enumerate(envelopes): write(output/'envelopes'/f'{i:03}.json', envelope)
    write(output/'plan.json', envelopes)
    sources = [*sorted(HERE.glob('*.py')), *sorted(HERE.glob('*.json')), *sorted(HERE.glob('*.md')),
               ROOT/'docs/design-passage-review.md', ROOT/'tests/test_passage_review.py',
               *sorted((ROOT/'src/attune_harness').glob('*.py'))]
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    for name in hashes:
        destination = output/'sources'/name; destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT/name).read_bytes())
    inputs = {str(p.relative_to(output)): sha(p) for p in [*sorted((output/'cases').rglob('*.md')),
              *sorted((output/'envelopes').glob('*.json')), output/'plan.json', output/'installed.json',
              output/'tokenizer-identity.json', output/'baseline-installed.json']}
    write(output/'freeze.json', {'sources': hashes, 'inputs': inputs, 'tokenizer_file': str(profile),
                                'tokenizer_sha256': sha(profile), 'python': str(python)})
    print(json.dumps({'status': 'frozen', 'trials': len(envelopes), 'max_generations': protocol['max_generations']}))


def execute(output):
    frozen = verify_freeze(output); plan = read(output/'plan.json'); protocol = plan[0]['protocol']
    if (output/'execution-started.json').exists(): raise ValueError('Campaign already started; no automatic rerun')
    write(output/'execution-started.json', {'unix_time': time.time(), 'max_generations': protocol['max_generations']})
    started = time.monotonic(); rows = []
    for index, trial in enumerate(plan):
        verify_freeze(output)
        if time.monotonic() - started > protocol['max_seconds']: raise RuntimeError('Campaign time budget exhausted')
        directory = output/f'{index:03}'
        process = subprocess.run([trial['python'], '-I', str(HERE/'run.py'), '--worker',
            str(output/'envelopes'/f'{index:03}.json'), '--output', str(directory)], cwd=output,
            capture_output=True, text=True, timeout=200)
        write(output/f'process-{index:03}.json', {'exit': process.returncode, 'stdout': process.stdout, 'stderr': process.stderr})
        if process.returncode or not (directory/'result.json').exists():
            raise RuntimeError('Worker failed; retain partial campaign and do not retry: ' + process.stderr)
        result = read(directory/'result.json')
        rows.append({'directory': str(directory), 'trial_id': trial['trial_id'], 'status': result['status'],
                     'generations': len(result['generation_records'])})
        assert sum(r['generations'] for r in rows) <= protocol['max_generations']
        write(output/'progress.json', {'trials': len(rows), 'rows': rows})
        print(f"{index+1}/{len(plan)} {trial['trial_id']}: {result['status']}", flush=True)
    verify_freeze(output)
    write(output/'execution-summary.json', {'status': 'execution_complete', 'trials': len(rows),
        'generation_records': sum(r['generations'] for r in rows), 'elapsed_seconds': time.monotonic()-started,
        'paid_api_calls': 0, 'rows': rows})
    blind(output)


def blind(output):
    plan = read(output/'plan.json'); items = []
    for index, trial in enumerate(plan):
        path = output/f'{index:03}'/'result.json'
        if not path.exists(): continue
        for n, narrative in enumerate(read(path)['narratives']):
            text = narrative['text'].removeprefix('Local model review (unverified proposal):\n')
            items.append({'case_id': trial['case_id'], 'text': text, 'text_sha256': text_sha(text),
                          'trial_id': trial['trial_id'], 'narrative_index': n, 'result_sha256': sha(path)})
    random.Random(plan[0]['protocol']['blind_seed']).shuffle(items)
    mapping, packet = {}, []
    for index, item in enumerate(items):
        ident = f'q{index:03}'; mapping[ident] = item
        packet.append({'id': ident, **{k: item[k] for k in ('case_id', 'text', 'text_sha256')}})
    write(output/'blind-mapping.json', mapping); write(output/'blind-packet.json', packet)
    write(output/'blind-freeze.json', {name: sha(output/name) for name in ('blind-mapping.json','blind-packet.json')})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true'); parser.add_argument('--execute', action='store_true')
    parser.add_argument('--local-model', action='store_true'); parser.add_argument('--worker', type=Path)
    parser.add_argument('--python', type=Path); parser.add_argument('--tokenizer-file', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); output = args.output.absolute()
    if args.worker: worker(args.worker, output)
    elif args.prepare:
        if not args.python or not args.tokenizer_file: parser.error('Preparation requires --python and --tokenizer-file')
        prepare(args.python.absolute(), args.tokenizer_file.absolute(), output)
    elif args.execute and args.local_model: execute(output)
    else: parser.error('Select --prepare or explicit --execute --local-model')
