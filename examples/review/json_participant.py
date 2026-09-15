"""Independent deterministic peer for the JSON command profile. No model calls."""

import json
import sys

request = json.load(sys.stdin)
turn = request['turn']
index = len(turn['history'])
if index < len(turn['tools']):
    name = turn['tools'][index]
    action = {'kind': 'tool', 'name': name,
              'arguments': {'query': turn['query'], 'k': 3} if name == 'retrieve' else {}}
else:
    outcomes = ', '.join(f"{item['action']['name']}={item['result']['status']}" for item in turn['history'])
    action = {'kind': 'final', 'text': f'Independent command fixture: {outcomes}. No model judgment.'}
print(json.dumps({'schema_version': 1, 'request_digest': request['request_digest'], 'action': action}))
