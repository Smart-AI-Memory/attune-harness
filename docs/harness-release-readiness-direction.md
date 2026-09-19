# Harness release readiness — direction and proposed next step

Date: 2026-09-17. This records Patrick's corrected direction and a proposed
engineering method; it is not a wholesale implementation or release authorization.

## Patrick's direction

2026-09-17 steering: Patrick is leaning toward publishing Attune Harness and
deprecating Attune AI as soon as it makes sense. Prioritize documented Harness
release blockers, then shared value, then optional AI-only work. Keep reusable
validation in Harness while maintaining the compatibility adapters needed for
current journeys. This is direction, not a retirement date or release approval.
Memory preservation and the intended workflows and human controls must have
operational evidence before deciding the transition is ready.

Release Attune Harness soon, with reliability essential. Continue building on the
work on `/spec`. Agents, teams, workflows and other intended product features
must be connected and reliable. The verb interface is an important part of the
communication grammar. Existing memories must retain their useful value.

Experiments provide direction by identifying opportunities, approaches to revise
and approaches not worth pursuing. Installed integration and operational evidence
answer the separate question of readiness. Do not dismiss experimental evidence
merely because it is not a release receipt.

## Correction: preserve useful capability and refine deliberately

Patrick clarified: “I don't want you to subtract useful features.” The organic
growth of the product is the reason to inspect, integrate, grow and refine it
logically, using relevant, credible industry practice and academic evidence.
**Harness is Patrick's portfolio piece and must reflect his high standards.**

The earlier assistant framing around a smaller release scope is superseded. Its
A/B/C scope-reduction choice is withdrawn; no response is needed to it. Do not
treat a useful capability as expendable merely because its integration is hard
or incomplete. Track dependencies and evidence gaps to sequence the work, not
to redefine completeness downward. No feature subtraction is authorized.

An inventory should map every intended capability to its user value, actual
implementation, callers, agent/team roles, services, human decisions, outputs and
recovery path. Component-level passing tests do not prove these parts operate
together. The purpose of this map is to identify what to preserve, connect,
repair or improve and to reveal what is only advertised or partially wired.

## Proposed engineering method

1. Establish current useful behavior and integration baselines before changing
   interfaces or implementation. Preserve memory content and useful legacy paths.
2. Reuse the existing research and receipts, verifying their premises against the
   current code. Form a specific engineering question for each material gap.
3. Consult relevant primary industry sources and academic research. State what
   the source actually establishes, its limitations and its applicability here;
   publication or popularity alone is not proof that a practice fits Harness.
4. Compare concrete alternatives. Use a bounded experiment when evidence is
   insufficient or the tradeoff is material. Preserve unsuccessful results.
5. Implement through the evolving spec and grammar, connecting the actual agents,
   teams, workflows, services and verb commands to one coherent lifecycle.
6. Qualify complete installed journeys, including human control, failure,
   interruption, recovery and rollback. State supported hosts and limitations.
7. Retain an auditable chain from user value through source evidence, design
   judgment, experiment, implementation and acceptance. This is portfolio-quality
   engineering evidence, not a requirement to maximize paperwork or add model
   committees to routine work.

Research helps decide what to pursue, change or stop. Product qualification
establishes whether the chosen implementation works reliably. Both are valuable;
neither should be used to dismiss the other. Useful features remain part of the
product objective while their implementation and qualification are improved.

## Reflection cadence — Patrick's instruction

Focus on each spec element and pause at appropriate intervals to reflect and
learn from the work. Use meaningful checkpoints: completion of an element,
surprising evidence or repeated difficulty. State what the evidence showed,
what an assumption or method got wrong, and what should change next. Retain
useful lessons and verify how the element interacts with the complete journey.
These are working checkpoints, not new routine user-approval gates. Existing
independent review and acceptance obligations remain in force.

## Starting evidence, not a completed feature inventory

| Area | Current evidence or gap | Required journey-level question |
|---|---|---|
| Spec, plan and build | `docs/specs/plan-build/tasks.md` is explicitly a scoping draft; no executable plan or accepted tasks | Can a real goal become an accepted spec and a correct feature through the same work record? |
| Human verbs and grammar | Current CLI help includes review/fix/status/resume; plan/build/ship/reflect are not executable commands | Can the person guide work, challenge a proposal and disposition findings without losing the current revision or decision? |
| Agents and teams | The phased roadmap records bounded role, protocol and recovery receipts plus unqualified combinations | Do the selected lead, worker, reviewer and team paths hand off actual evidence and fail visibly when a participant is unavailable? |
| Workflows and services | Existing integration receipts must be mapped to actual callers and deployed artifacts | Does each intended workflow reach the same supported implementation from CLI and host entry points? |
| Memory | All five adoption tasks accepted at revision 23; 151 installed checks and 24 rollback checks passed on the declared macOS/Python profile; fresh dependency resolution and live native use remain unqualified | Which remaining installation and live-use qualifications are required by the intended release journeys? |
| Forms | Native question disappearance investigation is underway | Can a person read and answer without a hover, timer or task transition losing the decision surface? |
| Recovery and rollback | Bounded existing receipts; need mapping to each selected release journey | Can interrupted and uncertain work be inspected and resumed without silently repeating effects? |

Proposed acceptance for each advertised journey: installed entry point reaches the
intended implementation; relevant evidence is retained; expected and deliberately
wrong outcomes are distinguishable; applicable quality gates govern real effects;
interruption, unavailable dependency and stale decisions have tested outcomes;
rollback and supported host/platform limits are stated. Native/model claims need
their own evidence and the existing spend authorization.

The shared-memory ladder is complete under its existing approval. This document
adds no wholesale feature-implementation, release or deprecation action.
