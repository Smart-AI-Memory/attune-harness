# Build and accept the Voyage plugin runner

The `attune-harness[voyage]` wheel includes the source of the Voyage embed,
rerank and local LanceDB index runner. The runner is **unsigned** until a
signer reviews its exact bundle and signs the artifact digest. Harness does
not create a signer, register a trust key or accept a registry digest for you.

1. Run `python -m attune_voyage_plugin.bundle --output /absolute/new/bundle`.
   The output directory must not exist. The command writes deterministic
   `code.zip`, `manifest.json` and `SKILL.md` and prints `artifact_digest`.
   Repeating in another empty directory from the same wheel yields the same
   digest. It never reads `VOYAGE_API_KEY` or invokes Voyage.
2. Review the manifest, code and grant. Sign the printed 64-character digest
   as **64 ASCII bytes with no newline** using a chosen key; for example,
   `printf %s DIGEST | gpg --armor --detach-sign --output /absolute/new/bundle/artifact.sig -`.
   The public key and its fingerprint belong in the registry's `signers`
   section. Keep the private key outside the bundle and registry.
3. Install the bundle disabled with `attune-harness extension install
   /absolute/new/bundle/manifest.json --state-dir /absolute/state-dir`.
   In the registry's `extensions.voyage`, bind that state directory and the
   printed `artifact_digest`, and grant the manifest's named capabilities:
   `VOYAGE_API_KEY`, `index_staging`, scratch, time and output. Enable it with
   `attune-harness extension enable --state-dir /absolute/state-dir
   --checkpoint STATE_DIGEST --registry /absolute/registry.json` after
   inspecting the disabled state. The registry's `signers` list must contain
   the public key for the detached signature.
4. Add `voyage_plugin` to the normalized Voyage config with absolute registry
   path, `extension_id: "voyage"`, and `tools: {"embed":"embed",
   "rerank":"rerank","index":"index"}`. Run `attune-harness index plan
   --config CONFIG` to inspect `observed_registry_digest`. Copy it into
   `voyage_plugin.registry_digest` **only after reviewing the whole normalized
   extensions section**. Planning never writes that pin. Any registry edit,
   even to another registration, requires a fresh explicit acceptance.

With a pinned accepted selection, `index build` or `index update` uses the
signed embed tool for new paid stages and the signed index tool for local
LanceDB materialization. New paid stages require `--allow-provider` and a
locally set `VOYAGE_API_KEY`; completed stages and published generations replay
without either. The index tool receives `index_staging`, not the host ledger
or the key. Retrieval uses only the selected embed/rerank tools and retains
the host's scope and evidence validation. These are cooperating subprocess
boundaries, not an OS sandbox. Offline tests prove wiring and local index
integrity; they do not qualify live model quality or answer accuracy.
