## What a normal 1.5.0 install supplies

Harness requires Python 3.10 or later. Its released package metadata pins these
base dependencies. You do not need to install attune-forms separately for the
Harness forms journey.

| Package | Pinned version | Used for |
| --- | --- | --- |
| attune-forms | 0.17.0 | Rendered forms and answer collection |
| attune-rag | 1.2.0 | Local source retrieval |
| attune-verify | 0.6.0 | Supported verification checks |
| mcp | 2.2.0 | MCP integration |
| tiktoken | 0.12.0 | Token counting |
| packaging | 26.3 | Version compatibility checks |

These are Harness's **release pins**, not a claim that they are each package's
latest version. Independent dependency upgrades require compatibility review.
The [release package metadata](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/pyproject.toml) is authoritative.

## Add optional integrations only when needed

| Extra | Release dependency pins | Boundary |
| --- | --- | --- |
| redis | redis 5.3.1 | Optional Redis integration |
| voyage | voyageai 0.5.0, lancedb 0.38.0, pyarrow 25.0.1, jsonschema 4.26.0, httpx2 2.13.0 | Requires a Voyage key; retrieval makes paid calls |
| memory-native | anthropic 1.6.0, httpx2 2.13.0 | Experimental native memory; live-provider acceptance remains open |
| all | redis and voyage extras | Excludes experimental memory-native |

For example, install `'attune-harness[redis]==1.5.0'` in the isolated
environment if the requested integration needs Redis. `all` combines Redis and Voyage; the local examples
in this Help Center need only the normal base install. Installing an extra does
not grant execution authority or authorize spending.

## Integrate with a host

- [Codex plugin and standalone skill](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/docs/codex-plugin.md): install the host integration separately from the Python CLI, and verify its installed help.
- [Browser companion reference](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/.agents/skills/attune-harness/references/browser.md): open existing task forms through the selected interpreter; treat launch URLs as private.
- [CLI integration guide](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/docs/cli-guide.md): participant configuration, task execution and MCP setup. Keep Harness and Attune-AI in separate environments because of their MCP SDK pins.

## Read guidance for your version

- [Harness 1.5.0 release](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.5.0) and [1.5.0 CLI reference](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/docs/cli-guide.md): baseline for these pages.
- [Current main documentation — development](https://github.com/Smart-AI-Memory/attune-harness/tree/main/docs): may describe newer work; compare its version and evidence before using it.
- [Prototypes — unreleased](https://github.com/Smart-AI-Memory/attune-harness/tree/main/prototypes): design exploration, not released help.
- [Smart AI Memory documentation](https://smartaimemory.com/docs/): the product documentation index.

Browser build dispatch and execution resume are unavailable in Harness 1.5.0.
General workspace navigation and a browser specification editor remain outside the released forms interface. The walkthrough checks cover synthetic macOS examples. Full Windows parity, desktop and shell journeys, complete saved-store acceptance and live native-memory acceptance remain open; see the release notes.

## Changes and chronology

The [changelog](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/CHANGELOG.md) records the sequence: 1.3.0 supplied browser draft intake and intent approval; later changes under the prepared 1.4.0 heading refined approval labels, saved-request inspection and reload recovery. Those changes are present in published 1.5.0. The 1.5.0 release ships the stated Windows components while deferring full parity. The Unreleased 1.5.1 changes are not part of these instructions.

## Sources and verification limits

Read the [released changelog](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/CHANGELOG.md), [CLI guide](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/docs/cli-guide.md), [dependency metadata](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/pyproject.toml) and [1.5.0 release notes](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/docs/release-notes-1.5.0.md). Published-release command checks and their limits are recorded in the [verification record](/harness/help/verification.json). Historical candidate observations retain their original artifact identity.
