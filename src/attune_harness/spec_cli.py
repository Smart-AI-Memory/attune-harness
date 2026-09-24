"""Provider-free Spec intake and receipt-backed presentation."""
import json
import sys
from pathlib import Path
from .spec_intake import area_candidates, existing_spec_slugs, compose_spec_contract, build_spec_intake_form
from .spec_tasks import read_spec
from .spec_state import load_state
from . import spec_presenter as present


def add_command(sub):
    parser=sub.add_parser('spec',help='Prepare Spec intake and present existing task evidence')
    commands=parser.add_subparsers(dest='spec_command',required=True)
    intake=commands.add_parser('intake',help='Print an intake form or compose answers from stdin')
    intake.add_argument('--project',type=Path,default=Path.cwd())
    intake.add_argument('--compose',action='store_true')
    show=commands.add_parser('present',help='Read a plan and present its tasks or verified test evidence')
    show.add_argument('view',choices=['tasks','task','result','progress'])
    show.add_argument('--plan',type=Path,required=True)
    show.add_argument('--task')
    show.add_argument('--test-run',type=Path)


def execute(args):
    try:
        if args.spec_command=='intake':
            project=args.project.resolve(strict=True)
            if not project.is_dir(): raise ValueError('Project must be an existing directory')
            areas=area_candidates(project);taken=existing_spec_slugs(project)
            if args.compose:
                raw=sys.stdin.read(65537)
                if len(raw.encode('utf-8'))>65536: raise ValueError('Answers exceed 64 KiB')
                from .review_contract import parse_json
                answers=parse_json(raw,65536)
                if not isinstance(answers,dict): raise ValueError('Answers must be an object')
                if set(answers)-{'outcome','done_when','area','slug'}: raise ValueError('Unknown intake field')
                if any(not isinstance(v,str) for v in answers.values()): raise ValueError('Intake values must be strings')
                if any(not answers.get(k,'').strip() for k in ('outcome','done_when')): raise ValueError('Outcome and done_when are required')
                print(compose_spec_contract(answers,taken),end='')
            else:
                form=build_spec_intake_form(areas)
                print(json.dumps({'form':{'title':form.title,'description':form.description,
                    'fields':[{k:v for k,v in {'id':q.id,'text':q.text,'type':q.type.value,
                        'options':list(q.options),'default':q.default,'help_text':q.help_text,
                        'required':q.required}.items() if v is not None} for q in form.questions]},
                    'areas':areas,'taken_slugs':taken},indent=2))
        else:
            tasks=read_spec(str(args.plan));state=load_state(str(args.plan))
            if args.view in ('tasks','progress'):
                if args.task or args.test_run: raise ValueError('This view does not take --task or --test-run')
                if args.view=='tasks': print(present.present_tasks(tasks,state))
                else: print(present.format_progress_bar(len(state.completed) if state else 0,len(tasks)))
            else:
                if not args.task: raise ValueError('--task is required for task/result')
                task=next((t for t in tasks if t.task_id==args.task),None)
                if task is None: raise ValueError('Task is absent from plan')
                if args.view=='task':
                    if args.test_run: raise ValueError('--test-run is only valid with result')
                    print(present.present_task_detail(task))
                else:
                    if not args.test_run: raise ValueError('--test-run is required for result')
                    from .spec_handoff import bind_test_evidence
                    evidence=bind_test_evidence(args.test_run)
                    # Spec task IDs and testing-run IDs are distinct namespaces.
                    # Require the persisted acceptance to bind this exact evidence,
                    # including its source task ID, checkpoint and outcome.
                    from .spec_workspace import _accepted_receipt
                    if state is None or task.task_id not in state.completed:
                        raise ValueError('Result requires a completed Spec task with accepted evidence')
                    accepted = [_accepted_receipt(r) for r in state.task_receipts
                                if r.get('task_id') == task.task_id]
                    if len(accepted) != 1 or accepted[0].receipt.test_evidence != evidence:
                        raise ValueError('Testing evidence differs from the accepted Spec task binding')
                    print(present.present_task_result(task,evidence))
        return 0
    except (OSError,ValueError,TypeError,RecursionError) as exc:
        print(f'{type(exc).__name__}: {exc}',file=sys.stderr)
        return 2
