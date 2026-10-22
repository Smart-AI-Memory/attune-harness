"""Fail when a Markdown link is dead, or when a document has no row in the index.

Every tracked ``*.md`` file is read. Local inline and reference links to
Markdown or source files must resolve to tracked files. Markdown fragments
must name a heading or explicit HTML anchor; source fragments must name an
existing line or ordered line range (``L12`` or ``L12-L20``). Markdown source
line links require ``?plain=1``. Absolute URLs
and receipt/artifact formats such as JSON, XML and wheels are not checked.
A target that starts with ``/``
is taken from the repository root. A target that exists on disk but is not
tracked is reported as such: ``git add`` it, or the published tree will not
have it.

Every tracked ``docs/**/*.md`` other than the index itself must be linked
from ``docs/README.md``, so a new document cannot land unindexed.

The root README is also rendered on PyPI, where repository-relative links
resolve under ``pypi.org/project/attune-harness/`` and fail. Its Markdown
links must therefore be absolute HTTP(S) URLs or same-page anchors.

``scripts/known_dead_links.txt`` lists the targets that were already dead when
this check began, one per line. A link to one of them does not fail. The list
may only shrink: a listed target that now exists, or that nothing links to any
more, fails the check, so the list cannot go stale. Remove the line when the
link is fixed or cut.

``historical_link_exceptions.txt`` records newly exposed historical defects as
``document<TAB>target`` pairs. Exceptions apply only to that document and exact
URL, permit one original occurrence, must still fail validation, and must still
occur. Do not add new broken
links to this inventory. Original historical documents stay unchanged.

Exit 0 when nothing is wrong, 1 otherwise, with every finding on its own line
as ``file:line: target`` or ``docs/README.md: no row for <path>``. Run from
the repository root: ``python scripts/check_doc_links.py``.
"""

from __future__ import annotations

import html
from html.parser import HTMLParser
import posixpath
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

LINK = re.compile(r'(?<!\\)\[((?:[^\[\]\n]|\[[^\[\]\n]*\])*)\]\(\s*'
                  r'(<[^>\n]*>|(?:\\.|[^\s()\\]|\([^()\n]*\))+)'
                  r'(?:\s+[\"\'][^\n]*?[\"\'])?\s*\)')
REFERENCE = re.compile(r'^ {0,3}\[([^\]\n]+)\]:\s*(<[^>\n]*>|\S+)', re.MULTILINE)
REFERENCE_USE = re.compile(r'(?<!\\)\[([^\]\n]+)\](?:\[([^\]\n]*)\])?')
KNOWN_NAME = "known_dead_links.txt"
HISTORICAL_NAME = "historical_link_exceptions.txt"
INDEX = "docs/README.md"
SOURCE_SUFFIXES = {'.py', '.pyi', '.js', '.jsx', '.cjs', '.mjs', '.ts', '.tsx',
                   '.sh', '.bash', '.ps1', '.yml', '.yaml', '.toml', '.c', '.h',
                   '.cpp', '.rs', '.go'}


def visible(text: str) -> str:
    """Mask comments and fenced/indented code, preserving source line numbers."""
    result = []
    fence = None
    comment = False
    for line in text.splitlines(keepends=True):
        quote = re.match(r'^(?: {0,3}> ?)+', line)
        depth = quote[0].count('>') if quote else 0
        content = line[quote.end():] if quote else line
        if fence is not None and depth != fence[1]:
            fence = None
        content = re.sub(r'^ {0,3}(?:[-+*]|\d+[.)]) ', '', content)
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', content)
        hidden = fence is not None
        if fence is not None:
            if (marker and marker[1][0] == fence[0][0]
                    and len(marker[1]) >= len(fence[0]) and not marker[2].strip()):
                fence = None
        elif marker and not comment:
            fence = marker[1], depth
            hidden = True
        elif not comment and content.startswith(('    ', '\t')):
            hidden = True
        if hidden:
            result.append(re.sub(r'[^\n]', ' ', line))
            continue
        # Comments inside code examples are literal text. Conversely, a fence
        # marker inside an actual HTML comment cannot hide the following page.
        candidates = inline_code_mask(line)
        pieces = []
        position = 0
        while position < len(line):
            if comment:
                end = line.find('-->', position)
                stop = len(line) if end < 0 else end + 3
                pieces.append(re.sub(r'[^\n]', ' ', line[position:stop]))
                position = stop
                comment = end < 0
            else:
                start = candidates.find('<!--', position)
                if start < 0:
                    pieces.append(line[position:])
                    break
                pieces.append(line[position:start])
                position = start
                comment = True
        result.append(''.join(pieces))
    return ''.join(result)


