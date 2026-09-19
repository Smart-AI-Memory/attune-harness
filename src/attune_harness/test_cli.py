"""The test verb uses the same durable task controls as review and fix."""

import json
from pathlib import Path

from .test_change import (
    accept_test_task,
    create_test_task,
    execute_test_task,
    exit_code,
    present_test_task,
    public_test_task,
)


def add_command(sub) -> None:
    """Register explicit scope, preview and accepted pytest execution."""
    parser = sub.add_parser(
        "test", help="Test a captured change and retain the evidence"
    )
    parser.add_argument("--project", type=Path)
    parser.add_argument(
        "--from-task",
        type=Path,
        help="Completed repair task; derive checkout and changed paths, preserve provenance",
    )
    parser.add_argument(
        "--scope",
        action="append",
        help="Changed repository-relative file or directory; repeatable",
    )
    parser.add_argument(
        "--tests",
        action="append",
        help="Explicit test file/directory under --test-root; repeatable",
    )
    parser.add_argument("--test-root", default="tests")
    parser.add_argument(
        "--interpreter", help="Explicit Python executable containing pytest"
    )
    parser.add_argument("--goal", default="Test this change")
    parser.add_argument(
        "--task-dir",
        type=Path,
        required=True,
        help="New task directory outside the repository",
    )
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--max-output-bytes", type=int, default=1024 * 1024)
    parser.add_argument(
        "--pytest-arg",
        action="append",
        help="Qualified pytest option, e.g. --pytest-arg=-q",
    )
    parser.add_argument(
        "--pytest-plugin",
        action="append",
        help="Explicit plugin module, e.g. pytest_asyncio.plugin",
    )
    parser.add_argument(
        "--accept",
        action="store_true",
        help="Accept this exact deterministic plan and execute",
    )
    parser.add_argument(
        "--checkpoint",
        help="Accept a saved preview at this checkpoint; no input overrides",
    )
    parser.add_argument("--intake-only", action="store_true")
    parser.add_argument("--pause-after", type=int)


def execute(args) -> int:
    """Create/accept a preview and optionally run once, returning durable grammar."""
    try:
        if args.checkpoint:
            if (
                not args.accept
                or args.scope
                or args.tests
                or args.interpreter
                or args.project
                or args.from_task
                or args.test_root != "tests"
                or args.goal != "Test this change"
                or args.timeout != 60
                or args.max_output_bytes != 1024 * 1024
                or args.pytest_arg
                or args.pytest_plugin
            ):
                raise ValueError(
                    "Saved preview acceptance requires --accept and no input overrides"
                )
            task = accept_test_task(args.task_dir, args.checkpoint)
        else:
            if (not args.scope and not args.from_task) or not args.interpreter:
                raise ValueError(
                    "Test requires --scope or --from-task, and --interpreter; or saved preview --checkpoint --accept"
                )
            task = create_test_task(
                args.project if args.from_task else args.project or Path.cwd(),
                args.task_dir,
                scope=args.scope,
                tests=args.tests,
                test_root=args.test_root,
                interpreter=args.interpreter,
                goal=args.goal,
                timeout=args.timeout,
                max_output_bytes=args.max_output_bytes,
                pytest_args=args.pytest_arg,
                plugins=args.pytest_plugin,
                source_task=args.from_task,
            )
            if args.accept:
                task = accept_test_task(args.task_dir, task["checkpoint_digest"])
        if task["status"] == "accepted" and not args.intake_only:
            result = execute_test_task(args.task_dir, max_operations=args.pause_after)
        else:
            result = present_test_task(task)
        print(
            json.dumps(
                public_test_task(result), indent=2, ensure_ascii=False, allow_nan=False
            )
        )
        return exit_code(result)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "error": {"type": type(exc).__name__, "detail": str(exc)},
                }
            )
        )
        return 2
