"""Exercise installed CLI funding journeys with inert requests and synthetic auth."""

import argparse
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
KEY = 'offline_funding_fixture_0123456789'
POLICY = {'mode': 'api', 'credential_env': 'OPENAI_API_KEY'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.write_text(json.dumps(value), encoding='utf-8')
    return path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def journey(base):
    from attune_harness.cli import main
    from attune_harness.process import ProcessResult
    calls, commands = [], []

    def cli(*argv, codes=(0,)):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main([str(arg) for arg in argv])
        require(KEY not in stdout.getvalue() + stderr.getvalue(), 'CLI exposed a credential')
        value = json.loads(stdout.getvalue())
        require(code in codes, 'Unexpected CLI outcome: ' + ' '.join(map(str, argv)))
        commands.append({'command': str(argv[0]), 'exit_code': code, 'status': value['status']})
        return value

    def witness(argv, raw, **options):
        require(options['environment'] == {'OPENAI_API_KEY': KEY}, 'Unscoped API environment')
        require(argv[1:3] == ('-I', '-S') and Path(argv[3]).name == 'openai_worker.py',
                'Unexpected worker invocation')
        body = json.loads(raw)['body']
        require(body['tools'] == [] and body['store'] is False, 'Unexpected API request options')
        request = json.loads(body['input'].split('\n', 1)[1])
        require(request['version'] == 1, 'Missing correlated request envelope')
        inner = json.loads(request['attempt']['task']['objective'])
        turn = inner['turn'] if 'turn' in inner else inner
        saved = read((review_dir if 'turn' in inner else directory) / 'record.json')
        event = next(e for e in saved['events'] if e.get('funding', {}).get('request_digest') == digest(turn))
        require(event['phase'] == 'dispatching' and event['funding']['api_authorized'] is True,
                'Request preceded durable funding admission')
        if 'turn' in inner:
            index = len(turn['history'])
            action = ({'kind': 'tool', 'name': turn['tools'][index], 'arguments':
                       {'query': turn['query'], 'k': 3} if turn['tools'][index] == 'retrieve' else {}}
                      if index < len(turn['tools']) else
                      {'kind': 'final', 'text': 'Offline fixture; no provider judgment.'})
            text = json.dumps({'schema_version': 1, 'request_digest': inner['request_digest'], 'action': action})
        else:
            text = json.dumps({'verdict': 'uncertain', 'summary': 'Offline fixture; no provider judgment.',
                               'evidence': [{'path': 'sample.md', 'line': 1, 'detail': 'Frozen fixture.'}]})
        calls.append({'model': body['model'], 'request_digest': digest(turn)})
        response = {'id': 'resp_offline_' + str(len(calls)), 'model': body['model'], 'status': 'completed',
                    'error': None, 'incomplete_details': None, 'usage': {'input_tokens': 10,
                    'output_tokens': 5, 'input_tokens_details': {'cached_tokens': 2}},
                    'output': [{'type': 'message', 'role': 'assistant', 'status': 'completed',
                                'content': [{'type': 'output_text', 'text': json.dumps({'text': text})}]}]}
        return ProcessResult(argv, 0, json.dumps(response), '')

    def bound(record, configurations):
        funded = [e for e in record['events'] if e.get('funding', {}).get('dispatch_outcome') == 'completed']
        require(funded, 'Missing completed funding evidence')
        for event in funded:
            funding = event['funding']
            participant = event.get('participant_id', event['operation_key'].partition(':')[2])
            attempt = event.get('turn_id') or digest([record['contract_digest'], event['operation_key']])
            require(funding['configuration_digest'] == digest(configurations[funding['participant_id']])
                    and funding['request_digest'] == event['request_digest']
                    and funding['participant_id'] == participant and funding['attempt_id'] == attempt
                    and funding['attempt'] == event['attempts'] and funding['api_authorized'] is True
                    and funding['state'] == 'matched' and funding['observed'] == 'api', 'Funding binding changed')
            identity = event['result']['identity']
            require(identity['funding'] == funding, 'Result lost its admission')
            usage = identity['usage']
            require(usage['profile'] == 'native-usage-v1' and usage['state'] == 'reported'
                    and usage['input_tokens'] == 10 and usage['output_tokens'] == 5
                    and usage['cached_input_tokens'] == 2, 'Reported usage changed')
            require(all(usage[name] is None for name in ('cache_creation_tokens', 'provider_reported_cost_usd',
                    'billed_cost_usd', 'remaining_balance')), 'Unknown cost became a billing claim')

    def refusal(directory, before):
        require(len(calls) == before, 'Missing authority dispatched a request')
        record = read(directory / 'record.json')
        event = next(e for e in record['events'] if e.get('funding', {}).get('basis') == 'api_authority_required')
        require(event['phase'] == 'prepared' and event['state'] == 'pending' and 'result' not in event
                and event['funding']['api_authorized'] is False
                and event['funding']['dispatch_outcome'] == 'not_started', 'Refusal invented external effects')

    with ExitStack() as stack:
        stack.enter_context(patch('attune_harness.openai_exchange.invoke', witness))
        stack.enter_context(patch('subprocess.Popen', side_effect=ValueError('Unexpected subprocess')))
        stack.enter_context(patch('socket.socket.connect', side_effect=ValueError('Unexpected network')))
        project = base / 'project'
        project.mkdir()
        (project / 'sample.md').write_text('[Quartz retention policy](reference.md)', encoding='utf-8')
        (project / 'reference.md').write_text('Quartz retention policy is a fixture.', encoding='utf-8')
        seats = {name: {'adapter': 'openai', 'timeout': 10, 'funding': POLICY,
                       'identity': {'provider': 'openai', 'model': 'offline-' + name}} for name in ('alpha', 'beta')}
        config = write(base / 'consultation.json', {'schema_version': 1, 'question': 'Inspect fixtures',
            'author': {'provider': 'fixture', 'model': 'chair'}, 'rounds': 1, 'participants': seats})
        require(cli('roundtable', 'check', '--config', config)['model_calls'] == 0 and not calls,
                'Inspection dispatched a request')
        directory = base / 'consultation-run'
        prepared = cli('roundtable', 'prepare', '--project', project, '--path', 'sample.md',
                       '--config', config, '--run-dir', directory)
        run = ('roundtable', 'run', directory, '--accept', prepared['contract_digest'], '--allow-external')
        cli(*run, codes=(2,)); refusal(directory, 0)
        cli('roundtable', 'status', directory, codes=(0, 2))
        require(cli(*run, '--allow-api-spend', '--max-operations', 1)['status'] == 'paused', 'Pause failed')
        require(len(calls) == 1, 'Call budget changed')
        cli(*run, codes=(2,)); refusal(directory, 1)
        completed = cli(*run, '--allow-api-spend')
        require(completed['status'] == 'completed' and len(calls) == 2, 'Consultation did not complete')
        bound(completed, seats)
        cli('roundtable', 'status', directory)
        cli('roundtable', 'evidence', directory)
        cli(*run, '--allow-api-spend', codes=(2,))
        require(len(calls) == 2, 'Inspection or terminal replay dispatched')

        roster = {name: {'adapter': 'openai', 'model': 'offline-' + name, 'timeout': 10,
                         'funding': POLICY, 'tools': ['retrieve', 'verify'], 'max_turns': 3,
                         'max_tool_calls': 2} for name in ('alpha', 'beta')}
        registry = write(base / 'registry.json', {'schema_version': 1, 'participants': roster})
        form = cli('review-form', '--config', registry)['submission']
        form.update(accepted=True, answers={'objective': 'Check evidence', 'query': 'quartz retention policy',
            'document': 'project/sample.md', 'context': 'context.json', 'corpus': 'project',
            'lead': 'alpha', 'reviewer': 'beta'})
        write(base / 'context.json', {'schema_version': 1, 'project_root': 'project'})
        request = write(base / 'request.json', form)
        review_dir = base / 'review-run'
        result = cli('review', request, '--config', registry, '--run-dir', review_dir,
                     '--allow-external', '--allow-api-spend')
        require(result['status'] == 'completed' and len(calls) == 8, 'Registry journey did not complete')
        bound(result, roster)
        cli('inspect-review', review_dir)
        require(len(calls) == 8, 'Registry inspection dispatched')
        require(KEY not in json.dumps([read(p) for p in base.rglob('record.json')]), 'Saved credential')
    return {'commands': commands, 'request_witness_calls': len(calls), 'provider_calls': 0,
            'checks': ['both_shared_paths', 'prepared_refusal', 'fresh_resume_authority',
                       'terminal_no_dispatch', 'bound_funding_usage', 'unknown_billing', 'no_saved_credential']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    require(sys.flags.isolated, 'Run this script with the installed wheel Python and -I')
    original = os.environ
    try:
        os.environ = {'OPENAI_API_KEY': KEY}
        source = runpy.run_path(str(ROOT / 'scripts/qualify_platform.py'))['installed_source']()
        with tempfile.TemporaryDirectory(prefix='attune-funding-') as scratch:
            base = Path(scratch).resolve()
            require(not base.is_relative_to(ROOT), 'Scratch state must be outside the checkout')
            result = journey(base)
        result.update(profile='participant-funding-installed-v1', status='passed',
            receipt_types=['evidence-chain', 'live-fire'],
            live_fire_scope='Installed CLI owners with an inert request witness; no provider qualification',
            platform=sys.platform, package_version=importlib.metadata.version('attune-harness'),
            installed_source=str(source), script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            sources_sha256={name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in
                ('openai_exchange.py', 'participant_funding.py', 'consultation.py',
                 'task_runtime.py', 'review_participants.py', 'funding_usage.py')})
    finally:
        os.environ = original
    text = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.output:
        with args.output.open('x', encoding='utf-8') as output:
            output.write(text)
    else:
        print(text, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
