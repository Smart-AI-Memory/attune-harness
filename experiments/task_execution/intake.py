"""Measure source-checkout intake without any participant/provider dispatch."""

import argparse
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

# Isolated Python omits the script directory; load this explicit sibling probe.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from baseline import ROOT, offline, sha, write


def probe(output, samples=30, process_samples=5):
    from attune_harness.task_contract import create_task
    from attune_harness.task_cli import clear_template_cache, present_task
    if samples < 1 or process_samples < 1:
        raise ValueError('Sample counts must be positive')
    output = output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    project = output / 'project'; project.mkdir()
    docs = project / 'docs'; docs.mkdir()
    (docs / 'guide.md').write_text('[Reference](reference.md)', encoding='utf-8')
    (docs / 'reference.md').write_text('Quartz retention evidence.', encoding='utf-8')
    write(project / 'context.json', {'schema_version': 1, 'project_root': '.'})
    config = project / 'registry.json'
    write(config, {'schema_version': 1, 'participants': {'assessor': {
        'adapter': 'deterministic', 'tools': ['retrieve', 'verify'], 'max_turns': 3, 'max_tool_calls': 2}}})
    directory = output / 'task'
    timings = {mode: [] for mode in ('cold', 'warm', 'bypass')}
    transport = []
    with offline():
        create_task(project, config, goal='Check the guide', directory=directory,
                    answers={'criteria': 'Identify unsupported claims', 'query': 'quartz',
                             'document': 'docs/guide.md', 'context': 'context.json',
                             'corpus': 'docs', 'assessor': 'assessor'})
        expected = present_task(directory)['submission']
        record_before = sha(directory / 'record.json')
        modes = list(timings)
        for i in range(samples):
            # Rotate order. Cold explicitly clears process-local entries.
            for mode in modes[i % 3:] + modes[:i % 3]:
                if mode == 'cold':
                    clear_template_cache()
                elif mode == 'warm':
                    present_task(directory)
                start = time.perf_counter_ns()
                result = present_task(directory, bypass=mode == 'bypass')
                elapsed = (time.perf_counter_ns() - start) / 1e6
                assert result['submission'] == expected and result['execution_status'] == 'not_started'
                assert result['intake_metrics']['cache'] == {'cold': 'miss', 'warm': 'hit', 'bypass': 'bypass'}[mode]
                timings[mode].append({'presentation_ms': elapsed, **result['intake_metrics']})
        write(output / 'samples.json', {'presentations': timings, 'guarded_fresh_process_ms': transport})
        for index in range(process_samples):
            start = time.perf_counter_ns()
            child = subprocess.run([sys.executable, '-I', '-B', str(Path(__file__).resolve()),
                                    '--child', str(directory)], cwd=output,
                                   capture_output=True, text=True, timeout=30)
            elapsed = (time.perf_counter_ns() - start) / 1e6
            write(output / f'child-{index}.json', {'exit': child.returncode, 'stdout': child.stdout,
                                                  'stderr': child.stderr, 'elapsed_ms': elapsed})
            if child.returncode:
                raise RuntimeError(child.stderr)
            result = json.loads(child.stdout)
            assert result['submission'] == expected and result['intake_metrics']['cache'] == 'miss'
            transport.append(elapsed)
        assert sha(directory / 'record.json') == record_before
    summary = {'schema_version': 1, 'samples_per_mode': samples, 'provider_attempts': 0,
               'python': sys.executable, 'presentation_median_ms': {
                   mode: statistics.median(row['presentation_ms'] for row in rows)
                   for mode, rows in timings.items()},
               'template_median_ms': {mode: statistics.median(row['elapsed_ms'] for row in rows)
                                      for mode, rows in timings.items()},
               'guarded_fresh_process_median_ms': statistics.median(transport),
               'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT / 'src/attune_harness').glob('*.py'))},
               'measurement_sha256': {str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__).resolve(), ROOT / 'experiments/task_execution/baseline.py')},
               'limits': ['Local source checkout; not installed qualification',
                          'Fresh process includes probe, source import, poison-boundary setup and JSON transport',
                          'No end-to-end assessment, live-model, UI or human timing measured']}
    write(output / 'samples.json', {'presentations': timings, 'guarded_fresh_process_ms': transport})
    write(output / 'summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--output', type=Path)
    mode.add_argument('--child', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--samples', type=int, default=30)
    parser.add_argument('--process-samples', type=int, default=5)
    args = parser.parse_args()
    if args.child:
        from attune_harness.task_cli import present_task
        with offline():
            print(json.dumps(present_task(args.child)))
    else:
        summary = probe(args.output, args.samples, args.process_samples)
        print(json.dumps({k: v for k, v in summary.items() if not k.endswith('sha256')}, indent=2))
