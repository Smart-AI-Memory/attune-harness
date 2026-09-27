# Recorded Voyage stage fixture

`stages.json.gz` contains four normalized stage requests and results from one bounded paired Voyage run on 2026-09-27. Both the in-process and signed subprocess arms returned the same canonical requests and normalized results. The source corpus was five public Harness files at Git commit `6bece93e8d5ddae3205d394b9b9c90d4408b8ee3`; their paths and SHA-256 values are in the fixture. The installed wheel SHA-256 was `bed12094e8b394604ced9fe3a9ab990af6b5116f84b5fdbbd2848784795963d2`; the signed production bundle code ZIP SHA-256 was `aa9e655da3fedf332c05915c8a74ee3c7bcfd8b7470658239436d1e24f08c90a`.

The fixture excludes credentials, signer identity, private registry, local absolute paths, and raw HTTP responses. Tests reconstruct SDK response envelopes from the **recorded normalized results**, verify the exact canonical request and SDK wire fields, and refuse sockets. A dummy test-only credential satisfies the host's name-presence gate. The synthetic kill case uses a captured request but does not replay a real interrupted paid call.

Before test signing, the fixture normalizes generated Windows CRLF bytes in the manifest, skill, and code ZIP source members to the retained LF artifact; the production bundle builder is unchanged.

This is one fixed query and source corpus, not a model-quality benchmark. Its eight live stages had known token usage; the calculated cost at the pinned rates was `$0.00249178` across both arms, not an independently verified provider invoice. R6/R7 qualification still depends on the reviewed offline replay and required platform CI receipts.
