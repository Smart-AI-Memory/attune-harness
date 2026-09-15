# Fable and Opus review candidates

Patrick selected Fable as the next candidate on September 15, 2026, retiring
Llama from the intended workflow. Historical Llama experiments remain preserved.

[participants.fable.json](../participants.fable.json) selects a Claude Fable 5.1
lead (`claude-fable-5-1`) and an Astra/xhigh reviewer. The Fable identifier comes
from the local attune-ai model registry. This profile is configured and checked
offline; live model access and review accuracy have not been qualified.

Patrick also selected Opus for lighter work. The registry includes `opus-worker`
using `claude-opus-5`, the existing default in attune-ai's `models/editing.py`. Select
it as lead with `astra-reviewer` for a smaller-work candidate, or select
`fable-lead` and `opus-worker` for a Fable/Opus review. The current workflow uses
two selected roles; adding a third registry entry does not dispatch three agents.
Both Anthropic models remain unqualified for this workflow. This configuration
supports evidence reviews; code repair requires its own task and independent tests.

Using the current installed dev11 environment:

```sh
attune-harness review-form --config participants.fable.json
```

Fill and accept the generated request, selecting `fable-lead` and
`astra-reviewer`, or the Opus pairing above. The configured execution command, after live execution is
authorized, is:

```sh
attune-harness review request.json --config participants.fable.json --run-dir new-fable-review --allow-external
```

The host retrieves and verifies the supplied evidence before either model writes
a review. The two narratives remain proposals; a correct reviewer does not
automatically remove an incorrect lead finding. Independent grading and repair
checks are still required. No provider fallback is configured.

The existing Claude adapter selects the model explicitly but does not override
Claude reasoning effort. Its host setting remains in effect. Codex's catalog and
effort settings apply only to the Astra role.

Live qualification is pending Patrick's Anthropic API spending hold and subsequent
first-spend authorization. Do not use the saved eight-case campaign's `execute`
command for this profile: that immutable experiment is pinned to its original
Astra/Sol/Llama participants. A Fable comparison needs a separate frozen run.

The current default `participants.json` continues to select Astra. Fable and Opus
are quality candidates. Keep routine status monitoring deterministic and measure
cost per verified repair before selecting a worker by presumed savings. No Fable
or Opus cost advantage has been measured in this harness.
