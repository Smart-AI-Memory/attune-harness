# Model-aware token accounting

Patrick approved replacing the conservative byte estimate with model-aware
accounting where available, retaining output reserves and the 32 KiB narrative
transport boundary. This is an implementation increment in attune-harness;
done means tested preflight counting, explicit failure modes, and an installed
local pilot with a larger output budget. No paid inference or provider migration.

Disposable probe before production edits: read the installed model's metadata
through local `/api/show` (no generation). Its Llama BPE vocabulary has 128,000
ordinary and 256 special tokens. Existing local tiktoken 0.12.0, using those
exact ranks and the qualified system/user/assistant template, counts **4,383**
tokens for each retained dev4 pilot prompt. Both match the server's reported
prompt count; the earlier estimate was **15,338 bytes**. The server's returned
context IDs omit the automatically inserted BOS token, so the scratch report's
naive full-ID comparison is false; it is not a failure of the matching count.
Evidence: `receipts/token-accounting/disposable-count-probe.json` and the retained
raw `disposable-show.json`. No new generations were made for these probes.

Implement an optional local tokenizer extra, a bounded export/load path, and
`--tokenizer-file` on the review peer/pilot. Qualify only the existing model digest,
server 0.31.1, template and vocabulary. The exported profile's exact SHA256 is
compiled into the loader: a changed file, unsupported model or missing dependency
fails explicitly instead of silently reverting to estimates. Do not use a nearby
model's tokenizer. No HTTP requests occur during counting; tiktoken executes
locally with supplied vocabulary and never selects a provider or downloads data.
Keep the portable core and the ordinary review extra independent of tiktoken.

Count the full templated prompt, including BOS and role markers, then require
input tokens + requested output tokens + 512 margin <= context. Preserve the
existing scalar/context bounds and transport limits. With no tokenizer selected,
use the existing conservative byte budget and label that mode in the receipt.
Store counting identity, count/estimate, reserves and available capacity even
when budget validation rejects the prompt. With a tokenizer selected, require
the server's reported input count to match after generation; mismatch remains a
failed invocation with raw evidence retained. Disable server truncation/context
shifting explicitly. Do not retry, summarize inputs, drop evidence or silently
reduce the accepted output budget.

Cases: real retained prompt; plain text/code/multilingual/special-marker inputs;
empty system text; exact context boundary and one-token overflow; invalid output
reserve; model/profile/dependency mismatch; metadata drift; malformed/oversized
profile or show response; input-count mismatch after generation; command binding
and receipt visibility; byte fallback; existing Unicode narrative/wire limits.
Run full suite, focused mutation checks in disposable source copies, clean
installed qualification, and the two-generation real pilot at 2,048 output
tokens. Preserve dev0..dev4 wheels, historical records and frozen research envs.

Rejected: byte/4 heuristics (unsafe for arbitrary language/code); a generation
call solely to measure each prompt (extra inference and effects); private runner
ports (unstable dependency); implementing BPE ourselves (unnecessary complexity);
claiming generic tokenizer support from one qualified local model. Ollama 0.31.1's
render-only debug path does not enforce the desired output reservation and is
not a substitute for token accounting.

Primary references: [Ollama v0.31.1 generate implementation](https://github.com/ollama/ollama/blob/v0.31.1/server/routes.go),
[prompt rendering](https://github.com/ollama/ollama/blob/v0.31.1/server/prompt.go),
and [Meta's Llama tokenizer reference](https://github.com/meta-llama/llama3/blob/main/llama/tokenizer.py).
