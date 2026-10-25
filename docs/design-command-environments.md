# Command environment first shipping slice

This design adds an explicit finite environment to configurable command
participants. It preserves omitted-policy behavior during the migration window.
It does not change native CLI, provider, plugin or generic process environments,
implement later removal, or claim an OS sandbox.

The public configuration and migration instructions are in
[Command participant environments](command-environments.md).

## Owners and boundaries

| Owner | Responsibility |
| --- | --- |
| `command_environment.py` | Validate names, select current assigned configurations, construct one dispatch snapshot, manage scratch lifetime, and produce names-only metadata and display notices. |
| `review_contract.py`, `consultation.py` | Admit the command-only policy in existing exact-field validators. Consultation keeps its owned process, cancellation and receipt behavior. |
| `review_participants.py` | Apply the common policy only to command transport. Add host-owned protected roots without changing custom exchange factory arguments. |
| `task_runtime.py`, `task_policies.py`, `work_runtime.py`, `work_build.py` | Supply existing corpus, checkout, project and task-state exclusions at command factory ownership points. Legacy review and recovery share the task runtime. |
| `consultation_preflight.py` | Check an absolute finite-profile executable directly; never search ambient PATH for it or execute configured wrappers. Native status probes retain their current behavior. |
| `consultation_cli.py`, `review_cli.py`, `task_cli.py`, `work_cli.py` | Add optional notices to detached final presentation envelopes using validated retained selections. Do not warn about unused registry entries. |
| `consultation_output.py`, `human_output.py`, `assessment_view.py`, `task_view.py` | Render the same notices in existing Markdown and HTML views without changing owner records. |
| `gui_build.py`, `gui_decisions.py`, `gui_forms.py` | Present notices before current decision and build grant controls. Keep nonces, decision bindings and record digests unchanged. |

These are 20 production files. Existing `features.with_deprecation` supplies the
notice schema. MCP has no command-participant dispatch route and requires no
schema change. GUI routes, generic recovery and storage owners are unchanged.

## Invocation and authority

1. Existing configuration validation admits the exact command policy. The policy
   and its named grants become part of the owner's existing accepted digests.
2. Existing admission checks verify grants, freshness and budgets before a
   participant turn. The command sink takes a fresh parent-environment snapshot.
3. The finite policy refuses relative executables, missing or invalid named
   values, ambiguous Windows names, invalid Windows baseline paths and scratch
   parents inside protected roots before creating scratch or invoking the child.
4. Scratch home and temp directories remain alive across the existing owned
   process call. Its timeout, cancellation and output bounds remain in force.
5. Cleanup runs after the process operation returns. Expected OS and recursive
   cleanup failures add a names-only failure flag without replacing the owned
   result or exception. Interrupt and exit exceptions retain their semantics.
6. New invocation metadata contains only the profile, policy digest and key
   names. Inspection and completed replay do not dispatch or rebuild environments.

Filesystem identity checks supplement path spelling for case aliases on
case-insensitive volumes. They enforce the scratch placement invariant; they
do not claim protection against an adversarial concurrent filesystem rewrite.
Explicit passthrough grants can restore baseline paths, including HOME and PATH.

## Compatibility and verification

Omitted-policy commands retain the original process-call argument shape and
identity shape, plus a Python warning at actual dispatch. Presentation notices
stay outside frozen records and their digests. Transferred assessment assignments
select the current participant. Existing custom exchange factories receive their
original positional and keyword arguments.

Focused tests exercise real synthetic child exclusion/inclusion, dispatch-time
rotation, cancellation, timeout, output limits, cleanup failure, case aliases,
Windows map rules, all factory ownership paths, native route spies, raw API and
saved-byte equality, presentation notices and browser text/grant boundaries.
The full source suite and a separately installed wheel qualify software behavior;
actual Windows results must come from CI. Neither is evidence of model quality.

The fixed prospective schedule is notice release 1.5.2 and removal no earlier
than 1.6.0. Release preparation must confirm the actual first notice release;
this slice does not change version metadata, publish a release or implement
removal. Later removal and any support-floor change require their own decision.
