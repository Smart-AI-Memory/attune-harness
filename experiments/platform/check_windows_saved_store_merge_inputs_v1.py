"""Read public source/provenance only; never import or execute a proof/helper."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

LIMIT = 1024 * 1024
PINS = {
    'experiments/platform/windows_saved_store_standard_user_gui_proposal_v3b3.ps1': '696879df5b141def393235708f3a2baf0e8c9bb1cdb24d125082b53bc81a5804',
    'experiments/platform/windows_saved_store_gui_lease_helper_v4.ps1': '5786e2eefbb6e61f65ef4caaf17a4668ad7dd14ae8f552d72dffcc21845729bf',
    'experiments/platform/windows_saved_store_helper_cold_compile_v1.ps1': '496275b061b807302281834e036546361b5a1aa3651a3553c553b23db4db6885',
    'experiments/platform/windows_saved_store_combined_driver_v1.py': 'e3aa0931328aabd2541b64b21f717c478b8121278dc7d10bb597e0cb0cf41937',
    'experiments/platform/windows_saved_store_proof.py': 'b233497ffe18973eca3a4db29b2eca7ee5269c4ae2ef78429a8cf10db1ce7355',
    'experiments/platform/windows_saved_store_namespace_witness_v4.py': 'f326803457453fccf02b795144ef1a48986c4c7068eef87aa56d21591ddd643e',
    'src/attune_harness/windows_effects.py': 'ffc46d2f054a7bcf6c95230551a87fb5c73d9992ecebdde9497d2226d0763139',
}


def sha1(value):
    if not isinstance(value, str) or re.fullmatch(r'[0-9a-f]{40}', value) is None:
        raise ValueError('invalid_commit_id')
    return value


def parents(header):
    """Parse raw commit header: shallow traversal must not hide parent IDs."""
    if len(header) > 65536 or b'\n\n' not in header:
        raise ValueError('invalid_commit_header')
    result = []
    for line in header.split(b'\n\n', 1)[0].splitlines():
        if line.startswith(b'parent '):
            result.append(sha1(line[7:].decode('ascii')))
    return result


def provenance(event, expected_sha, head_sha, base_sha, actual_sha, actual_parents):
    sha1(expected_sha); sha1(actual_sha)
    if actual_sha != expected_sha:
        raise ValueError('checkout_not_event_sha')
    if event == 'pull_request':
        sha1(head_sha); sha1(base_sha)
        if actual_parents != [base_sha, head_sha]:
            raise ValueError('checkout_not_expected_merge')
    elif event != 'push':
        raise ValueError('unexpected_event')
    return {'event': event, 'event_sha': expected_sha, 'event_head': head_sha,
            'event_base': base_sha, 'actual_checkout': actual_sha,
            'actual_parents': actual_parents}


def git(repo, *arguments):
    # Read-only plumbing. No fetch, credential helper, branch or settings change.
    result = subprocess.run(['git', *arguments], cwd=repo, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
    if result.returncode or len(result.stdout) > 65536:
        raise ValueError('git_read_refused')
    return result.stdout


def observe_file(repo, path, expected, blob_reader):
    row = {'path': path, 'expected_sha256': expected}
    try:
        with (repo / path).open('rb') as stream:
            raw = stream.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise ValueError('source_limit')
        row['actual_sha256'] = hashlib.sha256(raw).hexdigest()
        row['actual_git_blob'] = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        row['head_git_blob'] = sha1(blob_reader(path))
        row['matched'] = row['actual_sha256'] == expected and row['actual_git_blob'] == row['head_git_blob']
    except (OSError, ValueError) as exc:
        row.update(matched=False, failure_type=type(exc).__name__)
    return row


def native_binding(raw):
    """Read the historical driver's literal binding as data, never import it."""
    tree = ast.parse(raw)
    values = [node.value.value for node in tree.body
              if isinstance(node, ast.Assign) and len(node.targets) == 1
              and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'NATIVE_SHA'
              and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)]
    if len(values) != 1 or re.fullmatch(r'[0-9a-f]{64}', values[0]) is None:
        raise ValueError('invalid_historical_driver_binding')
    return values[0]


def execute(repo, output, context, git_reader=git):
    if output.exists():
        raise ValueError('refuse_retained_report')
    report = {'status': 'started', 'sources': [], 'expected_sources': dict(PINS), 'failure_type': None,
              'account_fixture_invoked': False, 'accounts_or_credentials_created': False,
              'gui_objects_created': False, 'native_methods_invoked': False,
              'proof_invoked': False, 'future_account_readiness': False,
              't2_d3_gate': 'unpassed', 'production_port_allowed': False}

    def save():
        output.write_text(json.dumps(report, ensure_ascii=True, allow_nan=False,
                                     sort_keys=True, indent=2) + '\n', encoding='ascii')

    save()
    try:
        actual = git_reader(repo, 'rev-parse', 'HEAD').decode('ascii').strip()
        actual_parents = parents(git_reader(repo, 'cat-file', 'commit', 'HEAD'))
        report['provenance'] = {'actual_checkout': actual, 'actual_parents': actual_parents, **context}
        save()
        report['provenance'] = provenance(context['event'], context['sha'], context['head'],
                                          context['base'], actual, actual_parents)
        for path, digest in PINS.items():
            row = observe_file(repo, path, digest,
                               lambda path: git_reader(repo, 'rev-parse', 'HEAD:' + path).decode('ascii').strip())
            report['sources'].append(row)
            save()
        if not all(row['matched'] for row in report['sources']):
            raise ValueError('source_identity_refused')
        driver = repo / 'experiments/platform/windows_saved_store_combined_driver_v1.py'
        with driver.open('rb') as stream:
            driver_raw = stream.read(LIMIT + 1)
        if len(driver_raw) > LIMIT or hashlib.sha256(driver_raw).hexdigest() != PINS[str(driver.relative_to(repo)).replace('\\', '/')]:
            raise ValueError('historical_driver_changed_after_scan')
        report['historical_driver_native_binding'] = native_binding(driver_raw)
        report['historical_driver_matches_current_native'] = (
            report['historical_driver_native_binding'] == PINS['src/attune_harness/windows_effects.py'])
        report['status'] = 'merge_sources_verified_for_cold_control_only'
    except (OSError, ValueError, KeyError, UnicodeError, subprocess.SubprocessError) as exc:
        report.update(status='merge_sources_refused', failure_type=type(exc).__name__)
    finally:
        save()
    return 0 if report['status'] == 'merge_sources_verified_for_cold_control_only' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    context = {key: os.environ.get('T2_EVENT_' + name, '') for key, name in
               [('event', 'NAME'), ('sha', 'SHA'), ('head', 'HEAD'), ('base', 'BASE')]}
    return execute(args.repo, args.output, context)


if __name__ == '__main__':
    raise SystemExit(main())
