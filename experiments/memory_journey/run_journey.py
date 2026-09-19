"""Freeze/run one native journey, or demonstrate it with labeled offline fixtures."""
import argparse
from copy import deepcopy
from contextlib import contextmanager
import importlib.metadata
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from managed_stash import ManagedStash, Conflict, ROOT, worker
from journey import prepare, execute, apply_job
from fixtures import packet, participant
from baseline import Transport, write, old
from verify_worker import verify_prior, sha, read

HERE = Path(__file__).resolve().parent
DEST = ROOT/'docs/receipts/memory-journey-2026-09-16'
CANARY = 'ELM_PRIVATE_CANARY: keep the rehearsal key in locker 7.'


class ArtifactPreservationError(OSError):
    def __init__(self, directory):
        self.directory = directory
        super().__init__('Receipt persistence failed; inspect retained synthetic files at ' + str(directory))


@contextmanager
def scratch_store():
    root=Path(tempfile.mkdtemp(prefix='memory-journey-'))
    try:
        yield root
    except ArtifactPreservationError:
        raise  # Keep the only surviving copy of possibly pending effects.
    except BaseException:
        shutil.rmtree(root)
        raise
    else:
        shutil.rmtree(root)


def protocol():
    prior = verify_prior()
    previous_dir = ROOT/'docs/receipts/memory-worker-2026-09-16'
    previous = read(previous_dir/'verification.json')
    for name, expected in {**previous['sources'], **previous['external_sources']}.items():
        if sha(ROOT/name) != expected:
            raise ValueError('Prior worker dependency changed: ' + name)
    sources = dict(previous['sources'])
    for name in prior:
        sources.update(read(ROOT/'docs/receipts'/(name+'-2026-09-16')/'protocol.json')['sources'])
    sources.update({str(p.relative_to(ROOT)):sha(p) for p in HERE.glob('*.py')})
    for name in ('DESIGN.md','cases.json'):
        sources[str((HERE/name).relative_to(ROOT))] = sha(HERE/name)
    external = dict(previous['external_sources'])
    external_path = Path(next(p for p in external if p.endswith('/file_stash.py'))).parents[1]/'security/path_validation.py'
    external[str(external_path)] = sha(external_path)
    cases = packet()
    selected = [s['id'] for s in cases['stages'] if worker.sampled(s['id'],cases['policy'])]
    if selected != ['correction']:
        raise ValueError('Expected the preselected correction audit only')
    return dict(version=1, authorization='Patrick: great go, following the isolated Luna note-journey recommendation.',
        cases=cases, sampled=selected, models=old.previous.MODELS,
        planned_calls=4, max_native_calls=7, per_call_timeout=180, campaign_timeout=900,
        automatic_retries=0, route='existing Codex ChatGPT subscription', direct_api_spend=False,
        live_memory_writes=0, voyage_calls=0,
        cli_version=subprocess.run(['codex','--version'],capture_output=True,text=True,check=True).stdout.strip(),
        file_stash_package_version=importlib.metadata.version('attune-ai'),
        sources=sources, external_sources=external, prior_verified=prior,
        worker_receipts={p.name:sha(p) for p in previous_dir.iterdir() if p.is_file()},
        grading='Frozen stage rubrics; unblinded lead grades every initial/final reply and audit against actual source text. Separate shape, host acceptance, citation relevance, meaning and stored effects.',
        limits='One synthetic feasibility journey on macOS. No production integration, broad taxonomy/security qualification, power-loss durability, live context erasure, quality rate or comparative cost claim.')


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def require_stale(adapter, context):
    try:
        adapter.assert_context(context)
    except Conflict:
        return
    raise ValueError('Old context unexpectedly remained current')


