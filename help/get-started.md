## Set up an isolated environment

**1.5.1 preparation:** Obtain the reviewed local candidate wheel and its source/hash record. The final release artifact is not yet selected. For an installation from the package index today, use the [published 1.5.0 instructions](/harness/help/1-5-0/). Do not request an unpublished 1.5.1 package from the index.

Use Python 3.10 or later. Keep Harness in its own environment: Harness and
Attune-AI pin different MCP SDK versions. Attune-AI is not required.

1. In a new working directory, create an environment: `python3 -m venv .venv`.
2. Activate it. On macOS or Linux, use `source .venv/bin/activate`. On Windows PowerShell, use `.venv\Scripts\Activate.ps1`.
3. Install the reviewed local validation wheel: `python -m pip install /absolute/path/to/attune_harness-1.5.1-py3-none-any.whl`.
4. Check the selected interpreter's installed version: `python -c "from importlib.metadata import version; print(version('attune-harness'))"`.
5. Run the local demonstration: `python -m attune_harness`.

**Expected result:** The validation version is `1.5.1`. The demonstration prints a JSON
receipt with a verified result. It uses a deterministic local worker and an
independent arithmetic check; it makes no model call. This result establishes
that example's check, not the quality of an AI participant.

## Choose the next outcome

- [Start and continue work](/harness/help/start-and-continue/): answer an existing draft's questions and review its intent.
- [Plan and accept work](/harness/help/plan-and-accept/): preview the allowed files and acceptance criteria before a build.
- [Research a question](/harness/help/research/): retrieve local sources and check a supported link claim.
- [Save and resume](/harness/help/save-and-resume/): reopen saved intake and understand execution boundaries.

The browser companion opens existing saved tasks. It does not provide a released
**New task** control in the inspected preparation source. The two form walkthroughs include a disposable
trainer fixture; sample answers are examples, not findings for your project.

## Prepare the release examples

The planning and research examples use files from the repository, which are not
included in the installed wheel. With the selected validation environment active, put the inspected source
checkout in an unused directory:

```sh
git clone --no-checkout https://github.com/Smart-AI-Memory/attune-harness.git harness-preparation
git -C harness-preparation checkout 0f2711b4c88ee4f231f61d71cd70a0c840be6357
```

Set `R` to that checkout's absolute path. In a macOS/Linux shell, from its
parent directory, use `R="$PWD/harness-preparation"`. The inspected preparation commit is
`0f2711b4c88ee4f231f61d71cd70a0c840be6357`. Verify it with `git -C "$R" rev-parse HEAD`.
The tutorial setup uses POSIX shell syntax; Windows command adaptation is not
newly tested here. Keep task records outside checkouts used for file effects.
The PowerShell activation command is reference syntax, not a newly qualified Windows walkthrough. On macOS use canonical paths; `/tmp` is a symlink to `/private/tmp`.

Read [dependencies and compatibility](/harness/help/dependencies/) before adding
optional providers or integrating with another host.

## Sources and verification limits

The 1.5.1 preparation baseline is the [reviewed changelog](https://github.com/Smart-AI-Memory/attune-harness/blob/0f2711b4c88ee4f231f61d71cd70a0c840be6357/CHANGELOG.md), [CLI guide](https://github.com/Smart-AI-Memory/attune-harness/blob/0f2711b4c88ee4f231f61d71cd70a0c840be6357/docs/cli-guide.md) and [metadata](https://github.com/Smart-AI-Memory/attune-harness/blob/0f2711b4c88ee4f231f61d71cd70a0c840be6357/pyproject.toml). The [preparation record](/harness/help/preparation.json) keeps the final-source/artifact gate open. The sources and observations below describe published 1.5.0, not a final 1.5.1 qualification.

Read the [released changelog](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/CHANGELOG.md), [CLI guide](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/docs/cli-guide.md), [dependency metadata](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/pyproject.toml) and [1.5.0 release notes](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/docs/release-notes-1.5.0.md). Published-release command checks and their limits are recorded in the [verification record](/harness/help/verification.json). Historical candidate observations retain their original artifact identity.
