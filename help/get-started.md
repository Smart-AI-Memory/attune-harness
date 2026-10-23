## Set up an isolated environment

Use Python 3.10 or later. Keep Harness in its own environment: Harness and
Attune-AI pin different MCP SDK versions. Attune-AI is not required.

1. In a new working directory, create an environment: `python3 -m venv .venv`.
2. Activate it. On macOS or Linux, use `source .venv/bin/activate`. On Windows PowerShell, use `.venv\Scripts\Activate.ps1`.
3. Install the released base package: `python -m pip install 'attune-harness==1.5.0'`.
4. Check the selected interpreter's installed version: `python -c "from importlib.metadata import version; print(version('attune-harness'))"`.
5. Run the local demonstration: `python -m attune_harness`.

**Expected result:** The version is `1.5.0`. The demonstration prints a JSON
receipt with a verified result. It uses a deterministic local worker and an
independent arithmetic check; it makes no model call. This result establishes
that example's check, not the quality of an AI participant.

## Choose the next outcome

- [Start and continue work](/harness/help/start-and-continue/): answer an existing draft's questions and review its intent.
- [Plan and accept work](/harness/help/plan-and-accept/): preview the allowed files and acceptance criteria before a build.
- [Research a question](/harness/help/research/): retrieve local sources and check a supported link claim.
- [Save and resume](/harness/help/save-and-resume/): reopen saved intake and understand execution boundaries.

The browser companion opens existing saved tasks. It does not provide a released
**New task** control in 1.5.0. The two form walkthroughs include a disposable
trainer fixture; sample answers are examples, not findings for your project.

## Prepare the release examples

The planning and research examples use files from the repository, which are not
included in the installed wheel. With the environment active, put a release
checkout in an unused directory:

```sh
git clone --branch v1.5.0 --depth 1 https://github.com/Smart-AI-Memory/attune-harness.git harness-1.5.0
```

Set `R` to that checkout's absolute path. In a macOS/Linux shell, from its
parent directory, use `R="$PWD/harness-1.5.0"`. The published commit is
`7caa86ab6d476e9599b08ff75a81bc816e60c382`. Verify it with `git -C "$R" rev-parse HEAD`.
The tutorial setup uses POSIX shell syntax; Windows command adaptation is not
newly tested here. Keep task records outside checkouts used for file effects.
The PowerShell activation command is reference syntax, not a newly qualified Windows walkthrough. On macOS use canonical paths; `/tmp` is a symlink to `/private/tmp`.

Read [dependencies and compatibility](/harness/help/dependencies/) before adding
optional providers or integrating with another host.

## Sources and verification limits

Read the [released changelog](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/CHANGELOG.md), [CLI guide](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/docs/cli-guide.md), [dependency metadata](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/pyproject.toml) and [1.5.0 release notes](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/docs/release-notes-1.5.0.md). Published-release command checks and their limits are recorded in the [verification record](/harness/help/verification.json). Historical candidate observations retain their original artifact identity.
