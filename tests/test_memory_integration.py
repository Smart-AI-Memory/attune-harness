"""Both host entry points, current context, transport and telemetry boundaries."""

import asyncio
from copy import deepcopy
from datetime import timedelta
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from attune_harness.memory_context import MemoryHost
from attune_harness.memory_worker import WorkerStore, validated_proposal
from test_memory_worker import packet, proposal  # noqa: F401 -- shared input fixture


@pytest.fixture
def memory_case(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('ATTUNE_HOME', str(tmp_path / 'telemetry'))
    monkeypatch.setenv('ATTUNE_VERSION_CHECK', '0')
    monkeypatch.setenv('ATTUNE_USAGE_PING', '0')
    root = tmp_path / 'memory'
    root.mkdir()
    document = root / 'decision.md'
    document.write_text('---\nname: decision\ndescription: Aurora CI exception\nmetadata:\n  type: reference\n---\n# Aurora\n' + 'Use port 9000 except in CI. ' * 80 + 'FINAL_DETAIL')
    (root / 'summaries_by_path.json').write_text(json.dumps({'decision.md': 'Aurora CI exception'}))
    jobs = tmp_path / 'jobs'
    jobs.mkdir()
    config = dict(schema_version=1, actor='patrick', owners=['patrick'], scopes=['project'],
                  classifications=['internal'], profiles=['luna', 'astra'],
                  roots=[dict(id='project', path=str(root.resolve()), tier='curated',
                              scope='project', owner='patrick', classification='internal')])
    cfg = tmp_path / 'config.json'
    cfg.write_text(json.dumps(config))
    guard = tmp_path / 'guard'
    guard.mkdir()
    (guard / 'sitecustomize.py').write_text(
        'import socket,os\nfrom pathlib import Path\n'
        'if os.environ.get("COVERAGE_PROCESS_START"):\n'
        '    import coverage\n    coverage.process_startup()\n'
        'def block(*args, **kwargs):\n'
        '    Path(os.environ["NETWORK_ATTEMPTS"]).write_text("attempted")\n'
        '    raise AssertionError("No network in memory qualification")\n'
        'socket.socket.connect = block\n')
    import structlog
    logging_config = structlog.get_config()
    yield SimpleNamespace(config=config, config_path=cfg, jobs=jobs, document=document, directory=tmp_path, guard=guard)
    structlog.configure(**logging_config)
    assert not (tmp_path / 'network-attempts').exists()


def environment(case):
    return {**os.environ, 'ATTUNE_HOME': str(case.directory / 'telemetry'),
            'ATTUNE_VERSION_CHECK': '0', 'ATTUNE_USAGE_PING': '1',
            'PYTHONDONTWRITEBYTECODE': '1', 'NETWORK_ATTEMPTS': str(case.directory / 'network-attempts'),
            'PYTHONPATH': str(case.guard) + os.pathsep + os.environ['PYTHONPATH']}


def invoke_cli(case, host, *arguments):
    prefix = ['-m', 'attune_harness', 'memory'] if host == 'harness' else ['-m', 'attune.cli_minimal', 'memory', 'worker']
    result = subprocess.run([sys.executable, '-B', *prefix, '--config', str(case.config_path),
                             '--jobs', str(case.jobs), *arguments], cwd=case.directory,
                            env=environment(case), capture_output=True, text=True, timeout=30)
    return result, json.loads(result.stdout)


def test_current_context_replaces_corrections_deletions_and_resolves_full_source(memory_case):
    case = memory_case
    host = MemoryHost(case.config, case.jobs)
    original = case.document.read_text()
    first = host.invoke('recall', dict(query='Aurora', k=3, max_chars=40))
    assert first['status'] == 'available'
    assert len(first['items'][0]['excerpt']) == 40 and first['items'][0]['truncated']
    handle = first['items'][0]['handle']
    assert host.invoke('resolve', dict(handle=handle))['text'] == original
    case.document.write_text(original.replace('9000', '9001'))
    with pytest.raises(ValueError, match='refresh'):
        host.invoke('resolve', dict(handle=handle))
    second = host.invoke('refresh', dict(context=first))
    assert second['invalidated_ids'] == [handle['id']]
    latest = second['context']['items'][0]['handle']
    assert '9001' in host.invoke('resolve', dict(handle=latest))['text']
    case.document.unlink()
    third = host.invoke('refresh', dict(context=second['context']))
    assert third['invalidated_ids'] == [latest['id']] and third['context']['items'] == []


@pytest.mark.parametrize('host_name', ['harness', 'ai'])
@pytest.mark.parametrize('remaining_root', [False, True])
def test_cli_refresh_propagates_degraded_memory(memory_case, host_name, remaining_root):
    case = memory_case
    if remaining_root:
        second = case.directory / 'second'
        second.mkdir()
        (second / 'decision.md').write_text(case.document.read_text())
        (second / 'summaries_by_path.json').write_text('{"decision.md":"Aurora CI exception"}')
        case.config['roots'].append({**case.config['roots'][0], 'id': 'second', 'path': str(second)})
        case.config_path.write_text(json.dumps(case.config))
    result, context = invoke_cli(case, host_name, 'recall', 'Aurora')
    assert result.returncode == 0
    saved = case.directory / 'context.json'
    saved.write_text(json.dumps(context))
    case.document.parent.rename(case.directory / 'temporarily-unavailable')
    result, refreshed = invoke_cli(case, host_name, 'refresh', str(saved))
    expected = 'partial' if remaining_root else 'unavailable'
    assert refreshed['context']['status'] == expected
    assert result.returncode == 2, refreshed
    assert refreshed['status'] == expected
    assert refreshed['invalidated_ids'] == ['project:decision.md']
    assert bool(refreshed['context']['items']) is remaining_root


def test_empty_memory_is_distinct_from_unavailable(memory_case):
    case = memory_case
    case.document.unlink()
    for host_name in ('harness', 'ai'):
        result, context = invoke_cli(case, host_name, 'recall', 'Aurora')
        assert result.returncode == 0 and context['status'] == 'empty'
        assert context['items'] == [] and context['problems'] == []


def test_plugin_lifecycle_keeps_existing_tools_and_refuses_closed_calls(memory_case):
    from attune_harness.memory_bridge import MemoryWorkerPlugin, SCHEMAS
    server = SimpleNamespace(tools={'existing_tool': {'description': 'existing'}}, _plugin_handlers={})
    plugin = MemoryWorkerPlugin(memory_case.config, memory_case.jobs)
    with pytest.raises(ValueError, match='explicit activation'):
        plugin.register_mcp_tools(server)
    with plugin.activate():
        plugin.register_mcp_tools(server)
        names = set(server.tools)
        assert names == {'existing_tool'} | {'harness_memory_' + name for name in SCHEMAS}
        with pytest.raises(ValueError, match='already registered'):
            plugin.register_mcp_tools(server)
        assert set(server.tools) == names
        handler = server._plugin_handlers['harness_memory_capabilities']
        assert asyncio.run(handler(server, {}))['memory']['native_worker'] == 'unavailable'
    with pytest.raises(ValueError, match='inactive'):
        asyncio.run(handler(server, {}))
    with pytest.raises(ValueError, match='closed'):
        with plugin.activate():
            pytest.fail('closed plugin reactivated')


def test_host_authority_rejects_exposure_and_job_path_changes(memory_case, packet):
    case = memory_case
    host = MemoryHost(case.config, case.jobs)
    envelope, policy = packet
    bad = deepcopy(envelope)
    bad['access']['actor'] = 'someone-else'
    with pytest.raises(ValueError, match='actor'):
        host.invoke('create', dict(run_id='bad', envelope=bad, policy=policy))
    with pytest.raises(ValueError, match='identity'):
        host.invoke('create', dict(run_id='../escape', envelope=envelope, policy=policy))
    assert list(case.jobs.iterdir()) == []
    with pytest.raises(ValueError, match='separate'):
        MemoryHost(case.config, case.document.parent)
    with pytest.raises(ValueError, match='Unsupported'):
        host.invoke('apply', {})


@pytest.mark.parametrize('dimension', ['actor', 'owners', 'scopes', 'classifications', 'profiles'])
def test_inspection_checks_historical_job_authority(memory_case, packet, dimension):
    case = memory_case
    envelope, policy = packet
    host = MemoryHost(case.config, case.jobs)
    host.invoke('create', dict(run_id='history', envelope=envelope, policy=policy))
    host.invoke('replay', dict(run_id='history', job_id='job',
                             replies=[dict(role='worker', profile='luna', value=proposal(envelope))]))
    # A legitimate host update keeps prior job snapshots for inspection. A new
    # owner must not receive an old owner's snapshot through the new envelope.
    updated, updated_policy = deepcopy(envelope), deepcopy(policy)
    config = deepcopy(case.config)
    if dimension == 'actor':
        updated['access']['actor'] = config['actor'] = 'next-actor'
    elif dimension == 'profiles':
        updated['access']['profiles'] = config['profiles'] = ['next-routine', 'next-stronger']
        updated_policy.update(routine_profile='next-routine', stronger_profile='next-stronger')
    else:
        field = dict(owners='owner', scopes='scope', classifications='classification')[dimension]
        replacement = 'public' if dimension == 'classifications' else 'next-' + field
        config[dimension] = [replacement]
        target = updated['input']['grants'] if dimension == 'scopes' else updated['access']
        target[dimension] = [replacement]
        for source in updated['input']['sources']:
            source[field] = replacement
        for root in config['roots']:
            root[field] = replacement
        if dimension == 'scopes':
            for fact in updated['input']['record']['facts']:
                fact['scope'] = replacement
    store = WorkerStore(case.jobs / 'history')
    store.replace_host_state(envelope=updated, policy=updated_policy)
    next_host = MemoryHost(config, case.jobs)
    with pytest.raises(ValueError, match='actor|authority'):
        next_host.invoke('inspect', dict(run_id='history', job_id='job'))
    assert store.read()['jobs']['job']['envelope'] == envelope


def test_replay_checks_claimed_job_after_host_state_change(memory_case, packet, monkeypatch):
    case = memory_case
    envelope, policy = packet
    host = MemoryHost(case.config, case.jobs)
    host.invoke('create', dict(run_id='transition', envelope=envelope, policy=policy))
    original_claim = WorkerStore.claim

    def change_before_claim(store, job_id, participant):
        updated = deepcopy(envelope)
        updated['access']['actor'] = 'next-actor'
        store.replace_host_state(envelope=updated)
        return original_claim(store, job_id, participant)

    monkeypatch.setattr(WorkerStore, 'claim', change_before_claim)
    with pytest.raises(ValueError, match='actor'):
        host.invoke('replay', dict(run_id='transition', job_id='job',
                                 replies=[dict(role='worker', profile='luna', value=proposal(envelope))]))
    job = WorkerStore(case.jobs / 'transition').inspect('job')
    assert job['status'] == 'unresolved'
    assert job['attempts'][0]['state'] == 'unresolved'
    assert 'reply' not in job['attempts'][0]


@pytest.mark.parametrize('host_name', ['harness', 'ai'])
def test_real_cli_calls_shared_worker_and_persists_job(memory_case, packet, host_name):
    case = memory_case
    envelope, policy = packet
    for name, value in [('envelope', envelope), ('policy', policy),
                        ('replies', [dict(role='worker', profile='luna', value=proposal(envelope))])]:
        (case.directory / (name + '.json')).write_text(json.dumps(value))
    result, context = invoke_cli(case, host_name, 'recall', 'Aurora')
    assert result.returncode == 0 and context['status'] == 'available', result.stderr
    result, created = invoke_cli(case, host_name, 'create', host_name,
                                 '--envelope', str(case.directory / 'envelope.json'),
                                 '--policy', str(case.directory / 'policy.json'))
    assert result.returncode == 0 and created['status'] == 'created', result.stderr
    result, replayed = invoke_cli(case, host_name, 'replay', host_name, 'job',
                                  '--replies', str(case.directory / 'replies.json'))
    assert result.returncode == 0 and replayed['status'] == 'proposal_ready', result.stderr
    assert replayed['mode'] == 'offline_replay' and replayed['provider_calls'] == 0
    store = WorkerStore(case.jobs / host_name)
    assert validated_proposal(store, 'job')['version'] == 8
    result, inspected = invoke_cli(case, host_name, 'inspect', host_name, 'job')
    assert inspected == store.inspect('job')
    again, refused = invoke_cli(case, host_name, 'replay', host_name, 'job',
                                '--replies', str(case.directory / 'replies.json'))
    assert again.returncode == 2 and refused['status'] == 'failed'
    assert len(store.inspect('job')['attempts']) == 1


def test_actual_attune_mcp_transport_reaches_same_core(memory_case, packet):
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    case = memory_case
    envelope, policy = packet
    params = StdioServerParameters(command=sys.executable,
        args=['-B', '-m', 'attune_harness.memory_bridge', '--config', str(case.config_path), '--jobs', str(case.jobs)],
        env=environment(case), cwd=str(case.directory))

    async def journey(errlog):
        # The SDK's default can retain a pytest capture stream from import time.
        # Own a real stream so transport checks do not depend on suite order.
        async with stdio_client(params, errlog=errlog) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=15)) as client:
                await client.initialize()
                listing = await client.list_tools()
                assert 'harness_memory_replay' in [tool.name for tool in listing.tools]

                async def call(operation, arguments):
                    response = await client.call_tool('harness_memory_' + operation, arguments)
                    value = json.loads(response.content[0].text)
                    assert value['success'], value
                    return value['memory']

                current = await call('recall', dict(query='Aurora', k=3, max_chars=40))
                assert current['status'] == 'available'
                case.document.write_text(case.document.read_text().replace('9000', '9002'))
                refreshed = await call('refresh', dict(context=current))
                assert refreshed['invalidated_ids'] == [current['items'][0]['handle']['id']]
                source = await call('resolve', dict(handle=refreshed['context']['items'][0]['handle']))
                assert '9002' in source['text'] and source['text'].endswith('FINAL_DETAIL')
                await call('create', dict(run_id='mcp', envelope=envelope, policy=policy))
                result = await call('replay', dict(run_id='mcp', job_id='job',
                    replies=[dict(role='worker', profile='luna', value=proposal(envelope))]))
                assert result['status'] == 'proposal_ready'
                inspected = await call('inspect', dict(run_id='mcp', job_id='job'))
                assert len(inspected['attempts']) == 1
    with (case.directory / 'mcp-stderr.log').open('w') as errlog:
        asyncio.run(journey(errlog))
    assert validated_proposal(WorkerStore(case.jobs / 'mcp'), 'job')['version'] == 8


