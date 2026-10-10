"""Read-only qualification diagnostics; this report never qualifies a platform."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

MAX_INPUT_BYTES = 16 * 1024 * 1024


def _integer(value):
    return type(value) is int


def _loads(data):
    def refuse(value):
        raise ValueError('nonfinite JSON constant: ' + value)
    def number(value, convert):
        result = convert(value)
        try:
            finite = math.isfinite(result)
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError('nonfinite or oversized JSON number')
        return result
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key: ' + key)
            result[key] = value
        return result
    return json.loads(data, parse_constant=refuse, object_pairs_hook=object_pairs,
                      parse_int=lambda v:number(v, int), parse_float=lambda v:number(v, float))


def diagnose(directory):
    directory = Path(directory)
    issues, warnings, inputs = [], [], {}

    def read(name):
        path = directory / name
        try:
            if path.is_symlink() or not path.is_file():
                raise ValueError('missing or nonregular file')
            with path.open('rb') as stream:
                data = stream.read(MAX_INPUT_BYTES + 1)
            if len(data) > MAX_INPUT_BYTES:
                raise ValueError('input exceeds diagnostic size bound')
            inputs[name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            return data
        except (OSError, ValueError) as error:
            issues.append(name + ': ' + str(error))
            return None

    receipt, events, counts = {}, [], None
    data = read('platform.json')
    if data is not None:
        try:
            receipt = _loads(data)
            if not isinstance(receipt, dict) or type(receipt.get('schema_version')) is not int or receipt['schema_version'] != 1:
                raise ValueError('unsupported receipt schema')
            if any(not _integer(receipt.get(k)) for k in ('pytest_exit', 'exit')):
                raise ValueError('missing or invalid process outcome')
            if not isinstance(receipt.get('status'), str) or receipt['status'] not in {
                    'checks_passed', 'failed', 'instrumented_checks_passed', 'instrumented_failed'}:
                raise ValueError('unsupported status')
        except (ValueError, UnicodeDecodeError) as error:
            receipt = {}
            issues.append('platform.json: ' + str(error))
    data = read('test-timings.jsonl')
    if data is not None:
        try:
            if not data.endswith(b'\n'):
                raise ValueError('incomplete final timing record')
            previous = -1
            for line in data.splitlines():
                event = _loads(line)
                if not isinstance(event, dict) or type(event.get('schema_version')) is not int or event['schema_version'] != 1:
                    raise ValueError('unsupported timing schema')
                elapsed = event.get('elapsed_seconds')
                if type(elapsed) not in (int, float) or not math.isfinite(elapsed):
                    raise ValueError('invalid elapsed time')
                if elapsed < previous or elapsed < 0:
                    warnings.append('Timing clock reversed or became negative; elapsed intervals are unreliable.')
                if not isinstance(event.get('event'), str) or event['event'] not in {'suite_start', 'suite_end', 'case_start', 'case_end',
                                             'phase_start', 'phase_end'}:
                    raise ValueError('unsupported timing event')
                if event['event'].startswith(('case_', 'phase_')) and not isinstance(event.get('nodeid'), str):
                    raise ValueError('missing case identity')
                if event['event'].startswith('phase_') and (not isinstance(event.get('phase'), str)
                        or event['phase'] not in {'setup','call','teardown'}):
                    raise ValueError('invalid phase')
                if 'duration_seconds' in event and (type(event['duration_seconds']) not in (int,float)
                        or not math.isfinite(event['duration_seconds'])):
                    raise ValueError('invalid duration')
                if event.get('duration_seconds', 0) < 0:
                    warnings.append('Timing duration is negative; elapsed intervals are unreliable.')
                previous = elapsed
                events.append(event)
            if not events or events[0]['event'] != 'suite_start':
                raise ValueError('missing suite start')
            if sum(e['event'] == 'suite_start' for e in events) != 1:
                raise ValueError('conflicting suite start records')
            if sum(e['event'] == 'suite_end' for e in events) > 1:
                raise ValueError('conflicting suite end records')
            if any(e['event'] == 'suite_end' for e in events[:-1]):
                raise ValueError('timing events after suite end')
            for event in events:
                if event['event'] == 'suite_end' and not _integer(event.get('exit_status')):
                    raise ValueError('invalid session outcome')
        except (ValueError, UnicodeDecodeError) as error:
            issues.append('test-timings.jsonl: ' + str(error))
    data = read('tests.xml')
    if data is not None:
        try:
            root = ET.fromstring(data)
            if root.tag not in ('testsuites', 'testsuite'):
                raise ValueError('unsupported JUnit root')
            suites = list(root.iter('testsuite'))
            if not suites:
                raise ValueError('missing test suite')
            counts = {key: sum(int(s.attrib[key]) for s in suites)
                      for key in ('tests', 'failures', 'errors', 'skipped')}
            if any(int(s.attrib[k]) < 0 for s in suites for k in counts):
                raise ValueError('negative JUnit count')
            if counts['tests'] <= counts['skipped'] or sum(counts[k] for k in ('failures','errors','skipped')) > counts['tests']:
                raise ValueError('inconsistent or empty JUnit counts')
            cases = list(root.iter('testcase'))
            observed = {key: sum(c.find(tag) is not None for c in cases)
                        for key, tag in [('failures','failure'), ('errors','error'), ('skipped','skipped')]}
            if not cases or any(counts[k] != v for k, v in observed.items()):
                raise ValueError('JUnit declared counts disagree with cases')
            difference = counts['tests'] - len(cases)
            if difference:
                # Pytest 9 adds passing subtests to tests but omits their case elements.
                # Require the matching closing transcript instead of ignoring count drift.
                transcript = read('tests.txt')
                summaries = re.findall(rb'(?m)^.*\b(\d+) subtests passed.* in [0-9.]+s.*$', transcript or b'')
                if difference < 0 or not summaries or difference != int(summaries[-1]):
                    raise ValueError('JUnit count difference lacks matching passing-subtest summary')
        except (ValueError, KeyError, ET.ParseError) as error:
            counts = None
            issues.append('tests.xml: ' + str(error))

    ends = [e for e in events if e['event'] == 'suite_end']
    session = ends[0] if len(ends) == 1 else None
    tests_clean = counts is not None and counts['failures'] == counts['errors'] == 0
    if receipt.get('pytest_exit') == 0 and session and session.get('exit_status') != 0:
        issues.append('session and controller outcomes conflict')
    if session and session.get('exit_status') == 0 and counts and not tests_clean:
        issues.append('session and JUnit outcomes conflict')
    if receipt.get('status') in ('checks_passed', 'instrumented_checks_passed') and (
            receipt.get('exit') != 0 or receipt.get('pytest_exit') != 0):
        issues.append('receipt status conflicts with process outcomes')
    if receipt.get('status') in ('failed', 'instrumented_failed') and receipt.get('exit') == 0:
        issues.append('failed receipt has successful final exit')
    if receipt.get('pytest_exit') != 0 and receipt.get('exit') == 0:
        issues.append('failed pytest process has successful final exit')
    if receipt.get('failure') == 'suite_timeout' and receipt.get('pytest_exit') != 124:
        issues.append('timeout marker conflicts with process outcome')
    if bool(receipt.get('instrumentation')) != str(receipt.get('status', '')).startswith('instrumented_'):
        issues.append('instrumentation label conflicts with status')

    classification = 'inconclusive_evidence'
    explanation = 'Missing, invalid or incomplete evidence; original verdict is unchanged.'
    if not issues:
        if receipt.get('failure') == 'suite_timeout' and receipt['pytest_exit'] == 124:
            if session and session['exit_status'] == 0 and tests_clean:
                classification = 'session_completed_process_timeout'
                explanation = 'Pytest session completed successfully; supervised process exceeded deadline. Late-exit cause unknown.'
            else:
                classification = 'suite_process_timeout'
                explanation = 'Supervised pytest process exceeded deadline; successful session completion is unproven.'
        elif session and (session['exit_status'] != 0 or not tests_clean):
            classification = 'pytest_session_failed'
            explanation = 'Pytest recorded a failing session; see original failures and transcript.'
        elif receipt['pytest_exit'] != 0:
            classification = 'pytest_process_failed'
            explanation = 'Supervised pytest process returned nonzero; original verdict is unchanged.'
        elif not session:
            issues.append('missing suite end; session completion unproven')
        elif receipt['exit'] != 0:
            classification = 'post_pytest_qualification_failed'
            explanation = 'Pytest process succeeded; later qualification checks recorded failure.'
        else:
            classification = 'instrumented_success_recorded' if receipt.get('instrumentation') else 'success_recorded'
            explanation = 'Original receipt records success; this diagnostic does not verify identity or grant qualification.'
    return {'schema_version': 1, 'qualification_authority': False,
            'classification': classification, 'explanation': explanation,
            'original_outcome': {k: receipt.get(k) for k in ('status','pytest_exit','exit','failure','instrumentation')},
            'session_end': session, 'junit_counts': counts,
            'last_timing_event': events[-1] if events else None,
            'timing_sequence_valid': not any(issue.startswith('test-timings.jsonl:') for issue in issues),
            'timing_elapsed_trustworthy': not warnings,
            'timing_warnings': list(dict.fromkeys(warnings)),
            'evidence_issues': issues, 'inputs': inputs,
            'limits': ['advisory only; installed-source and evidence authenticity are not reverified',
                       'session timestamps use a later epoch than controller timeout; no exact shutdown gap inferred']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    evidence = args.evidence.resolve()
    if args.output and args.output.resolve().is_relative_to(evidence):
        parser.error('Keep new diagnostic output outside original evidence')
    result = diagnose(evidence)
    rendered = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.output:
        with args.output.open('x', encoding='utf-8') as stream:
            stream.write(rendered)
    print(rendered, end='')
    return 0  # Successful analysis is never a qualification verdict.


if __name__ == '__main__':
    raise SystemExit(main())
