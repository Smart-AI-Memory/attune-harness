# Harness 1.8.1 on Windows ARM64

Observed November 16, 2026. These results cover Windows 11 Pro build 26200 in
Parallels, native ARM64 CPython 3.12.10, a standard user account and local NTFS.
They are separate from earlier runs of x64 Python under emulation.

**Published Harness 1.8.1 completed bounded native ARM64 workflows with two
locally built dependency wheels.** A binary-only base installation from PyPI
alone remains blocked: the checked PyPI inventories for the pinned
[`tiktoken==0.12.0`](https://pypi.org/project/tiktoken/0.12.0/#files) and
[`cryptography==50.0.2`](https://pypi.org/project/cryptography/50.0.2/#files)
did not include Windows ARM64 wheels. This experiment did not change Harness's
dependency pins or publish replacement binaries.

For installation without a compiler toolchain, use x64 CPython 3.12 in a new
environment, including under emulation on an ARM64 device. Follow the
[installation guide](installation.md#install-181-with-pipx-or-a-virtual-environment)
and [Windows workflow requirements](supported-journeys.md#windows-capabilities-and-reliability).
Python 3.10 is unsupported by Harness 1.8.1; the package requires Python 3.12 or later.

## Published 1.8.1 with the exact pinned dependencies

The installation used the unchanged published Harness wheel, locally built
Windows ARM64 wheels for tiktoken 0.12.0 and cryptography 50.0.2, and the five
release constraint files. The local wheelhouse supplied both native dependencies;
this was not an installation from PyPI alone. Both extensions reported PE machine
`0xAA64`. Cryptography used static ARM64 OpenSSL 3.5.9, with no OpenSSL DLL imports
or runtime `OPENSSL_DIR` setting.

| Check or workflow | Observed result | Boundary |
| --- | --- | --- |
| Fresh binary-only base installation using the local wheels | Passed; selected wheel paths and hashes matched; `pip check` found no broken requirements | Both experimental wheels were supplied locally |
| Native token and crypto operations | BPE merge and Unicode round trip, AES-GCM, Ed25519 and signed JWT checks passed, including tamper rejection | Token checks used synthetic ranks, not a complete model vocabulary |
| OpenSSL configured upstream suite | 3,820 tests; 290 passing recipes and 57 skipped recipes | The separate preliminary FIPS configuration check was also skipped; skip reasons were retained |
| Plan acceptance, feature build and `status` | One build completed, with a passing baseline and three passing acceptance probes; status reported completion | Three local command-participant turns, three allowed files changed and four protected files unchanged |
| Documentary review | Intake acceptance and one deterministic assessment completed; the source task and project stayed unchanged | Document outcome remained `unknown`, retrieval returned `no_results`, and acceptance remained `unverified` |
| Verification, retrieval and CLI help | All 11 staged checks met their expected outcomes | Negative and uncertain inputs retained their refusals or uncertainty; no model calls |

The feature and review used four local participant turns in total and made zero
model calls. These checks establish the recorded software behavior, not model
quality or complete Windows qualification.

### Retained failures

The original all-in-one checker failed while reading a successful acceptance
response because its host reader and child process used different encodings
(CP1252 and UTF-8). Saved acceptance was inspected independently. The subsequent
staged checks captured raw output and selected UTF-8 explicitly. Their success
does not turn the original failed checker into a passing run.

The first documentary-review preparation also stopped at an unexpected prompt:
Windows `NUL` stdin appeared interactive to Python. The saved, unaccepted draft
was preserved and inspected before a later controlled continuation used an empty
stdin pipe. No Harness source or installed package was changed to obtain these
results. Earlier setup failures and their original output remain retained.

### Artifact identities

These hashes identify the local experiment; they are not download links or
instructions to trust a third-party wheel.

| Artifact | SHA-256 |
| --- | --- |
| Published `attune_harness-1.8.1-py3-none-any.whl` | `f83e924599b0eb0b3d40c428a80cb8fc5794c22cf2341752702cccf2f98ceaae` |
| Local `tiktoken-0.12.0-cp312-cp312-win_arm64.whl` | `437438502f27264cc8a2b1902deeece2ce3ed1b5fa6304b053754ae1462593c4` |
| Local `cryptography-50.0.2-cp312-abi3-win_arm64.whl` | `9a8e9cb9c5cdc86d5ba4d5599f48c9a8bfcae4e2d1b0907a5640791a97237389` |
| Retained staged evidence archive | `8ea05948b98684285f42e52724ec3c074ba30822f591b6ef6c2cf15db85febb5` |

The published Harness source is
[`f2baa8b1f9c0acaab2109cbc7facfb029c596586`](https://github.com/Smart-AI-Memory/attune-harness/tree/f2baa8b1f9c0acaab2109cbc7facfb029c596586).
The local archive passed CRC and all 371 recorded file-hash checks, including
verification of the eight fixture snapshots. The archive and experimental wheels
remain local records; this summary does not redistribute them.

## Separate validation of newer upstream source

Both upstream projects already have Windows ARM64 build support on their main
branches. A later experiment on the same Windows/Python profile built and tested
newer source, independently of the pinned Harness 1.8.1 environment:

| Project and exact source | Result | Public report |
| --- | --- | --- |
| tiktoken `79dc2c0533685b893616c78160b5d9e40876e724` | Native wheel built; all 33 upstream tests passed without skips | [Validation on PR #634](https://github.com/openai/tiktoken/pull/634#issuecomment-6933942152) |
| cryptography `3602bbd16ae731a4ce4dab9d43db334dbedad082` | Native wheel built; Nox `tests-nocoverage` completed with 4,714 passed, 45 skipped and 6 warnings | [Validation on PR #15350](https://github.com/pyca/cryptography/pull/15350#issuecomment-6933962883) |

The tiktoken development source declares 0.14.0 but differs from the published
0.14.0 tag. The cryptography source declares 51.0.0.dev1. Neither local wheel is
an official release artifact, and these runs do not qualify a Harness dependency
update. The full cryptography local Nox workflow, Rust unit tests, lint and type
checks were not run. Two earlier Nox invocation failures remain separate from
the passing session; the session-name behavior is reported in
[cryptography issue #16016](https://github.com/pyca/cryptography/issues/16016).

## What remains open

- **Normal native ARM64 installation:** official compatible wheels must reach
  PyPI. Harness then needs a separately qualified dependency update unless the
  exact pinned releases receive compatible wheels. No release date is promised.
- **Windows 11 desktop use:** the revised quickstart and generated report/status
  pages still need Windows browser inspection. Server CI and matching HTML bytes
  do not replace that check.
- **Wider native coverage:** a second clean Windows host, complete model
  vocabulary, live providers, storage/recovery behavior and the full platform
  qualification remain open.
- **Optional integrations:** the native base experiment does not qualify the
  Voyage or complete-extra profile; pinned `pyarrow` and `lancedb` have separate
  ARM64 wheel gaps. Windows Redis service checks also remain separate.

See the [Windows reliability requirements](windows-reliability.md) before
extending these results to other workflows or environments.
