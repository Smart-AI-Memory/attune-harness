"""Two explicit local-only output-budget probes using an installed wheel."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from pilot_review import MODEL, DIGEST, SERVER


def main(python, work):
    work.mkdir(parents=True, exist_ok=False)
    results = []
    for name, budget in [('long-review', 2048), ('token-exhaustion', 8)]:
        turn = {'objective': 'Review this fictional documentation independently. For this disposable length test only, '
                'write approximately 650 to 750 words, addressing every assertion with its missing evidence and a concrete '
                'way to check it. Do not treat the assertions as facts or claim to have run any checks.',
                'document': {'path': 'fictional-budget-fixture.md', 'text':
                    'Fictional assertions for a length test, not factual project documentation:\n'
                    '1. Every adapter is portable.\n2. All retries are safe.\n3. Model prose is always verified.\n'
                    '4. Cancellation proves no effects.\n5. All caches predict availability.\n'
                    '6. Every upgrade is backward compatible.\n7. Every source is trustworthy.\n'
                    '8. Authentication never expires.\n9. All local models have equal costs.\n'
                    '10. Every checkpoint resumes on another operating system.\n'
                    '11. Token counts equal character counts.\n12. Truncated output proves completion.'},
                'query': 'fictional evidence review', 'history': [], 'tools': [],
                'remaining_tool_calls': 0, 'remaining_turns': 1, 'role': 'reviewer', 'turn_id': name}
        request_digest = hashlib.sha256(json.dumps(turn, sort_keys=True, separators=(',', ':'),
                                                  ensure_ascii=True, allow_nan=False).encode()).hexdigest()
        request = {'schema_version': 1, 'request_digest': request_digest, 'turn': turn}
        argv = [str(python), '-I', '-m', 'attune_harness.ollama_review', '--model', MODEL,
                '--digest', DIGEST, '--server-version', SERVER, '--receipts', str(work/'generations'),
                '--seed', '64001', '--max-output-tokens', str(budget)]
        (work/(name+'-request.json')).write_text(json.dumps(request, indent=2)+'\n')
        run = subprocess.run(argv, input=json.dumps(request), capture_output=True, text=True,
                             cwd=work, timeout=90)
        (work/(name+'-stdout.json')).write_text(run.stdout)
        (work/(name+'-stderr.txt')).write_text(run.stderr)
        saved = json.loads((work/'generations'/request_digest/'record.json').read_text())
        generation = saved.get('generation') or {}
        result = {'name': name, 'argv': argv, 'exit': run.returncode, 'status': saved['status'],
                  'max_output_tokens': saved['options']['num_predict'],
                  'done_reason': generation.get('done_reason'), 'eval_count': generation.get('eval_count'),
                  'generation_receipt': str(work/'generations'/request_digest/'record.json')}
        if run.returncode == 0:
            verified = subprocess.run([str(python), '-I', '-c',
                'import sys; from attune_harness.review_participants import decode_action; '
                'decode_action(sys.stdin.read(),sys.argv[1])', request_digest],
                input=run.stdout, capture_output=True, text=True, cwd=work, check=True)
            text = saved['response']['review']
            result.update(review_characters=len(text), review_utf8_bytes=len(text.encode()),
                          review_words=len(text.split()), exceeds_old_character_cap=len(text)>3000,
                          narrative_utf8_bytes=len(json.loads(run.stdout)['action']['text'].encode()),
                          transport_accepted=verified.returncode == 0)
        results.append(result)
        (work/'results.json').write_text(json.dumps(results, indent=2)+'\n')
    assert results[0]['status'] == 'completed' and results[0]['transport_accepted'], results[0]
    assert results[1]['status'] == 'failed' and results[1]['done_reason'] == 'length', results[1]
    summary = {'status': 'passed', 'kind': 'live_local_disposable_fixture', 'model_generations': 2,
               'paid_api_calls': 0, 'results': results}
    (work/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--local-model', action='store_true', required=True,
                        help='Authorize exactly two local generations, no downloads or paid APIs')
    args = parser.parse_args()
    main(args.python.absolute(), args.work_dir.absolute())