def test_usage_guard_preserves_configured_team_coordination_and_local_events(memory_case, monkeypatch):
    from attune_harness.memory_cli import configure_process
    from attune.telemetry.agent_coordination import CoordinationSignals
    from attune.telemetry.memory_events import log_memory_event
    from attune.telemetry import usage_ping
    monkeypatch.setenv('ATTUNE_USAGE_PING', '1')
    configure_process()
    assert not usage_ping.is_enabled(True)
    client = Mock()
    client.xadd.return_value = b'123-0'
    backend = SimpleNamespace(_client=client)
    coordinator = CoordinationSignals(memory=backend, agent_id='lead', enable_streaming=True)
    signal_id = coordinator.signal('task_complete', target_agent='worker', payload={'status': 'done'})
    assert signal_id and client.setex.call_count == 1 and client.xadd.call_count == 1
    assert client.xadd.call_args.args[0] == 'stream:coordination_signal'
    log_memory_event('memory_feedback', action='reject', ids=['synthetic'])
    assert (memory_case.directory / 'telemetry' / 'telemetry' / 'memory_events.jsonl').is_file()


@pytest.mark.parametrize('remove_guard', [False, True])
def test_process_shutdown_keeps_local_usage_but_blocks_product_upload(memory_case, remove_guard):
    case = memory_case
    script = case.directory / 'shutdown.py'
    script.write_text('''
import json, os, sys
from pathlib import Path
from types import SimpleNamespace
from attune.config.loader import ConfigLoader
from attune.config.sections.telemetry import TelemetryConfig
from attune.telemetry.usage_tracker import UsageTracker
from attune.telemetry import usage_ping
from attune_harness import memory_cli
root = Path(os.environ['ATTUNE_HOME'])
root.mkdir(exist_ok=True)
configuration = root / 'legacy-opt-in.json'
configuration.write_text('{"telemetry":{"usage_ping":true,"install_id":"synthetic"}}')
ConfigLoader.get_default_config_path = staticmethod(lambda: configuration)
ConfigLoader.load = lambda self: SimpleNamespace(telemetry=TelemetryConfig(usage_ping=True, install_id='synthetic'))
tracker = UsageTracker.get_instance(telemetry_dir=root / 'telemetry')
tracker.track_llm_call(workflow='synthetic', stage='fixture', tier='cheap', model='fixture',
                      provider='fixture', cost=0.01, tokens={'input':12,'output':3},
                      cache_hit=False, cache_type=None, duration_ms=1)
actual_sync = usage_ping.run_sync
def scoped_sync(config, **kwargs):
    return actual_sync(config, telemetry_dir=tracker.telemetry_dir, **kwargs)
usage_ping.run_sync = scoped_sync
def intercepted_poster(endpoint, records, timeout):
    (root / 'upload-attempt.json').write_text(json.dumps(records))
    return True
usage_ping.run_sync_at_exit.__kwdefaults__['poster'] = intercepted_poster
if os.environ['REMOVE_USAGE_GUARD'] == '1':
    memory_cli.configure_process = lambda: None
raise SystemExit(memory_cli.main(sys.argv[1:]))
''')
    env = environment(case)
    env['REMOVE_USAGE_GUARD'] = '1' if remove_guard else '0'
    result = subprocess.run([sys.executable, '-B', str(script), '--config', str(case.config_path), 'capabilities'],
                            env=env, cwd=case.directory, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    local = case.directory / 'telemetry' / 'telemetry' / 'usage.jsonl'
    rows = [json.loads(line) for line in local.read_text().splitlines()]
    assert rows[0]['tokens'] == {'input': 12, 'output': 3}
    assert (case.directory / 'telemetry' / 'upload-attempt.json').exists() is remove_guard
