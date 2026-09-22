"""The command workspace host: registration, one-shot authority, events, eviction.

Carried from Attune AI's tests/unit/elicitation/test_command_workspace.py at
b89f7953f. Changed on porting: async tests run through asyncio.run, since the
suite has no async plugin; the test that drove Attune AI's MCP server stayed
behind; the three telemetry tests are replaced by event-sink tests. New: the
eviction of terminal workspaces and the bounded memory of consumed ids.
"""
# qualify: platform

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from collections.abc import Mapping
from dataclasses import dataclass

import pytest

pytest.importorskip("attune_forms")
from attune_forms import WorkspaceActionResponse, workspace_from_dict  # noqa: E402

from attune_harness import command_workspace  # noqa: E402
from attune_harness.command_workspace import (  # noqa: E402
    CONSUMED_IDS_KEPT,
    CommandWorkspaceError,
    CommandWorkspaceHost,
    CommandWorkspaceProjection,
    CommandWorkspaceTransition,
    jsonl_event_writer,
)

LOGGER = "attune_harness.command_workspace"


def run(coroutine):
    return asyncio.run(coroutine)


@dataclass(frozen=True)
class _State:
    stage: str


class _Adapter:
    adapter_id = "example"
    schema_version = 1

    def __init__(self) -> None:
        self.project_suffix = ""
        self.contract_suffix = ""
        self.receipt_actions = False

    def create(self, intake: Mapping[str, object], *, prior_state: object | None = None) -> _State:
        if prior_state is not None and prior_state != _State("intake"):
            raise CommandWorkspaceError(["select edit before replacing preview"])
        return _State(str(intake.get("stage", "preview")))

    def project(self, state: object) -> CommandWorkspaceProjection:
        if not isinstance(state, _State):
            raise CommandWorkspaceError(["incompatible example state"])
        if state.stage == "preview":
            data = {
                "id": "preview",
                "title": f"Example workspace{self.project_suffix}",
                "actions": [
                    {"id": "edit", "label": "Edit"},
                    {
                        "id": "approve",
                        "label": "Approve",
                        "consequence": "Approve this exact example.",
                        "requires_explicit_choice": True,
                    },
                ],
            }
        elif state.stage == "intake":
            data = {"id": "intake", "title": "Example intake", "summary": "Submit replacement intake."}
        else:
            data = {"id": "receipt", "title": "Example receipt", "summary": "The example completed."}
            if self.receipt_actions:
                data["actions"] = [{"id": "again", "label": "Again"}]
        view = workspace_from_dict(data)
        material = f"{state.stage}:{view!r}:{self.contract_suffix}".encode()
        return CommandWorkspaceProjection(view, hashlib.sha256(material).hexdigest())

    def apply(self, state: object, action: WorkspaceActionResponse) -> CommandWorkspaceTransition:
        if state != _State("preview"):
            raise CommandWorkspaceError(["example is not awaiting an action"])
        if action.action == "edit":
            return CommandWorkspaceTransition(_State("intake"))
        if action.action == "approve":
            return CommandWorkspaceTransition(
                _State("receipt"), terminal=True, result={"approved_value": "example"}
            )
        raise CommandWorkspaceError(["unsupported example action"])

    def publish(self, state: object, event: Mapping[str, object]) -> CommandWorkspaceTransition:
        kind = event.get("kind")
        if kind == "progress":
            return CommandWorkspaceTransition(
                state, result={"detail": event.get("detail", "")}, authority_changed=False
            )
        if kind == "bad-progress":
            return CommandWorkspaceTransition(_State("intake"), authority_changed=False)
        if kind == "terminal-without-authority":
            return CommandWorkspaceTransition(_State("receipt"), terminal=True, authority_changed=False)
        if kind == "finish":
            return CommandWorkspaceTransition(_State("receipt"), terminal=True, result={"finished": True})
        return CommandWorkspaceTransition(_State("preview"))


def _host(adapter: _Adapter | None = None, **kwargs) -> tuple[CommandWorkspaceHost, _Adapter]:
    resolved = adapter or _Adapter()
    host = CommandWorkspaceHost(**kwargs)
    host.register(resolved)
    return host, resolved


