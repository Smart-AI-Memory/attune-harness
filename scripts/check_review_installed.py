"""Installed review CLI acceptance checks, without provider calls or source imports."""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path


def check(python: Path, core_only: bool) -> dict:
    cases = []
    root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory(prefix='harness-review-installed-') as temporary:
        work = Path(temporary)
        project = work / 'project'
        project.mkdir()
        (project / 'guide.md').write_text('[Quartz policy](reference.md)', encoding='utf-8')
        (project / 'reference.md').write_text('Quartz policy reference.', encoding='utf-8')
        (work / 'context.json').write_text(json.dumps({'schema_version': 1, 'project_root': 'project'}), encoding='utf-8')
        config = work / 'participants.json'
        config.write_bytes((root / 'examples/review/participants.json').read_bytes())
        request = work / 'request.json'

        def run(arguments, code, expected):
            result = subprocess.run([str(python), '-I', '-m', 'attune_harness', *map(str, arguments)],
                                    cwd=work, capture_output=True, text=True, timeout=30)
            assert result.returncode == code, (result.stdout, result.stderr)
            value = json.loads(result.stdout)
            assert value['status'] == expected, value
            cases.append({'command': arguments[0], 'exit': code, 'status': expected})
            return value

        absent = ['attune', 'anthropic', 'claude_agent_sdk', 'openai']
        if core_only:
            absent += ['attune_forms', 'attune_verify', 'attune_rag']
        subprocess.run([str(python), '-I', '-c',
                        'import importlib.util; assert all(importlib.util.find_spec(n) is None for n in ' + repr(absent) + ')'],
                       cwd=work, check=True)
        if core_only:
            run(['review-form', '--config', config], 2, 'unavailable')
            (work / 'old').mkdir()
            (work / 'old/record.json').write_text(json.dumps({'schema_version': 1, 'operation': 'review', 'status': 'running'}), encoding='utf-8')
            assert run(['inspect-review', work / 'old'], 2, 'unresolved')['persisted_status'] == 'running'
        else:
            form = run(['review-form', '--config', config], 0, 'ready')
            submission = form['submission']
            submission.update(accepted=True, answers={'objective': 'Check the local policy evidence', 'query': 'quartz policy',
                                                       'document': 'project/guide.md', 'context': 'context.json', 'corpus': 'project',
                                                       'lead': 'sample-lead', 'reviewer': 'sample-reviewer'})
            def submit():
                request.write_text(json.dumps(submission), encoding='utf-8')
            def arguments(name):
                return ['review', request, '--config', config, '--run-dir', work / name]
            submit()
            result = run(arguments('success'), 0, 'completed')
            assert result['document_outcome'] == 'verified'
            assert all(item['tool_calls'] == 2 for item in result['participants'].values())
            assert run(['inspect-review', work / 'success'], 0, 'completed') == result
            assert json.loads((work / 'success/record.json').read_text(encoding='utf-8')) == result
            run(arguments('success'), 2, 'failed')
            (project / 'guide.md').write_text('[bad](absent.md)', encoding='utf-8')
            assert run(arguments('refuted'), 1, 'completed')['document_outcome'] == 'refuted'
            (project / 'guide.md').write_text('No supported claims', encoding='utf-8')
            assert run(arguments('unknown'), 1, 'completed')['document_outcome'] == 'unknown'
            (project / 'guide.md').write_text('[Quartz policy](reference.md)', encoding='utf-8')
            submission['answers']['query'] = 'nonmatchingzzzz'
            submit()
            assert run(arguments('no-sources'), 1, 'completed')['retrieval_outcome'] == 'no_results'
            submission['accepted'] = False
            submit()
            run(arguments('declined'), 2, 'failed')
            assert not (work / 'declined').exists()
            submission['accepted'] = True
            submission['answers']['query'] = 'quartz policy'
            # Same workflow through a separately implemented local process peer.
            peer = work / 'peer.py'
            peer.write_bytes((root / 'examples/review/json_participant.py').read_bytes())
            registry = json.loads(config.read_text(encoding='utf-8'))
            registry['participants']['sample-reviewer'].update(adapter='command', command=[str(python), '-I', str(peer)], timeout=3)
            config.write_text(json.dumps(registry), encoding='utf-8')
            submit()
            run(arguments('stale'), 2, 'failed')
            submission['form_revision'] = run(['review-form', '--config', config], 0, 'ready')['form_revision']
            submit()
            run(arguments('external-denied'), 2, 'unavailable')
            external = run(arguments('command') + ['--allow-external'], 0, 'completed')
            assert external['participants']['reviewer']['tool_calls'] == 2
            assert 'Independent command fixture' in external['participants']['reviewer']['text']
            assert len([event for event in external['events'] if event['kind'] == 'tool']) == 4
        help_result = subprocess.run([str(python.parent / 'attune-harness'), 'review', '--help'],
                                     cwd=work, capture_output=True, text=True, check=True)
        assert '--run-dir' in help_result.stdout and '--allow-external' in help_result.stdout
    return {'mode': 'core' if core_only else 'review', 'cases': cases,
            'provider_calls': 0, 'provider_dependencies_absent': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--core-only', action='store_true')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = check(args.python.absolute(), args.core_only)
    args.report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'mode': result['mode'], 'cases': len(result['cases']), 'provider_calls': 0}))
