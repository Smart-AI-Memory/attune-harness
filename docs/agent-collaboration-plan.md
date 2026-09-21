# Agent collaboration: what is in force, and what is planned

How coding agents work together in this repository beyond the rules in
[AGENTS.md](../AGENTS.md). This file separates what applies today from what is
only intended, so nobody reads an aspiration as a rule.

## In force, as of 2026-09-21

- [AGENTS.md](../AGENTS.md) is the shared rule for every agent.
- Review is on the honour system. The author of a change does not review it,
  and a change that touches `src/` gets a review from a different model or from
  Patrick before it merges, recorded in the pull request.
- Nothing enforces that. Every agent acts through Patrick's single GitHub
  account, which is the repository's only collaborator, so GitHub cannot tell
  one agent from another or from Patrick. Branch protection requires a pull
  request and zero approvals. Requiring one approval today would block every
  pull request, because GitHub does not let an account approve its own.

## Planned option, not scheduled: separate identities and a required approval

Patrick wants this in time. It is an intention, not a commitment, and no agent
should act on it or set anything up.

Each agent vendor gets its own GitHub identity, a machine user or a GitHub App,
and `main` then requires one approving review.

What it buys:

- "The author does not review" is enforced, not trusted.
- Patrick becomes an eligible approver. Today he cannot approve any pull
  request, since his account authors all of them.
- Attribution comes from the identity that did the work, not from a trailer an
  agent writes about itself.
- The rule in AGENTS.md about which messages direct an agent becomes checkable,
  because a comment's author is then a real account.

What it costs. These are estimates and none has been tested here:

| Route | Patrick's setup time |
| --- | --- |
| Machine user for one vendor | about 1 hour |
| Machine users for two vendors | about 2 hours |
| One GitHub App per vendor | 3 to 5 hours, including a helper that mints installation tokens, which expire hourly |

After that, one approval per pull request. While only one vendor's agent is
active, Patrick is the only possible approver, and because protection is
enforced for admins, nothing merges while he is unreachable.

Order of operations, which matters:

1. Create the identity, give it write access, and point that vendor's agent at
   its credentials.
2. Merge one pull request authored by the new identity.
3. Only then set required approvals to 1.

Doing step 3 first blocks every pull request from Patrick's account. It is the
same trap as requiring a status check before the workflow reports it.

Settle these first, with a throwaway pull request:

- `main` requires signed commits. GitHub signs the squash commit, but every
  branch commit merged so far was already signed, so whether a pull request
  with unsigned branch commits merges is untested. The new identity may need
  its own signing key.
- Whether an approval from a GitHub App counts toward required reviews. This
  matters only for the App route.

Who does what: creating accounts, entering credentials and tokens, and changing
branch protection are Patrick's actions. An agent can write the checklist and
verify each step afterwards.

Smallest first step: a machine user for one vendor. That alone gives
enforcement, because Patrick can then approve.

Revisit when a second vendor's agent returns to regular work here. That is the
moment two agents' work actually meets.

## Aspirational goal, not scheduled: reproducible source distributions

This one is about releases, not about agents. It is recorded here because this
is the file that separates what is in force from what is only intended. Nobody
should act on it without Patrick asking.

In force: `publish-pypi.yml` sets `SOURCE_DATE_EPOCH` to the release commit's
time, and that makes the wheel reproducible. Measured on 2026-09-21 with
setuptools 84.0.0, two builds of one commit from trees with different file
times:

| | Wheel | Sdist |
| --- | --- | --- |
| `SOURCE_DATE_EPOCH` unset | differs | differs |
| `SOURCE_DATE_EPOCH` set | identical | differs |

The sdist differs because setuptools ignores the variable there. All 83 tar
members carried a checkout or build time, the gzip header carried the build
time, and the builder's user id and name were embedded. File names and contents
were identical.

The goal: a small script, `scripts/normalize_sdist.py`, that repacks the
`.tar.gz` with a fixed time, owner and gzip header, run in the build job before
`twine check` and the installed check, so the publish run's hashes can be
compared with the rehearsal's for both files.

What it needs first:

- A design note. The script rewrites the bytes that are uploaded to PyPI.
- Tests that build twice and require equal hashes, and that compare the
  repacked file list and contents with the original.
- A TestPyPI rehearsal, because the workflow changes. That is blocked until the
  `testpypi` environment allows a branch that exists; see
  [the release runbook](release-runbook.md).

Rejected for this goal: moving to a build backend with reproducible sdists. It
changes packaging for every user to fix a hash comparison.
