"""E2 fixture worker using installed Harness; never imports checkout src/.

The broken-runtime injection changes only this process's retriever callback.
"""
import argparse
import asyncio
import hashlib
import importlib.metadata
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import attune_harness
from attune_harness import extensions
from attune_harness.recovery import snapshot_sources
from attune_harness.review import review
from attune_harness.review_contract import load_registry, review_form
from attune_harness.review_store import read_record

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
TOOL = 'evidence.search'


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def accept(cell, registry):
    write(cell / 'config.json', registry)
    submission = review_form(load_registry(cell / 'config.json'))['submission']
    submission.update(accepted=True, answers={'objective': 'E2 local capability experiment',
        'query': 'quartz retention policy', 'document': 'corpus/guide.md', 'context': 'context.json',
        'corpus': 'corpus', 'lead': 'lead', 'reviewer': 'reviewer'})
    write(cell / 'request.json', submission)


def setup(cell):
    corpus, bundle = cell / 'corpus', cell / 'bundle'
    corpus.mkdir(); bundle.mkdir()
    (corpus / 'guide.md').write_text('[Quartz retention policy](reference.md)', encoding='utf-8')
    (corpus / 'reference.md').write_text('Quartz retention policy is an independently checked E2 fixture.', encoding='utf-8')
    (bundle / 'SKILL.md').write_text('Use local evidence and cite its paths.', encoding='utf-8')
    write(bundle / 'extension.json', {'schema_version': 1, 'id': 'evidence', 'version': '0.1.0',
        'skill': 'SKILL.md', 'tools': {'search': 'retrieve'}})
    write(cell / 'context.json', {'schema_version': 1, 'project_root': 'corpus'})
    state = extensions.install(bundle / 'extension.json', cell / 'extension-state')
    state = extensions.mutate(cell / 'extension-state', state['state_digest'], 'enable')
    registry = {'schema_version': 1, 'extensions': {'evidence': {'state_dir': str(cell / 'extension-state'),
                 'artifact_digest': state['artifact_digest']}}, 'participants': {
        'lead': {'adapter': 'command', 'command': [sys.executable, '-I', str(HERE / 'participant.py')],
                 'timeout': 5, 'tools': [TOOL], 'max_turns': 2, 'max_tool_calls': 1},
        'reviewer': {'adapter': 'deterministic', 'tools': [TOOL], 'max_turns': 2, 'max_tool_calls': 1}}}
    accept(cell, registry)


def alter(cell, state_name):
    registry = read(cell / 'config.json')
    directory = cell / 'extension-state'
    state = extensions.inspect_extension(directory)
    if state_name == 'advertised-but-broken':
        (cell / 'broken-runtime.flag').write_text('Explicit fixture fault; not capability metadata', encoding='utf-8')
    elif state_name in ('disabled', 'upgraded'):
        state = extensions.mutate(directory, state['state_digest'], 'disable')
        if state_name == 'upgraded':
            manifest = cell / 'bundle/extension.json'
            value = read(manifest); value['version'] = '0.2.0'; write(manifest, value)
            (cell / 'bundle/SKILL.md').write_text('Updated guidance: cite local evidence.', encoding='utf-8')
            state = extensions.mutate(directory, state['state_digest'], 'replace', manifest=manifest)
            state = extensions.mutate(directory, state['state_digest'], 'enable')
            registry['extensions']['evidence']['artifact_digest'] = state['artifact_digest']
            accept(cell, registry)
    elif state_name == 'permission-denied':
        registry['participants']['lead']['tools'] = ['retrieve']
        accept(cell, registry)
    elif state_name not in ('working', 'dependency-missing'):
        raise ValueError('Unknown seeded state')


