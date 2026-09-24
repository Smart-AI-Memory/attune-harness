"""Real workspace authority through the MCP adapter, no model calls."""

# qualify: platform
import asyncio
import json
import sys
from pathlib import Path
import pytest
from attune_harness import workspace_mcp as m
from attune_harness.mcp_server import inspect_session
from attune_harness.review_store import PersistenceError


def response(render, **changes):
    value = {'__elicitation_response__': True, 'title': 'Spec creation preview', 'view': render['view'],
             'action': 'create_spec', 'confirmed': True,
             **{k: render[k] for k in ('workspace_id', 'revision', 'action_nonce', 'contract_hash')}}
    return {**value, **changes}


def test_actions_replay_events_and_record(tmp_path):
    async def journey():
        scope = m.WorkspaceSession(tmp_path, tmp_path/'session')
        with scope.store.lease():
            scope.save()
            opened = await scope.invoke('command_workspace_open', {'adapter_id':'spec','intake':{
                'outcome':'A project draft', 'done_when':'Draft is reviewed', 'slug':'demo'}})
            assert opened['success'] and opened['html'] and opened['markdown']
            original = response(opened)
            for invalid in [response(opened, action_nonce='0'*20), response(opened, revision=999),
                            response(opened, contract_hash='0'*64)]:
                assert not (await scope.invoke('command_workspace_collect_action',{'response':invalid}))['success']
            accepted = await scope.invoke('command_workspace_collect_action', {'response':original})
            assert accepted['success']
            assert not (await scope.invoke('command_workspace_collect_action',{'response':original}))['success']
            scope.finish()
        return scope, opened
    scope, opened = asyncio.run(journey())
    record = inspect_session(scope.store.directory)
    assert record['status']=='completed' and record['model_calls']==0 and record['provider'] is None
    assert record['calls_failed']==4
    assert opened['action_nonce'] not in scope.store.path.read_text()
    events=(scope.store.directory/'workspace-events.jsonl').read_text()
    assert opened['action_nonce'] not in events and 'render' in events


def test_persistence_failure_stops_dispatch(tmp_path, monkeypatch):
    async def journey():
        scope=m.WorkspaceSession(tmp_path,tmp_path/'session')
        def fail(record): raise PersistenceError('disk full')
        monkeypatch.setattr(scope.store,'save',fail)
        for _ in range(2):
            with pytest.raises(PersistenceError):
                await scope.invoke('command_workspace_open',{'adapter_id':'spec','intake':{}})
        assert not scope.host._records
    asyncio.run(journey())


@pytest.mark.parametrize('name,args',[
    ('missing',{}), ('command_workspace_open',{'adapter_id':'spec','intake':{},'project':'/'}),
    ('command_workspace_open',{'adapter_id':'spec','intake':{'outcome':'x'*m.INPUT_LIMIT}}),
    ('command_workspace_collect_action',{'response':{}}),
])
def test_invalid_input_never_starts(tmp_path,name,args):
    scope=m.WorkspaceSession(tmp_path,tmp_path/'session')
    with pytest.raises(Exception): asyncio.run(scope.invoke(name,args))
    assert scope.record['calls_started']==0


def test_sdk_workspace_profile(tmp_path):
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client, StdioServerParameters
    source=str(Path(m.__file__).resolve().parent.parent)
    boot=f'import sys;sys.path.insert(0,{source!r});from attune_harness.cli import main;raise SystemExit(main(sys.argv[1:]))'
    parameters=StdioServerParameters(command=sys.executable,args=['-c',boot,'mcp-serve','--workspace',
        '--project',str(tmp_path),'--state-dir',str(tmp_path/'stdio')])
    async def journey():
        async with stdio_client(parameters) as (read,write):
            async with ClientSession(read,write,read_timeout_seconds=10) as client:
                await client.initialize()
                listing=await client.list_tools()
                assert [t.name for t in listing.tools]==list(m.tool_schemas())
                resources=await client.list_resources()
                assert len(resources.resources)==1
                app=await client.read_resource(resources.resources[0].uri)
                assert '<!doctype html>' in app.contents[0].text
                assert listing.tools[0].meta['ui']['resourceUri']==resources.resources[0].uri
                opened=await client.call_tool('command_workspace_open',{'adapter_id':'spec','intake':{
                    'outcome':'Demo','done_when':'Receipt exists','slug':'demo'}})
                assert not opened.is_error
                data=opened.structured_content
                assert json.loads(opened.content[0].text)==data
                accepted=await client.call_tool('command_workspace_collect_action',{'response':response(data)})
                assert not accepted.is_error
                replay=await client.call_tool('command_workspace_collect_action',{'response':response(data)})
                assert replay.is_error
    asyncio.run(journey())
    assert inspect_session(tmp_path/'stdio')['model_calls']==0


