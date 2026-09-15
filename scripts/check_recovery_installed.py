"""Exercise installed recovery controls with local fixtures and zero model calls."""

import argparse
import copy
import json
import subprocess
import tempfile
from pathlib import Path


def check(python: Path):
    root = Path(__file__).resolve().parent.parent
    cases = []
    with tempfile.TemporaryDirectory(prefix='harness-recovery-installed-') as tmp:
        work = Path(tmp)
        corpus = work / 'project'
        corpus.mkdir()
        (corpus / 'guide.md').write_text('[Quartz](reference.md)', encoding='utf-8')
        (corpus / 'reference.md').write_text('Quartz policy reference', encoding='utf-8')
        (work / 'context.json').write_text(json.dumps({'schema_version': 1, 'project_root': 'project'}), encoding='utf-8')
        config = work / 'participants.json'
        registry = json.loads((root / 'examples/review/participants.json').read_text(encoding='utf-8'))
        registry['participants']['alternate'] = copy.deepcopy(registry['participants']['sample-lead'])
        config.write_text(json.dumps(registry), encoding='utf-8')
        request = work / 'request.json'

        def run(args, code, status):
            result = subprocess.run([str(python), '-I', '-m', 'attune_harness', *map(str, args)],
                                    cwd=work, text=True, capture_output=True, timeout=30)
            payload = json.loads(result.stdout)
            assert result.returncode == code, (args[0], result.returncode, payload.get('status'),
                                               payload.get('error'), payload.get('retrieval_outcome'), result.stderr)
            assert payload['status'] == status, payload
            cases.append({'command': args[0], 'exit': code, 'status': status})
            return payload

        submission = run(['review-form', '--config', config], 0, 'ready')['submission']
        submission.update(accepted=True, answers={'objective': 'Review policy evidence', 'query': 'quartz policy',
                          'document': 'project/guide.md', 'context': 'context.json', 'corpus': 'project',
                          'lead': 'sample-lead', 'reviewer': 'sample-reviewer'})
        request.write_text(json.dumps(submission), encoding='utf-8')
        directory = work / 'run'
        first = run(['review', request, '--config', config, '--run-dir', directory, '--max-operations', '4'], 1, 'paused')
        assert run(['inspect-review', directory], 1, 'paused') == first
        first_events = copy.deepcopy(first['events'])

        def resume_args(record, target=directory):
            return ['resume-review', target, '--request', request, '--config', config,
                    '--checkpoint', record['checkpoint_digest']]
        moved = run(['transfer-review', directory, '--checkpoint', first['checkpoint_digest'],
                     '--lead', 'alternate', '--reason', 'Continue the same accepted review'], 1, 'paused')
        run(resume_args(first), 2, 'failed')
        middle = run(resume_args(moved) + ['--max-operations', '2'], 1, 'paused')
        returned = run(['transfer-review', directory, '--checkpoint', middle['checkpoint_digest'],
                        '--lead', 'sample-lead', '--reason', 'Return the local lead assignment'], 1, 'paused')
        complete = run(resume_args(returned), 0, 'completed')
        assert complete['events'][:4] == first_events
        assert complete['accepted'] == first['accepted']
        assert complete['document_outcome'] == 'verified'
        assert len(complete['recovery']['transfers']) == 2
        assert run(resume_args(complete), 0, 'completed') == complete
        assert run(['cancel-review', directory, '--checkpoint', complete['checkpoint_digest'], '--reason', 'too late'], 0, 'completed') == complete

        abandoned_dir = work / 'abandoned'
        paused = run(['review', request, '--config', config, '--run-dir', abandoned_dir, '--max-operations', '1'], 1, 'paused')
        cancelled = run(['cancel-review', abandoned_dir, '--checkpoint', paused['checkpoint_digest'], '--reason', 'Abandon fixture'], 1, 'cancelled')
        run(resume_args(cancelled, abandoned_dir), 2, 'failed')
        old = work / 'old'
        old.mkdir()
        (old / 'record.json').write_text(json.dumps({'schema_version': 1, 'operation': 'review', 'status': 'running'}), encoding='utf-8')
        run(['inspect-review', old], 2, 'unresolved')
        run(['resume-review', old, '--request', request, '--config', config, '--checkpoint', 'old'], 2, 'unavailable')

        # One known local process writes an effect marker and reply, then exits
        # unsuccessfully. Recovery must reuse the reply without another process.
        peer, counter, reply = work / 'peer.py', work / 'effects.txt', work / 'reply.json'
        peer.write_text('import json,sys,pathlib\n'
                        'd=json.load(sys.stdin)\n'
                        'p=pathlib.Path(sys.argv[1]); p.write_text(p.read_text()+"effect\\n" if p.exists() else "effect\\n")\n'
                        'pathlib.Path(sys.argv[2]).write_text(json.dumps(dict(schema_version=1,request_digest=d["request_digest"],action=dict(kind="final",text="Recovered command fixture"))))\n'
                        'sys.exit(23)\n', encoding='utf-8')
        registry['participants']['sample-lead'].update(adapter='command', command=[str(python), '-I', str(peer), str(counter), str(reply)], timeout=3)
        config.write_text(json.dumps(registry), encoding='utf-8')
        submission['form_revision'] = run(['review-form', '--config', config], 0, 'ready')['form_revision']
        request.write_text(json.dumps(submission), encoding='utf-8')
        uncertain_dir = work / 'uncertain'
        uncertain = run(['review', request, '--config', config, '--run-dir', uncertain_dir, '--allow-external'], 2, 'failed')
        run(resume_args(uncertain, uncertain_dir) + ['--allow-external'], 2, 'unresolved')
        event = uncertain['events'][-1]
        run(['reconcile-review', uncertain_dir, '--checkpoint', uncertain['checkpoint_digest'],
             '--event', event['event_id'], '--retry-read-only'], 2, 'unresolved')
        recovered = run(['reconcile-review', uncertain_dir, '--checkpoint', uncertain['checkpoint_digest'],
                         '--event', event['event_id'], '--reply', reply], 1, 'paused')
        run(resume_args(recovered, uncertain_dir), 2, 'unavailable')
        recovered_complete = run(resume_args(recovered, uncertain_dir) + ['--allow-external'], 0, 'completed')
        assert counter.read_text(encoding='utf-8') == 'effect\n'
        assert recovered_complete['participants']['lead']['text'] == 'Recovered command fixture'
        run(['reconcile-review', uncertain_dir, '--checkpoint', recovered_complete['checkpoint_digest'],
             '--event', event['event_id'], '--reply', reply], 2, 'failed')
    return {'cases': cases, 'provider_calls': 0, 'external_fixture_effect_count': 1,
            'transfer_directions': 2, 'accepted_constraints_preserved': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = check(args.python.absolute())
    args.report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'cases': len(result['cases']), 'provider_calls': 0, 'external_fixture_effect_count': 1}))
