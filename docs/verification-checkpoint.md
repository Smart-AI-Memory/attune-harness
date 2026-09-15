# Verification checkpoint — 2026-09-14

Completed before retrieval implementation. Real attune-verify 0.6.0 calls return
strict verified/refuted/unknown outcomes and retain claims, findings and artifact
hashes. A public CLI prints and optionally saves the same JSON report.

Suite: 152 passed, 98.74% statement coverage. A fresh core-only installed wheel
runs the original demo and reports verify unavailable. A fresh verify-only install
passes valid, broken, unknown, no-claim, protected-output and missing-input cases
from outside the source tree using isolated Python. Provider SDKs and attune-ai
are absent. See receipts/verification-core-install.json and
receipts/verification-installed-checkpoint.json for the exact tested calls.

Checkpoint wheel SHA256: `88132114e79d66b0d697ac12b7db77f01d0d289b59e7f570ede4fe920d917d70`.
Dependency commits and wheel hashes: ../dependency-lock.json. No source checkouts
were changed. No model calls ran. Retrieval is the next authorized step.
