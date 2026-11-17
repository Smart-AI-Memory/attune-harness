# Harness 1.8.1 release notes

Harness 1.8.1 fixes Windows path handling in prepared PowerShell commands.
Paths with spaces and special characters stay in their intended arguments,
and trailing backslashes preserve the following option. Python 3.12 or later
remains required.

[Version 1.8.1 is published on PyPI](https://pypi.org/project/attune-harness/1.8.1/).
The [release record](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.8.1)
identifies its artifacts and checks. The
[readiness record](release-readiness-1.8.1.md) retains the preparation evidence.

## Use your Windows project paths

Prepared commands for initialization, plan and repair previews, review intake,
and roundtable preparation preserve spaces, dollar signs, backticks,
apostrophes and Unicode characters. The change covers Windows PowerShell 5.1
and PowerShell 7. POSIX command rendering is unchanged.

In Windows PowerShell 5.1, a path containing whitespace and ending in
backslashes now reaches the native executable without consuming the next
option. PowerShell 7 retains its behavior in Windows, Standard and Legacy
argument modes. See the [PowerShell fix](https://github.com/Smart-AI-Memory/attune-harness/pull/364).

Preparing a command still does not accept a plan or start execution. Review
the saved scope and use the existing acceptance and execution steps.

## Find setup and follow the reporting course

Recent documentation updates make the Help Center and quickstart easier to
find, bring reporting practice into one maintained course, and improve lesson
readability, setup guidance and navigation. Open
[Get started](https://smartaimemory.com/harness/help/get-started/) to install
Harness, then [set up the reporting course](https://smartaimemory.com/harness/learn/).

The course retains its published 1.7.0 and 1.8.0 compatibility records and
historical walkthroughs. Those records describe the versions tested; they are
not new 1.8.1 course qualification. Website delivery has its own source and
import records, separate from package publication.

## Install and keep a rollback path

Select `attune-harness==1.8.1` explicitly in a separate Python 3.12 environment.
Keep your working runtime, participant registry, saved tasks and memory setup
until you have checked the workflows you use.

Existing Windows profile, process-recovery, storage and optional-provider
limits still apply. Follow the [installation guide](installation.md) and
[Windows capability guidance](supported-journeys.md#windows-capabilities-and-reliability).
The later [Windows ARM64 validation](windows-arm64-validation-1.8.1.md) installed
the published wheel with locally built, exact pinned dependencies and completed
bounded native workflows. That result does not make a binary-only native ARM64
installation from PyPI available or qualify every Windows desktop workflow.

The [1.8.0 release notes](release-notes-1.8.0.md) retain the earlier command
environment and memory changes. Package publication, the Claude Code
marketplace update, and Help Center or course publication remain separate
steps. Keep existing memory writers and host hooks in place.
