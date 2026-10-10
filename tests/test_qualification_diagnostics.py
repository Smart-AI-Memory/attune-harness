"""Prototype diagnostic regressions; no qualification assertion is weakened."""
# qualify: platform
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('diagnostic', ROOT / 'scripts/diagnose_qualification.py')
DIAGNOSTIC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DIAGNOSTIC)


def evidence(root, *, controller=0, final=0, session=0, instrumentation=False):
    receipt = {'schema_version': 1, 'pytest_exit': controller, 'exit': final,
               'status': ('instrumented_' if instrumentation else '') + ('checks_passed' if final == 0 else 'failed')}
    if instrumentation:
        receipt['instrumentation'] = 'coverage; not platform qualification'
    if controller == 124:
        receipt['failure'] = 'suite_timeout'
    (root / 'platform.json').write_text(json.dumps(receipt))
    events = [{'schema_version': 1, 'event': 'suite_start', 'elapsed_seconds': 0},
              {'schema_version': 1, 'event': 'suite_end', 'elapsed_seconds': 1, 'exit_status': session}]
    (root / 'test-timings.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in events))
    (root / 'tests.xml').write_text('<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0"><testcase name="synthetic"/></testsuite></testsuites>')


@pytest.mark.parametrize('controller,final,session,expected', [
    (124,124,0,'session_completed_process_timeout'),
    (1,1,1,'pytest_session_failed'), (0,1,0,'post_pytest_qualification_failed'),
    (0,0,0,'success_recorded')])
def test_outcomes_stay_distinct(tmp_path, controller, final, session, expected):
    evidence(tmp_path, controller=controller, final=final, session=session)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    result = DIAGNOSTIC.diagnose(tmp_path)
    assert result['classification'] == expected
    assert result['qualification_authority'] is False
    assert result['original_outcome']['exit'] == final
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


def test_instrumentation_never_becomes_qualification(tmp_path):
    evidence(tmp_path, instrumentation=True)
    result = DIAGNOSTIC.diagnose(tmp_path)
    assert result['classification'] == 'instrumented_success_recorded'
    assert result['original_outcome']['status'] == 'instrumented_checks_passed'
    assert result['qualification_authority'] is False


@pytest.mark.parametrize('name,content', [
    ('platform.json','{}'), ('platform.json','{'),
    ('platform.json','{"schema_version":1,"pytest_exit":0,"exit":0,"status":[]}'),
    ('platform.json','{"schema_version":1,"pytest_exit":1,"pytest_exit":0,"exit":0,"status":"checks_passed"}'),
    ('test-timings.jsonl','{"schema_version":1,"event":"suite_end"}'),
    ('test-timings.jsonl','{"schema_version":1,"event":"suite_start","elapsed_seconds":NaN}\n'),
    ('test-timings.jsonl','{"schema_version":1,"event":"suite_start","elapsed_seconds":true}\n'),
    ('test-timings.jsonl','{"schema_version":1,"event":[],"elapsed_seconds":0}\n'),
    ('test-timings.jsonl','{"schema_version":1,"event":"phase_start","nodeid":"x","phase":[],"elapsed_seconds":0}\n'),
    ('test-timings.jsonl','{"schema_version":1,"event":"suite_start","elapsed_seconds":1e999}\n'),
    ('test-timings.jsonl','{"schema_version":1,"event":"suite_start","elapsed_seconds":' + '9'*1000 + '}\n'),
    ('tests.xml','<testsuites>'),
    ('tests.xml','<testsuite tests="1" failures="0" errors="0" skipped="0"/>')])
def test_invalid_evidence_is_inconclusive(tmp_path, name, content):
    evidence(tmp_path, controller=124, final=124)
    (tmp_path / name).write_text(content)
    result = DIAGNOSTIC.diagnose(tmp_path)
    assert result['classification'] == 'inconclusive_evidence'
    assert result['evidence_issues'] and result['qualification_authority'] is False


def test_missing_evidence_is_inconclusive(tmp_path):
    result = DIAGNOSTIC.diagnose(tmp_path)
    assert result['classification'] == 'inconclusive_evidence'
    assert len(result['evidence_issues']) == 3


def test_shared_test_clock_does_not_invalidate_recorded_verdict(tmp_path):
    evidence(tmp_path, controller=124, final=124)
    path = tmp_path / 'test-timings.jsonl'
    events = [json.loads(line) for line in path.read_text().splitlines()]
    events.insert(1, {'schema_version':1,'event':'phase_end','elapsed_seconds':-999,
                     'nodeid':'synthetic_clock','phase':'call','outcome':'passed'})
    path.write_text(''.join(json.dumps(e) + '\n' for e in events))
    result = DIAGNOSTIC.diagnose(tmp_path)
    assert result['classification'] == 'session_completed_process_timeout'
    assert result['timing_elapsed_trustworthy'] is False
    assert result['timing_warnings']


@pytest.mark.parametrize('subtest_summary,expected', [('2','success_recorded'), ('1','inconclusive_evidence')])
def test_junit_subtest_count_requires_matching_summary(tmp_path, subtest_summary, expected):
    evidence(tmp_path)
    path = tmp_path / 'tests.xml'
    path.write_text(path.read_text().replace('tests="1"', 'tests="3"'))
    (tmp_path / 'tests.txt').write_text('1 passed, ' + subtest_summary + ' subtests passed in 1.23s\n')
    assert DIAGNOSTIC.diagnose(tmp_path)['classification'] == expected


def test_conflicting_session_is_inconclusive(tmp_path):
    evidence(tmp_path, session=1)
    assert DIAGNOSTIC.diagnose(tmp_path)['classification'] == 'inconclusive_evidence'


@pytest.mark.parametrize('patch', [{'status':'failed'}, {'status':'unknown'},
    {'failure':'suite_timeout'}, {'pytest_exit':124}, {'schema_version':True},
    {'pytest_exit':True}, {'extra':float('nan')}])
def test_receipt_contradictions_are_inconclusive(tmp_path, patch):
    evidence(tmp_path)
    path = tmp_path / 'platform.json'
    path.write_text(json.dumps(dict(json.loads(path.read_text()), **patch)))
    assert DIAGNOSTIC.diagnose(tmp_path)['classification'] == 'inconclusive_evidence'


@pytest.mark.parametrize('mutation', ['duplicate_start','duplicate_end','late_event','bool_schema','bad_phase','bad_nodeid'])
def test_tainted_timing_sequence_is_inconclusive(tmp_path, mutation):
    evidence(tmp_path, controller=124, final=124)
    path = tmp_path / 'test-timings.jsonl'
    events = [json.loads(line) for line in path.read_text().splitlines()]
    if mutation == 'duplicate_start':
        events.insert(1, events[0])
    elif mutation == 'duplicate_end':
        events.append(events[-1])
    elif mutation == 'late_event':
        events.append({'schema_version':1, 'event':'case_start','elapsed_seconds':2,'nodeid':'late'})
    elif mutation == 'bool_schema':
        events[0]['schema_version'] = True
    elif mutation == 'bad_phase':
        events.insert(1, {'schema_version':1,'event':'phase_start','elapsed_seconds':0.5,'nodeid':'x','phase':'invalid'})
    else:
        events.insert(1, {'schema_version':1,'event':'case_start','elapsed_seconds':0.5,'nodeid':4})
    path.write_text(''.join(json.dumps(e) + '\n' for e in events))
    result = DIAGNOSTIC.diagnose(tmp_path)
    assert result['classification'] == 'inconclusive_evidence'
    assert result['timing_sequence_valid'] is False


def test_cli_refuses_original_directory_and_overwrite(tmp_path):
    original = tmp_path / 'original'
    original.mkdir()
    evidence(original)
    destination = tmp_path / 'existing.json'
    destination.write_text('preserve me')
    for output in (original / 'new.json', destination):
        result = subprocess.run([sys.executable, '-I', str(ROOT / 'scripts/diagnose_qualification.py'),
                                 '--evidence', str(original), '--output', str(output)],
                                capture_output=True, timeout=10)
        assert result.returncode != 0
    assert destination.read_text() == 'preserve me'
    assert not (original / 'new.json').exists()


def test_real_passing_session_with_atexit_stall_remains_failed(tmp_path):
    # Synthetic discrimination only; never an attribution of the retained Windows failure.
    child_test = tmp_path / 'test_synthetic.py'
    child_test.write_text('import atexit,time\natexit.register(time.sleep, 60)\ndef test_pass():\n    assert True\n')
    argv = [sys.executable, '-m', 'pytest', '-q', '-c', '/dev/null' if os.name == 'posix' else 'NUL',
            '-p', 'harness_qualification_stacks', '-o', 'faulthandler_timeout=0',
            '--junitxml=' + str(tmp_path / 'tests.xml'), str(child_test)]
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHONPATH=str(ROOT / 'scripts'),
               HARNESS_QUALIFICATION_OUTPUT=str(tmp_path))
    env.pop('PYTEST_ADDOPTS', None)
    env.pop('PYTEST_PLUGINS', None)
    with (tmp_path / 'synthetic-child.txt').open('wb') as log:
        child = subprocess.Popen(argv, cwd=tmp_path, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            startup_deadline = time.monotonic() + 15
            journal = tmp_path / 'test-timings.jsonl'
            while time.monotonic() < startup_deadline and child.poll() is None:
                if journal.exists() and b'"event": "suite_end"' in journal.read_bytes():
                    break
                time.sleep(0.02)
            else:
                pytest.fail('synthetic child did not reach session end within finite startup budget')
            with pytest.raises(subprocess.TimeoutExpired):
                child.wait(timeout=0.3)
        finally:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)
    (tmp_path / 'platform.json').write_text(json.dumps({'schema_version':1, 'status':'failed',
        'pytest_exit':124, 'exit':124, 'failure':'suite_timeout'}))
    result = DIAGNOSTIC.diagnose(tmp_path)
    assert result['classification'] == 'session_completed_process_timeout'
    assert result['session_end']['exit_status'] == 0
    assert result['junit_counts']['failures'] == result['junit_counts']['errors'] == 0
    assert result['original_outcome']['exit'] == 124
    assert 'cause unknown' in result['explanation'] and result['qualification_authority'] is False


def test_journal_clock_survives_test_replacing_shared_clock(tmp_path):
    test = tmp_path / 'test_clock.py'
    test.write_text('import time\ndef test_mock_clock(monkeypatch):\n    monkeypatch.setattr(time,"monotonic",lambda:-999)\n    assert time.monotonic()==-999\n')
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHONPATH=str(ROOT / 'scripts'),
               HARNESS_QUALIFICATION_OUTPUT=str(tmp_path))
    env.pop('PYTEST_ADDOPTS', None)
    env.pop('PYTEST_PLUGINS', None)
    result = subprocess.run([sys.executable,'-m','pytest','-q',
        '-c','/dev/null' if os.name == 'posix' else 'NUL','-p','harness_qualification_stacks',
        '-o','faulthandler_timeout=0',str(test)], cwd=tmp_path,env=env,capture_output=True,timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    journal = [json.loads(line) for line in (tmp_path / 'test-timings.jsonl').read_text().splitlines()]
    elapsed = [e['elapsed_seconds'] for e in journal]
    assert elapsed == sorted(elapsed) and all(t >= 0 for t in elapsed)
    assert journal[-1]['event'] == 'suite_end' and journal[-1]['exit_status'] == 0
