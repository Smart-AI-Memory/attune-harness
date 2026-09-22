# Item E — implementation handoff

September 18, 2026. **Inspection only; production integration is not implemented.**
The goal monitor stopped work at a reported 59,575 tokens against Patrick's
50,000-token budget. Do not interpret this handoff as completion or a new budget.

## Authorized scope

Integrate the demonstrated function-body boundary into the existing production
effect owner, retain protected behavioral checks, and qualify saved-work
compatibility. Fresh native/model trials and release work are excluded. A and B
are already verified locally. The dirty checkout contains their implementation
and other prerequisite work; preserve it. No commit or worktree was created.

## Selected model routing

Patrick selected **Astra design and final review; Sol implementation** in the
September 18 routing question. This is a routing decision, not a new token or
credit allocation; the existing goal remains budget-limited at this checkpoint.

| Stage | Model | Responsibility |
|---|---|---|
| Design | Astra | Run the disposable probes and specify the edit boundary, saved-work compatibility, edge cases and acceptance checks before production edits. |
| Implementation | Sol | Implement the agreed design, run verification and repair ordinary failures. |
| Final review | Astra | Review the changed boundary enforcement, saved-work compatibility and recovery paths, even if Sol's tests pass; keep review focused on the diff and verification evidence. |

Escalate from Sol when the design contract must change, edit-boundary behavior
remains uncertain, or the same problem survives two attempted fixes. Routine
editing alone does not require Astra. The final review adds cost and may
duplicate checks; savings from this hybrid have not been measured.

Selection provenance: the user answered the routing question
`call_Qod5anEjImMWcaoHZDuj5dhY`, item 0, with
“Astra design and final review; Sol implementation (Recommended).”

Patrick asked whether C and D should precede E. Recommendation: continue bounded
offline E; C must precede another paid experiment. D improves review-to-builder
handoff but is not a prerequisite for enforcing the body boundary. E's narrow
supported profile limits its usefulness; avoid generalizing it into an editing
framework or claiming model reliability from offline qualification.

## Verified source seams

- `experiments/plan_build/function_body_replacements.py` is a disposable replay
  prototype. It binds a path, function name and source hash, replaces the AST
  body's line span, and compares the surrounding AST. It supports one selected
  top-level multiline function, UTF-8/LF and four-space indentation. It is not a
  runtime sandbox. The twelve prototype tests include Unicode, decorated nested
  functions, stale source, dedented code, unchanged bodies and wrong logic.
- `src/attune_harness/work_effects.py` owns manifest validation, full-file proposal
  validation, atomic writes and recovery. Enforce body restrictions here as well
  as in worker decoding; otherwise the standalone effect API could bypass them.
- `src/attune_harness/work_build.py` constructs worker requests and replays saved
  requests/replies against their original event prefix. Existing response
  contracts 1 and 2 must retain their exact prompt/digest behavior. New runs
  currently use contract 2; reviewer replies already have their own schema.
- `src/attune_harness/work_runtime.py` reconstructs effect manifests during
  `preserve_completed` repair. Preserve selected function restrictions when
  refreshing pending preimages; do not silently broaden them to full-file edits.
- `src/attune_harness/work_cli.py` decodes retained worker replies for read-only
  evidence presentation. Any new decoder contract must remain inspectable after
  a rejection and must not require rereading a preimage from a modified checkout.
- `repair.MAX_FILE` is 65,536 bytes. Reuse existing snapshot, protected probe,
  operation journal, atomic write and reconciliation controls.

## Design questions still open

No design decision or scratch probe has been completed. Before editing production
code, run source-span edge probes and write the required short design note.
Evaluate an opt-in versioned manifest retaining the accepted original source and
selected symbol, with a strict body-only worker reply materialized by the host.
The production effect owner must validate the resulting complete file against
that retained boundary. Decide whether the first supported profile requires all
outputs to be existing selected functions; mixed new-file/body edits would widen
qualification. Do not reinterpret existing manifests or response versions.

Probe comments before/after the body, decorators, multiline signatures/strings,
Unicode byte offsets, duplicate symbols, async functions, tabs/CRLF/BOM,
dedented comments/code, syntax that parses but fails compilation, stale source,
and byte limits. Preserve the original prefix/suffix and function interface.
Body safety does not establish correct behavior; protected probes remain required.

## Next steps

1. On continuation with an available budget, snapshot current source and original
   experimental receipt hashes. Do not rerun the original replay script against
   its original output directory.
2. Run disposable probes and write the design note before production edits.
3. Implement the chosen boundary through manifest, decoding, effects and repair
   paths; retain legacy prompt/digest semantics.
4. Qualify real writes, protected logic failures, rejected replies, status,
   pause/resume, reconciliation, repair authority, stale source and forged
   journals. Include a direct effect-owner bypass attempt and saved v1/v2 work.
5. Run source and isolated installed checks, guard-removal mutations, and verify
   original experiment evidence remains unchanged. Document supported limits and
   update the opportunity register only after actual completion.

## Retained validation environment

Python: `/private/tmp/attune-fresh-resolution-y74ui3g8/integrated/bin/python`
(3.12.13). Qualified optional dependencies:
`/private/tmp/task7-installed-spec-n2emxesr/installed`.
Put this checkout's `src` first on `PYTHONPATH`; disable usage/version pings and
bytecode writes. A/B baseline: 492 tests passed, zero skipped, one existing
`ModelTier` warning, using `tests/test_work_*.py`, `tests/test_connected_journey.py`,
`tests/test_task_compatibility.py` and
`tests/test_plan_build_default_compatibility.py`. E has no new verification yet.

For copied-source mutation runs, use a scratch working directory and pytest
`-c /dev/null -p no:cacheprovider`; otherwise repository pytest configuration can
silently select the real source. Never reset the dirty checkout for mutations.