def _payload(render, action: str, *, confirmed: bool = False) -> dict[str, object]:
    return {
        "__elicitation_response__": True,
        "title": render.record.view.title,
        "view": render.record.view.id.value,
        "action": action,
        "confirmed": confirmed,
        **render.record.binding.to_payload(),
    }


# --- carried -----------------------------------------------------------------


def test_registration_rejects_unknown_duplicate_and_invalid_adapters() -> None:
    host, adapter = _host()
    assert host.adapter("example") is adapter
    assert host.get("missing") is None
    with pytest.raises(CommandWorkspaceError, match="duplicate"):
        host.register(adapter)
    with pytest.raises(CommandWorkspaceError, match="unknown"):
        host.adapter("missing")
    invalid = _Adapter()
    invalid.adapter_id = "Bad Adapter"
    with pytest.raises(CommandWorkspaceError, match="adapter_id"):
        host.register(invalid)
    with pytest.raises(CommandWorkspaceError, match="required protocol"):
        host.register(object())
    create_only = type(
        "CreateOnly", (), {"adapter_id": "create_only", "schema_version": 1, "create": lambda *args: None}
    )()
    with pytest.raises(CommandWorkspaceError, match="required protocol"):
        host.register(create_only)


@pytest.mark.parametrize("schema_version", [True, 0])
def test_registration_rejects_invalid_schema_versions(schema_version: object) -> None:
    adapter = _Adapter()
    adapter.schema_version = schema_version
    with pytest.raises(CommandWorkspaceError, match="schema_version"):
        CommandWorkspaceHost().register(adapter)


def test_projection_and_transition_validate_portable_contract() -> None:
    preview = workspace_from_dict({"id": "preview", "title": "Preview", "actions": [{"id": "go", "label": "Go"}]})
    with pytest.raises(ValueError, match="SHA-256"):
        CommandWorkspaceProjection(preview)
    with pytest.raises(TypeError, match="WorkspaceView"):
        CommandWorkspaceProjection("not-a-view")
    with pytest.raises(TypeError, match="hash must be a string"):
        CommandWorkspaceProjection(preview, 7)
    receipt = workspace_from_dict({"id": "receipt", "title": "Receipt"})
    with pytest.raises(ValueError, match="must be a SHA-256"):
        CommandWorkspaceProjection(receipt, "bad")
    with pytest.raises(TypeError, match="terminal flag"):
        CommandWorkspaceTransition(_State("preview"), terminal="yes")
    with pytest.raises(TypeError, match="result must be a mapping"):
        CommandWorkspaceTransition(_State("preview"), result=[])


def test_open_renders_widget_markdown_and_headless_binding_parity() -> None:
    host, _ = _host()
    render = run(host.open("example", {}))
    assert render.record.revision == 0
    assert render.record.adapter_version == 1
    assert render.record.binding.contract_hash == render.record.contract_hash
    for action_id in ("edit", "approve"):
        assert f'data-workspace-action="{action_id}"' in render.html
        assert f"{chr(96)}{action_id}{chr(96)}" in render.markdown
    public = render.to_dict()
    assert public["action_nonce"] == render.record.action_nonce
    assert public["view"] == "preview"
    assert render.record.workspace_id in render.html
    assert render.record.workspace_id in render.markdown


def test_edit_invalidates_authority_and_adapter_controls_reentry() -> None:
    host, _ = _host()

    async def scenario():
        first = await host.open("example", {})
        edited = await host.collect(_payload(first, "edit"))
        assert edited.record.revision == 1
        assert edited.record.view.id.value == "intake"
        assert edited.record.action_nonce == ""
        with pytest.raises(CommandWorkspaceError, match="awaiting a bound action"):
            _ = edited.record.binding
        second = await host.open("example", {}, workspace_id=first.record.workspace_id)
        assert second.record.revision == 2
        assert second.record.action_nonce != first.record.action_nonce
        with pytest.raises(CommandWorkspaceError, match="select edit"):
            await host.open("example", {}, workspace_id=second.record.workspace_id)

    run(scenario())


