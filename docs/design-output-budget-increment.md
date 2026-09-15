# Configurable review output budget

Patrick approved removing the 3,000-character cap and fixed word-count instruction,
configuring output tokens per workflow, and testing the existing transport limits.
This increment changes the local Ollama review peer and its pilot launcher. The
portable command contract stays at 32,768 UTF-8 bytes per final narrative and
65,536 bytes per JSON response. The narrative includes the unverified-proposal
label. Output remains evidence to review, never independently verified prose.

Before editing production code, a disposable fixture sent a 4,160-character,
480-word review through installed dev3. The transport accepted it; the peer
rejected it with `Local review must contain 1..3000 characters`. No model call
was made. See `receipts/output-budget/before-probe.json`.

Add `--max-output-tokens` to the peer and pilot launcher, defaulting to the
existing 512 tokens. Put the selected value in the accepted participant command
and generation receipt. Each invocation copies its runtime options. Budget
changes therefore require accepting a new workflow profile; they cannot silently
change a paused run. Remove both the character check and word-count instruction.
Validate the actual serialized response through the existing command decoder
before recording successful generation. Encode Unicode directly as UTF-8 so
escaping does not impose an accidental smaller multilingual narrative limit.
Keep empty/malformed output, transport overflow and truncated generation as
visible failures, retaining raw evidence with no truncation or retry.

Replace the local client's arbitrary 1,024-output-token ceiling with a context
check: positive integer output budget, context 1,024..16,384, 512 tokens reserved
for framing, and the remaining context conservatively allocated to prompt/system
UTF-8 bytes plus output tokens. This byte estimate is deliberately conservative,
not a tokenizer guarantee. The default review context remains 16,384. Invalid
scalar budgets fail before dispatch; prompt-dependent exhaustion fails before
any model access. A token budget is a ceiling, not a requested response length.
The existing timeout still applies. Larger budgets can require smaller inputs.

Tests cover a review beyond both old restrictions; exact and overflowing 32 KiB
ASCII/multibyte narratives including the label; JSON escaping overflow; independent
default/custom budgets in requests and receipts; invalid budgets before dispatch;
context reservation; CLI forwarding; and accepted-profile changes on resume.
Run the full suite, installed-artifact checks, and targeted mutation checks in
disposable copies. Try bounded local inference against the existing pinned model,
retain its actual outcome, and make no paid calls. Build dev4 separately; preserve
all historical wheels, frozen research sources and pilot receipts.

Rejected: merely increasing the character cap (still duplicates transport policy),
unbounded generation (no meaningful per-workflow budget), or silently clipping
long output (would destroy evidence and misrepresent completion).
