"""The starter command participant (starter-files R3). Example code, not a profile or a default.

Applies one declared replacement, `PATH OLD NEW` from its arguments, as the
worker of a build or a repair, and approves as the reviewer without judging.
No model call. participants.json carries this file inline (`python -c`), so it
needs `python` on PATH; tests/test_cold_start_journey.py checks the two match.
"""
import hashlib, json, sys
path, old, new = sys.argv[1:4]
request = json.load(sys.stdin)
turn = request['turn']
repair = turn.get('repair')


def swap(text):
    if text.count(old) != 1:
        raise SystemExit(f'starter worker: expected exactly one {old!r} in {path}')
    return text.replace(old, new)


if repair is not None and turn['role'] == 'worker':
    value = {'schema_version': 1, 'replacements': [
        {'path': path, 'before_sha256': repair['before_hashes'][path], 'text': swap(repair['before_files'][path])}]}
elif repair is not None:
    value = {'schema_version': 1, 'artifact_digest': repair['artifact_digest'],
             'probe_digest': repair['probe_digest'], 'verdict': 'approve', 'findings': []}
elif turn['role'] == 'worker':
    step, source = turn['step'], turn['source_evidence']
    value = {'schema_version': 1, 'task_id': step['id'], 'dependencies': step['dependencies'], 'files': [
        {'path': path, 'before_sha256': hashlib.sha256(source[path].encode('utf-8')).hexdigest(),
         'text': swap(source[path])}]}
else:
    value = {'kind': 'critique', 'findings': [],
             'notes': ['The starter reviewer approves without judging; it is an example, not a review.']}
print(json.dumps({'schema_version': 1, 'request_digest': request['request_digest'],
                  'action': {'kind': 'final', 'text': json.dumps(value)}}))