def test_altered_unknown_and_replayed_actions_fail_without_mutation() -> None:
    host, _ = _host()

    async def scenario():
        render = await host.open("example", {})
        original = host.get(render.record.workspace_id)
        base = _payload(render, "approve", confirmed=True)
        for change in ({"revision": 9}, {"action_nonce": "n" * 32}, {"contract_hash": "0" * 64}, {"action": "unknown"}):
            with pytest.raises(CommandWorkspaceError):
                await host.collect({**base, **change})
            assert host.get(render.record.workspace_id) == original
        result = await host.collect(base)
        assert result.record.terminal is True
        assert result.result == {"approved_value": "example"}
        assert result.to_dict()["result"] == {"approved_value": "example"}
        with pytest.raises(CommandWorkspaceError, match="already consumed"):
            await host.collect(base)
        with pytest.raises(CommandWorkspaceError, match="terminal.*replaced"):
            await host.open("example", {}, workspace_id=render.record.workspace_id)

    run(scenario())


def test_concurrent_confirmations_publish_one_terminal_transition() -> None:
    host, _ = _host()

    async def scenario():
        render = await host.open("example", {})
        payload = _payload(render, "approve", confirmed=True)
        results = await asyncio.gather(host.collect(payload), host.collect(payload), return_exceptions=True)
        accepted = [item for item in results if not isinstance(item, Exception)]
        rejected = [item for item in results if isinstance(item, CommandWorkspaceError)]
        assert len(accepted) == 1 and len(rejected) == 1
        assert accepted[0].record.revision == 1
        assert accepted[0].record.view.id.value == "receipt"
        assert accepted[0].record.action_nonce == ""

    run(scenario())


def test_projection_drift_fails_before_adapter_apply() -> None:
    adapter = _Adapter()
    host, _ = _host(adapter)

    async def scenario():
        render = await host.open("example", {})
        adapter.project_suffix = " changed"
        with pytest.raises(CommandWorkspaceError, match="view changed"):
            await host.collect(_payload(render, "edit"))
        assert host.get(render.record.workspace_id) == render.record

    run(scenario())


def test_contract_drift_and_terminal_actions_fail_before_publication() -> None:
    adapter = _Adapter()
    host, _ = _host(adapter)

    async def scenario():
        render = await host.open("example", {})
        adapter.contract_suffix = "changed"
        with pytest.raises(CommandWorkspaceError, match="contract changed"):
            await host.collect(_payload(render, "edit"))
        assert host.get(render.record.workspace_id) == render.record

    run(scenario())


def test_progress_publication_has_independent_event_sequence() -> None:
    host, _ = _host()

    async def scenario():
        render = await host.open("example", {})
        progress = await host.publish(render.record.workspace_id, {"kind": "progress", "detail": "seat 1 complete"})
        assert progress.record.revision == render.record.revision
        assert progress.record.action_nonce == render.record.action_nonce
        assert progress.record.event_sequence == 1
        assert progress.result == {"detail": "seat 1 complete"}
        changed = await host.publish(render.record.workspace_id, {"kind": "checkpoint"})
        assert changed.record.revision == render.record.revision + 1
        assert changed.record.event_sequence == 2
        assert changed.record.action_nonce != render.record.action_nonce
        edited = await host.collect(_payload(changed.render, "edit"))
        assert edited.record.event_sequence == 2

    run(scenario())


def test_progress_publication_cannot_smuggle_authority_changes() -> None:
    host, adapter = _host()

    async def scenario():
        render = await host.open("example", {})
        with pytest.raises(CommandWorkspaceError, match="changed action authority"):
            await host.publish(render.record.workspace_id, {"kind": "bad-progress"})
        with pytest.raises(CommandWorkspaceError, match="must change authority"):
            await host.publish(render.record.workspace_id, {"kind": "terminal-without-authority"})
        with pytest.raises(CommandWorkspaceError, match="event must be a mapping"):
            await host.publish(render.record.workspace_id, [])
        with pytest.raises(CommandWorkspaceError, match="unknown or expired"):
            await host.publish("workspace-missing", {"kind": "progress"})
        adapter.contract_suffix = ""
        adapter.receipt_actions = True
        with pytest.raises(CommandWorkspaceError, match="terminal.*cannot expose actions"):
            await host.collect(_payload(render, "approve", confirmed=True))
        assert host.get(render.record.workspace_id) == render.record

    run(scenario())


