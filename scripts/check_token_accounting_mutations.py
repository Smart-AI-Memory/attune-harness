"""Check token-accounting guards using disposable copies of production source."""
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
        'count-bytes-instead-of-tokens': ('ollama.py', 'self.tokenizer.count(prompt, system)', "len((prompt + system).encode('utf-8'))"),
        'remove-context-preflight': ('ollama.py', "if self.last_context_accounting['remaining_after_reserves'] < 0:", 'if False:'),
        'omit-output-reserve': ('ollama.py', "options['num_ctx'] - input_units - options['num_predict'] - 512", "options['num_ctx'] - input_units - 512"),
        'ignore-server-count-drift': ('ollama.py', "if self.tokenizer is not None and result['prompt_eval_count'] != input_units:", 'if False:'),
        'allow-server-truncation': ('ollama.py', "'truncate': False, 'shift': False", "'truncate': True, 'shift': True"),
        'omit-accounting-from-receipt': ('ollama_review.py', "record['context_accounting'] = getattr(model, 'last_context_accounting', None)", "record['context_accounting'] = None"),
        'ignore-profile-integrity': ('llama_tokens.py', "if len(raw) > MAX_PROFILE_BYTES or hashlib.sha256(raw).hexdigest() != PROFILE_SHA256:", 'if False:'),
        'ignore-model-binding': ('llama_tokens.py', "if any(getattr(pin, key, None) != value for key, value in PIN.items()):", 'if False:'),
        'ignore-tokenizer-version': ('llama_tokens.py', "if importlib.metadata.version('tiktoken') != '0.12.0':", 'if False:'),
        'omit-bos-token': ('llama_tokens.py', "rendered = '<|begin_of_text|>'", "rendered = ''"),
        'allow-server-reserve-overrun': ('ollama.py', "if result['prompt_eval_count'] + options['num_predict'] + 512 > options['num_ctx']:", 'if False:'),
    }
    def run(label, source):
        report = output/(label+'.xml')
        argv = [str(python), '-m', 'pytest', str(ROOT/'tests/test_token_accounting.py'), '-q',
                '-o', 'pythonpath='+str(source), '--junitxml='+str(report)]
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=60)
        (output/(label+'.txt')).write_text(result.stdout+'\n'+result.stderr)
        cases = ET.parse(report).getroot().findall('.//testcase')
        assert cases and not any(c.find('error') is not None or c.find('skipped') is not None for c in cases), label
        return {'name': label, 'exit': result.returncode, 'cases': len(cases),
                'failed_tests': [c.attrib['name'] for c in cases if c.find('failure') is not None], 'argv': argv}
    baseline = run('baseline', ROOT/'src')
    assert baseline['exit'] == 0, baseline
    results, detected = [], set()
    for label, (filename, before, after) in mutants.items():
        with tempfile.TemporaryDirectory(prefix='harness-token-mutation-') as directory:
            source = Path(directory)/'src'
            shutil.copytree(ROOT/'src/attune_harness', source/'attune_harness', ignore=shutil.ignore_patterns('__pycache__'))
            path = source/'attune_harness'/filename
            original = path.read_text(); assert before in original, label
            path.write_text(original.replace(before, after))
            result = run(label, source)
            assert result['exit'] == 1 and result['failed_tests'], result
            results.append(result); detected.update(result['failed_tests'])
    summary = {'status': 'passed', 'kind': 'targeted_mutations_not_exhaustive_mutation_score',
               'new_test_cases': baseline['cases'], 'distinct_tests_detecting_mutations': len(detected),
               'mutants_killed': len(results), 'mutants_tried': len(mutants), 'baseline': baseline,
               'results': results, 'model_calls': 0, 'working_source_modified': False}
    (output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps({k: v for k, v in summary.items() if k not in ('baseline', 'results')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); main(args.python.absolute(), args.output.absolute())
