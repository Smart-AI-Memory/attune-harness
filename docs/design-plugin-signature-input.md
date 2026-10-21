# Bind plugin verification to the validated signature bytes

Design before code, October 21, 2026. Scope: the detached-signature input to
`plugin_signing.inspect_signature`; no change to signer authority, registry
keys, signature verdicts, subprocess limits or historical evidence.

The September 24 second review of #118 found that Harness walked the decoded
first armor block but gave GPG the original file, including unchecked trailing
data. The finding remains in [the opportunity log](opportunity-log.md) and
[the review log](review-findings.md). Preserve those dated observations.

## Contract and cases

Decode one complete signature envelope, walk every decoded packet, then write
that same binary buffer into the private verifier home. Refuse malformed or
additional envelope data before finding or running GPG. Binary input retains
the existing rule: one or more definite-length Signature packets, with no
unwalked bytes. The existing 16 KiB file bound and private GPG home still apply.

| Input | Expected result |
| --- | --- |
| Binary signature, including multiple Signature packets | Walk the entire buffer; give GPG those exact bytes |
| One ASCII signature block with LF or CRLF, optional headers/checksum and outer ASCII whitespace | Decode, walk and verify the same binary buffer |
| Signature followed by a message, another armor block or raw data | Refuse before GPG starts |
| Missing/reversed/duplicate delimiters, invalid base64 or non-ASCII armor | Refuse before GPG starts |
| Present but malformed or incorrect armor checksum | Keep the deployed GPG path's refusal |
| Compressed, literal, partial-length or truncated packet | Keep the packet guard's refusal |

Disposable probes against `ef04cd5`, before changing source, established that a
three-byte synthetic Signature packet reached the verifier unchanged as binary
but became a 64-byte armor file or a 128-byte signature-plus-message file at
the subprocess boundary. This probe stubbed GPG and proves byte binding only.
A separate real-GPG probe with an isolated disposable key accepted binary,
LF armor and CRLF armor, and refused an altered checksum with `NODATA`.
Neither probe used or changed a user keyring or retained receipt.

## Choice and verification

Use a small ASCII envelope parser and strict base64 decoding, with the existing
packet walker. Preserve optional checksum validation when a checksum is present
so normalizing input does not silently broaden the deployed acceptance profile.
The CRC24 algorithm is specified in [RFC 9580, section 6.1](https://www.rfc-editor.org/rfc/rfc9580.html#section-6.1).
That RFC requires general OpenPGP implementations to tolerate checksum errors;
this application keeps its narrower existing GPG-compatible input profile and
does not claim full RFC 9580 armor acceptance.

Rejected: strip everything after the first block and verify its decoded bytes.
That binds the bytes but silently accepts the original trailing-data exploit.
Rejected: keep the original armor file after checking its first decoded block;
that leaves two parsers interpreting different inputs.

Regression checks must observe the actual GPG input file and a real valid
signature verdict, and prove malformed/two-block inputs never reach GPG.
Exercise near-bound input and mutations that restore the original write or
remove the envelope guard. Run focused tests, the full suite and installed-wheel
qualification, then obtain an independent review of the immutable change.
Native Windows remains a CI check; local POSIX results do not qualify it.

## CI fixture follow-through

October 21, 2026: current-head Windows supplemental coverage retained one
failure in the golden-envelope test's scratch signer setup. Its first
`gpg --version` probe used the production verifier's 10-second deadline and
timed out before key generation. The instrumented run completed with 2,880
passes and one failure; all 117 signing cases and ordinary Windows qualification
passed. This was not a suite deadline or packet-validation failure.

Probe the fixture's GPG path style independently under its existing 120-second
key-generation budget, with a bounded output, private scratch directory,
`--no-options` and the verifier's minimal environment. Cache only the fixture's
metadata. Keep actual verification and its version probe at 10 seconds; do not
change source, workflow deadlines, golden outputs or assertions to clear this
failure. A deterministic regression must simulate setup needing more than
10 seconds and still prove production refuses that same delayed probe. Preserve
the failed run and artifact; a fresh Windows run must confirm the repair.
