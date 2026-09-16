"""Code-grounded Python API documentation with optional author/reviewer callbacks.

This is static evidence, not a semantic correctness certificate. Project code
and generated examples are never executed. Callbacks are trusted caller code.
"""

import ast
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Callable
from urllib.parse import quote


@dataclass(frozen=True)
class Source:
    path: str
    text: str
    sha256: str


@dataclass(frozen=True)
class Snapshot:
    module: str
    sources: tuple[Source, ...]


@dataclass(frozen=True)
class Claim:
    kind: str  # symbol, signature, or behavior
    symbol: str
    value: str
    path: str
    start: int
    end: int


@dataclass(frozen=True)
class Finding:
    claim: Claim
    status: str
    reason: str


@dataclass(frozen=True)
class Documentation:
    snapshot: Snapshot
    findings: tuple[Finding, ...]
    reviewer_notes: str | None = None

    @property
    def status(self) -> str:
        statuses = {finding.status for finding in self.findings}
        if 'refuted' in statuses:
            return 'refuted'
        return 'verified' if statuses == {'verified'} else 'unknown'

    def to_dict(self) -> dict:
        """Portable evidence; status applies only to the listed extracted claims."""
        return {
            'schema_version': 1, 'kind': 'documentation', 'status': self.status,
            'scope': 'Listed static API claims only; behavior is not certified',
            'module': self.snapshot.module,
            'sources': [{'path': s.path, 'sha256': s.sha256} for s in self.snapshot.sources],
            'findings': [asdict(f) for f in self.findings],
            'reviewer_notes': self.reviewer_notes,
        }

    def markdown(self) -> str:
        """Render structured claims, keeping unresolved statements visible."""
        lines = [f'# API: {_escape(self.snapshot.module)}', '',
                 'Scope: listed static API claims only. Behavior is not certified.', '']
        for finding in self.findings:
            claim = finding.claim
            target = quote(claim.path, safe='/')
            lines.extend([
                f'## {_escape(claim.symbol)}', '',
                f'{_escape(claim.value)}', '',
                f'**{finding.status}** — {_escape(finding.reason)}', '',
                f'Source: [{_escape(claim.path)}:{claim.start}–{claim.end}]'
                f'({target}#L{claim.start}-L{claim.end})', '',
            ])
        if self.reviewer_notes is not None:
            lines.extend(['## Reviewer notes (advisory, unverified)', '',
                          _escape(self.reviewer_notes), ''])
        return '\n'.join(lines)


def _escape(text: str) -> str:
    for char in ('\\', '`', '*', '_', '[', ']', '<', '>', '#', '!'):
        text = text.replace(char, '\\' + char)
    return text


def _path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError('Source paths must be nonempty and relative to project_root')
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError('Source escapes project_root')
    return candidate


def snapshot(project_root: Path, module: str, tests: tuple[str, ...] = ()) -> Snapshot:
    """Read explicitly selected UTF-8 Python files without importing them."""
    root = Path(project_root).resolve()
    sources = []
    for relative in dict.fromkeys((module, *tests)):
        path = _path(root, relative)
        if path.suffix != '.py':
            raise ValueError('This increment supports Python source files only')
        raw = path.read_bytes()
        if len(raw) > 1_000_000:
            raise ValueError('Source exceeds 1 MB limit')
        text = raw.decode('utf-8')
        ast.parse(text, filename=relative)
        sources.append(Source(relative, text, hashlib.sha256(raw).hexdigest()))
    return Snapshot(module, tuple(sources))


def _symbols(source: Source) -> dict:
    """Inventory top-level public declarations; methods/re-exports are out of scope."""
    result = {}
    for node in ast.parse(source.text).body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if node.name.startswith('_'):
            continue
        if node.name in result:
            raise ValueError(f'Ambiguous duplicate declaration: {node.name}')
        signature = None
        if not isinstance(node, ast.ClassDef):
            prefix = 'async def' if isinstance(node, ast.AsyncFunctionDef) else 'def'
            signature = f'{prefix} {node.name}({ast.unparse(node.args)})'
            if node.returns:
                signature += f' -> {ast.unparse(node.returns)}'
        result[node.name] = (node.lineno, node.end_lineno, signature)
    return result


