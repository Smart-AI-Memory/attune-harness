"""The Python API documented in the CLI guide, run as written and pinned by name and parameters (4.1; D27.4).

Seven public names: ``run``, ``Task``, ``Output``, ``Check``, ``Receipt``,
``Status`` and ``Participant``. The CLI guide's checks-and-receipts example runs
unchanged, as a script; its two documented variants reject and fail; ``run``
calls the participant exactly once; and the names' parameters and defaults
match ``tests/fixtures/compatibility/public_api.txt``, a deliberate diff to
change. Annotation text is not compared, since Python versions render it
differently.
"""

# qualify: platform

import contextlib
import inspect
import io
import re
import runpy
from pathlib import Path

import pytest

import attune_harness
from attune_harness import Check, Output, Participant, Status, Task, run

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "cli-guide.md"
SNAPSHOT = ROOT / "tests" / "fixtures" / "compatibility" / "public_api.txt"
NAMES = ("run", "Task", "Output", "Check", "Receipt")


def guide_example():
    section = re.search(
        r"^## Checks and receipts\n(.*?)(?=^## |\Z)",
        GUIDE.read_text(encoding="utf-8"),
        re.M | re.S,
    )
    assert section, "the CLI guide must document checks and receipts"
    match = re.search(r"```python\n(.*?)```", section.group(1), re.S)
    assert match, "the checks-and-receipts section must contain the Python example"
    return match.group(1)


def run_example(source, directory):
    """Run the example as a script from a file, the way a reader would, capturing its output."""
    script = directory / "guide_example.py"
    script.write_text(source, encoding="utf-8")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        namespace = runpy.run_path(str(script), run_name="__main__")
    return namespace, out.getvalue().strip()


def test_the_guide_example_runs_as_written(tmp_path):
    namespace, out = run_example(guide_example(), tmp_path)
    assert out == "verified"
    assert namespace["receipt"].status is Status.VERIFIED
    assert namespace["receipt"].check.evidence == "Compared with independent arithmetic"


def test_the_guide_variants_reject_and_fail(tmp_path):
    source = guide_example()
    assert 'return Output("4")' in source
    _, out = run_example(source.replace('return Output("4")', 'return Output("5")'), tmp_path)
    assert out == "rejected"
    namespace, out = run_example(source.replace('return Output("4")', 'raise RuntimeError("no worker")'), tmp_path)
    assert out == "failed"
    assert namespace["receipt"].error == "participant: RuntimeError: no worker"


def test_run_calls_the_participant_once_and_never_retries():
    calls = []

    class Worker:
        def run(self, task):
            calls.append(task.task_id)
            return Output("4")

    def bad_check(task, output):
        raise ValueError("bad check")

    task = Task("addition", "Compute 2 + 2", ("Return the integer result",))
    rejected = run(task, "worker", Worker(), lambda t, o: Check(False, "always rejected"))
    failed = run(task, "worker", Worker(), bad_check)
    assert rejected.status is Status.REJECTED and failed.status is Status.FAILED
    assert failed.error == "verification: ValueError: bad check" and failed.output == Output("4")
    assert calls == ["addition", "addition"]


# Values tried against Task.schema_version; the snapshot records which are accepted, computed, not written.
SCHEMA_CANDIDATES = (0, 1, 2, 3, True, 1.0, "1", None)


def _accepts(value):
    try:
        Task("t", "objective", ("requirement",), schema_version=value)
    except (ValueError, TypeError):
        return False
    return True


def signature(obj):
    parts = []
    for parameter in inspect.signature(obj).parameters.values():
        default = "" if parameter.default is inspect.Parameter.empty else f"={parameter.default!r}"
        parts.append(parameter.name + default)
    return "(" + ", ".join(parts) + ")"


def snapshot():
    lines = [f"{name}{signature(getattr(attune_harness, name))}" for name in NAMES]
    lines.append(f"Participant.run{signature(Participant.run)}")
    lines.append("Status: " + ", ".join(f"{member.name}={member.value}" for member in Status))
    accepted = [repr(value) for value in SCHEMA_CANDIDATES if _accepts(value)]
    lines.append("Task.schema_version accepts: " + ", ".join(accepted))
    return "\n".join(lines) + "\n"


def test_the_seven_public_names_keep_their_parameters():
    assert snapshot() == SNAPSHOT.read_text(encoding="utf-8"), (
        "a public name's parameters changed; if that is deliberate, rewrite "
        "tests/fixtures/compatibility/public_api.txt and add a changelog line"
    )


@pytest.mark.parametrize("value", [0, 2, 3, True, 1.0, "1", None])
def test_task_schema_version_is_fixed_at_one(value):
    """Only the integer 1 (second review of #124, N2: the test tried 2 alone)."""
    with pytest.raises(ValueError, match="unsupported schema_version"):
        Task("t", "objective", ("requirement",), schema_version=value)
    assert Task("t", "objective", ("requirement",)).schema_version == 1
