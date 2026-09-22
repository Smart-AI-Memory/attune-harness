<!--
DRAFT for docs/opportunity-log.md. Not committed anywhere.

The log exists only on wip/local-snapshot-2026-09-19 (last touched a3b3934). It is
absent from main and from release/0.1.0rc1-packaging. To land this entry, append
the paragraph below the "ubuntu-latest moves to Ubuntu 26" entry at the end of the
"Dated evidence and follow-through" section on that branch. It follows that
section's existing convention: unnumbered, dated, evidence first, candidate
follow-up, effort, and a closing line that it authorizes nothing. Highest assigned
number today is O-36.

Checks before landing:
1. Patrick confirms the two open decisions named in the entry (what "recommended"
   means beside a stdlib-only base, and which packaging option for the backend).
2. The scoping note link resolves from docs/ on the branch where it lands.
3. Delete this comment block.
-->

Unnumbered, 2026-09-21 (assign the next O-number at the next log review): make
Redis-backed memory the recommended install for 0.2.0. After 0.1.0 was published
(run 35564794974, commit `8fc26a4`), Patrick observed that the README should have
recommended a `[redis]` extra as the default install. It could not have: 0.1.0
declares seven extras (`tokens`, `verify`, `rag`, `voyage`, `review`, `mcp`,
`memory-native`) and none is `redis`. `pip install "attune-harness[redis]"` against
0.1.0 warns that the extra does not exist and installs the bare core. No Redis
client is imported anywhere under `src/attune_harness`; the two matches for the word
are a comment in `attune_bridge.py` and the substring in "redispatch". The published
`memory-native` extra is a pinned Anthropic API transport for memory proposals, not
the Redis-backed direction, and its name is now permanent. The 0.1.0 page on PyPI is
frozen, so nothing about this can be corrected there; it can only be different in
0.2.0. The intent is already recorded: the
[native memory scoping note](specs/native-memory/scoping.md), direction N3, puts
Redis behind an optional `[redis]` extra, lazily loaded like the Voyage and MCP
extras, with a stdlib file backend in the base for people who do not run Redis, the
backend chosen at startup, and a configured but unreachable Redis reported as
unavailable instead of a write being diverted to files. Task 4 of that note's
candidate ladder ("Backend interface and Redis extra") is this work. Two things are
undecided. First, what "recommended" means beside a base that must stay stdlib-only:
the 0.1.0 README leads with a core that has no dependencies and needs no server, and
the clean-install check on 2026-09-21 confirmed zero packages pulled. A README that
shows `pip install "attune-harness[redis]"` as the recommended line and keeps the
bare `pip install attune-harness` beside it as the no-server option would hold both
claims; making Redis a hard dependency would not. Second, packaging: move the backend
into Harness under the extra, or republish `attune-redis` without its hard
`attune-ai>=3.5.0` dependency. The scoping note found the backend looks portable but
had not verified that `memory.py`, `config.py` and `signals.py` import cleanly with
attune-ai absent. Candidate follow-up: run that import check first, because it
decides the packaging question cheaply; then scope ladder Task 4 in the successor
spec. Done when, in a fresh environment with attune-ai absent,
`pip install "attune-harness[redis]"` yields a working Redis-backed working memory;
the bare install still pulls zero dependencies and uses the file backend; an
unreachable configured Redis is reported as unavailable and is distinct from "no
matching memory"; CI exercises the Redis backend against a real server on at least
one platform; and the README's qualified table says which platforms the Redis path
is and is not qualified on. An empty or alias `redis` extra added only so the install
line resolves is rejected: it would recommend an install that does nothing. Extra
names are permanent once published, so `redis` should be chosen deliberately against
the existing `memory-native`. Effort: larger; it crosses packaging, a new backend
interface and live qualification. Whether Task 4 can start before ladder Tasks 1 to
3 is not settled: the ladder is sequential only where a task consumes the previous
result, and working memory does not obviously consume the file-tier readers, but
that is an inference to confirm in the successor spec, not a finding. Nothing is
built, renamed, scheduled or authorized by this note.
