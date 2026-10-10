"""Extract the documented journeys: fenced blocks tagged ``<!-- journey: NAME -->``.

A tag sits on the line directly above a fenced block in one of ``SOURCES``.
The block is then a journey that
``tests/test_cold_start_journey.py`` runs as written, placeholders substituted,
so a documented command that stops working fails CI (first-run journey, R6).
Shell blocks yield one command per logical line: backslash continuations are
joined and ``#`` comment lines dropped. Other blocks yield their text whole.

``python scripts/doc_journeys.py`` lists every tagged block and its commands.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ('README.md', 'docs/cli-guide.md', 'docs/first-repair-1.3.0.md')
TAG = re.compile(r'^<!-- journey: ([a-z0-9-]+) -->$')
FENCE = re.compile(r'^(`{3,})(\w*)\s*$')
SHELLS = ('sh', 'bash', 'shell', 'console', '')


def blocks(text, source='<text>'):
    """Every tagged block in ``text`` as ``{name: {'language', 'body', 'source', 'line'}}``.

    A tag not followed by a fence, an unclosed fence or a name used twice is
    refused: a journey the test silently stops finding is the failure this
    module exists to prevent.
    """
    lines = text.splitlines()
    found = {}
    index = 0
    while index < len(lines):
        tag = TAG.match(lines[index].strip())
        if not tag:
            index += 1
            continue
        name, line = tag.group(1), index + 1
        fence = FENCE.match(lines[index + 1]) if index + 1 < len(lines) else None
        if not fence:
            raise ValueError(f'{source}:{line}: journey tag {name!r} is not directly above a fenced block')
        end = next((i for i in range(index + 2, len(lines)) if lines[i].rstrip() == fence.group(1)), None)
        if end is None:
            raise ValueError(f'{source}:{line}: journey {name!r} has no closing fence')
        if name in found:
            raise ValueError(f'{source}:{line}: journey {name!r} is already tagged at line {found[name]["line"]}')
        found[name] = {'language': fence.group(2), 'body': '\n'.join(lines[index + 2:end]) + '\n',
                       'source': source, 'line': line}
        index = end + 1
    return found


def commands(block):
    """The logical command lines of a shell block; the whole body of any other."""
    if block['language'] not in SHELLS:
        return [block['body']]
    result, pending = [], ''
    for raw in block['body'].splitlines():
        stripped = raw.strip()
        if not pending and (not stripped or stripped.startswith('#')):
            continue
        if stripped.endswith('\\'):
            pending += stripped[:-1].rstrip() + ' '
            continue
        result.append(pending + stripped)
        pending = ''
    if pending:
        raise ValueError(f'{block["source"]}:{block["line"]}: the last command ends in a continuation')
    return result


def substitute(command, table):
    """Replace every placeholder in ``command`` from ``table``; refuse one left over.

    Placeholders are the literal spellings the documentation uses, such as
    ``/path/to/repo`` or ``<preview-checkpoint>``. Longer keys are replaced
    first, so ``/path/to/repo`` never eats the start of ``/path/to/repo-two``.
    """
    for key in sorted(table, key=len, reverse=True):
        command = command.replace(key, table[key])
    leftover = re.findall(r'<[a-z][a-z0-9-]*>|/path/[\w./-]*', command)
    if leftover:
        raise ValueError(f'unsubstituted placeholder {leftover[0]!r} in: {command}')
    return command


def journeys(root=ROOT):
    """Every tagged block across the documentation sources."""
    found = {}
    for source in SOURCES:
        for name, block in blocks((root / source).read_text(encoding='utf-8'), source).items():
            if name in found:
                raise ValueError(f'{source}:{block["line"]}: journey {name!r} is already tagged in {found[name]["source"]}')
            found[name] = block
    return found


if __name__ == '__main__':
    listing = {name: {**block, 'commands': commands(block)} for name, block in journeys().items()}
    json.dump(listing, sys.stdout, indent=2)
    print()
