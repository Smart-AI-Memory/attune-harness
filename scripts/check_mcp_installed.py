"""Independent stdlib MCP peer against installed Harness; no SDK in this client."""
import argparse
import json
import os
import select
import subprocess
import tempfile
import time
from pathlib import Path


class Peer:
    def __init__(self, argv, directory, profile):
        self.err = tempfile.TemporaryFile(mode='w+')
        self.process = subprocess.Popen(argv, cwd=directory, stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=self.err, bufsize=0)
        self.buffer = b''
        self.profile, self.index, self.frames = profile, 0, []

    def send(self, value):
        self.process.stdin.write((json.dumps(value)+'\n').encode())
        self.process.stdin.flush()

    def call(self, method, params, *, version=None):
        self.index += 1
        params = dict(params)
        if self.profile == '2026-07-28':
            params['_meta'] = {'io.modelcontextprotocol/protocolVersion': version or self.profile,
                               'io.modelcontextprotocol/clientCapabilities': {},
                               'io.modelcontextprotocol/clientInfo': {'name':'independent-fixture','version':'1'}}
        self.send({'jsonrpc':'2.0','id':self.index,'method':method,'params':params})
        deadline = time.monotonic()+5
        while time.monotonic()<deadline:
            if b'\n' not in self.buffer:
                if not select.select([self.process.stdout],[],[],max(0,deadline-time.monotonic()))[0]:
                    break
                chunk = os.read(self.process.stdout.fileno(),65_536)
                if not chunk: break
                self.buffer += chunk
                assert len(self.buffer) <= 262_144, 'Oversized protocol response'
                continue
            line,self.buffer = self.buffer.split(b'\n',1)
            response=json.loads(line)
            self.frames.append(response)
            if response.get('id') == self.index:
                assert response['jsonrpc']=='2.0'
                return response
        self.err.seek(0)
        raise AssertionError('No correlated MCP response: '+self.err.read())

    def close(self):
        if self.process.stdin and not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
            raise AssertionError('Server did not shut down after EOF')
        assert self.process.returncode==0, self.process.returncode
        self.err.close()


