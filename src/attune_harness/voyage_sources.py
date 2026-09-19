"""Deterministic, bounded application source selection. No optional imports or uploads."""

import ast
import copy
import fnmatch
import hashlib
import re
import subprocess
from pathlib import Path

from .features import read_text
from .review_contract import bounded_text, digest, fields, parse_json, versioned

PROFILE = {'version': 1, 'embedding_model': 'voyage-code-4', 'dimensions': 1024,
           'rerank_model': 'rerank-2.5', 'chunker': 'source-byte-v1',
           'token_estimate': 'utf8-bytes-divided-by-4-v1', 'distance': 'cosine',
           'lexical': 'simple-no-stem-stop-fold-v1', 'fusion': 'rrf-60-v1', 'context_bytes': 512}
DEFAULTS = {'include': ['**/*.py', '**/*.md'], 'exclude': [],
            'allow_overlays': False, 'allow_untracked': False, 'max_files': 1000,
            'max_bytes': 16 * 1024 * 1024, 'max_file_bytes': 262144,
            'passage_bytes': 2000, 'candidates': 50, 'batch_size': 32,
            'max_provider_calls': 128, 'max_request_bytes': 262144}
SUFFIXES = {'.py', '.md', '.ts', '.tsx', '.js', '.jsx', '.go', '.rs', '.java',
            '.c', '.h', '.cpp', '.css', '.html', '.sql', '.sh'}
STRUCTURED_SUFFIXES = {'.json', '.toml', '.yaml', '.yml', '.ini', '.cfg', '.xml', '.mod'}
EXCLUDED = {'.git', '.hg', '.svn', 'node_modules', '__pycache__', 'dist', 'build',
            '.attune-index', '.idea', '.vscode'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def identifier(value, name='identifier'):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value):
        raise ValueError(f'Invalid {name}')
    return value


def hex_digest(value):
    if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{64}', value):
        raise ValueError('Expected a SHA-256 digest')
    return value


def relative(value):
    bounded_text(value, 'relative path', 1024)
    if (Path(value).is_absolute() or '\\' in value or ':' in value or
            any(p in ('', '.', '..') for p in value.split('/'))):
        raise ValueError('Invalid relative source path')
    return value


def config(value, base: Path):
    if not isinstance(value, dict):
        raise ValueError('Retrieval config must be an object')
    fields(value, {'schema_version', 'roots', 'index_dir'} |
           (set(value) & (set(DEFAULTS) | {'structured_paths'})))
    versioned(value)
    result = {**copy.deepcopy(DEFAULTS), **copy.deepcopy(value)}
    roots = result['roots']
    if not isinstance(roots, list) or not 1 <= len(roots) <= 16:
        raise ValueError('Select 1..16 application repositories')
    resolved = []
    for root in roots:
        fields(root, ('repo_id', 'path'))
        identifier(root['repo_id'], 'repository ID')
        bounded_text(root['path'], 'repository root')
        resolved.append({'repo_id': root['repo_id'], 'path': str((base / root['path']).resolve())})
    if len({r['repo_id'] for r in resolved}) != len(roots) or len({r['path'] for r in resolved}) != len(roots):
        raise ValueError('Repository IDs and roots must be unique')
    result['roots'] = sorted(resolved, key=lambda r: r['repo_id'])
    bounded_text(result['index_dir'], 'index directory')
    index = base / result['index_dir']
    if index.is_symlink() or any(p in ('.git', '.hg', '.svn') for p in index.resolve().parts):
        raise ValueError('Index cannot be a symlink or repository metadata')
    result['index_dir'] = str(index.resolve())
    if any(Path(r['path']).is_relative_to(index.resolve()) for r in result['roots']):
        raise ValueError('Index directory cannot contain a selected repository root')
    for key in ('include', 'exclude'):
        if not isinstance(result[key], list) or len(result[key]) > 64:
            raise ValueError('File patterns must be bounded lists')
        for pattern in result[key]:
            bounded_text(pattern, 'file pattern', 256)
            if pattern.startswith('/') or '..' in pattern.split('/') or '\\' in pattern:
                raise ValueError('Patterns must be relative to selected repositories')
    for key in ('allow_overlays', 'allow_untracked'):
        if type(result[key]) is not bool:
            raise ValueError(f'{key} must be boolean')
    # Optional rather than defaulted: old accepted config digests must not change.
    structured = result.get('structured_paths', [])
    if not isinstance(structured, list) or len(structured) > 256:
        raise ValueError('Select at most 256 explicit structured file paths')
    for path in structured:
        bounded_text(path, 'structured path', 1024)
        relative(path)
        if any(c in path for c in '*?[]') or Path(path).suffix.lower() not in STRUCTURED_SUFFIXES:
            raise ValueError('Structured paths must name supported files, not globs')
        if any(p in EXCLUDED or p.startswith(('.venv', '.env')) for p in Path(path).parts):
            raise ValueError('Structured path selects an excluded directory or environment file')
    for key, low, high in (('max_files', 1, 1000), ('max_bytes', 1, 16777216),
                          ('max_file_bytes', 1, 1048576), ('passage_bytes', 128, 4000),
                          ('candidates', 1, 50), ('batch_size', 1, 32),
                          ('max_provider_calls', 0, 10000), ('max_request_bytes', 4096, 262144)):
        if type(result[key]) is not int or not low <= result[key] <= high:
            raise ValueError(f'{key} must be an integer in {low}..{high}')
    return result


