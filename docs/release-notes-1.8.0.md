# Harness 1.8.0 release notes

Harness 1.8.0 keeps existing command participant configurations working and
adds internal checks for preparing memory hydration. It requires Python 3.12
or later. For the candidate artifacts, check results, and publication status,
see the [1.8.0 readiness record](release-readiness-1.8.0.md).

## Keep legacy command participants working

A command participant that omits the `environment` policy still inherits the
full parent environment in 1.8.0. The notice first shipped in 1.6.0. The
earliest removal moves from 1.8.0 to 1.9.0. The runtime notice and the
[active deprecation register](deprecations.json) use the same schedule.

To grant only the variables a command needs, configure the opt-in
`command-env-v1` profile and list the exact names. Follow the existing
preparation and acceptance process. See
[command participant environments](command-environments.md#migrate-legacy-configurations).

## Keep your memory writer and host hooks

Harness adds internal preparation for a four-layer memory projection and
checks whether its source inputs have changed. It also reduces repeated scans
in bare-key secret checks while preserving the existing matching rules.
These changes are groundwork for the hydration writer. Continue using your
existing writer and startup hooks to publish and deliver memory. A supported
**`memory hydrate`** command, Redis generation publication and cleanup, and
automatic fresh-session delivery remain outside this release. See the
[preparation increment](specs/native-memory/hydration-writer/preparation-increment.md)
and [migration guide](migration.md).

## Install and keep a rollback path

Before publication, install the exact reviewed 1.8.0 wheel in a separate
environment. After publication, select `attune-harness==1.8.0` explicitly.
Keep your previous runtime, participant registry, saved tasks, and memory setup
until you have checked the workflows you use. Follow the
[installation guide](installation.md#check-the-180-candidate) and
[Windows reliability guidance](supported-journeys.md#windows-capabilities-and-reliability).
The release workflow verifies the exact candidate wheel on Windows Server.
Windows 11 desktop qualification remains separate.

The [published 1.7.0 release](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.7.0)
has its own source and artifact records. The
[Help Center](https://smartaimemory.com/harness/help/) and
[six-lesson course](https://smartaimemory.com/harness/learn/) use published
1.7.0 for onboarding and practice. The Claude Code marketplace selects its
own tagged plugin. Package publication, the marketplace update, and website
delivery each have a separate step.
