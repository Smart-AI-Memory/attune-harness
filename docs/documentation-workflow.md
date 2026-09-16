# Code-grounded documentation

The first increment supports Python module API references: top-level public
functions (including async signatures) and class names. It does not import
project code or execute generated examples. It does not cover methods,
re-exports, dynamic APIs, decorator effects, or prove runtime behavior.

```sh
python -m attune_harness.documentation src/attune_harness/__init__.py \
  --test tests/test_contract.py > /tmp/harness-api-documentation.json
```

The JSON bundle contains Markdown and an evidence receipt. Markdown links are
relative to the project root: place the Markdown there, or rebase links when
publishing elsewhere. `verified` covers only the listed static claims, not the
completeness or semantic correctness of the document. Docstrings are not treated
as authoritative behavior descriptions. Selected tests provide source context
and drift tracking; the workflow does not claim to have run them.

## Library and coordinated roles

```python
from pathlib import Path
from attune_harness.documentation import generate, changed_sources

doc = generate(Path.cwd(), 'src/attune_harness/__init__.py',
               tests=('tests/test_contract.py',))
print(doc.markdown())
print(doc.to_dict())
print(changed_sources(Path.cwd(), doc))
```

Supply `author(snapshot) -> tuple[Claim, ...]` to draft with a model and optional
`reviewer(snapshot, findings) -> str` for independent advisory review. These are
trusted in-process callbacks, not isolated or budget-controlled model adapters.
The default author is deterministic and uses no provider. A provider adapter
must handle authorization, source-upload scope, cost receipts, and structured
output validation before deployment. No live model adapters were added here.

Both callbacks receive the same immutable source contents. The reviewer sees
each claim's check outcome but cannot override it. Behavioral claims remain
`unknown`; nonexistent symbols, wrong signatures, and invalid citations are
`refuted`. A missing source or source edit is returned by `changed_sources` and
requires review before publication. This function compares against the in-memory
document; persisted-receipt reload is not implemented in this increment.

The recommended initial team is one author plus an optional independent reviewer.
Model agreement alone cannot certify a document. Parallel section writers,
revision loops, live-provider integration, and comparative accuracy/cost trials
are follow-on work, not implicit behavior of this API.

Voyage can identify candidate files before calling this workflow. This increment
uses explicit full-file selection to stay usable offline; it does not issue
Voyage requests or automatically select repository contents.
