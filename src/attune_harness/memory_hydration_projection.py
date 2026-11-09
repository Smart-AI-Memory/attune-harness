"""Pure legacy-format projection of a complete, guarded source snapshot.

Source bytes stay authoritative. Literal projection and security-authority
parsing have separate owners. Every complete/decoded/derived string is checked
before pointer indexing is bounded; no Redis client is created here.
"""

from copy import deepcopy
import json
from pathlib import Path, PurePosixPath
import re

from .memory_controls import VERDICT_VALUES
from .memory_hydration_contract import LAYERS, generation_prefix
from .memory_hydration_secrets import check_secrets
from .memory_reader import FILE_LIMIT, SIDECARS, source_labels
from .memory_redis import RedisMemory, _ID_RE
from .review_contract import canonical, parse_json

INDEX_TEXT_CHARS = 32768
_LINK = re.compile(r'\[\[([^\]?][^\]]*)\]\]')
_FORWARD = re.compile(r'\[\[\?[^\]]*\]\]')
_LESSON = re.compile(r'^- \*\*')
_TITLE = re.compile(r'\*\*(.+?)\*\*:', re.DOTALL)


def _json_record(raw, check_budget):
    """Keep every decoded occurrence, including overwritten duplicate values."""
    occurrences = []
    def object_pairs(pairs):
        check_budget()
        occurrences.append(pairs)
        return dict(pairs)  # reference JSON lookup is last-wins
    check_budget()
    try:
        value = json.loads(raw, object_pairs_hook=object_pairs)
    except (ValueError, RecursionError) as error:
        raise ValueError('Hydration source JSON is malformed') from error
    check_budget()
    check_secrets('', occurrences, check_budget=check_budget)
    check_secrets('', value, check_budget=check_budget)
    return value



def _source_labels(root, text, occurrences, check_budget):
    """Sanitize parser failures without changing legacy reads or budget errors."""
    budget_failure = None

    def observed_budget():
        nonlocal budget_failure
        try:
            check_budget()
        except Exception as error:
            budget_failure = error
            raise

    try:
        return source_labels(root, text, {}, _observe=occurrences.append,
                             _check_budget=observed_budget)
    except Exception as error:
        if error is budget_failure:
            raise
    # Safe YAML constructors can include decoded values outside yaml.YAMLError
    # (for example an invalid !!int). Raise after leaving the handler so neither
    # the diagnostic nor its exception context retains the parser failure.
    raise ValueError('Hydration source security metadata is malformed or unauthorized')


def _sidecar(name, text, check_budget):
    if name == 'summaries_by_path.json':
        value = _json_record(text, check_budget)
        if not isinstance(value, dict):
            raise ValueError('Hydration summaries sidecar requires a JSON object')
        # The writer uses no summary lookup or summary-derived Redis field.
        # Preserve safe unknown values and standard duplicate lookup semantics;
        # do not add a new RAG value-validation policy to this writer.
        return
    for line in text.splitlines():
        check_budget()
        if not line.strip():
            continue
        try:
            value = parse_json(line, FILE_LIMIT)
        except (ValueError, RecursionError) as error:
            raise ValueError('Hydration verdict sidecar contains malformed JSON') from error
        check_secrets('', value, check_budget=check_budget)
        if (not isinstance(value, dict)
                or any(not isinstance(value.get(key), str) or not value[key]
                       for key in ('stem', 'verdict', 'digest', 'who', 'at'))
                or value['verdict'] not in VERDICT_VALUES):
            raise ValueError('Hydration verdict sidecar contains a malformed record')


def _literal_header(raw):
    """Literal delimiter/scalar mapping; this is not the authority parser."""
    raw = raw.removeprefix('\ufeff')  # match the authority parser's optional leading BOM
    if not raw.startswith('---'):
        return None
    end = raw.find('\n---', 3)
    return (raw[3:end], raw[end + 4:]) if end != -1 else None


