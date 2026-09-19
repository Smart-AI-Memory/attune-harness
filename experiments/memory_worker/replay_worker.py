"""Terminal demonstration using exact saved native replies; never calls a model."""
from copy import deepcopy
import argparse
import json
from pathlib import Path
import tempfile
from worker import WorkerStore, run

HERE = Path(__file__).resolve().parent


def fixtures():
    return json.loads((HERE / 'replay.json').read_text(encoding='utf-8'))


class Replay:
    def __init__(self, calls):
        self.calls = deepcopy(calls)
        self.used = 0

    def __call__(self, role, model, prompt, schema):
        if self.used >= len(self.calls):
            raise ValueError('Unexpected extra participant call')
        expected = self.calls[self.used]
        if (role, model, prompt, schema) != tuple(expected[k] for k in ('role','model','prompt','schema')):
            raise ValueError('Replay prompt, schema, role or model differs from recorded call')
        self.used += 1
        return deepcopy(expected['reply'])


def demonstrate():
    packet = fixtures()
    rows = []
    with tempfile.TemporaryDirectory(prefix='bounded-memory-worker-') as temporary:
        for case in packet['cases']:
            directory = Path(temporary) / case['id']
            store = WorkerStore.create(directory, case['envelope'], packet['policy'])
            before = deepcopy(store.read()['envelope'])
            replay = Replay(case['calls'])
            result = run(store, case['id'], replay)
            assert result['status'] == case['expected_action']
            assert replay.used == len(case['calls'])
            assert store.read()['envelope'] == before
            reopened = WorkerStore(directory).inspect(case['id'])
            assert reopened == result
            rows.append(dict(case_id=case['id'], status=result['status'],
                sampled=result['sampled'], replayed_calls=replay.used,
                roles=[a['role'] for a in result['attempts']], memory_record_unchanged=True,
                result=reopened))
    return dict(mode='saved-native-reply replay; no new model observations',
        native_calls=0, replayed_calls=sum(r['replayed_calls'] for r in rows),
        policy=packet['policy'], sampling_note=packet['sampling_note'], rows=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true', help='Include complete persisted job receipts')
    args = parser.parse_args()
    result = demonstrate()
    if not args.full:
        result['rows'] = [{k:v for k,v in row.items() if k != 'result'} for row in result['rows']]
    print(json.dumps(result, indent=2))
