"""Real SDK/stdio interop and the accepted retrieval scope. No model calls."""
import asyncio
import json
import sys
from pathlib import Path

import pytest

from attune_harness import mcp_server as module
from attune_harness.features import FeatureUnavailable
from attune_harness.review_store import PersistenceError, read_record
from attune_harness.extensions import mutate
from test_review import case, change_config
from test_extensions import bundle, installed, extended


@pytest.fixture
def mcp_case(extended):
    change_config(extended, lambda d: [p.update(tools=['evidence.search']) for p in d['participants'].values()])
    return extended


def make_scope(mcp_case):
    return module.RetrievalSession(mcp_case[0], mcp_case[1], 'alpha', mcp_case[2])


def test_scope_real_retrieval_and_bounded_budget(mcp_case):
    scope = make_scope(mcp_case)
    with scope.store.lease():
        scope.save()
        found = scope.invoke('harness.evidence.search', {'query': 'quartz policy', 'k': 3})
        absent = scope.invoke('harness.evidence.search', {'query': 'zzzznotfound', 'k': 3})
        assert found['status'] == 'retrieved' and found['sources']
        assert found['extension']['artifact_digest'] == scope.bindings['evidence']['artifact_digest']
        assert absent['status'] == 'no_results'
        with pytest.raises(PermissionError, match='budget'):
            scope.invoke('harness.evidence.search', {'query': 'quartz policy', 'k': 3})
        scope.finish()
    saved = read_record(mcp_case[2])
    assert saved['status'] == 'completed' and len(saved['events']) == 2
    assert all(e['state'] == 'completed' for e in saved['events'])


@pytest.mark.parametrize('tools', [['verify'], [], ['retrieve', 'verify']])
def test_unsupported_profile_grants_refused_before_store(case, tools):
    change_config(case, lambda d: d['participants']['alpha'].update(tools=tools))
    with pytest.raises(FeatureUnavailable, match='retrieval-only'):
        module.RetrievalSession(case[0], case[1], 'alpha', case[2])
    assert not case[2].exists()


@pytest.mark.parametrize('principal', ['missing', 'alpha'])
def test_unknown_or_zero_budget_principal_refused(case, principal):
    change_config(case, lambda d: d['participants']['alpha'].update(tools=['retrieve'], max_tool_calls=0))
    with pytest.raises(PermissionError):
        module.RetrievalSession(case[0], case[1], principal, case[2])
    assert not case[2].exists()


@pytest.mark.parametrize('name,args', [
    ('harness.verify', {}), ('harness.evidence.search', {'query': 'quartz', 'k': True}),
    ('harness.evidence.search', {'query': 'quartz', 'k': 3, 'corpus': '/tmp'}),
    ('harness.evidence.search', {'query': ' ', 'k': 3}),
])
def test_invalid_calls_never_dispatch(mcp_case, monkeypatch, name, args):
    scope = make_scope(mcp_case)
    monkeypatch.setattr(module, 'retrieve_sources', lambda *a, **k: pytest.fail('dispatched'))
    with pytest.raises((ValueError, PermissionError)):
        scope.invoke(name, args)
    assert not scope.record['events']


@pytest.mark.parametrize('action', ['disable', 'remove'])
def test_lifecycle_checked_per_call(mcp_case, installed, action):
    scope = make_scope(mcp_case)
    directory, state = installed
    mutate(directory, state['state_digest'], action)
    with pytest.raises(FeatureUnavailable):
        scope.invoke('harness.evidence.search', {'query': 'quartz', 'k': 3})
    assert not scope.record['events']


@pytest.mark.parametrize('file', ['guide.md', 'new.md'])
def test_changed_corpus_blocks_calls(mcp_case, file):
    scope = make_scope(mcp_case)
    (mcp_case[0].parent / 'project' / file).write_text('Changed source', encoding='utf-8')
    with pytest.raises(ValueError, match='changed'):
        scope.invoke('harness.evidence.search', {'query': 'quartz', 'k': 3})
    assert not scope.record['events']


def test_failed_feature_is_durable_and_consumes_budget(mcp_case, monkeypatch):
    scope = make_scope(mcp_case)
    def broken(*a, **k): raise RuntimeError('advertised but broken')
    monkeypatch.setattr(module, 'retrieve_sources', broken)
    with pytest.raises(RuntimeError, match='broken'):
        scope.invoke('harness.evidence.search', {'query': 'quartz', 'k': 3})
    scope.finish()
    saved = read_record(mcp_case[2])
    assert saved['events'][0]['state'] == 'failed' and 'result' not in saved['events'][0]


def test_failed_persistence_stops_further_calls_and_writes(mcp_case, monkeypatch):
    scope = make_scope(mcp_case)
    writes = []
    def fail(_):
        writes.append(1)
        raise PersistenceError('disk unavailable')
    monkeypatch.setattr(scope.store, 'save', fail)
    for _ in range(2):
        with pytest.raises(PersistenceError):
            scope.invoke('harness.evidence.search', {'query': 'quartz', 'k': 3})
    scope.finish()
    assert len(writes) == 1


def test_interrupt_keeps_pending_work_unresolved(mcp_case, monkeypatch):
    scope = make_scope(mcp_case)
    def stop(*a, **k): raise KeyboardInterrupt()
    monkeypatch.setattr(module, 'retrieve_sources', stop)
    with pytest.raises(KeyboardInterrupt):
        scope.invoke('harness.evidence.search', {'query': 'quartz', 'k': 3})
    scope.finish(interrupted=True)
    saved = read_record(mcp_case[2])
    assert saved['status'] == 'unresolved' and saved['events'][0]['state'] == 'pending'


