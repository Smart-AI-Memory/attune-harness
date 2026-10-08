"""Thin CLI shared by coding hosts; preparation never dispatches."""

import json
from pathlib import Path

from . import consultation
from .features import read_text
from .review_contract import parse_json


def add_commands(sub):
    for name in ('source-review', 'roundtable'):
        parser = sub.add_parser(name, help='Bounded model consultation over frozen selected source files')
        verbs = parser.add_subparsers(dest='consultation_action', required=True)
        prepare = verbs.add_parser('prepare', help='Freeze scope and return the contract; no provider calls')
        prepare.add_argument('--project', type=Path, required=True)
        prepare.add_argument('--path', action='append', required=True)
        prepare.add_argument('--config', type=Path, required=True)
        prepare.add_argument('--run-dir', type=Path, required=True)
        run = verbs.add_parser('run', help='Dispatch or resume only the exact accepted contract')
        run.add_argument('run_dir', type=Path)
        run.add_argument('--accept', required=True)
        run.add_argument('--allow-external', action='store_true')
        run.add_argument('--allow-native', action='store_true')
        run.add_argument('--max-operations', type=int)
        status = verbs.add_parser('status', help='Inspect retained evidence without dispatch')
        status.add_argument('run_dir', type=Path)
        evidence = verbs.add_parser('evidence', help='Inspect claims beside numbered frozen source context')
        evidence.add_argument('run_dir', type=Path)
        assess = verbs.add_parser('assess-citation', help='Record an advisory host decision; never dispatch')
        assess.add_argument('run_dir', type=Path)
        assess.add_argument('--checkpoint', required=True)
        assess.add_argument('--decisions', type=Path,
                            help='JSON list of {round, participant, citation, decision, note}; '
                                 'all are recorded or none. Replaces the single-decision options')
        assess.add_argument('--round', dest='round_number', type=int)
        assess.add_argument('--participant')
        assess.add_argument('--citation', type=int, help='Zero-based evidence index')
        assess.add_argument('--decision', choices=('supported', 'rejected', 'uncertain'))
        assess.add_argument('--note')
        abandon = verbs.add_parser('abandon', help='Stop continuation while retaining uncertain effects')
        abandon.add_argument('run_dir', type=Path)
        abandon.add_argument('--checkpoint', required=True)


def execute(args):
    assessment_saved = False
    try:
        if args.consultation_action == 'prepare':
            config = parse_json(read_text(args.config, 131072))
            result = consultation.prepare(args.command, args.project, args.path, config, args.run_dir)
        else:
            current = consultation.load(args.run_dir)
            if current['operation'] != args.command:
                raise ValueError('Command does not match the saved consultation')
            if args.consultation_action == 'run':
                result = consultation.run(args.run_dir, args.accept, allow_external=args.allow_external,
                                          allow_native=args.allow_native, max_operations=args.max_operations)
            elif args.consultation_action == 'abandon':
                result = consultation.abandon(args.run_dir, args.checkpoint)
            elif args.consultation_action == 'evidence':
                result = consultation.inspect_evidence(args.run_dir)
            elif args.consultation_action == 'assess-citation':
                single = (args.round_number, args.participant, args.citation, args.decision, args.note)
                if args.decisions is not None:
                    if any(value is not None for value in single):
                        raise ValueError('Use --decisions or the single-decision options, not both')
                    decisions = parse_json(read_text(args.decisions, 524288), 524288)
                    result = consultation.assess_citations(args.run_dir, args.checkpoint, decisions)
                elif any(value is None for value in single):
                    raise ValueError('A single decision needs --round, --participant, --citation, '
                                     '--decision and --note')
                else:
                    result = consultation.assess_citation(args.run_dir, args.checkpoint, *single)
                assessment_saved = True
            else:
                result = current
                if result['status'] == 'running':
                    result = {**result, 'status': 'unresolved', 'persisted_status': 'running'}
    except Exception as exc:
        result = {'schema_version': 1, 'operation': args.command, 'status': 'refused',
                  'error': {'type': type(exc).__name__, 'detail': str(exc)}}
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if assessment_saved or result['status'] in ('prepared', 'paused', 'completed', 'cancelled') else 2
