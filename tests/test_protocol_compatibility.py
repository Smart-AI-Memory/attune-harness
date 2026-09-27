"""Pin the actual tool listings by protocol, and the bounded A2A local profile.

Fixtures change deliberately with the documented protocol version, not merely
because an SDK upgrade produces a different schema. No paid providers are used.
"""

# qualify: platform
import asyncio
import copy
import json
import os
from pathlib import Path

import pytest

from attune_harness import a2a, mcp_server
from attune_harness.review_contract import digest
from test_review import case, change_config  # noqa: F401
from test_mcp import sdk_parameters
from test_a2a import peer_factory  # noqa: F401

FIXTURES = Path(__file__).resolve().parent / 'fixtures/compatibility'


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding='utf-8'))


async def capture_mcp(case, protocol):
    from mcp import Client, ClientSession
    from mcp.client.stdio import stdio_client

    def tools(listing):
        return [dict(name=tool.name,
                     input_schema=tool.input_schema,
                     output_schema=tool.output_schema,
                     input_digest=digest(tool.input_schema),
                     output_digest=digest(tool.output_schema),
                     annotations=tool.annotations.model_dump(mode='json', by_alias=True, exclude_none=True))
                for tool in listing.tools]

    if protocol == '2025-11-25':
        async with stdio_client(sdk_parameters(case)) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=5) as client:
                initialized = await client.initialize()
                assert initialized.protocol_version == protocol
                listing = await client.list_tools()
    else:
        async with Client(sdk_parameters(case), mode=protocol, read_timeout_seconds=5) as client:
            assert client.protocol_version == protocol
            listing = await client.list_tools()
    return {'protocol': protocol, 'tools': tools(listing)}


@pytest.mark.parametrize('protocol', ['2025-11-25', '2026-07-28'])
def test_actual_mcp_listing_matches_version_fixture(case, protocol):
    pytest.importorskip('mcp')
    change_config(case, lambda data: data['participants']['alpha'].update(tools=['retrieve']))
    actual = asyncio.run(capture_mcp(case, protocol))
    # Keep the observed listing on failure without replacing the accepted fixture.
    (case[0].parent / 'observed-protocol.json').write_text(json.dumps(actual, indent=2))
    assert actual == fixture(f'mcp-{protocol}.json')
    inspected = mcp_server.inspect_session(case[2])
    assert inspected['status'] == 'completed'
    assert inspected['profile']['protocol_profiles'] == ['2025-11-25', '2026-07-28']
    assert inspected['tools'] == {'harness.retrieve': 'retrieve'}
    assert inspected['events'] == []  # Discovery has no retrieval or provider effects.


def test_a2a_operations_and_task_states_match_local_profile():
    pinned = fixture('a2a-1.0.json')
    assert a2a.PROTOCOL == pinned['protocol']
    assert sorted(a2a.OPERATIONS) == pinned['operations']
    assert sorted(a2a.STATES) == pinned['states']
    assert sorted(a2a.TERMINAL) == pinned['terminal_states']


@pytest.mark.skipif(os.name != 'posix', reason='Existing independent peer fixture uses POSIX pipe readiness')
def test_a2a_actual_agent_card_matches_local_profile(peer_factory):
    peer, _, _, _ = peer_factory()
    card = copy.deepcopy(peer.check_card())
    # The ephemeral loopback port is the only machine-dependent field.
    assert card['supportedInterfaces'][0]['url'] == peer.endpoint
    card['supportedInterfaces'][0]['url'] = 'http://127.0.0.1:PORT/rpc'
    assert card == fixture('a2a-1.0.json')['agent_card']
