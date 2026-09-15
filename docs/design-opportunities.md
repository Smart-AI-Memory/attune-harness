# Reliability opportunities 1–5

Status: implementation authorized by Patrick, 2026-09-15. Evaluation artifacts
are bounded experiments; no automatic model promotion or autonomous repair.

Outcome: make review accuracy, context cost, narrow worker quality, repair economics,
and platform readiness reproducible. Done when the package builds, regression and
installed checks pass, frozen trials have retained outputs and explicit dispositions,
and unavailable platform/price/human evidence is reported as missing.

## Cases and implementation

1. Freeze eight new documentation scenarios (clean, contradiction, incomplete
   evidence, explicit uncertainty; two each). Compare direct Astra, two Astra roles,
   and Sol lead/Astra reviewer on identical evidence. Keep all role outputs and
   failures. Grade anonymous outputs against a prewritten key in a fresh Sol call;
   independently inspect judgments here. Model grading is separately executed,
   not a claim of independent human validation. Conflicts stay inconclusive.
2. Add an optional Codex skills-catalog token budget. Keep user/project instructions,
   hooks, approvals, sandbox and enabled capabilities. Compare two fresh native
   processes with the same task before selecting a focused experimental profile.
3. Evaluate Sol and the pinned installed Llama on six log/diagnostic cases. Add
   deterministic event routing with stable deduplication keys, pending/check failure
   distinctions, and bounded escalation. Model diagnosis never authorizes a repair.
4. Add a strict repair ledger: every attempt, failed/escalated work, checking cost,
   and human correction. Unknown tokens/prices/time remain unknown; reasoning tokens
   are a subset of output, not added twice. No cost ranking before a supplied quality
   floor passes. Exercise it with constrained synthetic configuration repairs whose
   independent checks run in host code. Separate fixture economics from real repairs.
5. Supply a native qualification command and OS matrix artifact for process failures,
   descendant cleanup and crash/recovery. Run on available hosts. Unsupported Windows
   execution remains explicitly unsupported until a real Windows implementation and
   run qualify it; a Mac mock is never a Windows pass. Keep mixed-team experiments
   opt-in unless measured benefit supports promotion.

## Probes before code

- dev9 uses one native call per role; direct evidence projection excludes peers.
- Installed Codex 0.153.4 exposes explicit model/config overrides. Its local model
  catalog lists Astra and Sol with xhigh. Official config documentation exposes
  `skills.max_context_tokens` (positive, at most 10000); use a 1000-token trial.
- Both process supervision and review writer locks explicitly require POSIX.
- Docker CLI exists but no daemon is reachable. No Linux/Windows runner is currently
  connected. Ollama's loopback probe requires sandbox permission; no model downloaded.
- No Git repository exists here; preserve wheel/source/evidence hashes instead.

Rejected: disabling global settings/instructions to make token counts look smaller;
replacing independent verification with a model verdict; treating missing costs as
zero; adding a speculative Windows supervisor that cannot be exercised here.

## Evidence and bounds

Preserve all prior artifacts and dev9 installation. Build dev10 into a fresh venv.
Freeze inputs, scoring criteria, native-call cap and installed sources before runs.
Native calls use the existing signed-in Codex path explicitly requested for this
work, with synthetic inputs; no credential inspection, API fallback or global edits.
Live execution approval is evaluated against that concrete frozen plan.

Sources: local `codex exec --help`, model cache and source; [official configuration
reference](https://learn.chatgpt.com/docs/config-file/config-reference).

## GitHub continuation

Patrick explicitly requested a GitHub home for the library during implementation.
Create a private Smart-AI-Memory/attune-harness repository, push reviewed source,
and use GitHub Actions' native OS runners. Exclude raw receipts, local environments
and personal working memory. GitHub's repository lookup returned not found for
the current account before creation. CI runs installed-artifact checks; Windows
records the current unsupported execution/recovery boundary rather than calling
that a native execution pass. The read-only REST adapter rejects incomplete pages,
stale revisions and ambiguous check states; it never dispatches or posts messages.

## Fable steering — September 15

Patrick retired Llama from the intended workflow and requested Fable as the next
candidate. Preserve the frozen Llama results and environments as history. Add an
explicit Fable-led/Astra-reviewed registry using `claude-fable-5-1`, the identifier
in the local attune-ai model registry. Validate it offline with the installed
review-form command. The current Astra default remains usable; the Fable profile
is configured but not live-qualified. Do not infer lower cost or better accuracy
from the model name. Live Anthropic execution remains subject to Patrick's saved
API spending freeze until September 16 and his first-spend authorization rule.
