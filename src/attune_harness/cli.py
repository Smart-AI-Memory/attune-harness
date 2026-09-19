"""Local feature CLI. JSON reports are distinct from model completion claims."""

import argparse
import json
from pathlib import Path

from .features import FeatureUnavailable, output_path, report, write_report


def main(argv: list[str] | None = None) -> int:
    import sys
    invocation = sys.argv[1:] if argv is None else argv
    if invocation[:1] == ['memory']:
        from .memory_cli import main as memory_main
        return memory_main(invocation[1:])
    parser = argparse.ArgumentParser(prog='attune-harness')
    sub = parser.add_subparsers(dest='command')
    from .review_cli import add_commands, execute
    add_commands(sub)
    from .task_cli import add_controls, execute_control, add_fix
    add_controls(sub)
    add_fix(sub)
    from .work_cli import add_commands as add_work
    add_work(sub)
    from .test_cli import add_command as add_test
    add_test(sub)
    from .extension_cli import add_commands as add_extensions
    add_extensions(sub)
    from .voyage_cli import add_commands as add_voyage
    add_voyage(sub)
    from .memory_cli import add_commands as add_memory
    add_memory(sub)
    for name, description in (
        ('triage-check', 'Suggest a bounded response to a trusted check event; never dispatch'),
        ('repair-economics', 'Account for all repair attempts and quality before cost ranking'),
    ):
        operation = sub.add_parser(name, help=description)
        operation.add_argument('input', type=Path)
    github = sub.add_parser('github-checks', help='Read a complete GitHub REST check-run export without dispatch')
    github.add_argument('input', type=Path)
    github.add_argument('--repository', required=True)
    github.add_argument('--revision', required=True)
    mcp = sub.add_parser('mcp-serve', help='Serve accepted retrieval grants over local MCP stdio')
    mcp.add_argument('--request', type=Path, required=True)
    mcp.add_argument('--config', type=Path, help='Review participant registry; omit for coding retrieval tasks')
    mcp.add_argument('--participant', required=True)
    mcp.add_argument('--session-dir', type=Path, required=True)
    mcp.add_argument('--allow-provider', action='store_true', help='Authorize accepted Voyage retrieval uploads/calls')
    inspect_mcp = sub.add_parser('mcp-inspect', help='Inspect local MCP call receipts without dispatching')
    inspect_mcp.add_argument('session_dir', type=Path)
    verify = sub.add_parser('verify', help='Verify supported Markdown claims against declared context')
    verify.add_argument('document', type=Path)
    verify.add_argument('--context', type=Path, required=True, help='Trusted attune-verify context manifest')
    verify.add_argument('--output', type=Path, help='Save a JSON report in an existing directory')
    retrieve = sub.add_parser('retrieve', help='Retrieve keyword evidence or an explicitly accepted Voyage coding task')
    retrieve.add_argument('query')
    retrieval_input = retrieve.add_mutually_exclusive_group(required=True)
    retrieval_input.add_argument('--corpus', type=Path)
    retrieval_input.add_argument('--request', type=Path, help='Accepted coding retrieval-task JSON')
    retrieve.add_argument('--participant', default='coding-agent')
    retrieve.add_argument('--session-dir', type=Path)
    retrieve.add_argument('--allow-provider', action='store_true')
    retrieve.add_argument('--k', type=int, default=3)
    retrieve.add_argument('--output', type=Path, help='Save a JSON report in an existing directory')
    from .cli_help import configure_help
    configure_help(parser, sub)
    args = parser.parse_args(argv)
    if args.command in ('plan', 'build'):
        from .work_cli import execute as execute_work
        return execute_work(args)
    if args.command == 'test':
        from .test_cli import execute as execute_test
        return execute_test(args)
    if args.command == 'fix':
        from .task_cli import validate_fix, execute_intake
        validate_fix(args, parser)
        return execute_intake(args)
    if args.command in ('status', 'resume', 'reconcile-task', 'transfer-task', 'cancel-task'):
        return execute_control(args)
    if args.command == 'review':
        from .task_cli import validate_mode, execute_intake
        if validate_mode(args, parser):
            return execute_intake(args)
    if args.command in ('code-config', 'index', 'retrieval-task'):
        from .voyage_cli import execute as execute_voyage
        return execute_voyage(args)
    if args.command == 'github-checks':
        from .features import read_text
        from .review_contract import parse_json
        from .github_checks import check_suggestions
        try:
            result = check_suggestions(parse_json(read_text(args.input, 1_048_576), 1_048_576),
                                       repository=args.repository, revision=args.revision)
        except Exception as exc:
            print(json.dumps({'status':'failed','error':{'type':type(exc).__name__,'detail':str(exc)}}))
            return 2
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    if args.command in ('triage-check', 'repair-economics'):
        from .features import read_text
        from .review_contract import parse_json, fields
        from .operations import triage, repair_economics
        try:
            value = parse_json(read_text(args.input, 1_048_576), 1_048_576)
            if args.command == 'triage-check':
                fields(value, ('event', 'handled_keys', 'max_attempts'))
                result = triage(value['event'], handled_keys=value['handled_keys'], max_attempts=value['max_attempts'])
            else:
                result = repair_economics(value)
        except Exception as exc:
            print(json.dumps({'status': 'failed', 'error': {'type': type(exc).__name__, 'detail': str(exc)}}))
            return 2
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    if args.command == 'mcp-inspect':
        from .mcp_server import inspect_session
        try:
            result = inspect_session(args.session_dir)
        except Exception as exc:
            result = report('mcp-inspect', 'failed', error={'type': type(exc).__name__, 'detail': str(exc)})
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0 if result['status'] == 'completed' else 2
    if args.command == 'mcp-serve':
        import asyncio
        import sys
        from .mcp_server import serve
        try:
            asyncio.run(serve(args.request, args.config, args.participant, args.session_dir,
                              allow_provider=args.allow_provider))
        except Exception as exc:
            # stdout is exclusively the MCP protocol stream.
            print(f'{type(exc).__name__}: {exc}', file=sys.stderr)
            return 2
        return 0
    if args.command == 'extension':
        from .extension_cli import execute as execute_extension
        return execute_extension(args)
    if args.command in ('review-form', 'review', 'inspect-review', 'resume-review', 'reconcile-review', 'transfer-review', 'cancel-review'):
        return execute(args)
    if args.command is None:
        from .__main__ import main as demo
        demo()
        return 0
    protected = ((args.document, args.context) if args.command == 'verify' else
                 (args.request,) if args.request else ())
    try:
        if args.output:
            output_path(args.output, protected)
    except (OSError, ValueError) as exc:
        print(json.dumps(report(args.command, 'failed', error={'type': type(exc).__name__, 'detail': str(exc)})))
        return 2
    try:
        if args.command == 'verify':
            from .verification import verify_document
            result = verify_document(args.document, args.context)
        else:
            if args.request:
                if args.session_dir is None:
                    raise ValueError('Coding retrieval requires --session-dir for durable provider receipts')
                from .mcp_server import RetrievalSession
                scope = RetrievalSession(args.request, None, args.participant, args.session_dir,
                                         allow_provider=args.allow_provider)
                with scope.store.lease():
                    scope.save()
                    try:
                        result = scope.invoke('harness.retrieve', {'query': args.query, 'k': args.k})
                    except BaseException:
                        scope.finish(interrupted=True)
                        raise
                    scope.finish()
            else:
                if args.allow_provider or args.session_dir:
                    raise ValueError('Provider/session options require an accepted retrieval task')
                from .retrieval import retrieve_sources
                result = retrieve_sources(args.query, args.corpus, k=args.k)
    except FeatureUnavailable as exc:
        result = report(args.command, 'unavailable', error={'type': type(exc).__name__, 'detail': str(exc)})
    except Exception as exc:
        result = report(args.command, 'failed', error={'type': type(exc).__name__, 'detail': str(exc)})
    try:
        if args.output:
            write_report(args.output, result, protected)
    except (OSError, ValueError, TypeError) as exc:
        result = report(args.command, 'failed', error={'type': type(exc).__name__, 'detail': f'Report write failed: {exc}'})
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    if result['status'] in ('verified', 'retrieved'):
        return 0
    return 1 if result['status'] in ('refuted', 'unknown', 'no_results') else 2
