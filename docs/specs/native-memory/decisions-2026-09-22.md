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

## D18: the six Task 4 decisions, all as recommended

Asked the six decisions in [the Task 4 design note](task-4-design.md),
Patrick answered "all as recommended": the four reads plus `status`,
read-only, against his keyspace and functions rather than the AMS backend;
`redis` pinned to the newest 5.x at the first pull request, verified against
a local Redis Stack; the URL from the memory config file or an environment
variable the config names, password embedded or from a configured
`password_env`; the scratch interface with both backends in this task,
startup-only selection, no divert; an in-process double at the client
boundary plus a live test gated on `ATTUNE_TEST_REDIS_URL`; three reviewed
pull requests, 4.1 reads and CLI, 4.2 scratch, 4.3 config and installed
checks. He also gave the go to merge the design note when green.

## D15, amended: `mcp` stays in the base; the split with attune-ai is documented

The review of #64 showed that `mcp==2.2.0` in the base breaks a co-installed
attune-ai, which pins `mcp==1.29.1`; pip installs the second anyway and exits
0. Offered the choice between keeping `mcp` as the one non-paid extra and
keeping it in the base with the split documented, and shown the trade-offs,
Patrick chose the base: "option 2". Three mitigations came with it: the
README leads with an isolated install (`pipx install attune-harness`, `uv
tool install attune-harness`) and names the split in the install section and
the attune-ai section; the changelog says the same; and `mcp-serve` prints a
notice on stderr when it starts beside an attune-ai whose MCP requirement
this install does not meet (`features.neighbor_conflict`). The notice never
changes behaviour and stays off stdout, the protocol channel.
