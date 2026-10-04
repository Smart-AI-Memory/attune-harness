"""The command line's surface is data, committed and documented (the interface freeze, 4.1; D27.1).

``attune_harness.cli_surface`` reads the parsers ``cli.build_parser`` returns;
``tests/fixtures/compatibility/surface.json`` is the committed form, including
each argument's choices and default, and the
verb table in ``docs/compatibility.md`` its rendering. A verb, subcommand,
positional or required option added, renamed or dropped fails here until the
fixture is rewritten on purpose and the page follows, the way the envelope
table works. Exit codes are pinned by the envelope table, not here.
"""

# qualify: platform

import json
import re
from pathlib import Path

import pytest

from attune_harness.cli import main
from attune_harness.cli_surface import rows, surface

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "compatibility" / "surface.json"
DOC = ROOT / "docs" / "compatibility.md"
START, END = "<!-- surface-rows -->", "<!-- /surface-rows -->"


def test_the_surface_matches_the_committed_file():
    committed = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert surface() == committed, (
        "the command line's surface changed; if that is deliberate, run "
        "scripts/compatibility_surface.py --write tests/fixtures/compatibility/surface.json, "
        "regenerate the table in docs/compatibility.md with --rows, and add a changelog line"
    )


def test_the_verbs_and_the_journey_are_all_there():
    value = surface()
    verbs = value["verbs"]
    assert len(verbs) == 32
    assert {"init", "plan", "build", "review", "fix", "test", "status", "resume"} <= set(verbs)
    assert value["options"] == ["--help-all"]
    assert set(verbs["extension"]["subcommands"]) == {
        "disable", "discover", "enable", "inspect", "install", "remove", "replace"
    }
    assert set(verbs["index"]["subcommands"]) == {"build", "inspect", "plan", "update"}
    memory = verbs["memory"]["subcommands"]
    assert set(memory["redis"]["subcommands"]) == {"digest", "node", "related", "search", "status"}
    assert set(memory["scratch"]["subcommands"]) == {"capabilities", "forget", "keys", "retrieve", "stash"}


def test_a_positional_records_whether_it_is_required():
    """An optional positional made required is a new required argument (second review of #124, S1)."""
    verbs = surface()["verbs"]
    assert verbs["review"]["positionals"] == [{"name": "request", "nargs": "?"}]
    keys = verbs["memory"]["subcommands"]["scratch"]["subcommands"]["keys"]
    assert keys["positionals"] == [{"name": "pattern", "nargs": "?"}]
    assert verbs["status"]["positionals"] == [{"name": "task_dir", "nargs": None}]
    assert "| `review` | - | `[request]` |" in "\n".join(rows(surface()))


def test_an_arity_the_surface_cannot_render_is_refused_not_shown_wrongly():
    """Review of #124's fixes (Claude Sonnet 5): REMAINDER or a count must fail loud."""
    import argparse
    from attune_harness.cli_surface import describe
    for nargs in (argparse.REMAINDER, 2):
        parser = argparse.ArgumentParser()
        parser.add_argument("rest", nargs=nargs)
        with pytest.raises(ValueError, match="does not describe positional 'rest'"):
            describe(parser)
    parser = argparse.ArgumentParser()
    parser.add_argument("many", nargs="*")
    parser.add_argument("some", nargs="+")
    assert [p["nargs"] for p in describe(parser)["positionals"]] == ["*", "+"]


def test_choices_and_defaults_are_pinned_with_argument_identity(tmp_path, monkeypatch):
    import argparse
    from pathlib import Path
    from attune_harness.cli_surface import describe

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("safe", "fast"), default="safe")
    parser.add_argument("--config", type=Path, default=Path("participants.json"))
    before = describe(parser)["arguments"]
    assert before == [
        {"name": "config", "option_strings": ["--config"], "choices": None,
         "default": {"kind": "path", "value": "participants.json"}},
        {"name": "mode", "option_strings": ["--mode"], "choices": ["safe", "fast"],
         "default": "safe"},
    ]
    parser._option_string_actions["--mode"].choices = ("safe",)
    assert describe(parser)["arguments"] != before
    parser._option_string_actions["--mode"].choices = ("safe", "fast")
    parser._option_string_actions["--mode"].default = "fast"
    assert describe(parser)["arguments"] != before
    monkeypatch.chdir(tmp_path)
    assert describe(parser)["arguments"][0]["default"] == {"kind": "path", "value": "participants.json"}


def test_dynamic_project_default_is_cwd_without_masking_fixed_absolute_path(tmp_path, monkeypatch):
    import argparse
    from pathlib import Path
    from attune_harness.cli_surface import describe, surface

    original = surface()
    monkeypatch.chdir(tmp_path)
    assert surface() == original
    intake = original["verbs"]["spec"]["subcommands"]["intake"]
    project = next(item for item in intake["arguments"] if item["name"] == "project")
    assert project["default"] == {"kind": "cwd"}

    fixed_path = tmp_path / "fixed-project"
    fixed = argparse.ArgumentParser()
    fixed.add_argument("--project", type=Path, default=fixed_path)
    value = next(item for item in describe(fixed, command_path=("spec", "intake"))["arguments"]
                 if item["name"] == "project")
    assert value["default"] == {"kind": "path", "value": str(fixed_path)}


def test_documented_surface_matches():
    if not DOC.is_file():
        pytest.skip("docs/compatibility.md is not part of this checkout")
    text = DOC.read_text(encoding="utf-8")
    assert text.count(START) == 1 and text.count(END) == 1, "the page keeps its generated block markers"
    block = text.split(START, 1)[1].split(END, 1)[0]
    documented = [line for line in block.splitlines() if line.startswith("| `")]
    assert documented == rows(surface()), (
        "docs/compatibility.md's verb table must equal `scripts/compatibility_surface.py --rows`"
    )


def test_help_all_names_every_verb(capsys):
    with pytest.raises(SystemExit) as stop:
        main(["--help-all"])
    assert stop.value.code == 0
    out = capsys.readouterr().out
    for verb in surface()["verbs"]:
        assert re.search(rf"^  {re.escape(verb)}\s", out, re.M), f"{verb} is missing from --help-all"