def test_open_rejects_unknown_workspace_bad_intake_and_adapter_mismatch() -> None:
    host, adapter = _host()

    async def scenario():
        with pytest.raises(CommandWorkspaceError, match="unknown command workspace_id"):
            await host.open("example", {}, workspace_id="workspace-missing")
        with pytest.raises(CommandWorkspaceError, match="intake must be a mapping"):
            await host.open("example", [])
        other = _Adapter()
        other.adapter_id = "other"
        host.register(other)
        render = await host.open("example", {})
        with pytest.raises(CommandWorkspaceError, match="canonical state"):
            await host.open("other", {}, workspace_id=render.record.workspace_id)
        with pytest.raises(CommandWorkspaceError, match="requested tool"):
            await host.collect(_payload(render, "edit"), expected_adapter_id="other")
        adapter.schema_version = 2
        with pytest.raises(CommandWorkspaceError, match="version changed"):
            await host.collect(_payload(render, "edit"))
        with pytest.raises(CommandWorkspaceError, match="version changed"):
            await host.open("example", {}, workspace_id=render.record.workspace_id)
        with pytest.raises(CommandWorkspaceError, match="must be a mapping"):
            await host.collect([])
        with pytest.raises(CommandWorkspaceError, match="requires workspace_id"):
            await host.collect({})
        with pytest.raises(CommandWorkspaceError, match="unknown or expired"):
            await host.collect({"workspace_id": "workspace-missing"})

    run(scenario())


# --- seam 1: events into a sink the caller names -----------------------------


def test_events_are_emitted_only_after_a_canonical_transition() -> None:
    events: list[dict] = []
    host, _ = _host(record_event=events.append)

    async def scenario():
        preview = await host.open("example", {})
        assert [e["event"] for e in events] == ["workspace_rendered"]
        assert events[0]["revision"] == 0 and events[0]["adapter_id"] == "example"
        assert preview.record.action_nonce not in json.dumps(events)
        payload = {**_payload(preview, "approve", confirmed=True), "instance_id": "0123456789abcdef" * 2}
        with pytest.raises(CommandWorkspaceError):
            await host.collect({**payload, "confirmed": False})
        assert len(events) == 1, "a rejected action emits nothing"
        result = await host.collect(payload)
        assert result.record.terminal is True
        with pytest.raises(CommandWorkspaceError):
            await host.collect(payload)
        accepted = [e for e in events if e["event"] == "workspace_accepted"]
        assert len(accepted) == 1, "a replay emits nothing"
        assert accepted[0]["revision"] == preview.record.revision
        assert accepted[0]["action"] == "approve"
        assert accepted[0]["instance_id"] == "0123456789abcdef" * 2
        assert accepted[0]["terminal"] is True
        assert preview.record.action_nonce not in json.dumps(events)
        assert "action_nonce" not in json.dumps(events)
        assert all(e["at"].endswith("+00:00") for e in events)
        # The terminal receipt has no binding, so no render event follows it.
        assert [e["event"] for e in events] == ["workspace_rendered", "workspace_accepted"]

    run(scenario())


def test_adapter_failure_emits_nothing() -> None:
    events: list[dict] = []
    host, adapter = _host(record_event=events.append)

    async def scenario():
        preview = await host.open("example", {})
        adapter.receipt_actions = True
        with pytest.raises(CommandWorkspaceError, match="terminal"):
            await host.collect(_payload(preview, "approve", confirmed=True))
        assert [e["event"] for e in events] == ["workspace_rendered"]

    run(scenario())


@pytest.mark.parametrize("error", [OSError("disk full"), TypeError("not serializable"), KeyError("x")])
def test_a_failing_sink_is_counted_and_never_blocks_a_decision(caplog, error) -> None:
    def broken(event: dict) -> None:
        raise error

    host, _ = _host(record_event=broken)

    async def scenario():
        with caplog.at_level(logging.WARNING, logger=LOGGER):
            preview = await host.open("example", {})
            result = await host.collect(_payload(preview, "approve", confirmed=True))
        assert result.record.terminal is True
        assert host.dropped_events == 2
        assert "not recorded" in caplog.text

    run(scenario())