def api_claims(evidence: Snapshot) -> tuple[Claim, ...]:
    """Deterministic default author; no guessed behavior or copied docstrings."""
    source = next(s for s in evidence.sources if s.path == evidence.module)
    return tuple(
        Claim('signature' if signature else 'symbol', name,
              signature or name, source.path, start, end)
        for name, (start, end, signature) in _symbols(source).items()
    )


def check_claim(evidence: Snapshot, claim: Claim) -> Finding:
    """Check the named proposition, never arbitrary prose attached to a symbol."""
    if not isinstance(claim, Claim):
        raise TypeError('Authors must return Claim objects')
    if any(not isinstance(v, str) or not v.strip()
           for v in (claim.kind, claim.symbol, claim.value, claim.path)):
        raise ValueError('Claim text fields must be nonempty strings')
    source = next((s for s in evidence.sources if s.path == claim.path), None)
    valid_range = (source is not None and type(claim.start) is int and
                   type(claim.end) is int and
                   1 <= claim.start <= claim.end <= len(source.text.splitlines()))
    if not valid_range:
        return Finding(claim, 'refuted', 'Citation is outside the selected source snapshot')
    if claim.kind not in ('symbol', 'signature'):
        return Finding(claim, 'unknown', 'Source citation alone does not establish this claim')
    if claim.path != evidence.module:
        return Finding(claim, 'unknown', 'API checks apply only to the selected module')
    declaration = _symbols(source).get(claim.symbol)
    if declaration is None:
        return Finding(claim, 'refuted', 'No matching top-level public declaration')
    start, end, signature = declaration
    if not claim.start <= start <= end <= claim.end:
        return Finding(claim, 'refuted', 'Citation does not cover the declaration')
    expected = claim.symbol if claim.kind == 'symbol' else signature
    if expected is None:
        return Finding(claim, 'unknown', 'Class call signatures are not inferred')
    if claim.value != expected:
        return Finding(claim, 'refuted', 'Claim differs from the static declaration')
    return Finding(claim, 'verified', 'Matches static declaration; runtime behavior unchecked')


def generate(
    project_root: Path,
    module: str,
    *,
    tests: tuple[str, ...] = (),
    author: Callable[[Snapshot], tuple[Claim, ...]] = api_claims,
    reviewer: Callable[[Snapshot, tuple[Finding, ...]], str] | None = None,
) -> Documentation:
    """Coordinate one author and optional advisory reviewer with no implicit retries.

    Injected model adapters own their provider authorization/budgets. Exceptions
    propagate; a failed author/reviewer never returns a successful document.
    """
    evidence = snapshot(project_root, module, tests)
    claims = author(evidence)
    if not isinstance(claims, tuple) or len(claims) > 1000:
        raise ValueError('Author must return a tuple of at most 1000 claims')
    findings = tuple(check_claim(evidence, claim) for claim in claims)
    notes = reviewer(evidence, findings) if reviewer is not None else None
    if reviewer is not None and (not isinstance(notes, str) or not notes.strip()):
        raise ValueError('Reviewer must return nonempty advisory text')
    return Documentation(evidence, findings, notes)


def changed_sources(project_root: Path, document: Documentation) -> tuple[str, ...]:
    """Return changed/missing selected sources; does not track transitive imports."""
    root = Path(project_root).resolve()
    changed = []
    for source in document.snapshot.sources:
        try:
            actual = hashlib.sha256(_path(root, source.path).read_bytes()).hexdigest()
        except (OSError, ValueError):
            actual = None
        if actual != source.sha256:
            changed.append(source.path)
    return tuple(changed)


def main() -> None:
    """Print a deterministic documentation/evidence bundle without paid calls."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('module', help='Python module path relative to root')
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--test', action='append', default=[])
    args = parser.parse_args()
    document = generate(args.root, args.module, tests=tuple(args.test))
    print(json.dumps({'markdown': document.markdown(), 'receipt': document.to_dict()}, indent=2))


if __name__ == '__main__':
    main()
