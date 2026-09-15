"""Run targeted output-budget mutations in disposable source copies only."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def main(python, output):
    output.mkdir(parents=True, exist_ok=False)
    mutants = {
        'restore-character-cap': ('ollama_review.py', "or not value['review'].strip():",
                                 "or not value['review'].strip() or len(value['review']) > 3000:"),
        'restore-word-instruction': ('ollama_review.py', 'Return a JSON review explaining important uncertainty.',
                                    'Return a review under 120 words in the required JSON object.'),
        'ignore-workflow-budget': ('ollama_review.py', "options = {**OPTIONS, 'num_predict': max_output_tokens}",
                                  'options = dict(OPTIONS)'),
        'remove-output-transport-check': ('ollama_review.py', "decode_action(response, request['request_digest'])", 'pass'),
        'escape-unicode-on-wire': ('ollama_review.py', "'action': action}, ensure_ascii=False)",
                                   "'action': action}, ensure_ascii=True)"),
        'omit-output-context-reservation': ('ollama.py', "options['num_ctx'] - input_units - options['num_predict'] - 512",
                                           "options['num_ctx'] - input_units - 512"),
        'remove-budget-validation': ('ollama.py',
            "    for name, value in (('num_ctx', num_ctx), ('num_predict', num_predict)):\n"
            "        if type(value) is not int or value < 1:\n"
            "            raise ValueError(name + ' must be a positive integer')\n"
            "    if not 1024 <= num_ctx <= 16384 or num_predict >= num_ctx - 512:\n"
            "        raise ValueError('Local context/output budget outside supported bounds; reserve context for input and framing')",
            '    pass'),
        'accept-token-truncation': ('ollama.py', " or result.get('done_reason') != 'stop'", ''),
        'ignore-accepted-budget-change': ('recovery.py',
            "if prepared['requirement_revision'] != record['requirement_revision']:", 'if False:'),
    }
    results, detected = [], set()
    def run(label, source):
        report = output/(label+'.xml')
        command = [str(python), '-m', 'pytest', str(ROOT/'tests/test_output_budget.py'), '-q',
                   '-o', 'pythonpath='+str(source), '--junitxml='+str(report)]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
        (output/(label+'.txt')).write_text(result.stdout+'\n'+result.stderr)
        cases = ET.parse(report).getroot().findall('.//testcase')
        assert cases and not any(c.find('error') is not None for c in cases), label
        failures = [c.attrib['name'] for c in cases if c.find('failure') is not None]
        return {'name': label, 'exit': result.returncode, 'cases': len(cases), 'failed_tests': failures, 'argv': command}
    baseline = run('baseline', ROOT/'src')
    assert baseline['exit'] == 0 and baseline['cases'] == 33, baseline
    for label, (name, before, after) in mutants.items():
        with tempfile.TemporaryDirectory(prefix='harness-output-mutation-') as directory:
            source = Path(directory)/'src'
            shutil.copytree(ROOT/'src/attune_harness', source/'attune_harness',
                            ignore=shutil.ignore_patterns('__pycache__'))
            path = source/'attune_harness'/name
            original = path.read_text()
            assert before in original, label
            path.write_text(original.replace(before, after))
            result = run(label, source)
            assert result['exit'] == 1 and result['failed_tests'], result
            detected.update(result['failed_tests'])
            results.append(result)
    summary = {'status': 'passed', 'kind': 'targeted_mutations_not_exhaustive_mutation_score',
               'new_test_cases': baseline['cases'], 'distinct_tests_detecting_mutations': len(detected),
               'mutants_killed': len(results), 'mutants_tried': len(mutants), 'baseline': baseline,
               'results': results, 'model_calls': 0, 'working_source_modified': False}
    (output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps({key: value for key, value in summary.items() if key not in ('results', 'baseline')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    main(args.python.absolute(), args.output.absolute())
