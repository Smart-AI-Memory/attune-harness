# Decisions

- D1: Patrick approved the first implementation slice directly; do not repeat the
  intake or plan-approval question. The case study remains historical research.
- D2: Reuse Harness process supervision and durable task mechanisms. Keep generic
  Attune AI verification and attune-verify unchanged. Their roles differ.
- D3: Conservative broad fallback is visible; operator-selected tests disclose
  excluded checks. A single passing subset proves neither complete selection nor
  general correctness.
- D4: Disposable captured working-tree execution preserves the original checkout.
  This is not a security sandbox or a hermetic environment. Git metadata/ignored
  dependency needs are explicit first-profile limits.
- D5: Scope is the working-tree change against HEAD, including staged deletions;
  committed revision ranges are a later opportunity. Reject clean-only scopes.
- D6: Initial discovery qualifies default `test_*.py` / `*_test.py` patterns.
  Pytest checks its effective configuration before collection. This supports INI
  and TOML precedence without a duplicate Harness parser. Custom patterns and
  collectors need their own qualification; do not silently omit them. Two retained
  integration failures led to removing the approximate intake config parser.
- D7: Keep complete manifests, test/exclusion lists and observed node IDs in the
  existing saved record. Bound the console grammar lists and link that record.
  The grammar view can be reconstructed by `status`; the installed case also has
  an archived Markdown rendering. No separate gate or form persistence service.