def describe(cell, adapter):
    bundle = extensions.discover(cell / 'bundle/extension.json')
    state = extensions.inspect_extension(cell / 'extension-state')
    registry = load_registry(cell / 'config.json')
    required = {'attune-rag': '1.2.0', 'attune-forms': '0.17.0', 'attune-verify': '0.6.0', 'attune-harness': '0.1.0.dev0'}
    if adapter.startswith('mcp'):
        required['mcp'] = '2.2.0'
    dependencies = {}
    for name in required:
        try:
            dependencies[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            dependencies[name] = None
    package = Path(attune_harness.__file__).parent
    engine = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(package.glob('*.py'))}
    from attune_harness.mcp_server import OUTPUT_SCHEMA
    return {'tool': TOOL, 'adapter': adapter, 'engine_modules': engine,
            'runtime': {'python': sys.version.split()[0], 'platform': sys.platform},
            'dependencies': dependencies, 'required_dependencies': required,
            'artifact': {'digest': bundle['artifact_digest'], 'version': bundle['declaration']['version']},
            'lifecycle': state['status'], 'grants': registry['participants']['lead']['tools'],
            'registry': registry, 'accepted_request': read(cell / 'request.json'),
            'corpus_root': str((cell / 'corpus').resolve()), 'sources': snapshot_sources(cell / 'corpus'),
            'arguments': {'query': 'quartz retention policy', 'k': 3},
            'input_schema': extensions.RETRIEVE_SCHEMA, 'output_schema': OUTPUT_SCHEMA,
            'declared_tools': [f"{bundle['declaration']['id']}.{name}" for name in bundle['declaration']['tools']]}


def inject_fault(cell):
    if (cell / 'broken-runtime.flag').exists():
        import attune_rag
        def broken(*args, **kwargs):
            raise RuntimeError('E2 seeded runtime failure with unchanged declared versions')
        attune_rag.KeywordRetriever.retrieve = broken


def command_call(cell, directory):
    inject_fault(cell)
    record = review(cell / 'request.json', cell / 'config.json', directory, allow_external=True)
    selected = [e for e in record['events'] if e['kind'] == 'tool'
                and e['participant_id'] == 'lead' and e['action']['name'] == TOOL]
    return {'record': record, 'target_result': selected[-1].get('result') if selected else None,
            'target_dispatches': len(selected), 'error': record.get('error')}


def mcp_call(cell, directory):
    spec = importlib.util.spec_from_file_location('independent_mcp_client', ROOT / 'scripts/check_mcp_installed.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    peer = module.Peer([sys.executable, '-I', str(HERE / 'worker.py'), 'serve', '--cell', str(cell),
                        '--adapter', 'mcp-stdio-2026-07-28', '--run-dir', str(directory)], cell, '2026-07-28')
    outcome = {'target_result': None, 'target_dispatches': 0}
    try:
        peer.call('server/discover', {})
        outcome['discovery'] = peer.call('tools/list', {})
        response = peer.call('tools/call', {'name': 'harness.' + TOOL,
                              'arguments': {'query': 'quartz retention policy', 'k': 3}})
        outcome['response'] = response
        if 'result' in response and not response['result'].get('isError'):
            outcome['target_result'] = response['result'].get('structuredContent')
            assert json.loads(response['result']['content'][0]['text']) == outcome['target_result']
        else:
            outcome['error'] = response
    except Exception as exc:
        outcome['error'] = {'type': type(exc).__name__, 'detail': str(exc)}
    finally:
        peer.process.stdin.close()
        try:
            peer.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            peer.process.kill(); peer.process.wait()
            raise RuntimeError('MCP shutdown exceeded deadline')
        peer.err.seek(0)
        outcome.update(frames=peer.frames, server_exit=peer.process.returncode, stderr=peer.err.read())
        peer.err.close(); peer.process.stdout.close()
    if (directory / 'record.json').exists():
        outcome['record'] = read_record(directory)
        outcome['target_dispatches'] = len(outcome['record']['events'])
    return outcome


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('setup', 'alter', 'describe', 'invoke', 'serve'))
    parser.add_argument('--cell', required=True, type=Path)
    parser.add_argument('--adapter', choices=('command-review', 'mcp-stdio-2026-07-28'))
    parser.add_argument('--state')
    parser.add_argument('--run-dir', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.action == 'setup':
        setup(args.cell)
    elif args.action == 'alter':
        alter(args.cell, args.state)
    elif args.action == 'describe':
        write(args.output, describe(args.cell, args.adapter))
    elif args.action == 'serve':
        inject_fault(args.cell)
        from attune_harness.mcp_server import serve
        try:
            asyncio.run(serve(args.cell / 'request.json', args.cell / 'config.json', 'lead', args.run_dir))
        except Exception as exc:
            print(f'{type(exc).__name__}: {exc}', file=sys.stderr)
            sys.exit(2)
    else:
        try:
            result = (command_call if args.adapter == 'command-review' else mcp_call)(args.cell, args.run_dir)
        except Exception as exc:
            result = {'target_result': None, 'target_dispatches': 0,
                      'error': {'type': type(exc).__name__, 'detail': str(exc)}}
        result['harness_location'] = str(Path(attune_harness.__file__))
        write(args.output, result)
