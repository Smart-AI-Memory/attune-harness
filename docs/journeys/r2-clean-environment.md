# R2: the clean-environment journey

*September 23, 2026. Spec authority Task 4, step (c); the R2 line of [the
spec authority's acceptance](../specs/spec-authority/README.md) and decision 1
of [D23](../specs/spec-authority/addendum-2026-09-23.md).*

R2 says: "Plan/build completes an approved-spec journey in a clean environment
with Attune AI absent. The import check passes in CI." This is that journey as
it runs, command by command, with the envelope each step returns, from the
install a user gets: `pip install attune-harness` into a fresh virtual
environment, its base dependencies with it, nothing from Attune AI on the path.
No model is called at any step: the build's worker and reviewer are two
`command` participants running one local script, and the review's assessor is
the deterministic adapter.

The same sequence runs three times in the repository, so that this document
cannot drift from what the code does:

- as a test, `tests/test_r2_journey.py`, in the platform selection, so the
  three platforms run it against the installed wheel on every push, in a child
  process that blocks the `attune` package outright;
- as the `journey` section of `scripts/check_installed.py`, which every
  platform job runs from its installed wheel (the platform receipt's
  `r2_journey` carries the outcome) and which the release gate runs twice, from
  the `--no-deps` wheel and from a venv that installs the wheel with its base
  dependencies from the index under the lock files (`core.json` and
  `with-deps.json` in the `release-evidence` artifact, both asserted on);
- and here.

## Run it yourself

```bash
python -m venv .venv-r2
.venv-r2/bin/python -m pip install attune-harness
python scripts/check_installed.py --python .venv-r2/bin/python --mode all
```

The report's `journey` object is the receipt below; `--mode core` against a
`--no-deps` install gives the refusals in the last section.

## The fixture

A Git checkout of seven files: `source.py` (`value()` returns 1), `plan.md`
(the artifact), `baseline.py` (asserts `value() == 1`, the protected check),
`oracle.py` (asserts `value() == 42`, the verification probe's oracle),
`pytest.ini`, and `docs/guide.md` with `docs/reference.md` for the review. A
participants file with three entries: `local` and `critic`, both the `command`
adapter running the same script, and `assessor`, the `deterministic` adapter.
The script reads one JSON request on stdin and prints one JSON reply: as the
worker it proposes the files the step names (`pkg/export.py` with `answer()`
returning 42, a generated test, and `source.py` rewired to call `answer()`),
each with the SHA-256 of the text it saw; as the reviewer it returns an empty
critique.

The request names two tasks, `export` (creates `pkg/export.py` and the
generated test) and `wire` (rewrites `source.py`, depends on `export`), one
required host control (`baseline`, run in the build phase), the three
assignments, and a frozen `effects` manifest: the three files in scope, the
parents `pkg`, `tests` and `tests/generated`, the four protected files, the
control's probe (`python -B baseline.py`) and a verification probe per task
(`answer() == 42` for `export`; `python -B oracle.py` for `wire` and the final
state).

**The one step outside the command line.** `plan --request` accepts the frozen
manifest, and no command line verb freezes one, so that step is Python against
the installed package, the same call the build's own tests make:

```python
from attune_harness import work_effects
effects = work_effects.freeze(root, scope, parents, protected, checks,
                              task_directory, verification=verification)
```

The test freezes it in-process; the gate section runs the same program through
the checked interpreter. A `plan --freeze-effects` that takes these inputs as a
file would make the journey the command line end to end; it is a candidate for
the opportunity log, not a plan.

## The sequence

Digests below are from one run and differ on yours; every other value is
what the step returns. Paths are shortened.

**1. Draft the work.** Exit 0, `status: draft`.

```bash
attune-harness plan --task-dir work --project project \
  --config participants.json --request request.json
```

```json
{"status": "draft", "authority": "draft", "phase": "draft", "revision": 1,
 "checkpoint_digest": "7434f9ba…03a90",
 "summary": "Draft ready for review; work is not yet accepted.",
 "next_action": "Review this work record; use plan --accept with this exact --checkpoint.",
 "missing": [], "questions": {"missing": [], "markdown": "", "definition": null},
 "blocking": true,
 "note": "Intent acceptance, execution evidence and paid dispatch permissions are separate.",
 "tasks": [{"id": "export", "outputs": ["pkg/export.py", "tests/generated/test_app.py"]},
           {"id": "wire", "dependencies": ["export"], "outputs": ["source.py"]}]}
```

**2. Accept it, with the displayed checkpoint.** Exit 0, `status: accepted`.
The receipt's disposition is `approve_task`, the explicit console approval
through Harness's own collector; this is the step that needs the forms package.

```bash
attune-harness plan --task-dir work --accept --checkpoint 7434f9ba…03a90
```

```json
{"status": "accepted", "authority": "accepted", "phase": "accepted", "revision": 1,
 "checkpoint_digest": "58cbaee7…8dc7",
 "summary": "Work scope is accepted and ready for build.",
 "next_action": "Use build with this task directory and --checkpoint, supplying only explicitly authorized dispatch flags.",
 "receipt": {"disposition": "approve_task", "completed": ["9faf4385-…"],
             "save_state": {"auto_run": false, "task_receipts": [{"severity": "low", "score": 0,
               "detail": "Explicit console approval of the current work intent.\nGoal: Export every finding\n…"}]}},
 "decision": {"display": {"kind": "spec", "title": "Task 9faf4385-… gate", "markdown": "## Task … gate\n\nlow severity, score 0.\n…"}},
 "blocking": false}
```

**3. Build.** Exit 0, `status: completed`, `blocking: false`. The two command
participants are external processes, so `--allow-external` is required and
the deterministic path refuses without it. The execution evidence records the
control's run, then each task's worker turn, reviewer turn and verification
probe, with digests of every input.

```bash
attune-harness build work --allow-external
```

```json
{"status": "completed", "authority": "accepted", "phase": "build",
 "checkpoint_digest": "0464e99f…b999",
 "summary": "Build completed: protected checks passed and no high-severity reviewer finding blocks completion.",
 "next_action": "Review the saved checks, reviewer findings and any optional advice. No build retry is needed; passing checks do not prove every semantic claim.",
 "completed": ["export", "wire"], "preserved_completion": [], "blocking": false,
 "execution_evidence": {"runs": [{"phase": "build", "run_pointer": "/build",
   "operations": [{"operation": "control:baseline", "kind": "build_control", "category": "host_check", "…": "…"},
                  "…"]}]}}
```

After it, `project/pkg/export.py` begins `def answer():` and `source.py`
calls it; `baseline.py` and `oracle.py` are untouched.

**4. Review a document against the result.** Exit 0, `operation: task`,
`status: completed`. The review is the top-level document-assessment verb; its
verification context file lives inside the project, as the intake requires,
and its assessor is the deterministic participant.

```bash
attune-harness review --goal "Check the guide against the exporter's evidence" \
  --project project --config participants.json --document docs/guide.md \
  --context project/context.json --corpus docs --query exporter \
  --criteria "Identify unsupported claims and preserve uncertainty" \
  --assessor assessor --accept --task-dir review
```

```json
{"operation": "task", "status": "completed", "schema_version": 1,
 "checkpoint_digest": "247c7dc2…0b513", "task_profile": "assessment-intake-v1",
 "acceptance": {"accepted": true, "permissions": {"external": false, "provider": false}},
 "recovery": {"profile": {"kind": "task-intake", "version": 1}, "runtime": {"kind": "assessment", "version": 1}},
 "execution": {"status": "completed",
   "events": [{"operation_key": "preflight", "kind": "preflight_verification", "state": "completed",
               "result": {"operation": "verify", "status": "unknown", "dependency": {"name": "attune-verify", "version": "0.6.0"}, "…": "…"}},
              "…"]}}
```

**5. Read the state back.** Exit 0; the record says what the build said.

```bash
attune-harness status work
```

```json
{"status": "completed", "authority": "accepted", "phase": "build",
 "summary": "Build completed: protected checks passed and no high-severity reviewer finding blocks completion.",
 "completed": ["export", "wire"], "blocking": false}
```

The receipt the gate section writes for this run:

```json
{"forms_installed": true, "model_calls": 0, "plan": "draft", "accept": "accepted",
 "build": "completed", "review": "completed", "status": "completed",
 "participants": "two command participants running one local script; a deterministic assessor"}
```

## From the `--no-deps` wheel

The release gate keeps a `--no-deps` install beside the journey, for the
narrower proof that the core imports need only the standard library and that a
missing base dependency refuses with the install hint (D23.1). There the
journey stops at acceptance, and each refusal is in the words the gate asserts:

| Step | Exit | `status` | `error.detail` |
| --- | --- | --- | --- |
| `plan --request` | 0 | `draft` | |
| `plan --accept` | 2 | `failed` | `attune-forms is missing; reinstall with: pip install --force-reinstall attune-harness` |
| `build` | 2 | `failed` | `Effects require current accepted work authority` |
| `review` | 2 | `failed` | `attune-verify is missing; reinstall with: pip install --force-reinstall attune-harness` |
| `status` | 0 | `draft` | |

The build's refusal is the authority rule, not a missing package: nothing
accepted the draft, so there is no accepted work to build. The review names
attune-verify because its intake checks the verifier before the forms package;
the hint is the same either way. The Task 4 design note expected the build to
run from `--no-deps`; it cannot, and the note carries the correction.

## On Windows

The Windows platform jobs run the test and the gate section like the others.
Freezing the manifest there produces the `windows-feature-effects-v1` profile,
and the build either completes through it or refuses with a
`FeatureUnavailable` whose detail names Windows; the test and the receipt
record which of the two it saw rather than skipping. On the first run, in the
pull request that added the journey (#108, September 23, 2026), both Windows
jobs completed the whole journey, the build included: `windows-latest` with
Python 3.10 and with 3.12 each record `accept accepted, build completed, review
completed` in `platform.json`'s `r2_journey`, and the test passed there in
under six seconds. The build ran through the Windows effects profile, which
has its own qualification workflow; the golden envelope tests still skip the
`build` verb off POSIX, a reason string that now reads narrower than the
evidence.
