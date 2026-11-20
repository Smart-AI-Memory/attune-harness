## What the inspected base install supplies

[Install Harness 1.8.1](/harness/help/get-started/#install-harness) with Python
3.12 or later. The base package installs these dependencies. It includes
`attune-forms` for the Harness forms workflow.

| Package | Pinned version | Used for |
| --- | --- | --- |
| `attune-forms` | `0.17.0` | Rendered forms and answer collection |
| `attune-rag` | `1.2.0` | Local source retrieval |
| `attune-verify` | `0.6.0` | Supported verification checks |
| `mcp` | `2.2.0` | MCP integration |
| `tiktoken` | `0.12.0` | Token counting |
| `packaging` | `26.3` | Version compatibility checks |
| `certifi` | `2026.10.23` | TLS certificate authorities |
| `cryptography` | `50.0.2` | Cryptographic operations |

Keep these versions when adding integrations to 1.8.1. See the
[signed release's package metadata](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.8.1/pyproject.toml)
for the exact dependency declarations.

## Add optional integrations only when needed

| Extra | Release dependency pins | Requirements |
| --- | --- | --- |
| `redis` | `redis` `5.3.1` | A separate Redis service that meets the [operation's requirements](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.8.1/docs/cli-guide.md#redis-requirements). |
| `voyage` | `voyageai` `0.5.0`, `lancedb` `0.38.0`, `pyarrow` `25.0.1`, `jsonschema` `4.26.0`, `httpx2` `2.13.0` | Voyage retrieval requires credentials and separate approval for paid calls. |
| `memory-native` | `anthropic` `1.6.0`, `httpx2` `2.13.0` | Experimental native memory. See the [qualification guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.8.1/docs/qualification.md) for the tested profiles. |
| `plan-oauth` | `Authlib` `1.9.3`, `joserfc` `1.8.0` | The **`openai-plan`** adapter requires macOS arm64 with CPython 3.12.2. See [participant funding](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.8.1/docs/participant-funding.md) for consent and execution requirements. |
| `all` | `redis` and `voyage` | Select `memory-native` or `plan-oauth` separately when required. |

For example, install the Redis extra in a selected, isolated Python 3.12
environment:

```sh
python -m pip install 'attune-harness[redis]==1.8.1'
```

For uv or Windows instructions, follow the
[1.8.1 installation guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.8.1/docs/installation.md#choose-optional-integrations-when-needed).

## Integrate with a host

- [Codex plugin and standalone skill](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.8.1/docs/codex-plugin.md): prepare the workflow plugin from the release source and install the Python runtime separately.
- [Claude Code setup](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.8.1/docs/installation.md#connect-the-agent-and-open-a-first-task): install the host plugin separately and check its version.
- [CLI and MCP guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.8.1/docs/cli-guide.md): configure participants, use task commands and set up MCP. Keep Harness and Attune AI in separate Python environments because they require different MCP SDK versions.

## Read guidance for your version

- [Harness 1.8.1 release documentation](https://github.com/Smart-AI-Memory/attune-harness/tree/v1.8.1/docs)
- [Harness 1.5.1 guide](/harness/help/1-5-1/) and [1.5.1 dependency reference](https://github.com/Smart-AI-Memory/attune-harness/blob/5929c18c542a667a8a175a06b67ca5f2f571b73a/help/dependencies.md)
- [Documentation archive](/harness/help/archive/)

## Changes and chronology

Read the [1.8.1 release notes](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.8.1/docs/release-notes-1.8.1.md)
and [released changelog](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.8.1/CHANGELOG.md)
for changes that affect upgrades.

## Sources and verification limits

The [1.8.1 Python distribution](https://pypi.org/project/attune-harness/1.8.1/)
and its [signed source tag](https://github.com/Smart-AI-Memory/attune-harness/tree/v1.8.1)
identify the package pins. Use the
[1.8.1 Windows capability table](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.8.1/docs/supported-journeys.md#windows-capabilities-and-reliability)
to choose a profile. The [historical verification record](/harness/help/verification.json)
identifies the earlier walkthroughs and their environments.

## 1.6.0 Redis requirements and limits

The [1.6.0 release record](/harness/help/release-1.6.0.json) documents the
original Redis 7.4.7 and Search 2.10.20 checks on macOS arm64. For 1.8.1,
use the operation-specific Redis requirements linked above. Keep existing
service data, memory writers, and session hooks while checking an upgrade.
