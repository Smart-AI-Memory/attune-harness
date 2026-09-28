# Moving from Attune AI to Harness

Migration guide drafted September 27, 2026. The rows describe the 1.0.0 core
release and its known gaps; they are not a notice that Attune AI is deprecated.
The candidate migration trial remains open. Confirm the installed artifact and
the host's actual workflow before replacing a working Attune AI path.

## Keep separate environments

Harness and Attune AI pin different MCP SDK versions. Keep Attune AI's existing
working environment and install Harness separately. Do not upgrade one package
inside the other's environment. Existing Attune AI skills and hydration can keep
running while a Harness successor is validated. No memory conversion or deletion
is required by this guide.

## Move one journey at a time

| Journey | Harness currently carries | What remains / what to use meanwhile |
| --- | --- | --- |
| Read existing memories | Native readers for the supported raw, personal and curated formats; Redis reads and serving under the configured roots. Installed checks cover bounded software behavior. | Keep existing writers. Do not change their formats without a Harness reader change first (D25/D28). Native file memory remains a documented Windows limit; use the POSIX profile through WSL2 where appropriate. |
| Hydrate and automatically recall across sessions | Serving consumes the existing hydrated Redis path; provenance and wrong/inactive filtering have tests. | The Attune AI SessionStart hydrate writer is not replaced. Keep that hook in its own environment. Validate real-session serving before switching a host hook. |
| Explicitly save memory or task intent | Harness 1.0.0 includes `memory saved` capture, search, revision, history and deferred opportunity-review checkpoints. Existing execution remains the owner of its task state. | Saved entries do not automatically feed fresh-session recall. Use explicit retrieval and keep execution evidence separately inspectable. |
| Plan, accept, build and inspect | The native Spec authority and installed deterministic R2 journey; status and recovery commands with retained evidence. | Native model-driven planning/building remain experimental. A completed deterministic journey does not qualify every model or project. Preserve interrupted records and use supported recovery. |
| Claude/Codex host workflow | Checkout-installable host plugin candidates, workspace MCP intake and presentation. | Candidates are not marketplace publication or complete lifecycle parity. M3 gates and observed host acceptance remain open; preserve the existing working host workflow until those hold. |
| Multi-agent workflows and roundtable | Explicit participant contracts and bounded workflow routes. | Full Attune AI multi-agent workflow/roundtable parity is a later milestone, not promised by stable core 1.0. Keep the existing workflow where required. |
| MCP tools | Accepted retrieval and workspace profiles with explicit scope. | This is not wholesale replacement of Attune AI's MCP tools. Compare required tools and profile schemas before changing a host's server configuration. |
| Executable extensions / Voyage | The bounded signed Python plugin profile has six installed-wheel platform receipts for signature/revocation, effective grants, cooperating import closure, subprocess bounds and host journals. One fixed public-corpus Voyage query completed eight live stages total across two paths (four matching request/result pairs); recorded replay and synthetic interruption passed across the platform matrix. | This is included in 1.0.0 but does not qualify arbitrary plugins, an OS sandbox, general ranking quality or live paid calls on each OS. Keep the current working provider setup until its exact signed artifact and effective grants are accepted; installation alone grants no paid-call authority. |
| Fix and test | Supported commands and retained check receipts within their declared profiles. | Follow the [qualification guide](qualification.md), especially Windows limits. A workflow port is not required to keep using the existing supported entry point. |

## Migration acceptance still open

Use this guide beside the installed 1.0.0 artifact and record each journey's outcome,
artifact version and evidence location. A row marked carried needs evidence from
that artifact; a missing successor needs a working, stated alternative. Record
interruptions and resume steps rather than marking a partial journey complete.
The observed non-programmer walkthrough remains unverified; writing these
instructions does not satisfy it.

Stable 1.0 and Attune AI's deprecation notice are separate events. The notice
waits for the approved host milestone and Patrick's decision; it is not implied
by this page. No release date or full parity promise is added here.

Authority: [D25–D30](specs/release-1.0/addendum-2026-09-23.md).
Current progress and remaining acceptance: [release plan](project-plan.md).
