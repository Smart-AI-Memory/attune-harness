"""Private complete-input preparation; no Redis or public check result.

Run this cooperative composition inside the hydration supervisor's owned worker.
No accepted value escapes a provisional source capture. A completed preparation
is neither a permission token nor evidence of hard interruption or publication.
"""

from copy import deepcopy

from .memory_hydration_capture import capture_sources
from .memory_hydration_contract import function_digest
from .memory_hydration_inputs import (
    ConfigurationObservation, context_commitment, projection_identity, source_preimage,
)
from .memory_hydration_ledger import finalize_manifest
from .memory_hydration_projection import (
    INDEX_TEXT_CHARS, generation_resources, project_snapshot,
)
from .review_contract import digest


class PreparedHydration:
    """Keep complete private evidence and compare a fresh observation before CAS.

    The caller owns input-file rereads, bounded Git context and external process
    supervision. Every method shares the caller's original budget callback.
    Nothing here constructs a client, emits source bodies or refreshes a base.
    """

    def __init__(self, config, sources, context, *, check_budget, environment=None):
        self._check_budget = check_budget
        check_budget()
        if not isinstance(context, str):
            raise ValueError('Hydration context must be text')
        self._configuration = ConfigurationObservation(config, environment=environment)
        observed_sources = deepcopy(sources)
        policy = projection_identity(check_budget=check_budget)
        bundle = function_digest()
        with capture_sources(config, sources, check_budget=check_budget) as snapshot:
            projection = project_snapshot(snapshot, check_budget=check_budget)
            preimage = source_preimage(
                snapshot, self._configuration.config_digest, policy, check_budget=check_budget)
            context_digest = context_commitment(context, check_budget=check_budget)
        # Accept nothing before all guarded roots have finished verification.
        self._configuration.verify(config)
        self._verify_policy(policy, bundle)
        self._configuration.verify(config)
        if sources != observed_sources:
            raise ValueError('Hydration source configuration changed during the operation')
        check_budget()
        self._preimage = preimage
        self._projection = projection
        self._context = context
        self._context_digest = context_digest
        self._function_digest = bundle
        self._source_digest = digest(preimage)
        self._dataset = self._configuration.settings['dataset']
        check_budget()

    def _verify_policy(self, policy, bundle):
        current = projection_identity(check_budget=self._check_budget)
        if current != policy or function_digest() != bundle:
            raise ValueError('Hydration implementation changed during the operation')
        self._check_budget()

    def summary(self):
        """Return bounded counts and commitments, without paths or source text."""
        self._check_budget()
        projection = self._projection
        return dict(
            binding=self._preimage['binding'],
            source_digest=self._source_digest,
            config_digest=self._configuration.config_digest,
            context_digest=self._context_digest,
            function_digest=self._function_digest,
            source_files=self._preimage['files'], source_bytes=self._preimage['bytes'],
            counts=deepcopy(projection['counts']), index_text_chars=INDEX_TEXT_CHARS,
            index_truncations=deepcopy(projection['index_truncations']),
            unresolved_links=projection['unresolved_links'], forward_links=projection['forward_links'],
            excluded_index_files=projection['excluded_index_files'],
            skipped_curated=projection['skipped_curated'])

    def materialize(self, generation, previous, publication_id, hydrated_at):
        """Build pure logical resources and their exact eleven-field manifest."""
        self._check_budget()
        resources = generation_resources(
            self._projection, self._dataset, generation, self._context,
            check_budget=self._check_budget)
        manifest = dict(
            schema_version=1, generation=generation, previous=previous,
            publication_id=publication_id, binding=self._preimage['binding'],
            source_digest=self._source_digest, context_digest=self._context_digest,
            function_digest=self._function_digest, hydrated_at=hydrated_at,
            counts=deepcopy(self._projection['counts']))
        complete, raw = finalize_manifest(
            self._dataset, manifest, resources, check_budget=self._check_budget)
        self._check_budget()
        return resources, complete, raw

    def verify_fresh(self, config, sources, context):
        """Refuse any changed complete input; preserve the original observation.

        This compares a new guarded capture, including empty directories and
        absent sidecars, rather than checking only old selected file versions.
        The caller supplies newly read input files and newly captured context.
        """
        check_budget = self._check_budget
        check_budget()
        self._configuration.verify(config)
        if not isinstance(context, str):
            raise ValueError('Hydration context must be text')
        observed_sources = deepcopy(sources)
        policy = projection_identity(check_budget=check_budget)
        bundle = function_digest()
        with capture_sources(config, sources, check_budget=check_budget) as snapshot:
            fresh = source_preimage(
                snapshot, self._configuration.config_digest, policy, check_budget=check_budget)
            current_context = context_commitment(context, check_budget=check_budget)
        self._configuration.verify(config)
        self._verify_policy(policy, bundle)
        self._configuration.verify(config)
        if sources != observed_sources:
            raise ValueError('Hydration source configuration changed during the operation')
        if (fresh != self._preimage or current_context != self._context_digest
                or bundle != self._function_digest):
            raise ValueError('Hydration inputs changed before publication')
        check_budget()