def load_config(path):
    return config(parse_json(read_text(path, 131072)), path.resolve().parent)


def code_config(root: Path, index_dir: Path, *, repo_id='app', include_docs=False,
                structured_paths=()):
    """Prepare a repository-first selection without changing legacy defaults."""
    suffixes = SUFFIXES if include_docs else SUFFIXES - {'.md'}
    return config({'schema_version': 1, 'roots': [{'repo_id': repo_id, 'path': str(root.absolute())}],
                   'index_dir': str(index_dir.absolute()),
                   'include': ['**/*' + suffix for suffix in sorted(suffixes)],
                   'structured_paths': list(structured_paths)}, Path.cwd())


def git(root, *args):
    # Snapshot reads must not refresh .git/index when an overlay becomes clean.
    run = subprocess.run(['git', '--no-optional-locks', '-c', 'diff.autoRefreshIndex=false',
                          '-C', str(root), *args], capture_output=True, timeout=15)
    if run.returncode:
        raise ValueError('Selected source must be a readable Git repository with a HEAD revision')
    if len(run.stdout) > 8 * 1024 * 1024:
        raise ValueError('Git selection exceeds manifest bounds')
    return run.stdout


def matches(path, patterns):
    return any(fnmatch.fnmatchcase(path, p) or (p.startswith('**/') and fnmatch.fnmatchcase(path, p[3:]))
               for p in patterns)


def selected(path, cfg):
    parts = Path(path).parts
    source = Path(path).suffix.lower() in SUFFIXES and matches(path, cfg['include'])
    structured = path in cfg.get('structured_paths', [])
    return ((source or structured) and
            not any(p in EXCLUDED or p.startswith(('.venv', '.env')) for p in parts) and
            not matches(path, cfg['exclude']))


def source_bytes(root, path, limit):
    relative(path)
    target = root / path
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError('Source escapes selected repository')
    if any(p.is_symlink() for p in (target, *list(target.parents)[:len(Path(path).parts)-1])):
        raise ValueError('Source symlinks are unsupported')
    return read_text(target, limit).encode('utf-8')


