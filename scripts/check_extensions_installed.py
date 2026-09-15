"""Installed, isolated CLI/command receipts; no provider or network calls."""

import argparse
import copy
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def check(python, core=False):
    root = Path(__file__).resolve().parent.parent
    checks = []
    with tempfile.TemporaryDirectory(prefix='harness-extensions-installed-') as scratch:
        work = Path(scratch)
        def run(args, code=0, status=None):
            completed = subprocess.run([str(python), '-I', '-m', 'attune_harness', *map(str, args)],
                                       cwd=work, capture_output=True, text=True, timeout=30)
            payload = json.loads(completed.stdout)
            assert completed.returncode == code, (args, completed.stderr, payload)
            if status:
                assert payload['status'] == status, payload
            checks.append({'command': ' '.join(str(a) for a in args[:2]), 'exit': code, 'status': payload['status']})
            return payload
        if core:
            source = root / 'examples/extensions/plugin/src/attune_harness_evidence'
        else:
            result = subprocess.run([str(python), '-I', '-c',
                'from importlib.metadata import distribution; '
                'd=distribution("attune-harness-evidence-example"); '
                'print(d.locate_file("attune_harness_evidence/extension.json"))'],
                cwd=work, capture_output=True, text=True, check=True)
            source = Path(result.stdout.strip()).parent
            assert source.is_relative_to(python.parent.parent)
        shutil.copytree(source, work / 'bundle')
        manifest = work / 'bundle/extension.json'
        original = run(['extension', 'discover', manifest], status='ready')['bundle']
        state_dir = work / 'extension-state'
        state = run(['extension', 'install', manifest, '--state-dir', state_dir], status='disabled')
        def mutation(action, current=state, *more, code=0, status=None):
            return run(['extension', action, '--state-dir', state_dir,
                        '--checkpoint', current['state_digest'], *more], code, status)
        if core:
            mutation('enable', code=2, status='unavailable')
            assert run(['extension', 'inspect', '--state-dir', state_dir]) == state
            mutation('remove', status='removed')
            return {'cases': checks, 'provider_calls': 0, 'profile': 'core-only'}
        state = mutation('enable', status='enabled')
        (state_dir / 'user-data.txt').write_text('preserve', encoding='utf-8')
        project = work / 'project'
        project.mkdir()
        (project / 'guide.md').write_text('[Quartz policy](reference.md)', encoding='utf-8')
        (project / 'reference.md').write_text('Quartz policy source.', encoding='utf-8')
        (work / 'context.json').write_text(json.dumps({'schema_version': 1, 'project_root': 'project'}))
        config, request = work / 'config.json', work / 'request.json'
        registry = {'schema_version': 1, 'extensions': {'evidence': {
            'state_dir': str(state_dir), 'artifact_digest': state['artifact_digest']}}, 'participants': {
            name: {'adapter': 'deterministic', 'tools': ['evidence.search', 'verify'], 'max_turns': 3, 'max_tool_calls': 2}
            for name in ('lead', 'peer')}}
        registry['participants']['peer'].update(adapter='command', timeout=3,
            command=[str(python), '-I', str(root / 'examples/extensions/json_participant.py')])
        def accept(query='quartz policy'):
            config.write_text(json.dumps(registry), encoding='utf-8')
            submission = run(['review-form', '--config', config], status='ready')['submission']
            submission.update(accepted=True, answers={'objective': 'Review scoped evidence', 'query': query,
                    'document': 'project/guide.md', 'context': 'context.json', 'corpus': 'project', 'lead': 'lead', 'reviewer': 'peer'})
            request.write_text(json.dumps(submission), encoding='utf-8')
        accept()
        run_dir = work / 'run'
        paused = run(['review', request, '--config', config, '--run-dir', run_dir,
                      '--allow-external', '--max-operations', '4'], 1, 'paused')
        events = copy.deepcopy(paused['events'])
        assert events[-1]['result']['extension']['artifact_digest'] == original['artifact_digest']
        def resume_args(record):
            return ['resume-review', run_dir, '--config', config, '--request', request,
                    '--checkpoint', record['checkpoint_digest'], '--allow-external']
        state = mutation('disable', state, status='disabled')
        run(resume_args(paused), 2, 'unavailable')
        assert run(['inspect-review', run_dir], 1, 'paused')['events'] == events
        state = mutation('enable', state, status='enabled')
        completed = run(resume_args(paused), status='completed')
        assert completed['events'][:4] == events
        assert completed['document_outcome'] == 'verified'
        assert completed['participants']['reviewer']['adapter'] == 'command'
        assert 'reference.md' in completed['participants']['reviewer']['text']
        assert len([e for e in completed['events'] if 'extension' in e.get('result', {})]) == 2

        # Hold a real tool call in another process while lifecycle mutation tries
        # to acquire the same lease. No lifecycle action reports success early.
        hold = '''import json,sys
from pathlib import Path
from attune_harness.extensions import invoke_tool
from attune_harness.retrieval import retrieve_sources
bindings=json.loads(sys.argv[1]); corpus=Path(sys.argv[2])
def call(query,k):
    print('READY',flush=True)
    sys.stdin.readline()
    return retrieve_sources(query,corpus,k=k)
print(json.dumps(invoke_tool(bindings,'evidence.search',{'query':'quartz policy','k':3},call)))
'''
        owner = subprocess.Popen([str(python), '-I', '-c', hold, json.dumps(registry['extensions']), str(project)],
                                 cwd=work, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            # select bounds the handshake rather than waiting on an unbounded readline.
            import select
            assert select.select([owner.stdout], [], [], 10)[0], 'Owner did not reach invocation'
            assert owner.stdout.readline().strip() == 'READY'
            mutation('disable', state, code=2, status='failed')
            stdout, stderr = owner.communicate('\n', timeout=10)
            assert owner.returncode == 0, stderr
            assert json.loads(stdout)['status'] == 'retrieved'
            checks.append({'command': 'independent process lease', 'exit': 0, 'status': 'retrieved'})
        finally:
            if owner.poll() is None:
                owner.kill()
                owner.wait()
        state = mutation('disable', state, status='disabled')
        data = json.loads(manifest.read_text())
        data['version'] = '0.2.0'
        manifest.write_text(json.dumps(data), encoding='utf-8')
        mutation('enable', state, code=2, status='unavailable')
        state = mutation('replace', state, '--manifest', manifest, status='disabled')
        assert state['artifact_digest'] != original['artifact_digest']
        state = mutation('enable', state, status='enabled')
        run(['review-form', '--config', config], 2, 'unavailable')
        registry['extensions']['evidence']['artifact_digest'] = state['artifact_digest']
        accept('zzzzunmatched')
        no_results = run(['review', request, '--config', config, '--run-dir', work / 'empty', '--allow-external'], 1, 'completed')
        assert no_results['retrieval_outcome'] == 'no_results'
        assert all(e['result']['status'] == 'no_results' for e in no_results['events'] if 'extension' in e.get('result', {}))
        state = mutation('remove', state, status='removed')
        assert (state_dir / 'user-data.txt').read_text() == 'preserve' and manifest.exists()
        mutation('enable', state, code=2, status='failed')
        run(['review', request, '--config', config, '--run-dir', work / 'removed', '--allow-external'], 2, 'unavailable')
    return {'cases': checks, 'provider_calls': 0, 'profile': 'installed review + data-only plugin wheel',
            'independent_peer': 'local command, no Harness imports', 'active_call_lease': 'separate process',
            'mcp_qualified': False, 'a2a_qualified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', required=True, type=Path)
    parser.add_argument('--core', action='store_true')
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    result = check(args.python.absolute(), args.core)
    args.report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f"{len(result['cases'])} installed extension checks passed; zero provider calls")
