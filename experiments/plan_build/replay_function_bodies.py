"""Replay closed originals through a separate, zero-provider body-only prototype."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from unittest.mock import patch

import function_body_replacements as bodies

ROOT = Path(__file__).resolve().parents[2]
PREP = ROOT / 'docs/receipts/plan-build-luna-broader-preparation-2026-09-18'
NATIVE = ROOT / 'docs/receipts/plan-build-luna-broader-native-2026-09-18'
OUT = ROOT / 'docs/receipts/plan-build-function-body-replay-2026-09-18'
SPEC = importlib.util.spec_from_file_location('body_replay_screen', ROOT / 'experiments/plan_build/repair_models.py')
screen = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(screen)
read, write, sha = screen.read, screen.write, screen.sha

WITNESSES = '''        # Replay-only, post-hoc regression checks; original oracle stays frozen.
        for code, expected in ((2, 'interrupted'), (4, 'blocked')):
            with self.subTest(exit_code=code):
                result = SimpleNamespace(failure=None, returncode=code)
                observed = dict(collection_errors=0, setup_errors=0, exit_code=code,
                                session_started=True, collect_only=False,
                                failed=0, passed=0, collected=0)
                self.assertEqual(subject.classify(result, observed)[0], expected)
'''


def receipt_hashes():
    return {str(p.relative_to(ROOT)): sha(p) for p in (ROOT / 'docs/receipts').rglob('*')
            if p.is_file() and OUT not in p.parents and '__pycache__' not in p.parts}


def clearance(payload, semantic=True):
    return {'payload_digest': screen.digest(payload), 'inspected_before_execution': True,
            'safe_to_execute': True, 'semantic_passed': semantic,
            'method': 'Local body projection from already inspected originals or known reference. Active-session inspection, no native or independent reviewer. Known logic failures remain failures.'}


def evaluate(folder, candidate, destination, semantic=True):
    payload = screen.proposal(folder, candidate.decode())
    write(destination / 'projected-payload.json', payload)
    return screen.evaluate(folder, payload, destination, clearance(payload, semantic))


def rejected(operation):
    try:
        operation()
    except (ValueError, SyntaxError) as error:
        return {'rejected': True, 'error_type': type(error).__name__, 'reason': str(error)}
    raise AssertionError('A required boundary rejection was lost')


def run():
    closed = read(NATIVE / 'closeout-verification.json')
    assert closed['status'] == 'verified-closed'
    assert read(NATIVE / 'ledger.json')['status'] == 'closed-stopped-reference-leakage'
    assert sha(NATIVE / 'grades.json') == read(NATIVE / 'grade-freeze.json')['sha256'] == closed['grade_sha256']
    grades = read(NATIVE / 'grades.json')
    OUT.mkdir(exist_ok=False)
    prior = receipt_hashes()
    write(OUT / 'prior-receipts.json', prior)
    protocol = {
        'native_calls_permitted': 0, 'original_trial_closed_before_start': closed,
        'scope': 'Offline projection of all usable retained originals plus twenty references, not fresh worker responses.',
        'binding': 'Trusted original accepted path, symbol and actual source hash. The worker supplies body text only; copied original envelope hashes are not transplanted.',
        'source_profile': 'One top-level multiline function, four-space body indentation, UTF-8/LF source. Header, decorators and all bytes outside the original body span remain fixed.',
        'skip_policy': 'Do not repair malformed JSON or syntactically invalid Python. Retain skipped originals and all original grades.',
        'acceptance': 'Boundary passes, actual installed supplemental and protected probes pass, semantic review passes, no-repeat and stale-source controls pass.',
        'known_logic_witness': 'Only the replay copy of observed-test-classification acceptance.py adds exit-code 2/4 zero-test precedence assertions. These post-hoc checks are not independent model validation.',
        'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__), ROOT / 'experiments/plan_build/function_body_replacements.py', ROOT / 'tests/test_plan_build_function_bodies.py')},
        'start_unix': time.time(), 'original_grade_sha256': sha(NATIVE / 'grades.json'),
    }
    write(OUT / 'protocol.json', protocol)
    unit = subprocess.run([sys.executable, '-B', str(ROOT / 'tests/test_plan_build_function_bodies.py')], text=True, capture_output=True, check=False)
    write(OUT / 'boundary-unit-tests.json', {'argv': [sys.executable, '-B', 'tests/test_plan_build_function_bodies.py'], 'returncode': unit.returncode, 'stdout': unit.stdout, 'stderr': unit.stderr, 'native_calls': 0})
    assert unit.returncode == 0
    prepared = {}
    controls = []
    with patch.object(screen.review_participants, 'NativeExchange', screen.forbidden), patch.object(screen.driver.native, 'dispatch', screen.forbidden):
        for original in sorted((PREP / 'cases').iterdir()):
            folder = OUT / 'cases' / original.name
            shutil.copytree(original / 'fixture', folder / 'fixture')
            case = read(original / 'case.json')
            if case['id'] == 'observed-test-classification':
                oracle = folder / 'fixture/acceptance.py'
                text = oracle.read_text()
                anchor = '    def test_1(self):\n'
                assert text.count(anchor) == 1
                oracle.write_text(text.replace(anchor, anchor + WITNESSES))
                case['fixture_sha256']['acceptance.py'] = sha(oracle)
                write(folder / 'oracle-change.json', {'original_sha256': sha(original / 'fixture/acceptance.py'), 'replay_sha256': sha(oracle), 'post_hoc': True, 'added_checks': WITNESSES})
            write(folder / 'case.json', case)
            source = (folder / 'fixture' / case['output']).read_bytes()
            binding = bodies.bind(source, case['output'], case['symbol'])
            reference = read(original / 'reference.json')['text'].encode()
            body = bodies.extract_body(reference, case['symbol'])
            candidate = bodies.replace_body(source, binding, body)
            preserved = bodies.preservation(source, candidate, case['symbol'])
            assert all(preserved.values())
            positive = evaluate(folder, candidate, OUT / 'controls/reference' / case['id'])
            assert positive['passed'], (case['id'], positive)
            escape = rejected(lambda: bodies.replace_body(source, binding, body + '\nUNRELATED_NEW_BEHAVIOR = True\n'))
            stale = rejected(lambda: bodies.replace_body(source + b'# foreign concurrent edit\n', binding, body))
            controls.append({'case': case['id'], 'reference_passed': True, 'preservation': preserved, 'dedent_escape': escape, 'stale_source': stale})
            prepared[case['id']] = (folder, case, source, binding)
            print('Reference and boundary controls: ' + case['id'], flush=True)

        rows = []
        for grade in grades:
            call_id = grade['id']
            folder, case, source, binding = prepared[grade['case']]
            original = NATIVE / 'calls' / call_id
            row = {'id': call_id, 'case': grade['case'], 'original_passed': grade['passed'],
                   'original_inspection_sha256': grade['inspection_sha256'], 'original_contract_valid': grade['contract_valid']}
            if not (original / 'decoded.json').exists():
                row.update(replay_passed=False, status='skipped-malformed-original-json', original_preserved=True)
                rows.append(row)
                continue
            payload = read(original / 'decoded.json')['payload']
            assert len(payload['files']) == 1 and payload['files'][0]['path'] == case['output']
            native_source = payload['files'][0]['text'].encode()
            try:
                body = bodies.extract_body(native_source, case['symbol'])
            except (ValueError, SyntaxError) as error:
                row.update(replay_passed=False, status='skipped-invalid-original-python', reason=str(error), original_preserved=True)
                rows.append(row)
                continue
            destination = OUT / 'replays' / call_id
            write(destination / 'body-only.json', {'body': body})
            write(destination / 'trusted-binding.json', binding.__dict__)
            try:
                candidate = bodies.replace_body(source, binding, body)
            except ValueError as error:
                row.update(replay_passed=False, status='rejected-before-effects', reason=str(error))
                rows.append(row)
                continue
            preserved = bodies.preservation(source, candidate, case['symbol'])
            assert all(preserved.values())
            known_semantic = call_id not in ('lb02', 'lb15')
            result = evaluate(folder, candidate, destination, semantic=known_semantic)
            row.update(status=result['status'], replay_passed=result['passed'], preservation=preserved,
                       probes_passed=[p['passed'] for p in result['probes']],
                       projected_source_sha256=screen.digest(candidate.decode()),
                       evaluation_sha256=sha(destination / 'evaluation.json'),
                       original_envelope_reused=False)
            rows.append(row)
            print(json.dumps({k: row[k] for k in ('id', 'original_passed', 'replay_passed', 'status')}), flush=True)

        # Remove the body restriction: the untouched original full-file proposal
        # reproduces lb07's unrelated renderer regression in a disposable owner.
        lb07 = read(NATIVE / 'calls/lb07/decoded.json')['payload']['files'][0]['text'].encode()
        unscoped = evaluate(prepared['substantive-prose'][0], lb07, OUT / 'controls/no-body-boundary', semantic=False)
        assert unscoped['probes'][0]['passed'] and not unscoped['probes'][1]['passed']
        # Remove only the replay-added logic checks: the same bounded body passes
        # the original eight checks, demonstrating why body scope alone is insufficient.
        lb02 = read(OUT / 'replays/lb02/projected-payload.json')['files'][0]['text'].encode()
        old_checks = evaluate(PREP / 'cases/observed-test-classification', lb02, OUT / 'controls/no-new-logic-checks', semantic=False)
        assert all(p['passed'] for p in old_checks['probes']) and not old_checks['passed']
        by_id = {r['id']: r for r in rows}
        assert by_id['lb07']['replay_passed'] and not by_id['lb07']['original_passed']
        assert by_id['lb12']['replay_passed'] and not by_id['lb12']['original_passed']
        assert by_id['lb02']['probes_passed'] == [True, False] and not by_id['lb02']['replay_passed']
        assert not by_id['lb15']['replay_passed'] and not by_id['lb18']['replay_passed']
    write(OUT / 'reference-and-boundary-controls.json', controls)
    write(OUT / 'replay-results.json', rows)
    assert all(sha(ROOT / name) == expected for name, expected in prior.items())
    assert sha(NATIVE / 'grades.json') == protocol['original_grade_sha256']
    assert all(sha(ROOT / name) == expected for name, expected in protocol['source_sha256'].items())
    summary = {
        'native_model_calls': 0, 'additional_worker_credits': 0, 'new_api_dollars': 0,
        'ordinary_session_usage_excluded': True, 'originals': len(rows),
        'original_passes_unchanged': sum(r['original_passed'] for r in rows),
        'original_grade_sha256': protocol['original_grade_sha256'],
        'prior_receipts_unchanged': len(prior), 'reference_replays_passed': len(controls),
        'dedent_attacks_rejected': len(controls), 'stale_sources_rejected': len(controls),
        'boundary_unit_tests': 12,
        'body_projections_evaluated': sum('evaluation_sha256' in r for r in rows),
        'projected_replays_passed': sum(r['replay_passed'] for r in rows),
        'skipped_original_ids': [r['id'] for r in rows if r['status'].startswith('skipped')],
        'unchanged_rejected_ids': [r['id'] for r in rows if r['status'] == 'rejected-before-effects'],
        'unrelated_edit_prevented': by_id['lb07']['replay_passed'],
        'within_function_failure_detected_by_actual_checks': by_id['lb02']['probes_passed'] == [True, False],
        'logic_guard_removal_reproduces_eight_green_original_checks': all(p['passed'] for p in old_checks['probes']),
        'body_guard_removal_reproduces_unrelated_regression': not unscoped['probes'][1]['passed'],
        'original_grades_changed': False, 'production_code_changed': False, 'task_8_accepted': False,
        'limits': 'Post-hoc replay of retained full-file replies, not a fresh model trial. Body scope prevents unrelated source edits, not runtime side effects or logic defects. Original contamination remains. No native reliability, speed or cost advantage measured.',
    }
    write(OUT / 'summary.json', summary)
    files = [p for p in OUT.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    write(OUT / 'manifest.json', {str(p.relative_to(ROOT)): sha(p) for p in sorted(files)})
    print(json.dumps(summary, sort_keys=True), flush=True)


if __name__ == '__main__':
    run()