def check(python, legacy_python=None):
    cases=[]; protocols={}
    with tempfile.TemporaryDirectory(prefix='harness-mcp-installed-') as scratch:
        work=Path(scratch)
        def cli(args,code=0):
            result=subprocess.run([str(python),'-I','-m','attune_harness',*map(str,args)],cwd=work,
                                  capture_output=True,text=True,timeout=15)
            assert result.returncode==code,(args,result.stdout,result.stderr)
            value=json.loads(result.stdout)
            cases.append({'command':args[0],'exit':code,'status':value['status']})
            return value
        project=work/'project';project.mkdir()
        (project/'guide.md').write_text('[Quartz policy](reference.md)',encoding='utf-8')
        (project/'reference.md').write_text('Quartz policy reference',encoding='utf-8')
        (work/'context.json').write_text(json.dumps({'schema_version':1,'project_root':'project'}))
        source=Path(__file__).resolve().parent.parent/'examples/extensions/plugin/src/attune_harness_evidence/extension.json'
        state_dir=work/'extension-state'
        state=cli(['extension','install',source,'--state-dir',state_dir])
        state=cli(['extension','enable','--state-dir',state_dir,'--checkpoint',state['state_digest']])
        config,request=work/'config.json',work/'request.json'
        registry={'schema_version':1,'extensions':{'evidence':{'state_dir':str(state_dir),'artifact_digest':state['artifact_digest']}},
                  'participants':{name:{'adapter':'deterministic','tools':['evidence.search'],'max_turns':3,'max_tool_calls':2}
                                  for name in ('lead','reviewer')}}
        config.write_text(json.dumps(registry),encoding='utf-8')
        submission=cli(['review-form','--config',config])['submission']
        submission.update(accepted=True,answers={'objective':'Review evidence','query':'quartz policy',
                          'document':'project/guide.md','context':'context.json','corpus':'project',
                          'lead':'lead','reviewer':'reviewer'})
        request.write_text(json.dumps(submission),encoding='utf-8')
        def command(directory):
            return [str(python),'-I','-m','attune_harness','mcp-serve','--request',str(request),
                    '--config',str(config),'--participant','lead','--session-dir',str(directory)]
        for profile in ('2025-11-25','2026-07-28'):
            directory=work/profile
            peer=Peer(command(directory),work,profile)
            try:
                if profile=='2025-11-25':
                    init=peer.call('initialize',{'protocolVersion':profile,'capabilities':{},
                                    'clientInfo':{'name':'independent-fixture','version':'1'}})['result']
                    assert init['protocolVersion']==profile
                    peer.send({'jsonrpc':'2.0','method':'notifications/initialized'})
                else:
                    assert 'result' in peer.call('server/discover',{})
                    assert 'error' in peer.call('tools/list',{},version='2099-01-01')
                tools=peer.call('tools/list',{})['result']['tools']
                assert [t['name'] for t in tools]==['harness.evidence.search']
                assert tools[0]['inputSchema']['additionalProperties'] is False and tools[0]['outputSchema']
                assert 'error' in peer.call('nonexistent/method',{})
                for name,args in [('harness.verify',{}),('harness.evidence.search',{'query':'quartz','k':True}),
                                  ('harness.evidence.search',{'query':'quartz','k':3,'corpus':'/tmp'})]:
                    result=peer.call('tools/call',{'name':name,'arguments':args})['result']
                    assert result['isError'] and 'structuredContent' not in result
                result=peer.call('tools/call',{'name':'harness.evidence.search','arguments':{'query':'quartz policy','k':3}})['result']
                assert not result.get('isError',False) and result['structuredContent']['status']=='retrieved'
                assert json.loads(result['content'][0]['text'])==result['structuredContent']
                assert result['structuredContent']['extension']['artifact_digest']==state['artifact_digest']
                state=cli(['extension','disable','--state-dir',state_dir,'--checkpoint',state['state_digest']])
                assert peer.call('tools/call',{'name':'harness.evidence.search','arguments':{'query':'quartz policy','k':3}})['result']['isError']
                state=cli(['extension','enable','--state-dir',state_dir,'--checkpoint',state['state_digest']])
                absent=peer.call('tools/call',{'name':'harness.evidence.search','arguments':{'query':'zzzznone','k':3}})['result']
                assert absent['structuredContent']['status']=='no_results'
                assert peer.call('tools/call',{'name':'harness.evidence.search','arguments':{'query':'quartz','k':3}})['result']['isError']
            finally:
                peer.close()
            saved=cli(['mcp-inspect',directory])
            assert saved['status']=='completed' and len(saved['events'])==2
            protocols[profile]={'responses':len(peer.frames),'calls_completed':2,'shutdown':'EOF exit 0',
                                'frames':peer.frames}
        if legacy_python:
            # Real SDK 1.29.1 client from its preserved environment, new 2.2.0 server.
            script='''import asyncio,json,sys
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters,stdio_client
async def main():
 async with stdio_client(StdioServerParameters(command=sys.argv[1],args=sys.argv[2:])) as (r,w):
  async with ClientSession(r,w) as c:
   init=await c.initialize()
   result=await c.call_tool('harness.evidence.search',{'query':'quartz policy','k':3})
   assert init.protocolVersion=='2025-11-25' and result.structuredContent['status']=='retrieved'
   print(json.dumps({'protocol':init.protocolVersion,'result':result.structuredContent['status']}))
asyncio.run(main())
'''
            result=subprocess.run([str(legacy_python),'-I','-c',script,*command(work/'legacy-sdk')],
                                  cwd=work,capture_output=True,text=True,timeout=15)
            assert result.returncode==0,result.stderr
            cases.append({'command':'SDK 1.29.1 client → SDK 2.2.0 server',**json.loads(result.stdout)})
    return {'cases':cases,'protocols':protocols,'provider_calls':0,'client':'independent stdlib JSON-RPC plus preserved legacy SDK',
            'server_sdk':'2.2.0','transport':'stdio','remote_authentication_qualified':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python',type=Path,required=True)
    parser.add_argument('--legacy-python',type=Path)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    result=check(args.python.absolute(),args.legacy_python.absolute() if args.legacy_python else None)
    args.report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(f"{len(result['protocols'])} independent protocol profiles passed; {len(result['cases'])} CLI/cross-version checks; zero provider calls")
