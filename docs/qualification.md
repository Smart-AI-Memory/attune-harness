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

## Accuracy and worker qualification

The model campaign is frozen on dev10, separately from the dev11 platform work.
Use the preserved dev10 environment with the review extra. On a fresh clone,
commit `c2fa34038483ec7a028a50f554bf1a95e54039a5` contains that version; build and
install it in an isolated environment before invoking the campaign. The current
library remains dev11; do not overwrite a frozen environment to run a comparison.

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