def inline_code_mask(text: str) -> str:
    return re.sub(r'(`+)(?!`)(.*?)(?<!`)\1(?!`)',
                  lambda m: re.sub(r'[^\n]', ' ', m[0]), text, flags=re.DOTALL)


def destinations(text: str):
    """Yield line/URL pairs for rendered inline and defined reference links."""
    text = inline_code_mask(visible(text))
    references = {}
    for match in REFERENCE.finditer(text):
        references.setdefault(re.sub(r'\s+', ' ', match[1]).casefold(), match[2].strip('<>'))
    spans = []
    for match in LINK.finditer(text):
        spans.append(match.span())
        yield text.count('\n', 0, match.start()) + 1, html.unescape(match[2].strip('<>'))
    for match in REFERENCE_USE.finditer(text):
        if any(start <= match.start() < end for start, end in spans):
            continue
        # A definition is not itself a rendered link.
        if text[match.end():].startswith(':'):
            continue
        key = re.sub(r'\s+', ' ', match[2] or match[1]).casefold()
        if key in references:
            yield text.count('\n', 0, match.start()) + 1, html.unescape(references[key])


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values = set()

    def handle_starttag(self, tag, attributes):
        for name, value in attributes:
            if value and (name == 'id' or tag == 'a' and name == 'name'):
                self.values.add(value)


def heading_ids(text: str) -> set[str]:
    """GitHub-style ATX/Setext headings plus explicit HTML IDs/named anchors.

    See GitHub Docs, Basic writing and formatting syntax, Section links.
    Custom anchors do not participate in automatic duplicate numbering.
    """
    text = visible(text)
    parser = Anchors()
    parser.feed(inline_code_mask(text))
    result = parser.values
    automatic = set()
    previous = ''
    for line in text.splitlines():
        line = re.sub(r'^ {0,3}(?:> ?)+', '', line)
        match = re.match(r'^ {0,3}#{1,6}(?:[ \t]+(.*)|$)', line)
        title = None
        if match:
            title = re.sub(r'[ \t]+#+[ \t]*$', '', match[1] or '')
        elif previous.strip() and re.fullmatch(r' {0,3}(?:=+|-+)[ \t]*', line):
            title = previous.strip()
        if title is not None:
            title = re.sub(r'!?\[([^\]]*)\]\([^)]*\)', r'\1', title)
            title = re.sub(r'<[^>]*>', '', title)
            title = re.sub(r'(`+)(.*?)\1', r'\2', title)
            title = re.sub(r'\*+(.*?)\*+|(?<!\w)_+(.*?)_+(?!\w)|~~(.*?)~~',
                           lambda m: next(g for g in m.groups() if g is not None), title)
            title = html.unescape(title).strip().lower()
            base = re.sub(r'[^\w -]', '', title).replace(' ', '-')
            anchor = base
            number = 0
            while anchor in automatic:
                number += 1
                anchor = f'{base}-{number}'
            automatic.add(anchor)
            result.add(anchor)
        previous = line if title is None else ''
    return result


def local_target(document: str, raw: str):
    raw = re.sub(r'\\([\\`*{}\[\]()#+\-.!_>])', r'\1', raw)
    url = urlsplit(raw)
    source_colon = Path(url.scheme).suffix in SOURCE_SUFFIXES
    if url.netloc or url.scheme and not source_colon:
        return None
    path = unquote(raw.split('#', 1)[0].split('?', 1)[0] if source_colon else url.path)
    # A colon line suffix is not GitHub syntax; still recognize its source type
    # so a broken ``file.py:12`` is not silently skipped.
    suffix = Path(re.sub(r':\d+(?:-\d+)?$', '', path)).suffix
    if path and suffix not in SOURCE_SUFFIXES | {'.md'}:
        return None
    target = (posixpath.normpath(path[1:] if path.startswith('/') else
                               posixpath.join(posixpath.dirname(document), path))
              if path else document)
    return target, unquote(url.fragment)


