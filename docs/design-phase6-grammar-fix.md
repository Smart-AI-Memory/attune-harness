# Pilot grammar and error diagnostic fix

The first dev2 live review failed before any narrative: Ollama returned HTTP 400.
The original command and generation receipts remain in `.pilot/phase6-local`.
A separate disposable prompt with the same schema reproduced HTTP 400 and
captured `Failed to initialize samplers: failed to parse grammar`. A second
disposable probe removed only the schema's maxLength 3000 and returned valid
JSON with HTTP 200. Receipts: `receipts/phase6/http-error-probe.json` and
`receipts/phase6/grammar-probe.json`. Neither probe resumed the failed review.

Remove that grammar-generation constraint; keep the 3,000-character post-response
validator, the 512-token generation cap, the prompt byte budget and the explicit
under-120-word instruction. This preserves bounded accepted output. Cases:
valid small response; empty/oversized/non-string/extra-field responses rejected;
runtime HTTP errors retain bounded diagnostics; oversized error bodies are
truncated visibly; no network or generation retries are introduced.

The local HTTP client currently loses the server's error body, hiding the cause.
Retain at most 4 KiB of decoded HTTP error detail and include status/truncation in
the exception. Test both a grammar error and an oversized body; remove the new
handler in a disposable copy to verify these tests detect its absence. Existing
E3 source archives and dev1 environment remain immutable evidence for that run.

Reject silently increasing generation retries or discarding the failed pilot.
Package dev3, rerun the suite and installed checks, then create a fresh pilot run
against the unchanged real document. Preserve dev0/dev1/dev2 wheels. The failed
run stays failed with no narrative or inferred verified completion.
