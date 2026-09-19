"""One bounded, independent two-participant evidence review; no automatic retries."""

import hashlib
from pathlib import Path
from uuid import uuid4

from .features import FeatureUnavailable, read_text, report
from .retrieval import retrieve_sources
from .verification import verify_document
from .review_contract import accept_request, bounded_text, canonical, digest, fields, load_registry
from .review_participants import PROTOCOL, ReviewExchange, decode_action
from .review_store import PersistenceError, RunStore
from .recovery import engine_profile, RecoveryCursor, ReviewPaused, UnresolvedOperation, snapshot_sources, stable_id


def prepare_review(request_path: Path, config_path: Path) -> dict:
    registry = load_registry(config_path)
    if registry.get('extensions'):
        from .extensions import catalog
        catalog(registry['extensions'], enabled=True)
    accepted = accept_request(request_path, registry)
    answers = accepted['submission']['answers']
    paths = {name: Path(value) for name, value in accepted['paths'].items()}
    document, context, corpus = (paths[name] for name in ('document', 'context', 'corpus'))
    if not document.is_relative_to(corpus):
        raise ValueError('Reviewed document must be inside the selected corpus')
    originals = {document: read_text(document, 65_536), context: read_text(context, 65_536)}
    artifacts = {name: {'path': str(paths[name]), 'sha256': hashlib.sha256(originals[paths[name]].encode('utf-8')).hexdigest()}
                 for name in ('document', 'context')}
    if 'retrieval' in registry:
        from .voyage_index import check_generation
        selected = registry['retrieval']
        _, metadata = check_generation(selected['config'], selected['generation'])
        roots = {r['repo_id']: Path(r['path']) for r in selected['config']['roots']}
        if corpus not in roots.values():
            raise ValueError('Review corpus must be one of the selected application roots')
        # Exclude the reviewed document before candidate selection and paid reranking.
        from .voyage_sources import in_scope
        if any((roots[p['repo_id']] / p['path']).resolve() == document and in_scope(p, selected['scope'])
               for p in metadata['passages']):
            raise ValueError('Accepted retrieval scope must exclude the reviewed document')
        source_snapshot = {'generation': selected['generation'], 'manifest': digest(metadata['manifest'])}
    else:
        source_snapshot = snapshot_sources(corpus)
    revision = digest({'submission': accepted['submission'], 'paths': accepted['paths'],
                       'registry': registry, 'artifacts': artifacts, 'source_snapshot': source_snapshot})
    return {'accepted': accepted, 'registry': registry, 'answers': answers, 'paths': paths,
            'originals': originals, 'artifacts': artifacts, 'source_snapshot': source_snapshot,
            'requirement_revision': revision}


def authorize_external(selected, allow_external):
    if not allow_external and any(item['adapter'] != 'deterministic' for item in selected.values()):
        raise FeatureUnavailable('External participant execution requires --allow-external; review the selected models, commands and call budgets first')


def review(request_path: Path, config_path: Path, run_directory: Path, *,
           allow_external: bool = False, allow_provider: bool = False, max_operations=None, exchange_factory=ReviewExchange) -> dict:
    prepared = prepare_review(request_path, config_path)
    accepted, registry, answers = (prepared[name] for name in ('accepted', 'registry', 'answers'))
    authorize_external({role: registry['participants'][answers[role]] for role in ('lead', 'reviewer')}, allow_external)
    store = RunStore(run_directory)
    run_id = str(uuid4())
    record = report('review', 'running', run_id=run_id, requirement_revision=prepared['requirement_revision'],
                    accepted=accepted, registry=registry, artifacts=prepared['artifacts'],
                    events=[], participants={}, record_path=str(store.path),
                    verification_scope='Supported claims in the reviewed document; participant narratives are not verified',
                    external_execution_enabled=allow_external,
                    recovery={'profile': engine_profile(registry), 'source_snapshot': prepared['source_snapshot'],
                              'assignments': {role: {'participant_id': answers[role], 'attempt_id': stable_id(run_id, role)}
                                              for role in ('lead', 'reviewer')},
                              'transfers': [], 'reconciliations': []})
    with store.lease():
        return execute_review(record, store, prepared, allow_external=allow_external,
                              allow_provider=allow_provider, max_operations=max_operations, exchange_factory=exchange_factory)


def execute_review(record, store, prepared, *, allow_external=False, allow_provider=False,
                   max_operations=None, exchange_factory=ReviewExchange):
    """Legacy schema adapter; operation ownership lives in the shared runtime."""
    from .task_runtime import execute_assessment
    return execute_assessment(record, store, prepared, allow_external=allow_external,
        allow_provider=allow_provider, max_operations=max_operations, exchange_factory=exchange_factory,
        services=(retrieve_sources, verify_document, authorize_external))
