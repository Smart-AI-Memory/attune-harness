# Review with GPT-6 Astra at extra-high reasoning

The workspace profile [participants.json](../participants.json) selects two distinct
roles, `astra-lead` and `astra-reviewer`, both using the native Codex adapter with
`model: gpt-6-astra` and `reasoning_effort: xhigh`. This is an explicit worker
selection; it does not depend on the model selected in the current Codex chat.
It also sets `skills_context_tokens: 1000`, supported from dev10 onward. The
[measured context comparison](opportunities-implementation-report.md) explains
this catalog budget and its limits.

The profile also selects `review_mode: evidence`. The host runs retrieval and
verification first and attaches the response identifier in code. Each role makes
one model invocation for its final review; the model does not copy protocol hashes.

## Use the installed dev11 environment

From `/Users/patrickroebuck/attune-harness`:

```sh
source .venv-platforms/bin/activate
attune-harness review-form
```

Save the returned submission as a new request JSON, fill the document, local
evidence corpus, verification context, objective and query, select `astra-lead`
and `astra-reviewer`, and explicitly accept that request. Then run:

```sh
attune-harness review request.json --run-dir new-review --allow-external
attune-harness inspect-review new-review
```

Both commands default to the current directory's `participants.json`. Use
`--config /absolute/path/participants.json` to select it from another directory.
The profile is a workspace file; installing the Python wheel in another project
does not automatically create this registry. Existing explicit configurations
continue to select their own models. Preserved Llama experiments remain historical
reproductions, not the workspace's current review profile.

The Codex executable must be on PATH and already signed in. Harness passes
`--model gpt-6-astra -c 'model_reasoning_effort="xhigh"'` on every native invocation.
The profile permits up to three turns and two Harness tool calls per role, with a
300-second timeout per turn. In evidence mode, only the final turn invokes Codex;
the host handles the first two turns. It uses native prose review and the existing
correlated exchange, not the Ollama-specific `--grounded-passages` command. Omitting
`review_mode` retains the legacy native action protocol for old configurations.
Native runtime settings,
hooks and internal retries can still affect execution.

The accepted registry and form bind the exact effort and model. Resume requires
the original request, registry and checkpoint. A changed effort or catalog budget needs a new
accepted review; existing runs are not silently repointed. There is no automatic
fallback to another model.

## Interpret the result

Participant identities record `requested_model`, `requested_reasoning_effort` and
the actual dispatch arguments. Codex JSONL supplies a session ID, but the current
decoder does not receive server-attested model/effort identity; requested settings
must not be presented as such an attestation. A model's self-report is insufficient.

Workflow completion and successful source/tool checks do not certify the review's
semantic accuracy. See the [native evidence receipt](native-evidence-review-receipt.md) for
actual dispatch and validation evidence, and the [earlier quality results](passage-review-receipt.md)
for the separate Llama-based workflow that failed acceptance.
