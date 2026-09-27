"""Host billing state under interruption; deterministic subprocesses, no paid calls."""
# qualify: platform
import json
import subprocess
import sys
from pathlib import Path

import pytest

from attune_harness.process import invoke
from attune_harness.review_store import read_record
from attune_harness.voyage_provider import (
    PaidStageInterrupted, PaidStageUnresolved, StageJournal,
)

CFG = {'max_request_bytes': 8192, 'max_provider_calls': 1}
REQUESTS = {'embed': {'texts': ['one'], 'input_type': 'query'},
            'rerank': {'query': 'one', 'documents': ['one'], 'k': 1}}


class StoppedChild:
    def __init__(self, root):
        self.root = root
        self.calls = 0
        self.checkpoint = None

    def embed(self, *args):
        self.calls += 1
        key = read_record(self.root)['stages'][0]
        self.checkpoint = (self.root / key / 'record.json').read_bytes()
        assert read_record(self.root / key)['status'] == 'dispatching'
        outcome = invoke((sys.executable, '-I', '-c', 'import time; time.sleep(60)'),
                         '', cwd=self.root, timeout=0.5)
        assert outcome.failure == 'timeout_effects_unknown'
        raise PaidStageInterrupted('private child diagnostic')

    rerank = embed


@pytest.mark.parametrize('kind', ['embed', 'rerank'])
def test_child_timeout_preserves_dispatch_and_refuses_fresh_replay(tmp_path, kind):
    root = tmp_path / 'stages'
    provider = StoppedChild(root)
    journal = StageJournal(root, CFG, allow_provider=True, provider=provider)
    with pytest.raises(PaidStageUnresolved, match='subprocess interrupted') as caught:
        journal.perform(kind, REQUESTS[kind], lambda value: value)
    assert 'private' not in str(caught.value)
    key = read_record(root)['stages'][0]
    assert (root / key / 'record.json').read_bytes() == provider.checkpoint
    for allowed in (False, True):
        resumed = StageJournal(root, CFG, allow_provider=allowed, provider=provider)
        with pytest.raises(PaidStageUnresolved, match='No automatic retry'):
            resumed.perform(kind, REQUESTS[kind], lambda value: value)
    assert provider.calls == 1
    # The interrupted stage still consumes its budget; a new request cannot evade it.
    with pytest.raises(PermissionError, match='budget'):
        journal.perform('embed', {'texts': ['two'], 'input_type': 'query'}, lambda v: v)
    assert provider.calls == 1


def test_abrupt_host_exit_leaves_same_dispatching_state(tmp_path):
    import attune_harness
    root = tmp_path / 'stages'
    # Select the exact checked source/installed wheel, not an ambient installation.
    package_parent = str(Path(attune_harness.__file__).resolve().parent.parent)
    script = '''import os, sys
sys.path.insert(0, sys.argv[1])
from pathlib import Path
from attune_harness.voyage_provider import StageJournal
class Stopped:
    def embed(self, *args): os._exit(17)
StageJournal(Path(sys.argv[2]), {'max_request_bytes':8192,'max_provider_calls':1},
             allow_provider=True, provider=Stopped()).perform(
    'embed', {'texts':['one'],'input_type':'query'}, lambda value:value)
'''
    result = subprocess.run([sys.executable, '-I', '-c', script, package_parent, str(root)],
                            capture_output=True, timeout=15)
    assert result.returncode == 17, result.stderr.decode(errors='replace')
    key = read_record(root)['stages'][0]
    assert read_record(root / key)['status'] == 'dispatching'
    provider = StoppedChild(root)
    with pytest.raises(PaidStageUnresolved, match='No automatic retry'):
        StageJournal(root, CFG, allow_provider=True, provider=provider).perform(
            'embed', REQUESTS['embed'], lambda value: value)
    assert provider.calls == 0


@pytest.mark.parametrize('kind', ['embed', 'rerank'])
def test_ordinary_provider_error_still_records_unresolved(tmp_path, kind):
    class Broken:
        def embed(self, *args): raise TimeoutError('private SDK diagnostic')
        rerank = embed
    root = tmp_path / 'stages'
    with pytest.raises(PaidStageUnresolved):
        StageJournal(root, CFG, allow_provider=True, provider=Broken()).perform(
            kind, REQUESTS[kind], lambda value: value)
    key = read_record(root)['stages'][0]
    record = read_record(root / key)
    assert record['status'] == 'unresolved'
    assert record['error']['type'] == 'TimeoutError'
    assert 'private' not in json.dumps(record)
