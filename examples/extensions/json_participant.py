"""Independent command peer consuming contributed contracts, no Harness imports."""
import json
import sys

request = json.load(sys.stdin)
turn = request['turn']
index = len(turn['history'])
if index < len(turn['tools']):
    name = turn['tools'][index]
    binding = turn.get('tool_contracts', {}).get(name, {}).get('binding', name)
    if binding not in ('retrieve', 'verify'):
        raise ValueError('Unsupported tool binding')
    action = {'kind': 'tool', 'name': name, 'arguments': (
        {'query': turn['query'], 'k': 3} if binding == 'retrieve' else {})}
else:
    sources = [source['path'] for entry in turn['history'] for source in entry['result'].get('sources', [])]
    action = {'kind': 'final', 'text': 'Independent local fixture used sources: ' + ', '.join(sources)}
print(json.dumps({'schema_version': 1, 'request_digest': request['request_digest'], 'action': action}))
