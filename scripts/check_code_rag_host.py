"""Installed Attune MCP round trip: repository selection, no evidence, no provider calls."""

import argparse
import asyncio
import json
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

from attune_harness.retrieval_task import task_template
from attune_harness.review_store import read_record
from attune_harness.voyage_index import build_index
from attune_harness.voyage_sources import code_config


def require(condition, message):
    if not condition:
        raise RuntimeError('Host qualification failed: ' + message)


async def check(work: Path) -> dict:
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    root = work / 'application'
    root.mkdir()
    (root / 'README.md').write_text('# Documentation is optional\n', encoding='utf-8')
    for command in (['init'], ['add', 'README.md'],
                    ['-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'fixture']):
        subprocess.run(['git', '-C', str(root), '-c', 'commit.gpgsign=false',
                        '-c', 'core.hooksPath=' + str(work / 'no-hooks'), *command],
                       check=True, capture_output=True)
    cfg = code_config(root, work / 'index')
    index = build_index(cfg)
    require(index['provider_calls'] == 0, 'empty index made provider calls')
    task = task_template(cfg, index['generation'], 'Find application code', max_calls=2)
    task['accepted'] = True
    request = work / 'task.json'
    request.write_text(json.dumps(task), encoding='utf-8')
    session = work / 'session'
    params = StdioServerParameters(command=sys.executable,
        args=['-I', '-m', 'attune_harness.attune_bridge', '--request', str(request), '--session-dir', str(session)],
        env={'ATTUNE_VERSION_CHECK': '0', 'ATTUNE_HOME': str(work / 'attune-home'),
             'VOYAGE_API_KEY': '', 'ANTHROPIC_API_KEY': ''})
    with (work / 'server-stderr.txt').open('w', encoding='utf-8') as errors:
        async with stdio_client(params, errlog=errors) as (read, write):
            async with ClientSession(read, write) as client:
                initialized = await client.initialize()
                listing = await client.list_tools()
                require('code_evidence_query' in {tool.name for tool in listing.tools}, 'code evidence tool is missing')
                response = await client.call_tool('code_evidence_query', {'query': 'Find payment processing', 'k': 3})
                result = json.loads(response.content[0].text)
                require(result['status'] == 'no_results', 'empty selection did not return no_results')
                require(result['sources'] == [], 'empty selection returned sources')
                require(result['evidence_basis']['answer_support'] == 'insufficient_evidence', 'unsupported answer support')
                require(result['usage']['new_provider_calls'] == 0, 'empty retrieval made provider calls')
    saved = read_record(session)
    require(saved['status'] == 'completed' and saved['events'][0]['state'] == 'completed', 'session did not complete')
    return {'status': 'passed', 'attune_ai': version('attune-ai'), 'harness': version('attune-harness'),
            'mcp_sdk': version('mcp'), 'server': initialized.serverInfo.name,
            'tool': 'code_evidence_query', 'result': result, 'provider_calls': 0,
            'qualification_scope': 'Real installed Attune MCP discovery/call/clean shutdown with an empty code selection; not semantic quality'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    result = asyncio.run(asyncio.wait_for(check(args.output.absolute()), timeout=60))
    (args.output / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'result'}, indent=2))