def tracked(root: Path) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"], capture_output=True, check=True
    ).stdout
    return [p.decode("utf-8") for p in out.split(b"\0") if p]


def links(path: str, text: str):
    """Yield line, normalized target, fragment and original URL for local links."""
    for number, raw in destinations(text):
        target = local_target(path, raw)
        if target is not None:
            yield number, *target, raw


def check(root: Path) -> list[str]:
    files = tracked(root)
    present = set(files)
    KNOWN = root / "scripts" / KNOWN_NAME
    known = set()
    if KNOWN.exists():
        known = {
            line.strip()
            for line in KNOWN.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        }
    findings: list[str] = []
    historical_path = root / 'scripts' / HISTORICAL_NAME
    historical = set()
    if historical_path.exists():
        for row in historical_path.read_text(encoding='utf-8').splitlines():
            if row.strip() and not row.startswith('#'):
                pair = row.split('\t')
                if len(pair) != 2 or not all(pair):
                    findings.append(f'{HISTORICAL_NAME}: expected document<TAB>target: {row}')
                elif tuple(pair) in historical:
                    findings.append(f'{HISTORICAL_NAME}: duplicate exception: {row}')
                else:
                    historical.add(tuple(pair))
    seen_historical = set()
    seen_known: set[str] = set()
    indexed: set[str] = set()
    anchors = {}
    lines = {}
    for path in sorted(files):
        if not path.endswith(".md"):
            continue
        text = (root / path).read_text(encoding="utf-8", errors="replace")
        if path == "README.md":
            for number, target in destinations(text):
                if not target.startswith(("https://", "http://", "#", "mailto:")):
                    findings.append(f"{path}:{number}: link will not resolve on PyPI: {target}")
        for number, target, fragment, raw in links(path, text):
            if path == INDEX:
                indexed.add(target)
            problem = None
            if target not in present and target in known:
                seen_known.add(target)
                continue
            if target not in present:
                hint = " (exists on disk but is untracked; git add it)" if (root / target).exists() else ""
                problem = f'dead link to {target}{hint}'
            elif fragment:
                plain = parse_qs(urlsplit(raw).query).get('plain') == ['1']
                if target.endswith('.md') and not plain:
                    if target not in anchors:
                        anchors[target] = heading_ids((root / target).read_text(encoding='utf-8', errors='replace'))
                    if fragment not in anchors[target]:
                        problem = f'unknown heading or anchor: {target}#{fragment}'
                else:
                    match = re.fullmatch(r'L([1-9]\d*)(?:-L([1-9]\d*))?', fragment)
                    if target not in lines:
                        content = (root / target).read_bytes()
                        lines[target] = content.count(b'\n') + int(bool(content) and not content.endswith(b'\n'))
                    if not match or not 1 <= int(match[1]) <= int(match[2] or match[1]) <= lines[target]:
                        problem = f'invalid source line fragment: {target}#{fragment}'
            if problem:
                if (path, raw) in historical and (path, raw) not in seen_historical:
                    seen_historical.add((path, raw))
                else:
                    findings.append(f'{path}:{number}: {problem}')
    for source, target in sorted(historical - seen_historical):
        findings.append(f'{HISTORICAL_NAME}: exception is resolved or unused: {source}\t{target}; remove it')
    for target in sorted(known):
        if target in present:
            findings.append(f"{KNOWN.name}: {target} exists now; remove it from the list")
        elif target not in seen_known:
            findings.append(f"{KNOWN.name}: nothing links to {target} any more; remove it from the list")
    if INDEX in present:
        for path in sorted(files):
            if path.startswith("docs/") and path.endswith(".md") and path != INDEX and path not in indexed:
                findings.append(f"{INDEX}: no row for {path}")
    return findings


def repository_root() -> Path:
    """The repository that contains the working directory, else this file's."""
    probe = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if probe.returncode == 0 and probe.stdout.strip():
        return Path(probe.stdout.strip())
    return Path(__file__).resolve().parents[1]


def main() -> int:
    root = repository_root()
    findings = check(root)
    for line in findings:
        print(line)
    if findings:
        print(f"{len(findings)} problem(s)", file=sys.stderr)
        return 1
    print("checked Markdown/source links resolve and every document has an index row")
    return 0


if __name__ == "__main__":
    sys.exit(main())
