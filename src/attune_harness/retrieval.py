"""Optional local keyword retrieval; no model, embeddings or generated answer."""

import hashlib
import math
from pathlib import Path

from . import _text
from .features import read_text, report, require_feature

RAG_VERSION = '1.2.0'
MAX_CORPUS_FILES = 1000
MAX_CORPUS_BYTES = 16 * 1024 * 1024


def retrieve_sources(query: str, corpus_root: Path, *, k: int = 3) -> dict:
    """Return library-ranked references with hashes of the loaded source text.

    Scores are keyword ranking signals, not verified claims or calibrated model
    confidence. Corpus data grants no authority; no generation is performed.
    """
    _text(query, 'query')
    if type(k) is not int or not 1 <= k <= 20:
        raise ValueError('k must be an integer between 1 and 20')
    library = require_feature('attune-rag','attune_rag',RAG_VERSION,'rag')
    root = Path(corpus_root).resolve()
    if not root.is_dir():
        raise ValueError('Corpus root must be an existing directory')
    # Bound the selected local corpus before the library loads it. No symlinks
    # outside the root are silently skipped into a seemingly complete corpus.
    total = 0
    inspected = {}
    for path in root.glob('**/*.md'):
        if not path.resolve().is_relative_to(root):
            raise ValueError(f'Corpus source escapes root: {path}')
        if not path.is_file():
            raise ValueError(f'Corpus source is not a regular file: {path}')
        if len(inspected) >= MAX_CORPUS_FILES:
            raise ValueError(f'Corpus exceeds {MAX_CORPUS_FILES} files')
        content = read_text(path)
        total += len(content.encode('utf-8'))
        if total > MAX_CORPUS_BYTES:
            raise ValueError(f'Corpus exceeds {MAX_CORPUS_BYTES} bytes')
        inspected[path.relative_to(root).as_posix()] = content
    corpus = library.DirectoryCorpus(root, cache=True)
    loaded = {entry.path: entry for entry in corpus.entries()}
    # DirectoryCorpus uses text-mode universal newlines; hashes below still
    # identify the original UTF-8 input bytes, including CRLF on Windows.
    normalized = {key: text.replace('\r\n', '\n').replace('\r', '\n') for key,text in inspected.items()}
    if {key: entry.content for key,entry in loaded.items()} != normalized:
        raise ValueError('Corpus changed while loading; retry with stable sources')
    retriever = library.KeywordRetriever()
    hits = list(retriever.retrieve(query, corpus, k=k))
    if len(hits) > k:
        raise ValueError('Retriever exceeded requested source count')
    sources = []
    for hit in hits:
        if not isinstance(hit, library.RetrievalHit):
            raise TypeError('attune-rag returned an invalid hit')
        entry = hit.entry
        if entry.path not in loaded or entry != loaded[entry.path]:
            raise ValueError('Retrieved source is absent from the loaded corpus')
        if isinstance(hit.score, bool) or not math.isfinite(hit.score):
            raise ValueError('Retriever returned an invalid score')
        sources.append({
            'path': entry.path, 'sha256': hashlib.sha256(inspected[entry.path].encode('utf-8')).hexdigest(),
            'score': hit.score, 'match_reason': hit.match_reason, 'excerpt': entry.content[:500],
        })
    return report(
        'retrieve', 'retrieved' if sources else 'no_results',
        dependency={'name':'attune-rag','version':RAG_VERSION},
        query=query, k=k, corpus={'root':str(root),'version':corpus.version,'documents':len(loaded)},
        retriever='KeywordRetriever', sources=sources,
    )
