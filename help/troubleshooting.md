## The private form link stopped working

The form listener must remain running. A stopped listener invalidates its link.

1. In the original selected environment, start a listener for the same canonical task directory: `python -m attune_harness.gui --task "$TASK" --edit --launch-json`.
2. Keep the process running. Open its new private `launch_url`; do not reuse the previous link.
3. Inspect **View saved request** and **Saved goal:**. If the remaining form is hidden, click **Continue form**. For an accepted request, inspect **View accepted request**; it is read-only.

**Expected result:** Previously saved answers remain in the authoritative task
record. Unsaved typing is not guaranteed to survive. Launcher links contain
private access information; keep them out of public docs, screenshots and logs.

## A reload does not restore the form

Same-page reload can restore the current form when session storage, navigation timing and exclusive browser ownership remain usable. It does not replay a save or approve a request. If another tab owns the form, the checkpoint changed or a submission was unconfirmed, inspect saved state first, then click the displayed **Continue form** or **Review your answers** to reopen deliberately. After restarting the listener, always open its new private link.

## The form says the checkpoint is stale

Opening a new form or restarting the listener can expire the prior checkpoint.

1. Open the current form for the same saved task.
2. Read the current guidance and saved answers. Review any changed scope before accepting it.
3. Submit through the current form only when its answers and intent are correct.

**Expected result:** The decision is bound to the current preview. Do not replay
an older submission or edit task evidence to bypass the refusal.

## A dependency or command is unavailable

1. Check the installed distribution in the interpreter you selected: `python -c "from importlib.metadata import version; print(version('attune-harness'))"`.
2. Read the selected route's `--help` and the actual diagnostic. Follow the installed interface if it differs from this guide.
3. Compare your installation with [the release dependency map](/harness/help/dependencies/). A `--no-deps` installation omits the normal base dependencies; restore the normal install in a disposable isolated environment.

**Expected result:** The CLI and interpreter refer to one environment. Optional
integrations are installed only for the requested journey. Do not upgrade a
retained evidence environment or combine Harness and Attune-AI to clear a refusal.

## A task path is refused

Use an existing canonical absolute directory for browser registration. Resolve
symlinks before launching; on macOS, use `/private/tmp` rather than `/tmp`.
Task directories must sit outside checkouts used for file effects. Read the
route-specific refusal before moving or recreating anything.

## A result is paused, rejected or failed

Inspect `attune-harness status "$TASK" --format markdown` and retain its
evidence. A successful status command means inspection worked; it does not mean
the task passed. Resolve its stated next action and current authority before
resuming. Unknown or uncertain effects need reconciliation, not a blind retry.

If you need help, report the version, route, redacted diagnostic and expected
result through [Harness issues](https://github.com/Smart-AI-Memory/attune-harness/issues).
Do not include private launcher links, credentials or project data.

## Request-based retrieval refuses a session directory

Voyage request retrieval requires a fresh canonical directory for durable receipts. Include `--session-dir SESSION_DIR` with `retrieve QUERY --request REQUEST.json --allow-provider`; replace both paths with the reviewed request and an unused session directory. This option retains evidence; provider execution still needs its separate authorization. A refusal before session creation is not a completed retrieval.

## A process could not be stopped or reaped

In the 1.6.0 preparation source, shutdown guidance retains the original cause and
reports unknown effects. Preserve the saved task and process/file evidence.
Inspect **`status`**, check whether the original process is still active and
reconcile affected files before choosing a recovery action. Do not assume the
error terminated descendants, rolled back changes or authorized another dispatch.

Unsupported Windows volumes or paths are refused before use. Use the workflow's
fixed local NTFS/dedicated-checkout profile; do not bypass an integrity guard or
move authoritative records to clear an error. A reported unavailable feature
names its reason; browser build dispatch/resume needs the supported CLI instead.

## Sources and verification limits

Published 1.5.1 uses release commit `ebb5b03b8a4398325df7ddabd28c08186451452e`. Read its [CLI guide](https://github.com/Smart-AI-Memory/attune-harness/blob/ebb5b03b8a4398325df7ddabd28c08186451452e/docs/cli-guide.md) and [release record](/harness/help/release-1.5.1.json) for source, artifact and check identities. The [historical preparation record](/harness/help/preparation.json) retains its original candidate boundary. The older observations below are 1.5.0 evidence; they are not new 1.5.1 walkthrough results.

Historical 1.5.0 sources: [changelog](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/CHANGELOG.md), [CLI guide](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/docs/cli-guide.md), [dependency metadata](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/pyproject.toml) and [1.5.0 release notes](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/docs/release-notes-1.5.0.md). Published-release command checks and their limits are recorded in the [verification record](/harness/help/verification.json). Historical candidate observations retain their original artifact identity.
