## Before you begin

Complete [Get started](/harness/help/get-started/) in a fresh working directory.
Keep the selected 1.5.1 validation environment active. `R` is the absolute preparation checkout
at commit `0f2711b4c88ee4f231f61d71cd70a0c840be6357`, as set in Get started; its example files are not in the wheel.
These examples use a POSIX shell and canonical paths. On macOS, use
`/private/tmp` instead of the `/tmp` symlink. Choose unused practice directories.
Windows desktop and shell journeys remain unqualified.

## Prepare the local corpus

Copy the example from the preparation checkout before retrieving or writing reports:

```sh
E="$PWD/training-research"
cp -R "$R/examples/local-workflow" "$E"
```

Choose an unused `E` directory outside the preparation checkout. The base install
includes local retrieval and verification. A fresh copy protects prior reports.

## Retrieve sources and verify a link

### 1. Retrieve local evidence

```sh
attune-harness retrieve "quartz retention policy" --corpus "$E/project" --output "$E/retrieval-report.json"
```

### 2. Inspect the sources

Read `retrieval-report.json`, then `project/reference.md`. Inspect both
returned sources, `guide.md` and `reference.md`, including excerpts and hashes.

### 3. Check the supported link claim

```sh
attune-harness verify "$E/project/guide.md" --context "$E/context.json" --output "$E/verification-report.json"
```

### 4. Inspect verification

Read `verification-report.json`. Check `status`, `passed`, `result.coverage`
and `result.semantic_ran`.

**Expected result:** Retrieval returns two Markdown sources. Verification returns
`verified`, `passed: true`, `result.coverage.total: 1` and
`result.coverage.verified: 1`. The `links` claim refers to `reference.md` at line
3 of the sample guide.

**Limit:** `result.semantic_ran` is false. This checks link validity; it does not
establish policy correctness. The example is local and makes no model or Voyage
call. Choose and authorize paid retrieval separately when a real task needs it.

## Verification and sources

For 1.5.1 preparation, compare the procedure with the [reviewed source](https://github.com/Smart-AI-Memory/attune-harness/blob/0f2711b4c88ee4f231f61d71cd70a0c840be6357/docs/cli-guide.md) and [preparation record](/harness/help/preparation.json). The final selected artifact still requires replay; the older observations below retain their original identity.

The [current verification record](/harness/help/verification.json) distinguishes fresh published-1.5.0 observations
from the retained [candidate walkthrough evidence](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/docs/tutorials-1.5.0-candidate.md).
The [changelog](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/CHANGELOG.md) supplies the change sequence;
[released CLI guidance](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/docs/cli-guide.md) and released UI source
supply the command and label baseline. Historical 1.3.0 observations remain
historical. These synthetic examples do not qualify Windows, all browser
ownership transitions, assistive technology, real participant quality or paid
providers. Approval and execution require separate decisions.