def test_protocol_schemas_are_pinned():
    fixture=Path(__file__).parent/'fixtures/compatibility/workspace-mcp.json'
    for schemas in json.loads(fixture.read_text()).values():
        assert schemas==m.tool_schemas()


@pytest.mark.parametrize('args', [
    ['--workspace','--request','missing.json'],
    ['--project','.'], ['--workspace','--allow-provider'], []])
def test_mixed_or_incomplete_profiles_refused(args,capsys):
    from attune_harness.cli import main
    assert main(['mcp-serve',*args])==2
    captured=capsys.readouterr()
    assert not captured.out and captured.err


from test_connected_journey import journey  # noqa: F401


def test_real_evidence_publish_accept_and_terminal_refusal(journey, capsys, tmp_path):
    from test_connected_journey import complete, run_linked
    from attune_harness.spec_state import SpecState, save_state, load_state
    from attune_harness.spec_handoff import bind_test_evidence
    complete(journey, capsys)
    tested = run_linked(journey)
    root = tmp_path / 'spec-project'
    plans = root / '.claude/plans'
    plans.mkdir(parents=True)
    (root / '.git').mkdir()
    plan = plans / 'demo.md'
    plan.write_text('<task id="1" name="test"><objective>Test the change</objective></task>\n')
    save_state(SpecState(plan_path=str(plan), current='1', completed=[]))
    binding = bind_test_evidence(Path(tested['record_path']).parent)
    assert binding['outcome'] == 'passed'
    async def run():
        scope = m.WorkspaceSession(root, tmp_path / 'receipt-session')
        with scope.store.lease():
            scope.save()
            opened = await scope.invoke('command_workspace_open', {'adapter_id':'spec',
                'intake':{'route':'resume', 'plan_path':'.claude/plans/demo.md'}})
            assert opened['success']
            event = {'kind':'task_result', 'task_id':'1', 'test_evidence':binding,
                     'severity':'low', 'score':100, 'probes':[binding['record_path']],
                     'detail':'Real local test receipt; synthetic collector submission'}
            gate = await scope.invoke('command_workspace_publish', {'workspace_id':opened['workspace_id'], 'event':event})
            assert gate['success'], gate
            record = scope.host.get(gate['workspace_id'])
            answer = {**response(gate, action='approve_task', confirmed=False), 'title':record.view.title}
            done = await scope.invoke('command_workspace_collect_action', {'response':answer})
            assert done['success'] and done['terminal'], done
            assert not (await scope.invoke('command_workspace_publish', {'workspace_id':done['workspace_id'], 'event':event}))['success']
            scope.finish()
        save_state(SpecState(**{**done['result']['save_state'], 'plan_path':str(plan)}))
        assert load_state(str(plan)).completed == ['1']
        assert done['result']['save_state']['task_receipts'][0]['test_evidence'] == binding
    asyncio.run(run())
    from attune_harness.cli import main
    args=['spec','present','result','--plan',str(plan),'--task','1','--test-run',str(Path(tested['record_path']).parent)]
    assert main(args)==0
    assert 'PASSED' in capsys.readouterr().out
    state=load_state(str(plan))
    state.task_receipts[0]['test_evidence']['task_id']='different-source-run'
    save_state(state)
    assert main(args)==2
    assert 'differs' in capsys.readouterr().err