def _curated(raw, stem, check_budget):
    split = _literal_header(raw)
    if split is None:
        return None
    inner, body = split
    labels = {}
    for line in inner.splitlines():
        check_budget()
        if ':' in line:
            key, value = line.strip().split(':', 1)
            labels.setdefault(key.strip(), value.strip())
    if labels.get('curated') != 'true':
        return None
    fields = dict(name=labels.get('description', stem), description=body.strip(),
                  type=labels.get('node_type', ''), status=labels.get('status', 'active'),
                  layer='curated', tags=','.join(part.strip() for part in labels.get('tags', '').split(',')
                                               if part.strip()),
                  updated_at=labels.get('updated_at', ''))
    edges = _json_record(labels['edges_json'], check_budget) if labels.get('edges_json') else []
    if not isinstance(edges, list):
        raise ValueError('Hydration explicit edges require a JSON array')
    projected = []
    for edge in edges:
        check_budget()
        if (not isinstance(edge, dict) or not isinstance(edge.get('target_id'), str)
                or not edge['target_id'] or not isinstance(edge.get('type', ''), str)
                or not isinstance(edge.get('description', ''), str)):
            raise ValueError('Hydration explicit edge fields must be strings with a target')
        projected.append(dict(target=edge['target_id'], type=edge.get('type', ''),
                              description=edge.get('description', '')))
    return labels.get('node_id', stem), fields, projected


def _file(raw, stem):
    name, description, kind, body = stem, '', '', raw
    split = _literal_header(raw)
    if split is not None:
        inner, body = split
        for line in inner.splitlines():
            line = line.strip()
            if line.startswith('name:'): name = line[5:].strip()
            elif line.startswith('description:'): description = line[12:].strip()
            elif line.startswith('type:'): kind = line[5:].strip()
    return dict(name=name, description=description, type=kind), body


def _lessons(raw, check_budget):
    lines = raw.splitlines()
    starts = []
    for index, line in enumerate(lines):
        check_budget()
        if _LESSON.match(line): starts.append(index)
    for position, start in enumerate(starts):
        check_budget()
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        chunk = '\n'.join(lines[start:end]).rstrip()
        title = _TITLE.search(chunk)
        title = ' '.join(title.group(1).split()) if title else chunk[:80]
        yield start + 1, title[:160], chunk


def _record_identity(ident, family):
    if not isinstance(ident, str) or not _ID_RE.fullmatch(ident):
        raise ValueError('Hydration record identity is unsupported')
    # Use the existing pure key mapper, not an independent approximation.
    reader = object.__new__(RedisMemory)
    reader.prefix = ''
    expected = 'node:' + ident if family == 'node' else ident
    if reader._key(ident) != expected or (family == 'node' and ident.startswith('file:')):
        raise ValueError('Hydration record identity redirects to another record')


def _pointer_path(root, relative, roots, ident):
    path = Path(root['path']) / relative
    matches = [item for item in roots if item['tier'] in ('personal', 'curated')
               and path != Path(item['path']) and Path(item['path']) in path.parents]
    if len(matches) != 1 or matches[0]['id'] != root['id'] or path.stem != ident.rsplit(':', 1)[-1]:
        raise ValueError('Hydration file pointer has ambiguous or unservable root authority')
    return str(path)


