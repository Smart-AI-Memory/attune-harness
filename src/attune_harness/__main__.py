"""Deterministic local demonstration: python -m attune_harness."""

import json
from dataclasses import asdict

from . import Check, Output, Task, run


class DemoParticipant:
    """Return a fixed answer without a provider or network connection."""

    def run(self, task: Task) -> Output:
        """Produce the demo answer."""
        return Output("4")


def verify(task: Task, output: Output) -> Check:
    """Check exact arithmetic output independently of the participant."""
    return Check(output.text == str(2 + 2), "Exact comparison against 2 + 2")


def main() -> None:
    """Print a JSON receipt for a deterministic, independently checked task."""
    task = Task("demo-1", "Compute 2 + 2", ("Return the exact integer",))
    print(
        json.dumps(asdict(run(task, "deterministic-demo", DemoParticipant(), verify)))
    )


if __name__ == "__main__":
    from .cli import main as cli_main
    raise SystemExit(cli_main())
