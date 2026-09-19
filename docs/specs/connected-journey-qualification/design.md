# Design note before the handoff change

The disposable baseline (receipt baseline.json) ran existing repair and testing
APIs: repair completed with verified-within-probe evidence and pytest passed, but
the test request carried no producing repair identity. The stages work separately;
the automatic association is missing. No provider participated in that probe.

Add one bounded reference to the existing testing request, exposed as
`test --from-task <completed-repair>`. Read the producer with shared task validation,
require completed repair/probe/review evidence, check current checkout and registry,
and derive the exact changed replacement paths. Bind task identity, request and
checkpoint digests, artifact/probe digests and record path. Test acceptance remains
separate and does not copy the repair's permissions. Existing standalone test
requests remain valid. Recheck the producer at intake, acceptance, execution and
status/reuse; a changed/missing record or checkout invalidates current success.

This is a dependency link between existing records, not a new journal, scheduler,
gate system or aggregate transaction. Assessment narratives remain unverified;
a human/executor selects the bounded repair scope. Existing Spec task-result and
collector semantics own consequential final decisions. Installed tests will drive
those real semantics with clearly labeled synthetic human actions. No product
claim of automatic assessment-to-repair planning is made.

Must pass: ordinary completed repair; required reviewer; explicit test subset;
standard broad fallback; pause and resume through repair/test; current Spec decision;
old standalone test records; unrelated initial dirty files preserved.
Must reject: unfinished/failed/non-repair producer; missing review; source/registry
or producer checkpoint change; supplied root/scope overriding the producer; stale
acceptance; lost producer; wrong test result; unavailable participant; uncertain
operation replay. Producer changes after passing retain history but invalidate
current qualification.

Rejected alternatives: filename-only receipt association (cannot prove origin);
a new workflow engine (duplicates authority/recovery); using a test pass to accept
a model narrative (different evidence); treating synthetic role peers as native
quality qualification. Native quality remains an explicit separate profile within
the same journey acceptance matrix.
