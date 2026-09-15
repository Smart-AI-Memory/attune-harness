"""Local feature CLI. JSON reports are distinct from model completion claims."""

import argparse
import json
from pathlib import Path

from .features import FeatureUnavailable, output_path, report, write_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='attune-harness')
    sub = parser.add_subparsers(dest='command')
    from .review_cli import add_commands, execute
    add_commands(sub)
    from .extension_cli import add_commands as add_extensions
    add_extensions(sub)
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
    mcp.add_argument('--config', type=Path, required=True)
    mcp.add_argument('--participant', required=True)
    mcp.add_argument('--session-dir', type=Path, required=True)
    inspect_mcp = sub.add_parser('mcp-inspect', help='Inspect local MCP call receipts without dispatching')
    inspect_mcp.add_argument('session_dir', type=Path)
    verify = sub.add_parser('verify', help='Verify supported Markdown claims against declared context')
    verify.add_argument('document', type=Path)
    verify.add_argument('--context', type=Path, required=True, help='Trusted attune-verify context manifest')
    verify.add_argument('--output', type=Path, help='Save a JSON report in an existing directory')
    retrieve = sub.add_parser('retrieve', help='Find local Markdown sources without model calls')
    retrieve.add_argument('query')
    retrieve.add_argument('--corpus', type=Path, required=True)
    retrieve.add_argument('--k', type=int, default=3)
    retrieve.add_argument('--output', type=Path, help='Save a JSON report in an existing directory')
    args = parser.parse_args(argv)
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
            asyncio.run(serve(args.request, args.config, args.participant, args.session_dir))
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
    protected = (args.document, args.context) if args.command == 'verify' else ()
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
