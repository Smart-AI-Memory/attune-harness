# Library qualification

## Platforms

`.github/workflows/qualification.yml` builds and installs the wheel on GitHub's
macOS, Ubuntu and Windows runners, using Python 3.10 and 3.12. Each job runs
`python -I scripts/qualify_platform.py --output qualification` and uploads the
platform identity, installed source hashes, test output and JUnit results.

The jobs exercise timeout, cancellation, bounded output, descendant termination,
lost acknowledgements, crash-released locks and explicit recovery. Windows uses
Job Objects with a gated bootstrap and native file locks. Its additional cases
cover owner death, failed job assignment, Unicode paths and reparse-point rejection.
The original dev10 Windows receipt records `unsupported`; dev11 is the first native
Windows implementation. Retain both versions' evidence when comparing support.
Model providers are not called by CI. These tests qualify the runner/platform and
adapter fixtures; native model behavior requires the separate frozen campaign.

Each platform job runs the test files selected in `scripts/qualify_platform.py`
against the installed wheel. One more job, on Ubuntu with Python 3.10, runs every
test from the source tree with plain `pytest`, so a test outside that selection
cannot break unnoticed. It qualifies no platform. The required `Qualification`
check passes only when the platform jobs and that job pass.

Each platform job also runs the R2 clean-environment journey from the installed
wheel, through `scripts/check_installed.py`: plan, accept, build, review and
status with `attune` absent and no model called. The platform receipt's
`r2_journey` records each step's outcome; on Windows the build's refusal, if it
refuses, is recorded in the platform's own words rather than skipped. The
sequence is in [the R2 journey](journeys/r2-clean-environment.md).

The installed-wheel selection also includes Voyage budget/replay checks,
evaluator CLI status checks, plugin lifecycle tests and host qualification
boundary fixtures. `tests/test_code_rag_host_check.py` compiles the actual host
check script with optimization levels 0 and 1 and supplies invalid result,
usage and session evidence. Explicit runtime checks must reject it in both modes;
`python -O` and `PYTHONOPTIMIZE=1` must not remove qualification checks. The
boundary fixtures run with Harness's MCP dependency alone. The five real Attune
dispatcher cases in `tests/test_code_rag.py` were removed with the module they
tested; they skipped whenever Attune AI was absent, so CI never ran them.

`scripts/check_code_rag_host.py` checked the tool through Attune AI's dispatcher
by launching `attune_harness.attune_bridge`. That module was removed after 0.2.0
(D8 in the [spec authority addendum](specs/spec-authority/addendum-2026-09-21.md)),
so the script can no longer complete a host check. It and its test stay for now
because `scripts/qualify_platform.py` still selects the test; removing them is
separate work.

The [September 16 fix receipt](sol-review-fix-receipt.md) distinguishes local
source regression results from historical installed-host evidence.

## Accuracy and worker qualification

The model campaign is frozen on dev10, separately from the dev11 platform work.
Use the preserved dev10 environment with the review extra. On a fresh clone,
commit `c2fa34038483ec7a028a50f554bf1a95e54039a5` contains that version; build and
install it in an isolated environment before invoking the campaign. The current
library is dev13; do not overwrite a frozen environment to run a comparison.

```sh
python -I experiments/opportunities/campaign.py prepare --out /absolute/new-run
# Inspect the frozen cases, protocol and inputs before external execution.
python -I experiments/opportunities/campaign.py execute --out /absolute/new-run
python -I experiments/opportunities/campaign.py score --out /absolute/new-run
```

Execution is explicit: it invokes the signed-in Codex CLI and the pinned local
Ollama model, up to 64 native calls and six local calls. It never downloads a model,
switches authentication, invokes an API fallback or repeats an existing campaign.
Retain an interrupted run; a `dispatching` record may represent a consumed call.

The eight review cases cover clean text, critical contradictions, missing evidence
and explicit uncertainty. Direct Astra, two Astra roles and a Sol/Astra team receive
identical projected evidence. All arms select xhigh and a 1000-token skills catalog
budget; context comparison uses two extra fresh Astra calls with/without that budget.
Skills, user/project instructions and runtime controls stay enabled. The budget
affects catalog description space, not the complete model context or access policy.

A fresh Sol invocation audits the key before seeing candidate outputs. Separate
per-case Sol calls grade anonymous outputs; the implementation author then audits
the judgments. Same-family model errors remain possible, and this is not independent
human grading. In the September 15 run, the author graded anonymous outputs before
reading Sol's grades and the role mapping; disagreements remain explicit in the
[results](opportunities-implementation-report.md). Eight synthetic cases with one repetition are screening evidence,
not a reliable estimate of production error rate. Do not promote a team or cheaper
model because of green software tests alone.

Six log cases separately evaluate Sol and pinned Llama diagnosis. Three small JSON
configuration repairs are checked by exact host comparisons against a frozen key;
Sol gets one attempt, then Astra only after a rejected repair. These narrow tasks
do not qualify arbitrary documentation rewriting or test-code repair.

Historical campaigns and installed environments remain preserved locally under
`docs/receipts/`; they are intentionally excluded from the Git repository. Some
historical experiment tests require those local artifacts. CI selects portable and
native contract tests that do not depend on unpublished receipts.

Configuration behavior: [official Codex reference](https://learn.chatgpt.com/docs/config-file/config-reference).
CI structure: [GitHub matrix documentation](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/run-job-variations).
