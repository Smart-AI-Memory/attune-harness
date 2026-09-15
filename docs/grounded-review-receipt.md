# Grounded review dev6 — closing receipt

**Disposition: revise.** This closes the documentation gap for the retained September 14, 2026 experiment; it does not rerun or alter it.

The dev6 `--grounded` mode required exact document/reference quotations, an explicit verdict and an uncertainty account. It retained invalid generations and rejected fabricated provenance. Its software and installed boundaries passed, but the evaluated local model could not satisfy the citation contract.

| Measure | Retained result |
|---|---:|
| Planned Harness workflows | 27 |
| Completed Harness workflows | **0** |
| Delivered Harness narratives | 0 |
| Harness generation attempts | 27 |
| Single-pass baseline on the three fresh cases | 9 completed; 6 passed quality criteria |
| Total generation records | 36 |
| Full software suite at that increment | 722 passed |

Every Harness trial stopped at `Reference quote/path is absent from retrieved evidence`. The [later offline diagnosis](reliability-accuracy-review-2026-09-14.md) reproduced all 27 rejections and found overlapping self-citation, absent document-quote and inconsistent-verdict problems. Zero delivered unsupported assertions is a consequence of zero delivered reviews, not evidence of accurate review.

The Harness arm covered six retained and three fresh cases, each repeated three times. The single-pass arm covered only the three fresh cases. Do not compare the overall 27-versus-9 denominators as a matched ranking. The local model was pinned `llama3.1:8b`, Q4_K_M, through Ollama 0.31.1; no paid calls, retries or prompt tuning occurred in that campaign.

The strict contract's software tests establish its guards, not semantic truth. The [design](design-grounded-review.md), [artifact identity](receipts/grounded-review/artifact.json), [raw summary and grades](receipts/grounded-review/run-01/summary.json), [freeze](receipts/grounded-review/run-01/freeze.json) and [full-suite log](receipts/grounded-review/full-tests.txt) remain unchanged.

The following increment adds an explicit [passage-based review mode](passage-review.md). The dev6 wheel, original command mode and failed campaign remain preserved; the new result must stand on its own evidence.
