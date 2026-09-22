# Native memory: decisions, September 22, 2026

[The scoping note](scoping.md) is a dated draft and is not edited. This file
records the rulings Patrick made on September 22, after 0.3.0 shipped, and
the numbers continue the spec authority's series so one list covers both.

## D15: the base install carries the journeys

Patrick, after 0.3.0: "the install calls on users to have to install
dependencies that should be automatically installed. The only added extra
that will be needed is for redis." Asked what goes in the base, he took the
recommendation: `review` + `mcp` + `tokens` (attune-forms, attune-verify,
attune-rag, mcp, tiktoken, 46 packages resolved), with `voyage` (91) and
`memory-native` (50) staying extras because both make paid calls. The old
extra names remain as empty extras until 1.0. Every dependency still loads on
first use, so the release gate's offline no-dependency check keeps its
meaning. Landed by the pull request "the base install carries the review,
test, acceptance and MCP journeys" (#64). This retires the zero-dependency
core that 0.1.0 advertised; the README says so.

## D16: `[redis]` delivers the backend, not a client pin

Asked whether `[redis]` should first add the client library with the backend
to follow, Patrick chose the backend: "2 backend". And: "I wouldn't have opted
for the redis configuration if I didn't think it enhanced the library a lot."
The configuration he means is the one he runs, described in
[the Task 4 design note](task-4-design.md), which names the decisions that
remain his before code starts.

## D17: now

Asked when, Patrick chose now, as the first 0.4.0 work.