def test_no_sink_means_no_events_and_no_cost() -> None:
    host, _ = _host()
    preview = run(host.open("example", {}))
    assert preview.html and host.dropped_events == 0


def test_jsonl_writer_appends_one_line_per_event(tmp_path) -> None:
    path = tmp_path / "workspace-events.jsonl"
    host, _ = _host(record_event=jsonl_event_writer(path))

    async def scenario():
        preview = await host.open("example", {})
        await host.collect(_payload(preview, "approve", confirmed=True))

    run(scenario())
    lines = path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["event"] for line in lines] == ["workspace_rendered", "workspace_accepted"]
    assert path.read_bytes().count(b"\r") == 0


def test_jsonl_writer_refuses_a_symlinked_file_or_directory(tmp_path) -> None:
    real = tmp_path / "real.jsonl"
    real.write_text("", encoding="utf-8")
    realdir = tmp_path / "realdir"
    realdir.mkdir()
    link = tmp_path / "link.jsonl"
    linkdir = tmp_path / "linkdir"
    try:
        link.symlink_to(real)
        linkdir.symlink_to(realdir, target_is_directory=True)
    except OSError as exc:
        pytest.skip("Runner cannot create symlinks: " + str(exc))
    with pytest.raises(ValueError, match="symlink"):
        jsonl_event_writer(link)({"event": "x"})
    with pytest.raises(ValueError, match="symlink"):
        jsonl_event_writer(linkdir / "e.jsonl")({"event": "x"})
    assert not (realdir / "e.jsonl").exists()


def test_jsonl_writer_refuses_a_file_past_its_limit_and_writes_ascii(tmp_path) -> None:
    path = tmp_path / "ascii.jsonl"
    jsonl_event_writer(path)({"event": "caf\u00e9 \u2028 x"})
    raw = path.read_bytes()
    assert raw.isascii() and raw.count(b"\n") == 1 and len(raw.decode().splitlines()) == 1
    small = jsonl_event_writer(tmp_path / "small.jsonl", limit=60)
    small({"event": "workspace_rendered", "n": 1})
    with pytest.raises(ValueError, match="would pass 60 bytes"):
        small({"event": "workspace_rendered", "n": 2})
    host, _ = _host(record_event=jsonl_event_writer(tmp_path / "tiny.jsonl", limit=10))
    result = run(host.open("example", {}))
    assert result.html and host.dropped_events == 1


# --- seam 2: terminal workspaces are evicted ---------------------------------


def test_terminal_workspace_is_evicted_and_a_replay_is_still_refused() -> None:
    host, _ = _host()

    async def scenario():
        render = await host.open("example", {})
        wid = render.record.workspace_id
        assert wid in host._records and wid in host._locks
        payload = _payload(render, "approve", confirmed=True)
        result = await host.collect(payload)
        assert result.record.terminal is True
        assert host.get(wid) is None
        assert wid not in host._records and wid not in host._locks
        assert host.consumed(wid)
        with pytest.raises(CommandWorkspaceError, match="already consumed"):
            await host.collect(payload)
        with pytest.raises(CommandWorkspaceError, match="terminal.*replaced"):
            await host.open("example", {}, workspace_id=wid)
        with pytest.raises(CommandWorkspaceError, match="terminal.*cannot accept events"):
            await host.publish(wid, {"kind": "progress"})

    run(scenario())


def test_terminal_publication_is_evicted_too() -> None:
    host, _ = _host()

    async def scenario():
        render = await host.open("example", {})
        wid = render.record.workspace_id
        result = await host.publish(wid, {"kind": "finish"})
        assert result.record.terminal is True
        assert result.record.revision == 1 and result.record.event_sequence == 1
        assert result.result == {"finished": True}
        assert host.get(wid) is None
        assert wid not in host._records and wid not in host._locks
        assert host.consumed(wid)
        with pytest.raises(CommandWorkspaceError, match="cannot accept events"):
            await host.publish(wid, {"kind": "progress"})
        with pytest.raises(CommandWorkspaceError, match="already consumed"):
            await host.collect({**_payload(render, "edit"), "workspace_id": wid})

    run(scenario())