def sdk_parameters(mcp_case, *, slow=False):
    from mcp.client.stdio import StdioServerParameters
    source = str(Path(module.__file__).resolve().parent.parent)
    boot = f'import sys;sys.path.insert(0,{source!r});'
    if slow:
        boot += ('import time;import attune_harness.mcp_server as m;real=m.retrieve_sources;'
                 'm.retrieve_sources=lambda *a,**k:(time.sleep(.25),real(*a,**k))[1];')
    boot += 'from attune_harness.cli import main;raise SystemExit(main(sys.argv[1:]))'
    return StdioServerParameters(command=sys.executable,args=['-c',boot,'mcp-serve','--request',str(mcp_case[0]),
           '--config',str(mcp_case[1]),'--participant','alpha','--session-dir',str(mcp_case[2])])


def test_sdk_stdio_discovery_schema_and_real_calls(mcp_case):
    pytest.importorskip('mcp')
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    async def journey():
        async with stdio_client(sdk_parameters(mcp_case)) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=5) as client:
                init = await client.initialize()
                assert init.protocol_version == module.MCP_LEGACY_PROTOCOL and init.capabilities.tools
                assert not init.capabilities.tools.list_changed
                listing = await client.list_tools()
                assert [t.name for t in listing.tools] == ['harness.evidence.search']
                assert listing.tools[0].output_schema and listing.tools[0].annotations.read_only_hint
                for name, args in [('harness.missing', {}), ('harness.evidence.search', {'query':'quartz','k':True}),
                                   ('harness.evidence.search', {'query':'quartz','k':3,'corpus':'/tmp'})]:
                    assert (await client.call_tool(name,args)).is_error
                found = await client.call_tool('harness.evidence.search', {'query':'quartz policy','k':3})
                assert not found.is_error and found.structured_content['status'] == 'retrieved'
                assert json.loads(found.content[0].text) == found.structured_content
                assert (await client.call_tool('harness.evidence.search', {'query':'zzzzz','k':3})).structured_content['status'] == 'no_results'
                assert (await client.call_tool('harness.evidence.search', {'query':'quartz','k':3})).is_error
    asyncio.run(journey())
    saved = read_record(mcp_case[2])
    assert len(saved['events']) == 2 and all(e['state'] == 'completed' for e in saved['events'])


def test_sdk_cancellation_retains_started_call_receipt(mcp_case):
    pytest.importorskip('mcp')
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    from mcp.shared.exceptions import MCPError
    async def journey():
        async with stdio_client(sdk_parameters(mcp_case,slow=True)) as (read,write):
            async with ClientSession(read,write) as client:
                await client.initialize()
                with pytest.raises(MCPError, match='[Tt]imed out|[Tt]imeout'):
                    await client.call_tool('harness.evidence.search', {'query':'quartz policy','k':3},
                                           read_timeout_seconds=.05)
                # Client timeout sends cancellation. Wait on observable record state,
                # not an assumption that a canceled response means the call did not run.
                for _ in range(100):
                    await asyncio.sleep(.01)
                    saved = read_record(mcp_case[2])
                    if saved['events'] and saved['events'][0]['state'] == 'completed':
                        break
                assert saved['events'][0]['result']['status'] == 'retrieved'
    asyncio.run(journey())


def test_cli_missing_mcp_keeps_stdout_clean(mcp_case, monkeypatch, capsys):
    from attune_harness.cli import main
    def missing(*args): raise FeatureUnavailable('mcp is missing')
    monkeypatch.setattr(module,'require_feature',missing)
    assert main(['mcp-serve','--request',str(mcp_case[0]),'--config',str(mcp_case[1]),
                 '--participant','alpha','--session-dir',str(mcp_case[2])]) == 2
    output = capsys.readouterr()
    assert output.out == '' and 'missing' in output.err


def test_cli_inspection_does_not_reexecute_running_record(mcp_case, capsys):
    from attune_harness.cli import main
    scope = make_scope(mcp_case)
    scope.save()
    assert main(['mcp-inspect',str(mcp_case[2])]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result['status'] == 'unresolved' and result['persisted_status'] == 'running'
    assert read_record(mcp_case[2])['status'] == 'running'
    scope.finish()
    assert main(['mcp-inspect',str(mcp_case[2])]) == 0
    assert json.loads(capsys.readouterr().out)['status'] == 'completed'
    assert main(['mcp-inspect',str(mcp_case[2]/'missing')]) == 2
    assert json.loads(capsys.readouterr().out)['status'] == 'failed'


def test_current_protocol_discovery_and_call(mcp_case):
    pytest.importorskip('mcp')
    from mcp import Client
    async def journey():
        async with Client(sdk_parameters(mcp_case),mode=module.MCP_PROTOCOL,read_timeout_seconds=5) as client:
            assert client.protocol_version == module.MCP_PROTOCOL
            tools = await client.list_tools()
            assert tools.tools[0].name == 'harness.evidence.search'
            result = await client.call_tool('harness.evidence.search',{'query':'quartz policy','k':3})
            assert not result.is_error and result.structured_content['status'] == 'retrieved'
    asyncio.run(journey())


def test_wrong_result_shape_is_failed_receipt(mcp_case,monkeypatch):
    import jsonschema
    scope=make_scope(mcp_case)
    monkeypatch.setattr(module,'retrieve_sources',lambda *a,**k:{'status':'verified'})
    with pytest.raises(jsonschema.ValidationError):
        scope.invoke('harness.evidence.search',{'query':'quartz policy','k':3})
    assert read_record(mcp_case[2])['events'][0]['state']=='failed'
