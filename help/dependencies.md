## What the inspected base install supplies

Current development source requires Python 3.12 or later. Published 1.5.1
retains its Python 3.10 minimum and uses the dependency pins below. The release
version for the new minimum remains open. You do not need to install attune-forms separately for the Harness forms
journey.

| Package | Pinned version | Used for |
| --- | --- | --- |
| attune-forms | 0.17.0 | Rendered forms and answer collection |
| attune-rag | 1.2.0 | Local source retrieval |
| attune-verify | 0.6.0 | Supported verification checks |
| mcp | 2.2.0 | MCP integration |
| tiktoken | 0.12.0 | Token counting |
| packaging | 26.3 | Version compatibility checks |

These are the inspected **dependency pins**, not a claim that they are each package's
latest version. Independent dependency upgrades require compatibility review.
The [release package metadata](https://github.com/Smart-AI-Memory/attune-harness/blob/ebb5b03b8a4398325df7ddabd28c08186451452e/pyproject.toml) is authoritative.

## Add optional integrations only when needed

| Extra | Release dependency pins | Boundary |
| --- | --- | --- |
| redis | redis 5.3.1 | Optional Redis integration |
| voyage | voyageai 0.5.0, lancedb 0.38.0, pyarrow 25.0.1, jsonschema 4.26.0, httpx2 2.13.0 | Requires a Voyage key; retrieval makes paid calls |
| memory-native | anthropic 1.6.0, httpx2 2.13.0 | Experimental native memory; live-provider acceptance remains open |
| all | redis and voyage extras | Excludes experimental memory-native |

For example, install `'attune-harness[redis]==1.5.1'` in the isolated
environment if the requested integration needs Redis. `all` combines Redis and Voyage; the local examples
in this Help Center need only the normal base install. Installing an extra does
not grant execution authority or authorize spending.

## Integrate with a host

- [Codex plugin and standalone skill](https://github.com/Smart-AI-Memory/attune-harness/blob/ebb5b03b8a4398325df7ddabd28c08186451452e/docs/codex-plugin.md): install the host integration separately from the Python CLI, and verify its installed help.
- [Browser companion reference](https://github.com/Smart-AI-Memory/attune-harness/blob/ebb5b03b8a4398325df7ddabd28c08186451452e/.agents/skills/attune-harness/references/browser.md): open existing task forms through the selected interpreter; treat launch URLs as private.
- [CLI integration guide](https://github.com/Smart-AI-Memory/attune-harness/blob/ebb5b03b8a4398325df7ddabd28c08186451452e/docs/cli-guide.md): participant configuration, task execution and MCP setup. Keep Harness and Attune-AI in separate environments because of their MCP SDK pins.

## Read guidance for your version

- [Harness 1.5.1 release](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.5.1) and [getting started](/harness/help/1-5-1/): current installation and limits.
- [Harness 1.5.0 release](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.5.0) and [1.5.0 CLI reference](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/docs/cli-guide.md): historical release guidance.
- [Current main documentation — development](https://github.com/Smart-AI-Memory/attune-harness/tree/main/docs): may describe newer work; compare its version and evidence before using it.
- [Prototypes — unreleased](https://github.com/Smart-AI-Memory/attune-harness/tree/main/prototypes): design exploration, not released help.
- [Smart AI Memory documentation](https://smartaimemory.com/docs/): the product documentation index.

Browser build dispatch and execution resume are unavailable in Harness 1.5.1.
General workspace navigation and a browser specification editor remain outside the released forms interface. The walkthrough checks cover synthetic macOS examples. Full Windows parity, desktop and shell journeys, complete saved-store acceptance and live native-memory acceptance remain open; see the release notes.

## Changes and chronology

The [released changelog](https://github.com/Smart-AI-Memory/attune-harness/blob/ebb5b03b8a4398325df7ddabd28c08186451452e/CHANGELOG.md) records the sequence. Published 1.5.0 introduced the stated Windows components while deferring full parity. Published 1.5.1 adds signature-input validation, completed-assessment evidence presentation and documentation/continuation checks. Historical 1.3.0, candidate and 1.5.0 observations retain their original source and artifact identities. Read the [1.5.1 guide](/harness/help/1-5-1/) for current installation and limits.

## Sources and verification limits

Published 1.5.1 uses release commit `ebb5b03b8a4398325df7ddabd28c08186451452e`. Read its [CLI guide](https://github.com/Smart-AI-Memory/attune-harness/blob/ebb5b03b8a4398325df7ddabd28c08186451452e/docs/cli-guide.md) and [release record](/harness/help/release-1.5.1.json) for source, artifact and check identities. The [historical preparation record](/harness/help/preparation.json) retains its original candidate boundary. The older observations below are 1.5.0 evidence; they are not new 1.5.1 walkthrough results.

Historical 1.5.0 sources: [changelog](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/CHANGELOG.md), [CLI guide](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/docs/cli-guide.md), [dependency metadata](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/pyproject.toml) and [1.5.0 release notes](https://github.com/Smart-AI-Memory/attune-harness/blob/7caa86ab6d476e9599b08ff75a81bc816e60c382/docs/release-notes-1.5.0.md). Published-release command checks and their limits are recorded in the [verification record](/harness/help/verification.json). Historical candidate observations retain their original artifact identity.
