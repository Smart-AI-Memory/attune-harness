# Coordinated local evidence review

Status: executable bounded increment, authorized by Patrick's “good proceed”
after the Phase 2 proposal. This implements the local journey; it does not execute
the unrelated draft steering-cards spec or claim the entire roadmap phase done.

Outcome: CLI accepts an explicit request with attune-forms, retrieves project
evidence, runs a configurable lead and independent reviewer with scoped feature
access, verifies the reviewed document, and saves a durable run record. The first
workflow reviews existing Markdown evidence. Participant narratives are retained
verbatim; attune-verify owns supported claims, findings, and evidence. Completion
of the workflow is distinct from document verification and narrative correctness.

Experiments before source edits: baseline 170 tests passed (98.69% statements).
Built attune-forms 0.17.0 from cached commit
4191c4e0c6bfe7ff21e4dd926f0ba8202775a9a7 without editing its older checkout.
Installed the wheel locally; public form_from_dict / collect_form_response
accepted a valid text/select request and rejected missing fields and an unknown
participant. form_to_markdown produced a fillable keyboard form. No provider calls.

Decisions for this slice: dependency-free synchronous coordinator; immutable
accepted request revision; one fresh attempt per selected participant; bounded
JSON turn protocol; atomic JSON record in an exclusively created run directory.
The coordinator records pending work before dispatch and results after it, never
automatically retries. An interrupted pending operation is unresolved, not safe to
repeat. This store supports inspection, not resume, transfer or exactly-once effects.
No database/server is needed for this single-writer workflow. ACP, direct-model
and production-runtime comparisons remain outstanding; this is a provisional
substrate decision supported by the existing synchronous adapters and local tests.

Registry profiles: explicit deterministic demonstration; native Claude/Codex via
the existing text exchange, carrying a JSON action inside text; externally supplied
JSON command for additional participants. Each native turn is a fresh bounded
invocation with full local transcript, not a resumed native session. External
adapters require a separate explicit CLI switch; their commands/configuration are
trusted local code and may use credentials or incur costs. This increment tests
them using injected transports and disposable local processes only. No fallback
between participants/providers; unavailable implementations fail visibly.

Tools: retrieve(query,k) confined to the accepted corpus and verify({}) confined
to the accepted document/context. Names, arguments, request correlation, grant
membership and per-participant call budgets are checked before invocation. Tool
results are data. Participant output cannot supply paths, grant more tools or
change the accepted request. Each participant receives the document and initial
retrieval, independently of the other's narrative. Both narratives remain in the
record so disagreements are visible without copying Attune's disposition schema.
The final independent verification is scoped to the reviewed document; it does
not verify arbitrary review prose. Local scope checks are not an OS sandbox for
configured executables, native host settings or trusted verification manifests.

Cases: accepted/missing/declined/stale request; duplicate/unknown JSON fields;
participant selection and disabled profiles; lead/reviewer separation; success,
refuted/unknown/no sources; tool denial, arbitrary paths, stale/duplicate replies,
bad versions, size limits, exhausted budgets; dependency absence; process failure;
source changes; persistence failure before/after dispatch; interruption; inspection
of unfinished records without rerunning work. Core-only and independently installed
wheel journeys must continue working. No live model qualification is inferred.

Rejected: building another forms validator or findings/disposition system, because
the existing public libraries own those semantics. Rejected: introducing a workflow
server or recovery engine before establishing one single-writer journey. Rejected:
pretending a prompt containing evidence grants callable features; the bounded
turn loop must actually dispatch and return the real library results.

Done when: installed CLI form → submitted request → retrieval → two participants
with observed real feature calls → independent verification → inspectable JSON
record works; fault cases fail honestly; runnable examples and receipts are saved.
Full Phase 2 still needs live Claude, Codex and additional-model journeys, existing
workflow comparison, broader host interaction and extension/help qualification.