def project_snapshot(snapshot, *, check_budget=lambda: None):
    """Build all four logical layers only after scanning the complete batch.

    Consume this inside capture_sources and finish that context successfully
    before accepting the result. Diagnostics here contain counts only; raw bytes,
    parsed metadata and private paths remain internal projection inputs.
    """
    roots = {root['id']: root for root in snapshot['roots']}
    texts = {}
    for key, entry in sorted(snapshot['entries'].items()):
        check_budget()
        if not entry['present']:
            continue
        try:
            text = entry['data'].decode('utf-8')
        except UnicodeError as error:
            raise ValueError('Hydration source must be valid UTF-8') from error
        check_secrets(text, check_budget=check_budget)
        name = entry['path']
        if name in SIDECARS:
            _sidecar(name, text, check_budget)
        else:
            occurrences = []
            labels = _source_labels(roots[entry['root_id']], text, occurrences, check_budget)
            check_budget()
            check_secrets('', occurrences, check_budget=check_budget)
            check_secrets('', labels, check_budget=check_budget)
            texts[key] = text.replace('\r\n', '\n').replace('\r', '\n')
    records, edges, memberships, pending_links, file_targets = {}, {}, {}, {}, {}
    counts, truncations = {layer: 0 for layer in LAYERS}, {layer: 0 for layer in LAYERS}
    seen_roles = set()
    skipped_curated = excluded_indexes = unresolved = forward = 0

    def add(ident, family, fields):
        _record_identity(ident, family)
        if ident in records:
            raise ValueError('Hydration projection contains duplicate record identities')
        check_secrets('', dict(record_id=ident, **fields), check_budget=check_budget)
        if 'text' in fields and len(fields['text']) > INDEX_TEXT_CHARS:
            truncations[fields['layer']] += 1
            fields['text'] = fields['text'][:INDEX_TEXT_CHARS]
        records[ident] = dict(family=family, fields=fields)
        counts[fields['layer']] += 1
        if family == 'node':
            for key in ('status', 'type'):
                memberships.setdefault(key + ':' + fields[key], set()).add(ident)

    for source, members in zip(snapshot['sources'], snapshot['inventories']):
        root, layer = roots[source['root_id']], source['layer']
        for relative in members:
            check_budget()
            role = (root['id'], relative, layer, source['corpus'])
            if role in seen_roles:
                continue
            seen_roles.add(role)
            raw = texts[(root['id'], relative)]
            stem = PurePosixPath(relative).stem
            path = str(Path(root['path']) / relative)
            if layer == 'curated':
                item = _curated(raw, stem, check_budget)
                if item is None:
                    skipped_curated += 1
                    continue
                ident, fields, outgoing = item
                add(ident, 'node', fields)
                edges[ident] = outgoing
            elif layer == 'file':
                if PurePosixPath(relative).name == 'MEMORY.md':
                    excluded_indexes += 1
                    continue
                ident = f"file:{source['corpus']}:{stem}"
                path = _pointer_path(root, relative, snapshot['roots'], ident)
                fields, body = _file(raw, stem)
                add(ident, 'file', dict(**fields, layer=layer, corpus=source['corpus'], path=path, text=body))
                file_targets.setdefault(source['corpus'], {})[stem] = ident
                pending_links[ident] = (source['corpus'], list(dict.fromkeys(_LINK.findall(body))))
                forward += len(_FORWARD.findall(body))
            elif layer == 'lesson':
                for line, title, chunk in _lessons(raw, check_budget):
                    add(f'lesson:{line}', 'lesson', dict(name=title, description=title, layer=layer,
                        corpus=source['corpus'], path=path, line=str(line), text=chunk))
            elif layer == 'rule':
                title = next((line[2:].strip() for line in raw.splitlines() if line.startswith('# ')), stem)
                add('rule:' + stem, 'rule', dict(name=stem, description=title, layer=layer,
                                                corpus=source['corpus'], path=path, text=raw))
    for outgoing in edges.values():
        for edge in outgoing:
            check_budget()
            if edge['target'] not in records or records[edge['target']]['family'] not in ('node', 'file'):
                raise ValueError('Hydration explicit edge target requires a selected curated or file record')
            check_secrets('', edge, check_budget=check_budget)
    for ident, (corpus, links) in pending_links.items():
        for target in links:
            check_budget()
            preferred = file_targets.get(corpus, {}).get(target)
            candidates = [items[target] for items in file_targets.values() if target in items]
            if preferred is not None:
                resolved = preferred
            elif len(candidates) > 1:
                raise ValueError('Hydration wikilink target is ambiguous')
            elif not candidates:
                unresolved += 1
                continue
            else:
                resolved = candidates[0]
            edge = dict(target=resolved, type='RELATED_TO')
            check_secrets('', edge, check_budget=check_budget)
            edges.setdefault(ident, []).append(edge)
    return dict(records=records, edges=edges,
                memberships={key: sorted(values) for key, values in memberships.items()},
                counts=counts, index_truncations=truncations, unresolved_links=unresolved,
                forward_links=forward, excluded_index_files=excluded_indexes, skipped_curated=skipped_curated)


def generation_resources(projection, dataset, generation, context, *, check_budget=lambda: None):
    """Materialize logical resources for the generation ledger, without Redis."""
    check_secrets(context, check_budget=check_budget)
    prefix = generation_prefix(dataset, generation)
    resources = []
    for ident, item in sorted(projection['records'].items()):
        check_budget()
        suffix = 'node:' + ident if item['family'] == 'node' else ident
        resources.append(dict(kind='hash', key=prefix + suffix, fields=deepcopy(item['fields'])))
    for suffix, members in sorted(projection['memberships'].items()):
        check_budget()
        if members:
            resources.append(dict(kind='set', key=prefix + suffix, members=list(members)))
    for ident, outgoing in sorted(projection['edges'].items()):
        check_budget()
        if outgoing:
            resources.append(dict(kind='list', key=prefix + 'edges:' + ident,
                                  items=[canonical(edge) for edge in outgoing]))
    resources.append(dict(kind='string', key=prefix + 'context', value=context))
    return resources
