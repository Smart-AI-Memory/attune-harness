# Task 4 — accepted file effects and controls

The trusted host prepares an optional `posix-feature-effects-v1` manifest in the
existing work request before its Spec acceptance. It freezes the dedicated local
Git checkout identity, complete bounded tree, exact editable files, exact missing
parent directories, protected acceptance inputs and trusted hook/check commands.
The existing acceptance binds the complete request. A worker supplies only file
paths, expected preimage hashes (null for creation) and bounded UTF-8 contents.
It cannot add permissions, choose checks or edit the accepted authoring artifact.

This slice supports one effect batch, at most 20 files, 20 explicitly declared
parents, 64 KiB per edited file, 1,000 snapshot entries and 16 MiB of source bytes.
The accepted operation budget also bounds controls plus file/directory operations.
No deletion operation exists. Existing unrelated dirty files and repository
metadata remain in the snapshot and must remain unchanged. A local `.git`
directory is required; worktrees with `.git` indirection are outside this profile.

Required build controls need exact owner, ID, kind and version matches. Declared
support alone is insufficient. Configured trusted hooks/checks use the existing
bounded subprocess runner with explicit interpreter, arguments, cwd, timeout,
output budget and minimal environment. Their complete bounded stdout/stderr and
command remain in the task journal. Every required control is resolved before
any command runs; all configured checks finish before the first file effect.
Failure, missing controls or uncertain execution blocks writes. An advisory
nonzero exit remains visible; timeout, invalid output or changed checkout blocks
even an advisory runner. Required host/human/guidance runners remain unsupported
here; instructions do not masquerade as enforcement. Required controls from
planning/acceptance phases also block effects because this slice has no qualified
execution receipt for them. Planning controls keep
their earlier fail-closed boundary until their own runner integration is ready.

Control configuration, executable identity and current checkout are checked on
resume. A completed control is reused only for this same immutable batch; it is
not a reusable approval for another change. The internal host checks enforce
accepted revision, storage owner, file scope, protected inputs, exact preimages,
operation budgets and complete snapshot transitions. This is bounded local
execution of trusted programs, not a security sandbox or a no-network guarantee.

The existing RunStore lease and RecoveryCursor persist prepared and dispatching
events before effects. Parent creation is explicit and ordered. New files use
exclusive creation, no symlink following, bounded writes and file/parent fsync.
Replacement reuses the existing repair owner and its staging/replacement checks.
No operation is silently repeated after an uncertain dispatch. Completed file
events are matched to their proposed bytes; controls to their original invocation.

Explicit reconciliation observes the whole checkout. An exact after-state is
fsynced again before being recorded complete; an exact before-state permits one
explicit retry. Partial bytes, foreign collisions, extra files, changed protected
inputs or a leftover replacement staging file remain unresolved and preserved.
Observation establishes state under the exclusive-owner assumption, not which
process originally created identical bytes. Process-death and injected fsync
tests do not prove survival of hardware failure or arbitrary power loss.

The task record owns the optional build journal; its presence does not rewrite
the earlier acceptance checkpoint. A completed batch is not Spec task acceptance
or proof the feature meets its requirements. The existing Python host projection
is used in synthetic acceptance fixtures. Actual collector integration remains
Task 6, dependent feature execution Task 5, installed verbs Task 7 and native
outcome qualification Task 8. Revising a work record with build effects is blocked
until the journal-preserving rebase/intervention path is qualified. Existing
legacy repair/planning records and routes remain available.

Falsifiable checks: wrong scope/preimage, implicit parents, edited protected
inputs, missing/failed controls, collisions, links, stale source/configuration,
changed root identity and unsupported platform refuse writes. Actual process
death, failed fsync and lost acknowledgments retain uncertainty. Exact recovery
avoids repeated writes; partial files remain intact. Targeted guard removals must
make their corresponding negative cases fail. No paid/native trial is required.