def snapshot(cfg):
    repositories, files, content, total = [], [], {}, 0
    for item in cfg['roots']:
        root, repo = Path(item['path']), item['repo_id']
        if Path(git(root, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != root:
            raise ValueError('Source root must be the Git repository root')
        revision = git(root, 'rev-parse', 'HEAD').decode().strip()
        tracked = set(git(root, 'ls-files', '-z', '--cached').decode('utf-8').strip('\0').split('\0')) - {''}
        # name-only trusts stale index stat data when auto-refresh is disabled.
        # numstat compares content, including binary and mode-only changes.
        changes = git(root, 'diff', '--numstat', '-z', '--no-renames',
                      '--no-ext-diff', '--no-textconv', 'HEAD', '--')
        dirty = {entry.split(b'\t', 2)[2].decode('utf-8')
                 for entry in changes.split(b'\0') if entry}
        names = set(tracked)
        if cfg['allow_untracked']:
            names.update(git(root, 'ls-files', '-z', '--others', '--exclude-standard').decode('utf-8').strip('\0').split('\0'))
        repositories.append({'repo_id': repo, 'root': str(root), 'revision': revision})
        for path in sorted(names - {''}):
            if not selected(path, cfg):
                continue
            relative(path)
            if (root / path).resolve().is_relative_to(Path(cfg['index_dir'])):
                continue
            if path in dirty and not cfg['allow_overlays']:
                raise ValueError('Selected tracked source changed; explicitly allow_overlays before indexing')
            if not (root / path).exists() and not (root / path).is_symlink():
                continue  # An explicitly selected overlay may delete a tracked file.
            raw = source_bytes(root, path, cfg['max_file_bytes'])
            total += len(raw)
            if len(files) >= cfg['max_files'] or total > cfg['max_bytes']:
                raise ValueError('Selected corpus exceeds file/byte limits')
            entry = {'repo_id': repo, 'revision': revision, 'path': path, 'sha256': sha(raw),
                     'bytes': len(raw), 'selection': ('untracked' if path not in tracked else
                                                     'overlay' if path in dirty else 'tracked')}
            files.append(entry)
            content[(repo, path)] = raw
    manifest = {'repositories': repositories, 'files': files}
    return manifest, content


def chunks(raw, path, limit):
    """Split at language boundaries first, then lines/UTF-8 boundaries; never normalize."""
    text = raw.decode('utf-8')
    lines = text.splitlines(keepends=True)
    starts = {0: ('lines', '')}
    if path.endswith('.py'):
        try:
            tree = ast.parse(text)
            starts[0] = ('python-symbol', '')
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    line = min([node.lineno, *[d.lineno for d in node.decorator_list]]) - 1
                    starts[line] = ('python-symbol', node.name)
        except SyntaxError:
            starts[0] = ('python-lines-unparsed', '')
    elif path.endswith('.md'):
        starts[0] = ('markdown-section', '')
        fence = None
        for i, line in enumerate(lines):
            marker = re.match(r'^\s{0,3}(`{3,}|~{3,})', line)
            if marker:
                token = marker[1]
                if fence is None:
                    fence = token
                elif token[0] == fence[0] and len(token) >= len(fence):
                    fence = None
            elif fence is None and re.match(r'^#{1,6}\s', line):
                starts[i] = ('markdown-section', line.strip())
    offset, block, method, context = 0, b'', *starts[0]
    for i, line in enumerate(lines):
        if i in starts and block:
            yield offset - len(block), offset, block, method, context
            block = b''
        if i in starts:
            method, context = starts[i]
        remaining = line.encode('utf-8')
        if block and len(block) + len(remaining) > limit:
            yield offset - len(block), offset, block, method, context
            block = b''
        while len(remaining) > limit:
            end = limit
            while remaining[end] & 0xC0 == 0x80:
                end -= 1
            piece, remaining = remaining[:end], remaining[end:]
            yield offset, offset + len(piece), piece, method + '-split', context
            offset += len(piece)
        block += remaining
        offset += len(remaining)
    if block:
        yield offset - len(block), offset, block, method, context


def collect(cfg):
    manifest, content = snapshot(cfg)
    passages = []
    for f in manifest['files']:
        raw = content[(f['repo_id'], f['path'])]
        for start, end, piece, method, context in chunks(raw, f['path'], cfg['passage_bytes']):
            if not piece.strip():
                continue
            passage = {**f, 'file_sha256': f['sha256'], 'start_byte': start, 'end_byte': end,
                       'start_line': raw[:start].count(b'\n') + 1,
                       'end_line': raw[:max(start, end-1)].count(b'\n') + 1,
                       'passage_sha256': sha(piece), 'chunk_method': method,
                       'excerpt': piece.decode('utf-8')}
            passage['passage_id'] = digest(passage)
            context = context.encode('utf-8')[:PROFILE['context_bytes']].decode('utf-8', errors='ignore')
            passage['embedding_text'] = f"{f['path']}\n{context}\n" + passage['excerpt']
            passages.append(passage)
            if len(passages) > 10000:
                raise ValueError('Corpus exceeds 10000 passages')
    return manifest, passages


def generation(cfg, manifest, passages):
    return digest({'config': cfg, 'profile': PROFILE, 'manifest': manifest,
                   'passages': [p['passage_id'] for p in passages]})


def in_scope(passage, scope):
    return (passage['repo_id'] in scope['repo_ids'] and
            {'repo_id': passage['repo_id'], 'path': passage['path']} not in scope['exclude_paths'])


def validate_scope(scope, cfg):
    fields(scope, ('repo_ids', 'exclude_paths'))
    repos = scope['repo_ids']
    if (not isinstance(repos, list) or not repos or any(not isinstance(r, str) for r in repos) or
            len(set(repos)) != len(repos) or not set(repos) <= {r['repo_id'] for r in cfg['roots']}):
        raise ValueError('Scope must select unique accepted repository IDs')
    if not isinstance(scope['exclude_paths'], list) or len(scope['exclude_paths']) > 1000:
        raise ValueError('Invalid scope exclusions')
    for item in scope['exclude_paths']:
        fields(item, ('repo_id', 'path'))
        if item['repo_id'] not in repos:
            raise ValueError('Excluded path must belong to selected scope')
        relative(item['path'])