def lifecycle(call, preserve=lambda value: None):
    """Every physical store is exclusively created inside a fresh temp root."""
    cases = packet()
    journal = dict(mode='actual temporary file-stash API', status='running', stages=[])
    with scratch_store() as root:
        journal['scratch_directory']=str(root)
        adapter = ManagedStash.create(root/'cedar', cases['scope'])
        foreign = ManagedStash.create(root/'elm', 'elm')
        # Explicit fixture setup outside the wrapper; never queried or sent to models.
        require(foreign.backend.remember(CANARY,memory_id='elm-note',
            topics=['type:note','cwd:elm','source:E1']), 'Could not seed foreign canary')
        foreign_before = foreign.path.read_bytes()
        context = None
        completed = []

        def save():
            journal['artifacts'] = {str(p.relative_to(root)):p.read_text(encoding='utf-8')
                for pattern in ('record.json','findings.jsonl') for p in root.rglob(pattern)}
            preserve(deepcopy(journal))

        try:
            for stage in cases['stages']:
                id = stage['id']
                store = prepare(adapter,root/id,target=cases['target'],operation=stage['operation'],
                    task=stage['task'],sources=stage['sources'],policy=cases['policy'])
                item = dict(id=id, before=adapter.snapshot(), state='started')
                journal['stages'].append(item)
                save()

                def guarded(*args):
                    prompt = args[2]
                    require(CANARY not in json.dumps(prompt), 'Foreign canary in participant prompt')
                    return call(id, *args)

                result = execute(adapter,store,id,guarded)
                item['result'] = result
                require(result['application'] is not None and
                        result['application']['disposition']=='applied', 'Stage did not produce an applied operation')
                require(result['worker']['sampled']==(id=='correction'), 'Sample selection changed')
                if context is not None:
                    require_stale(adapter,context)
                context = ManagedStash(root/'cedar',cases['scope']).recall('rehearsal')
                adapter.assert_context(context)
                require(context['version']==len(journal['stages']), 'Version did not advance exactly once')
                require(foreign.path.read_bytes()==foreign_before, 'Foreign store changed')
                before_retry = adapter.path.read_bytes()
                retry = apply_job(adapter,store,id)
                require(retry['replay'] and adapter.path.read_bytes()==before_retry, 'Retry changed storage')
                if id=='forget':
                    require(context['facts']==[] and before_retry==b'' and adapter.snapshot()['sources']==[],
                            'Active note, evidence or physical bytes remain after forgetting')
                else:
                    require(len(context['facts'])==1 and context['facts'][0]['id']==cases['target'],
                            'Expected exactly the selected stored note')
                item.update(state='completed',after=adapter.snapshot(),recall=context,retry=retry,
                            foreign_preserved=True,previous_context_stale=id!='capture')
                completed.append((store,id))
                save()
            for store,id in completed:
                require(apply_job(adapter,store,id)['replay'], 'Completed operation lost its replay receipt')
            require(adapter.path.read_bytes()==b'', 'An old operation resurrected the forgotten note')
            journal.update(status='completed',no_resurrection=True,final_version=adapter.snapshot()['version'])
        except Exception as error:
            journal.update(status='stopped',error_type=type(error).__name__,error=str(error))
            raise
        finally:
            try:
                save()  # Preserve known synthetic artifacts even when an effect is uncertain.
            except BaseException as error:
                raise ArtifactPreservationError(root) from error
    return journal


def native_run(frozen, destination):
    if protocol()!=frozen:
        raise ValueError('Frozen sources, profiles, fixtures or preserved receipts changed')
    transport = Transport(frozen,destination)
    def preserve(journal):
        write(destination/'journey.json',journal)
    try:
        lifecycle(transport.call,preserve)
        require(protocol()==frozen, 'Source drift during native execution')
        transport.ledger['status']='completed'
    except Exception as error:
        transport.ledger.update(status='stopped',reason=str(error))
        raise
    finally:
        write(transport.path,transport.ledger)
    return transport.ledger


def freeze(destination, suite_log):
    raw=suite_log.read_text(encoding='utf-8')
    match=re.search(r'\b(\d+) passed in ([0-9.]+)s',raw)
    require(match is not None and not any(s in raw for s in ('FAILED','ERROR')), 'Passing suite log required')
    frozen=protocol()
    destination.mkdir(parents=True,exist_ok=False)
    write(destination/'protocol.json',frozen)
    (destination/'suite.txt').write_text(raw,encoding='utf-8')
    write(destination/'offline.json',dict(suite_passed=int(match[1]),suite_seconds=float(match[2]),
        suite_sha256=sha(destination/'suite.txt'),native_calls=0,
        review=dict(receipt_type='evidence-chain',agent='luna_protocol_review',read_only=True,
            findings=['Validate actual claimed packet before participant dispatch.',
                      'Validate full physical rows, including hidden expired/malformed records.',
                      'Reject record/identifier/byte bounds before effects.',
                      'Retain the actual scratch directory when artifact persistence fails.'],
            disposition='Fixed before freeze and tested centrally.')))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    action=parser.add_mutually_exclusive_group()
    action.add_argument('--run',action='store_true')
    action.add_argument('--demo',action='store_true')
    parser.add_argument('--destination',type=Path,default=DEST)
    parser.add_argument('--suite-log',type=Path)
    args=parser.parse_args()
    if args.demo:
        result=lifecycle(lambda stage,*rest:participant(stage)(*rest))
        print(json.dumps(dict(mode='Injected offline answers; actual temporary storage; zero native calls',
            status=result['status'],stages=[dict(id=s['id'],version=s['after']['version'],
            notes=s['recall']['facts'],retry=s['retry']['replay'],foreign_preserved=s['foreign_preserved']) for s in result['stages']],
            no_resurrection=result['no_resurrection']),indent=2))
    elif args.run:
        result=native_run(read(args.destination/'protocol.json'),args.destination)
        print(json.dumps(dict(status=result['status'],native_calls=len(result['attempts'])),indent=2))
    else:
        if args.suite_log is None:parser.error('--suite-log is required to freeze')
        freeze(args.destination,args.suite_log)
        print(args.destination/'protocol.json')
