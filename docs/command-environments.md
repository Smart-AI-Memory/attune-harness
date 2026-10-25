# Command participant environments

Add `environment` to a trusted `command` participant configuration to opt in to
`command-env-v1`. The policy applies to consultation, review, assessment, repair,
planning and build command participants. Native CLI adapters, provider clients,
signed plugins and the generic process runner keep their existing behavior.

```json
{
  "adapter": "command",
  "command": ["/absolute/path/to/python", "-I", "/absolute/path/to/peer.py"],
  "timeout": 30,
  "tools": [],
  "max_turns": 1,
  "max_tool_calls": 0,
  "environment": {
    "profile": "command-env-v1",
    "passthrough": ["SERVICE_TOKEN"]
  }
}
```

Replace both example paths with existing absolute paths. On Windows, use a
fully qualified drive or UNC path, such as `C:\\Tools\\Python\\python.exe` in
JSON. `C:python.exe`, `\\python.exe` and a bare executable name are refused.
Consultation seats use the same `environment` object with their existing
`identity`, `timeout` and `command` fields.

The passthrough list grants exact variable names from the parent process at
each dispatch. It accepts at most 64 portable ASCII names, each at most 128
characters. Names must be distinct ignoring case. POSIX lookup is case-sensitive;
Windows lookup ignores case and refuses ambiguous spellings. Missing declared
variables and invalid values refuse dispatch. An explicitly present empty value
is allowed. The configuration contains no secret values or wildcards.

The finite baseline contains:

- `PATH`: Python's system default search path on POSIX; absolute `System32` and
  Windows directory entries derived from `SystemRoot` on Windows.
- `HOME`, `TMPDIR`, `TMP` and `TEMP`: directories owned by this invocation.
  Windows also sets `USERPROFILE`, `APPDATA` and `LOCALAPPDATA` under the temporary
  home, and sets `SystemRoot` and `WINDIR` from the validated Windows root.
- `LANG=C`, `LC_ALL=C`, `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`,
  `PYTHONDONTWRITEBYTECODE=1` and `PYTHONNOUSERSITE=1`.

An explicit passthrough grant overrides a baseline value. Granting `HOME`,
`USERPROFILE` or `PATH` deliberately restores access to that parent setting;
consider what the command can then discover or execute. Command wrappers that
use provider authentication must name their required variables explicitly.
The policy does not strip credentials from native CLI or provider adapters.

The scratch parent comes from the host's temp-directory setting, or a fixed OS
fallback when no setting is present. It must exist outside the command working
directory and the host's protected source, corpus and task-state roots. Path
aliases are checked by filesystem identity. The policy ignores `tempfile`'s
cached directory. Scratch remains available until the owned process operation
returns, then cleanup runs. An OS or recursive cleanup failure retains the owned
outcome and records `scratch_cleanup: "failed"`; it does not claim removal.

This policy filters environment inheritance. It is **not an OS sandbox**. It
does not block file access, native credential stores, networking, OS-added
environment variables or a command that reads other host resources. A child
can print a secret it has accessed; the existing output receipts are not a
general secret-redaction system.

## Authority and retained records

The policy object is part of the accepted participant configuration and its
existing digests. Add or change it before preparing or accepting work; changing
accepted configuration requires the owner's existing revision and acceptance
flow. Values are copied only when the command is dispatched. A later accepted
turn can therefore use a rotated named credential without storing its value in
the configuration. Replay of completed work does not rebuild an environment or
dispatch another command.

New command identity metadata records the profile, the policy digest and the
actual environment key names. It records no values or value fingerprints.
Migration notices are added only to display copies and Python warnings at an
actual legacy dispatch. Saved records, receipt bytes, checkpoints, form digests
and acceptance bindings are not rewritten to add notices. An unused legacy
registry entry does not produce a usage notice.

## Migrate legacy configurations

Omitting `environment` retains full parent inheritance during the compatibility
window. Selected legacy commands show notices in CLI and GUI presentations;
Python dispatch emits `CommandEnvironmentDeprecationWarning`. Add the finite
policy and explicit names, validate the absolute executable, then prepare or
revise and accept the configuration through its existing owner.

The prospective notice release is **1.5.2**, with removal **no earlier than
1.6.0**. The release gate must confirm the first actual notice release matches
that schedule before shipping. This implementation does not remove the legacy
form, change the package version or authorize a release.
