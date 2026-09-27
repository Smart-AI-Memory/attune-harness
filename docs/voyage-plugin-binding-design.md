# Voyage plugin binding: accepted selection and offline boundary

This slice adds an optional `voyage_plugin` object to normalized Voyage
config: absolute `registry`, optional `registry_digest`, `extension_id`, and
local `tools` named `embed`, `rerank`, `index`. Omission preserves the previous
normalized config and its digest. The digest pins the complete normalized
`extensions` section: registrations, grants, signer keys and revocations.
An unrelated section edit therefore needs a fresh explicit acceptance.

## Cases and probes before implementation

1. An unpinned draft can be planned offline. The plan reports the observed
   registry digest, `acceptance=unpinned`, and `dispatch_available=false`;
   neither the registry nor the config is written. A missing or drifted pin
   refuses selected dispatch before creating an index, generation, work area,
   stage ledger or provider, including when a provider is injected.
2. A matching pin validates only the selected enabled registration. Its
   artifact, signature, signer/revocation list, grants and installed import
   closure must match. Other registered bundles are not opened. The three
   named tools must each be a `run` binding in that bundle.
3. The selected bundle must declare exactly `api.voyageai.com` as its network
   host and `voyageai` and `lancedb` in its resolved import closure. Its
   effective grant must name `VOYAGE_API_KEY`, scratch, a bounded time and
   result/diagnostic output. Planning never reads the key or makes a call.
4. Even an accepted selection reports `dispatch_available=false` and selected
   build, retrieval and direct StageJournal use refuse. The adapter and index
   materialization belong to later slices. Existing unselected behavior runs
   through the unchanged implementation.

The focused probes use a disposable signed three-tool bundle, a temporary
registry and an injected provider that fails if called. They assert config
digest compatibility, draft inspection, signature/closure/grant/role errors,
and absence of new index/stage state after refusal. The full suite and a fresh
installed-wheel qualification are separate software evidence; they do not
qualify live Voyage model quality.

Rejected alternative: automatically copying the observed digest into config
would turn inspection into acceptance and silently authorize a changed grant
or signer set. The user must pin the reported digest in the config deliberately.
