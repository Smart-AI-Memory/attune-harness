"""The independent numeric-loopback peer must not need a hostname resolver."""
import json
from pathlib import Path
from urllib.request import urlopen

from test_a2a import _running_peer


PEER = Path(__file__).resolve().parents[1] / 'examples/a2a/peer.py'


def test_peer_is_ready_and_serves_its_card_without_hostname_resolution(tmp_path):
    with _running_peer(tmp_path, [str(PEER), '--log', str(tmp_path / 'peer.json')],
                       deny_resolver=True, communicate=True) as (process, error, line):
        assert line, f"Peer did not start; stderr retained at {tmp_path / 'stderr.txt'}"
        ready = json.loads(line)
        assert ready['endpoint'].startswith('http://127.0.0.1:')
        card_url = ready['endpoint'].removesuffix('/rpc') + '/.well-known/agent-card.json'
        with urlopen(card_url, timeout=5) as response:
            assert json.load(response) == ready['card']
