"""Freeze real local legacy behavior without calling a model or paid provider.

Run from the checkout with its review/MCP extras; output must not exist.
The retained directory contains path-bound records: do not move it for resume.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager, redirect_stderr, redirect_stdout
import hashlib
import importlib.metadata
import io
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
# Intentionally measure this checkout, not a possibly older installed Harness.
sys.path.insert(0, str(ROOT / 'src'))

COMMANDS = (
    'review-form', 'review', 'inspect-review', 'resume-review', 'reconcile-review',
    'transfer-review', 'cancel-review', 'extension', 'code-config', 'index',
    'retrieval-task', 'triage-check', 'repair-economics', 'github-checks',
    'mcp-serve', 'mcp-inspect', 'verify', 'retrieve',
)


class LiveDispatchForbidden(BaseException):
    """A poison boundary must escape CLI exception-to-JSON conversion."""


@contextmanager
def offline():
    from attune_harness import review_participants, voyage_provider
    attempted = []

    def reject(*args, **kwargs):
        attempted.append('live provider construction')
        raise LiveDispatchForbidden('Baseline cannot invoke a live provider')

    with patch.object(review_participants, 'NativeExchange', reject), \
            patch.object(voyage_provider, 'VoyageProvider', reject):
        yield attempted
    if attempted:
        raise LiveDispatchForbidden('A live invocation was attempted')


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(directory, content='[Quartz retention policy](reference.md)'):
    from attune_harness.review_contract import load_registry, review_form
    directory.mkdir()
    corpus = directory / 'project'
    corpus.mkdir()
    (corpus / 'guide.md').write_text(content, encoding='utf-8')
    (corpus / 'reference.md').write_text('Quartz retention policy is a test fixture.', encoding='utf-8')
    write(directory / 'context.json', {'schema_version': 1, 'project_root': 'project'})
    config = directory / 'config.json'
    write(config, {'schema_version': 1, 'participants': {
        name: {'adapter': 'deterministic', 'tools': ['retrieve', 'verify'],
               'max_turns': 3, 'max_tool_calls': 2} for name in ('alpha', 'beta', 'gamma')
    }})
    request = directory / 'request.json'
    data = review_form(load_registry(config))['submission']
    data.update(accepted=True, answers={
        'objective': 'Check evidence', 'query': 'quartz retention policy',
        'document': 'project/guide.md', 'context': 'context.json', 'corpus': 'project',
        'lead': 'alpha', 'reviewer': 'beta',
    })
    write(request, data)
    return request, config, directory / 'run'


def cli(argv):
    from attune_harness.cli import main
    stdout, stderr = io.StringIO(), io.StringIO()
    start = time.perf_counter_ns()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            code = main([str(x) for x in argv])
        except SystemExit as exc:
            code = exc.code
    result = {'argv': [str(x) for x in argv], 'exit_code': code,
              'stdout': stdout.getvalue(), 'stderr': stderr.getvalue(),
              'elapsed_ms': (time.perf_counter_ns() - start) / 1e6}
    try:
        result['json'] = json.loads(result['stdout'])
    except json.JSONDecodeError:
        pass
    return result


def measure(call, samples):
    values = []
    for _ in range(samples):
        start = time.perf_counter_ns()
        call()
        values.append((time.perf_counter_ns() - start) / 1e6)
    return {'samples_ms': values, 'median_ms': statistics.median(values),
            'p95_ms': sorted(values)[math.ceil(.95 * len(values)) - 1] if len(values) >= 20 else None}


def source_snapshot():
    paths = sorted((ROOT / 'src/attune_harness').glob('*.py'))
    paths += [ROOT / 'pyproject.toml', ROOT / 'tests/test_voyage.py',
              ROOT / 'docs/voyage-rag-session-starter.md',
              ROOT / 'experiments/voyage/profile_validation.py',
              Path(__file__).resolve(), ROOT / 'tests/test_task_compatibility.py']
    return {str(p.relative_to(ROOT)): sha(p) for p in paths if p.is_file()}


def baseline(output, samples=50, process_samples=20):
    from attune_harness.review_contract import accept_request, load_registry, review_form
    from attune_harness.review_store import inspect_run
    from attune_harness.mcp_server import RetrievalSession
    import attune_forms

    if samples < 1 or process_samples < 1:
        raise ValueError('Sample counts must be positive')
    output = output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    captured = output / 'cli'
    captured.mkdir()
    snapshots = output / 'snapshots'
    snapshots.mkdir()
    before = source_snapshot()
    rows = {}

    def capture(name, argv, expected):
        result = cli(argv)
        write(captured / f'{name}.json', result)  # Retain failures before asserting.
        assert result['exit_code'] == expected, (name, result)
        rows[name] = {'exit_code': result['exit_code'],
                      'status': result.get('json', {}).get('status'),
                      'command': str(argv[0])}
        return result.get('json', result)

    def review_args(case, *extra):
        req, cfg, run = case
        return ['review', req, '--config', cfg, '--run-dir', run, *extra]

    def resume_args(case, checkpoint):
        req, cfg, run = case
        return ['resume-review', run, '--request', req, '--config', cfg, '--checkpoint', checkpoint]

    with offline() as attempted:
        capture('help', ['--help'], 0)
        for name in COMMANDS:
            capture(f'help-{name}', [name, '--help'], 0)
        clean = fixture(output / 'clean')
        capture('form', ['review-form', '--config', clean[1]], 0)
        completed = capture('clean', review_args(clean), 0)
        assert (completed['document_outcome'], completed['retrieval_outcome']) == ('verified', 'retrieved')
        capture('inspect', ['inspect-review', clean[2]], 0)
        capture('completed-replay', resume_args(clean, completed['checkpoint_digest']), 0)
        assert inspect_run(clean[2]) == completed
        for name, content, outcome in [('refuted', '[broken](missing.md)', 'refuted'),
                                       ('unknown', 'No supported claims.', 'unknown')]:
            case = fixture(output / name, content)
            result = capture(name, review_args(case), 1)
            assert result['status'] == 'completed' and result['document_outcome'] == outcome
        empty = fixture(output / 'no-evidence')
        value = json.loads(empty[0].read_text()); value['answers']['query'] = 'zzzznotfound'
        write(empty[0], value)
        assert capture('no-evidence', review_args(empty), 1)['retrieval_outcome'] == 'no_results'
        for name, edit in [('declined', {'accepted': False}), ('stale-form', {'form_revision': 'stale'})]:
            case = fixture(output / name)
            value = json.loads(case[0].read_text()); value.update(edit); write(case[0], value)
            capture(name, review_args(case), 2)
            assert not case[2].exists()
        capture('missing-input', ['review', output / 'missing.json', '--config', clean[1],
                                  '--run-dir', output / 'missing-run'], 2)

        paused_case = fixture(output / 'paused')
        paused = capture('pause', review_args(paused_case, '--max-operations', '2'), 1)
        write(snapshots / 'paused.json', paused)
        finished = capture('resume', resume_args(paused_case, paused['checkpoint_digest']), 0)
        assert finished['events'][:2] == paused['events'] and len(finished['events']) == 13
        write(snapshots / 'resumed.json', finished)
        capture('stale-checkpoint', resume_args(paused_case, paused['checkpoint_digest']), 2)
        frozen_paused = fixture(output / 'frozen-paused')
        capture('frozen-paused', review_args(frozen_paused, '--max-operations', '2'), 1)
        for mode in ('cancel', 'transfer'):
            case = fixture(output / mode)
            record = capture(f'{mode}-pause', review_args(case, '--max-operations', '2'), 1)
            cmd = 'cancel-review' if mode == 'cancel' else 'transfer-review'
            extra = [] if mode == 'cancel' else ['--lead', 'gamma']
            record = capture(mode, [cmd, case[2], '--checkpoint', record['checkpoint_digest'],
                                    '--reason', 'frozen baseline', *extra], 1)
            if mode == 'transfer':
                record = capture('transferred-resume', resume_args(case, record['checkpoint_digest']), 0)
                assert record['participants']['lead']['participant_id'] == 'gamma'

        # A real local command writes once then loses its acknowledgement.
        uncertain = fixture(output / 'uncertain')
        peer = uncertain[0].parent / 'peer.py'
        effect = uncertain[0].parent / 'effect.txt'
        reply = uncertain[0].parent / 'reply.json'
        peer.write_text('import json,sys,pathlib\n'
                        'd=json.load(sys.stdin);p=pathlib.Path(sys.argv[1])\n'
                        'p.write_text(p.read_text()+"effect\\n" if p.exists() else "effect\\n")\n'
                        'pathlib.Path(sys.argv[2]).write_text(json.dumps(dict(schema_version=1,request_digest=d["request_digest"],action=dict(kind="final",text="Recovered local fixture reply"))))\n'
                        'sys.exit(23)\n', encoding='utf-8')
        cfg = json.loads(uncertain[1].read_text())
        cfg['participants']['alpha'].update(adapter='command', timeout=5,
                                            command=[sys.executable, '-I', str(peer), str(effect), str(reply)])
        write(uncertain[1], cfg)
        req = json.loads(uncertain[0].read_text())
        req['form_revision'] = review_form(load_registry(uncertain[1]))['form_revision']
        write(uncertain[0], req)
        failed = capture('uncertain-effect', review_args(uncertain, '--allow-external'), 2)
        write(snapshots / 'uncertain.json', failed)
        unresolved = capture('uncertain-resume', [*resume_args(uncertain, failed['checkpoint_digest']), '--allow-external'], 2)
        assert unresolved['status'] == 'unresolved' and effect.read_text() == 'effect\n'
        reconciled = capture('reconcile', ['reconcile-review', uncertain[2], '--checkpoint', failed['checkpoint_digest'],
                                          '--event', failed['events'][-1]['event_id'], '--reply', reply], 1)
        capture('reconciled-resume', [*resume_args(uncertain, reconciled['checkpoint_digest']), '--allow-external'], 0)
        assert effect.read_text() == 'effect\n'

        # Leave another genuine unresolved record at its original bound paths.
        frozen_uncertain = fixture(output / 'frozen-uncertain')
        frozen_effect = frozen_uncertain[0].parent / 'effect.txt'
        frozen_reply = frozen_uncertain[0].parent / 'reply.json'
        cfg = json.loads(frozen_uncertain[1].read_text())
        cfg['participants']['alpha'].update(adapter='command', timeout=5,
            command=[sys.executable, '-I', str(peer), str(frozen_effect), str(frozen_reply)])
        write(frozen_uncertain[1], cfg)
        req = json.loads(frozen_uncertain[0].read_text())
        req['form_revision'] = review_form(load_registry(frozen_uncertain[1]))['form_revision']
        write(frozen_uncertain[0], req)
        capture('frozen-uncertain', review_args(frozen_uncertain, '--allow-external'), 2)
        assert frozen_effect.read_text() == 'effect\n'

        capture('verify', ['verify', clean[0].parent / 'project/guide.md', '--context', clean[0].parent / 'context.json'], 0)
        capture('retrieve', ['retrieve', 'quartz retention policy', '--corpus', clean[0].parent / 'project'], 0)
        capture('extension-discover', ['extension', 'discover', ROOT / 'examples/extensions/plugin/src/attune_harness_evidence/extension.json'], 0)
        event = output / 'event.json'
        write(event, {'event': {'repository': 'fixture', 'revision': 'a'*40, 'check': 'tests', 'run_id': '1',
                              'status': 'failed', 'failure_kind': 'test', 'effects': 'none', 'attempts': 0},
                      'handled_keys': [], 'max_attempts': 2})
        assert capture('triage', ['triage-check', event], 0)['dispatch_authorized'] is False
        checks = output / 'checks.json'; write(checks, {'total_count': 0, 'check_runs': []})
        capture('github-checks', ['github-checks', checks, '--repository', 'example/project', '--revision', 'a'*40], 0)
        invalid = output / 'invalid.json'; write(invalid, {})
        capture('economics-invalid', ['repair-economics', invalid], 2)
        capture('code-config', ['code-config', '--repo', clean[0].parent / 'project', '--index-dir', output / 'index'], 0)
        capture('index-invalid', ['index', 'plan', '--config', invalid], 2)
        capture('retrieval-task-invalid', ['retrieval-task', '--config', invalid, '--generation', 'missing', '--objective', 'Check sources'], 2)
        mcp_case = fixture(output / 'mcp')
        cfg = json.loads(mcp_case[1].read_text())
        for participant in cfg['participants'].values(): participant['tools'] = ['retrieve']
        write(mcp_case[1], cfg)
        req = json.loads(mcp_case[0].read_text())
        req['form_revision'] = review_form(load_registry(mcp_case[1]))['form_revision']; write(mcp_case[0], req)
        scope = RetrievalSession(mcp_case[0], mcp_case[1], 'alpha', mcp_case[2])
        with scope.store.lease():
            scope.save(); scope.invoke('harness.retrieve', {'query': 'quartz retention policy', 'k': 3}); scope.finish()
        capture('mcp-inspect', ['mcp-inspect', mcp_case[2]], 0)
        capture('mcp-serve-invalid', ['mcp-serve', '--request', output / 'missing.json', '--config', clean[1],
                                     '--participant', 'alpha', '--session-dir', output / 'invalid-mcp'], 2)
        assert json.loads((captured / 'mcp-serve-invalid.json').read_text())['stdout'] == ''

        registry = load_registry(clean[1]); definition = review_form(registry)['definition']
        form = attune_forms.form_from_dict(definition)
        timings = {
            'schema_build_warm': measure(lambda: attune_forms.form_from_dict(definition), samples),
            'markdown_render_warm': measure(lambda: attune_forms.form_to_markdown(form), samples),
            'review_form_warm': measure(lambda: review_form(registry), samples),
            'accept_request_warm': measure(lambda: accept_request(clean[0], registry), samples),
        }

        def child():
            run = subprocess.run([sys.executable, '-I', str(Path(__file__).resolve()), '--form-child', str(clean[1])],
                                 cwd=output, text=True, capture_output=True, timeout=30)
            assert run.returncode == 0, run.stderr
            value = json.loads(run.stdout)
            assert value['status'] == 'ready'
        timings['fresh_process_cli'] = measure(child, process_samples)
        assert not attempted

    assert before == source_snapshot(), 'Source or concurrent work changed during baseline'
    write(output / 'timings.json', timings)
    dependencies = {name: importlib.metadata.version(name) for name in
                    ('attune-forms', 'attune-verify', 'attune-rag', 'mcp')}
    modules = {name: {'path': str(Path(sys.modules[name].__file__).absolute()),
                      'sha256': sha(Path(sys.modules[name].__file__))}
               for name in ('attune_forms', 'attune_verify', 'attune_rag', 'mcp')}
    head = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
                          capture_output=True, text=True, check=True).stdout.strip()
    summary = {'schema_version': 1, 'python': sys.executable, 'python_version': sys.version,
               'source_root': str(ROOT), 'git_head': head, 'source_sha256': before,
               'dependencies': dependencies, 'library_modules': modules,
               'commands': list(COMMANDS), 'captures': rows, 'provider_attempts': 0,
               'uncertain_peer_effects': {'reconciled': 1, 'retained_unresolved': 1},
               'retained_runs': {'completed': str(clean[2]), 'paused': str(frozen_paused[2]),
                                 'uncertain': str(frozen_uncertain[2])},
               'completed_review_events': len(completed['events']),
               'timings': {k: {n: v for n, v in val.items() if n != 'samples_ms'} for k, val in timings.items()},
               'limitations': ['Source-checkout baseline, not installed qualification',
                               'No live model quality, user-visible transport or human timing',
                               'Fresh-process time includes this probe and poison-boundary setup',
                               'Fresh processes may use warm OS filesystem caches',
                               'All command help captured; some operation routes use negative fixtures; full behavior in named regression suites',
                               'Saved records bind original absolute fixture paths'],
               'billed_cost_usd': None}
    write(output / 'summary.json', summary)
    write(output / 'manifest.json', {str(p.relative_to(output)): sha(p)
                                     for p in sorted(output.rglob('*')) if p.is_file()})
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--output', type=Path)
    mode.add_argument('--form-child', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--samples', type=int, default=50)
    parser.add_argument('--process-samples', type=int, default=20)
    args = parser.parse_args()
    if args.form_child:
        with offline():
            result = cli(['review-form', '--config', args.form_child])
            print(result['stdout'], end='')
            raise SystemExit(result['exit_code'])
    result = baseline(args.output, args.samples, args.process_samples)
    print(json.dumps({'output': str(args.output.absolute()), 'captures': len(result['captures']),
                      'provider_attempts': result['provider_attempts'], 'timings': result['timings']}, indent=2))
