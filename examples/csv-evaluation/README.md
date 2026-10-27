# Offline CSV evaluation fixture

This source-checkout example prepares and checks the CSV task from the
[performance evaluation plan](../../docs/specs/portable-user-journey/performance-evaluation.md).
It uses real Harness records, correction history, acceptance binding, bounded
file effects and protected subprocess checks. It uses no model, network service
or human participant. Scripted success is not evidence that Forms outperforms chat.

## Run the offline check

From the Harness checkout, use a Python 3.12 environment with the repository's
test dependencies. `PYTHONPATH=src` selects this checkout explicitly rather than
an unrelated installed Harness. On macOS, use `/private/tmp`, not its `/tmp`
symlink. The output directory must not exist; the fixture never overwrites or
cleans up an earlier attempt.

```sh
csv_fixture_parent=$(mktemp -d /private/tmp/harness-csv.XXXXXX)
PYTHONPATH=src python3.12 examples/csv-evaluation/fixture.py smoke \
  "$csv_fixture_parent/correction"
```

The default variant starts with a page/all-records question, records a scripted
all-records answer, corrects it to current page, binds explicitly synthetic
acceptance, then builds from a fixed known-good proposal. `--variant simple`
answers once; `--variant fully-specified` starts with no missing question.
Use a different unused output directory for each run.

Exit 0 means the offline build completed. Exit 1 means its retained build did
not complete; inspect the record, do not silently rerun it. Preparation errors
also exit nonzero. A synthetic acceptance receipt must never be carried into
a real human study or treated as Patrick's acceptance of feature work.

To prepare an unfinished, unaccepted draft without any execution:

```sh
PYTHONPATH=src python3.12 examples/csv-evaluation/fixture.py prepare \
  "$csv_fixture_parent/draft"
```

There is deliberately no provider/configuration option. The smoke command does
not execute a prepared draft: it creates its own new fixture. Human collection,
host UI qualification and a real model registry remain separate work and require
the evaluation plan's precollection ruling. This is not a ready-to-run live trial.

## Inspect the result

The output directory contains:

- `app/`: a dedicated synthetic Git checkout. Only `exporter.py` is editable by
  the build; `oracle.py`, `cases.json` and `task.md` are protected.
- `request.json`, `participants.json`, `prepared.json`: the original request,
  deterministic registry and preparation marker. The request is historical;
  `task/record.json` owns the effective corrected revision.
- `task/record.json`: correction history, explicitly synthetic acceptance,
  actual effect/check evidence and build outcome.
- `receipt.json`: offline software-check verdict, source/runtime fingerprints
  and explicit limits. Human/AI performance and token usage are `null`, not zero.
- `manifest.json`: SHA-256 hashes for retained task files, the final application
  files and the receipt. It excludes itself and is not a digital signature.

The oracle freezes expected row IDs for six cases in each export scope. It checks
filtering before pagination, row order, exact allowed columns/values, private-note
exclusion, quoting, multiline Unicode, partial/empty pages and empty results.
The known-good proposal is separate from the oracle. Tests deliberately supply
wrong exporters and verify that failed checks remain failed in the build journal.
Protected means the worker cannot edit those files through authorized effects;
it does not mean the cases are hidden from the build participant. The fixed
cases are workflow checks, not held-out evidence of general export correctness.

Run the fixture tests:

```sh
python3.12 -m pytest -q tests/test_csv_evaluation_fixture.py
```

These checks execute trusted local Python. They are not a sandbox for hostile
candidate code and do not establish general export security or human usability.
The host's installed/platform qualification remains separate from source tests.