def test_refused_unknown_ids_leave_no_lock_behind() -> None:
    """Found by review: a refused call once created a lock for any id it was
    given, so a stream of bad ids grew the host without bound."""
    host, _ = _host()

    async def scenario():
        for i in range(500):
            with pytest.raises(CommandWorkspaceError, match="unknown or expired"):
                await host.collect({"workspace_id": f"ghost-{i}"})
            with pytest.raises(CommandWorkspaceError, match="unknown or expired"):
                await host.publish(f"ghost-{i}", {"kind": "progress"})
            with pytest.raises(CommandWorkspaceError, match="unknown command workspace_id"):
                await host.open("example", {}, workspace_id=f"ghost-{i}")
        assert host._locks == {} and host._records == {}

    run(scenario())


def test_a_failed_creation_leaves_no_lock_behind() -> None:
    class Failing(_Adapter):
        adapter_id = "failing"

        def create(self, intake, *, prior_state=None):
            raise CommandWorkspaceError(["intake refused"])

    host, _ = _host(Failing())

    async def scenario():
        for _ in range(50):
            with pytest.raises(CommandWorkspaceError, match="intake refused"):
                await host.open("failing", {})
        assert host._locks == {} and host._records == {}

    run(scenario())


def test_host_memory_is_bounded_by_the_consumed_set() -> None:
    host, _ = _host()

    async def scenario():
        first = None
        for i in range(CONSUMED_IDS_KEPT + 5):
            render = await host.open("example", {})
            if first is None:
                first = render.record.workspace_id
            await host.collect(_payload(render, "approve", confirmed=True))
        assert host._records == {} and host._locks == {}
        assert len(host._consumed) == CONSUMED_IDS_KEPT
        assert not host.consumed(first), "the oldest id has been forgotten"
        # Forgotten means 'unknown or expired', still a refusal, never a grant.
        with pytest.raises(CommandWorkspaceError, match="unknown or expired"):
            await host.collect({"workspace_id": first})

    run(scenario())


def test_non_terminal_workspaces_are_kept() -> None:
    host, _ = _host()

    async def scenario():
        render = await host.open("example", {})
        edited = await host.collect(_payload(render, "edit"))
        assert host.get(render.record.workspace_id) == edited.record

    run(scenario())


def test_writer_refuses_a_hard_link(tmp_path):
    """An append through a hard link would land in the other file, such as record.json."""
    other = tmp_path / "record.json"
    other.write_text("{}\n", encoding="utf-8")
    target = tmp_path / "events.jsonl"
    try:
        os.link(other, target)
    except OSError as exc:  # a file system without hard links
        pytest.skip(f"hard links unavailable: {exc}")
    write = jsonl_event_writer(target)
    with pytest.raises(ValueError, match="hard link"):
        write({"event": "probe"})
    assert other.read_text(encoding="utf-8") == "{}\n"


def test_writer_appends_are_whole_across_processes(tmp_path):
    """Four processes, 500 lines each, one file: every line parses and none is lost.

    On POSIX ``O_APPEND`` already makes this hold; on Windows the C runtime
    appends by seeking and then writing, so without the writer's lock two
    processes tear each other's lines, which the Windows platform job showed.
    """
    import attune_harness

    path = tmp_path / "events.jsonl"
    script = tmp_path / "appender.py"
    script.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "from attune_harness.command_workspace import jsonl_event_writer\n"
        "write = jsonl_event_writer(Path(sys.argv[1]))\n"
        "who = sys.argv[2]\n"
        "for n in range(500):\n"
        "    write({'event': 'probe', 'who': who, 'n': n, 'pad': 'x' * 200})\n",
        encoding="utf-8",
    )
    env = {**os.environ, "PYTHONPATH": str(Path(attune_harness.__file__).resolve().parents[1])}
    children = [
        subprocess.Popen(
            [sys.executable, str(script), str(path), f"p{i}"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for i in range(4)
    ]
    for child in children:
        _, err = child.communicate(timeout=120)
        assert child.returncode == 0, err
    lines = path.read_bytes().split(b"\n")
    assert lines[-1] == b""
    events = [json.loads(line) for line in lines[:-1]]
    assert len(events) == 2000
    seen = {}
    for event in events:
        seen.setdefault(event["who"], set()).add(event["n"])
    assert seen == {f"p{i}": set(range(500)) for i in range(4)}
