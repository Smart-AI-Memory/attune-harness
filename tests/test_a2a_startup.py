"""The independent numeric-loopback peer must not need a hostname resolver."""
import json
from pathlib import Path
import select
import subprocess
import sys
from urllib.request import urlopen


PEER = Path(__file__).resolve().parents[1] / 'examples/a2a/peer.py'


def test_peer_is_ready_and_serves_its_card_without_hostname_resolution(tmp_path):
    boot = (
        'import runpy, socket, sys\n'
        'def unavailable(*args, **kwargs):\n'
        '    raise AssertionError("loopback fixture invoked hostname resolution")\n'
        'socket.getfqdn = unavailable\n'
        'sys.argv = [sys.argv[1], "--log", sys.argv[2]]\n'
        'runpy.run_path(sys.argv[0], run_name="__main__")\n'
    )
    process = subprocess.Popen([sys.executable, '-I', '-c', boot, str(PEER),
                                str(tmp_path / 'peer.json')],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert select.select([process.stdout], [], [], 5)[0], 'Peer did not start'
        line = process.stdout.readline()
        assert line, process.stderr.read()
        ready = json.loads(line)
        assert ready['endpoint'].startswith('http://127.0.0.1:')
        card_url = ready['endpoint'].removesuffix('/rpc') + '/.well-known/agent-card.json'
        with urlopen(card_url, timeout=5) as response:
            assert json.load(response) == ready['card']
    finally:
        process.terminate()
        process.communicate(timeout=5)
