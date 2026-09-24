"""The command line's surface as data, read from the parsers themselves.

``surface()`` walks the parser ``cli.build_parser`` returns and records, for
the program and for every verb and subcommand, the positional arguments, the
required options, the mutually exclusive groups that require one member, and
every option string. ``tests/fixtures/compatibility/surface.json`` holds the
committed form and ``docs/compatibility.md`` its table, kept in step by
``tests/test_compatibility_surface.py`` the way the envelope page is; a change
to either is a deliberate diff (the interface freeze, 4.1; D27.1). Exit codes
are behaviour, not parser data: the envelope table pins them, row by row.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import argparse


def _subcommands(parser: argparse.ArgumentParser):
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    return None


def _long(action: argparse.Action) -> str:
    return sorted(action.option_strings, key=len)[-1]


def describe(parser: argparse.ArgumentParser) -> dict:
    """One parser: its positionals, required options, one-of groups, options and subcommands."""
    commands = _subcommands(parser)
    positionals: list[str] = []
    required: list[str] = []
    options: list[str] = []
    for action in parser._actions:
        if action is commands or isinstance(action, argparse._HelpAction):
            continue
        if action.option_strings:
            options.extend(action.option_strings)
            if action.required:
                required.append(_long(action))
        else:
            positionals.append(action.dest)
    one_of = sorted(
        sorted(_long(action) for action in group._group_actions)
        for group in parser._mutually_exclusive_groups
        if group.required
    )
    entry: dict = {
        "positionals": positionals,
        "required_options": sorted(required),
        "one_of": one_of,
        "options": sorted(options),
    }
    if commands is not None:
        entry["subcommands"] = {name: describe(sub) for name, sub in sorted(commands.choices.items())}
    return entry


def surface() -> dict:
    """The whole command line, as the compatibility fixture stores it."""
    from .cli import build_parser

    top = describe(build_parser())
    return {
        "schema_version": 1,
        "program": "attune-harness",
        "options": top["options"],
        "verbs": top["subcommands"],
    }


def _tree(entry: dict) -> str:
    subs = entry.get("subcommands") or {}
    return " ".join(
        name + (f"({_tree(sub)})" if sub.get("subcommands") else "") for name, sub in subs.items()
    )


def rows(value: dict) -> list[str]:
    """The Markdown rows of the verb table in ``docs/compatibility.md``."""
    out = []
    for verb, entry in value["verbs"].items():
        subs = _tree(entry) or "-"
        positionals = " ".join(f"`{name}`" for name in entry["positionals"]) or "-"
        parts = [f"`{option}`" for option in entry["required_options"]]
        parts += ["one of " + ", ".join(f"`{option}`" for option in group) for group in entry["one_of"]]
        out.append(f"| `{verb}` | {subs} | {positionals} | {' '.join(parts) or '-'} |")
    return out
