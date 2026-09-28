# Unpublished 1.0 candidate saved-state capture

These 33 files are **raw bytes** from the local, unpublished `1.0.0rc1`
candidate writer at source commit
`ca5d9ee80ce6884d786acb4ad4cfe42ff246861e`. The clean-commit wheel is
`attune_harness-1.0.0rc1-py3-none-any.whl`, SHA-256
`18cda1a30c54f8143225007e80aac0a1bda211d2fcc49a07a3ab521272cc517f`.
The installed distribution and both package origins were checked against all
97 packaged source files before capture. `manifest.json` records the wheel,
source commit, per-file byte count and SHA-256. Its explicit
`record_writer: not_verified_by_capture_tool` is deliberate: byte copying
alone cannot establish which API wrote a record. The separate
`files/writer-receipt.json` records the eight offline writer families and 19
writer-output hashes. `scripts/compat_writer_recipe.py` (SHA-256
`047756d27d8c03171076957d3c4a9c94645f7380f04a2187c610c7e0b6dfeacd`)
called installed-wheel APIs with provider keys absent and socket connections
refused. The 14 remaining captured files are its synthetic inputs and that
receipt. Raw records were never scrubbed or rewritten after the writer ran.

The original capture root was `/private/tmp/attune-compat-candidate-a1` on
POSIX. Tests copy `files/` to a fresh root; `relocate()` in
`tests/test_compat_candidate_fixture.py` moves only these operational pointers
and derives only the values their readers require:

| File family | Exact changed pointers and derivations |
| --- | --- |
| Work draft and accepted records | `/request/project_root`, `/request/config/path`, `/record_path`; accepted also `/acceptance/decision/record_path`. Derive record checkpoint, accepted request bindings and draft decision binding with the production helpers. Decision sidecars update `/work` binding and accepted `/response/record_path`, then the sidecar digest. |
| Completed and paused assessment records | `/record_path` and its whole-record checkpoint digest only. The paths in accepted source, artifacts and historical events remain the original recorded evidence. Completed replay performs no dispatch; paused continuation refuses a changed source snapshot. |
| Test draft | `/request/project_root`, `/request/snapshot/root`, `/record_path` and checkpoint digest. The Git repository metadata is intentionally not copied, so freshness refuses with `Git input unavailable`; reading the durable draft remains supported. |
| Effects manifest | `/root` only. The captured `root_identity` device/inode is retained. A copied checkout must refuse freshness with `Checkout identity changed`; it cannot inherit the original owner's identity. |
| Saved store | The task's `execution/directory` and `scope/project` at the eight exact current, history and operation-replay pointers selected by its captured ID. Only the `save-task` operation digest is derived from the canonical saved request payload. The revised global memory and its operation identities remain unchanged. |
| Memory config | `/roots/0/path`, `/roots/1/path`, `/roots/2/path`, `/scratch/root`, `/saved/root`. The raw, personal and curated source files remain byte-identical. |
| Disabled extension state | `/manifest` and the state digest derived from the changed state. The bundled declaration is unsigned and disabled; this fixture makes **no** signed-artifact, accepted-grant or executable-plugin claim. |
| Plan, scratch and Voyage stage journals | No paths change. The schema 2 plan and format 2 scratch record read as written. Completed Voyage stage replay reports zero new tokens/cost without provider dispatch; a dispatching stage refuses automatic retry. |

The raw memory finding has the candidate's real write timestamp. The fixture
test evaluates its reader at that timestamp plus one day and then plus 31
days, proving both readability and the existing 30-day expiry without changing
the captured bytes or relying on the date of a future CI run.

This is a POSIX saved/effects native capture. The manifest/hash, path-free
Voyage replay/refusal, plan and scratch reader tests run on every platform;
path-bound copied-root reader and refusal tests run on POSIX. Windows effects
qualification, saved-state POSIX-only refusal on Windows, and signed enabled
Voyage plugin behavior remain evidenced by separate installed-wheel platform
and PR161 receipts. No paid provider call, RC publication, or candidate observation
period is implied by this fixture. Before release, compare the final wheel's
packaged bytes and relevant runtime metadata with this writer wheel; a changed
writer package requires a new candidate capture beside this one.
