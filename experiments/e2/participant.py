"""Independent command peer: request the experiment's target even when denied."""
import json
import sys

request = json.load(sys.stdin)
turn = request['turn']
action = ({'kind': 'tool', 'name': 'evidence.search', 'arguments': {'query': turn['query'], 'k': 3}}
          if not turn['history'] else {'kind': 'final', 'text': 'Local E2 fixture finished its tool request.'})
print(json.dumps({'schema_version': 1, 'request_digest': request['request_digest'], 'action': action}))
