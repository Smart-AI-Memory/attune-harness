"""Inspect frozen citation support; host assessments remain advisory."""

from .review_contract import bounded_text


def lines(text):
    """Editor lines follow LF/CRLF; other Unicode separators are content."""
    parts = text.split('\n')
    if len(parts) > 1 and not parts[-1]:
        parts.pop()
    terminated = text.count('\n')
    return [line[:-1] if i < terminated and line.endswith('\r') else line
            for i, line in enumerate(parts)]


def numbered_sources(snapshot):
    return {path: [{'line': i, 'text': text} for i, text in enumerate(lines(item['text']), 1)]
            for path, item in snapshot['files'].items()}


def claims(record):
    """Read only retained answers/source; never reopen the checkout or dispatch."""
    source = numbered_sources(record['contract']['snapshot'])
    results = []
    for turn in record['answers']:
        if not turn.get('answer'):
            continue
        for index, citation in enumerate(turn['answer']['evidence']):
            key = {'round': turn['round'], 'participant': turn['participant'], 'citation': index}
            row = {**key, **citation, 'source': source[citation['path']][max(0, citation['line'] - 2):citation['line'] + 1],
                   'support': 'unchecked', 'assessments': []}
            row['assessments'] = [item for item in record.get('citation_assessments', [])
                                  if all(item.get(k) == v for k, v in key.items())]
            if row['assessments']:
                row['support'] = row['assessments'][-1]['decision']
            results.append(row)
    return results


def assessment(record, round_number, participant, citation, decision, note):
    if type(round_number) is not int or type(citation) is not int:
        raise ValueError('Citation selectors must be integers')
    key = {'round': round_number, 'participant': participant, 'citation': citation}
    if not any(all(row[k] == v for k, v in key.items()) for row in claims(record)):
        raise ValueError('Unknown saved citation')
    if decision not in ('supported', 'rejected', 'uncertain'):
        raise ValueError('Unsupported citation decision')
    bounded_text(note, 'host citation assessment', 2048)
    if len(record.get('citation_assessments', [])) >= 128:
        raise ValueError('Citation assessment bound reached')
    return {**key, 'decision': decision, 'note': note,
            'snapshot_digest': record['contract']['snapshot']['digest'],
            'prior_checkpoint': record['checkpoint_digest'], 'authority': 'advisory_host_assessment'}
