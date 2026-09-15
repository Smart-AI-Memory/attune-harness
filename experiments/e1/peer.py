"""Independent local effect fixture; never invokes providers or Harness."""
import json
import os
import sys
from pathlib import Path

cell, fault = Path(sys.argv[1]), sys.argv[2]
request = json.load(sys.stdin)
with (cell / 'effects.jsonl').open('a', encoding='utf-8') as stream:
    stream.write(json.dumps(request) + '\n')
    stream.flush()
    os.fsync(stream.fileno())
reply = {'schema_version': 1, 'request_digest': request['request_digest'],
         'action': {'kind': 'final', 'text': 'Local fixture response; no semantic model judgment.'}}
(cell / (request['request_digest'] + '.reply.json')).write_text(json.dumps(reply), encoding='utf-8')
if fault == 'lost-ack':
    raise SystemExit(23)
print(json.dumps(reply))
