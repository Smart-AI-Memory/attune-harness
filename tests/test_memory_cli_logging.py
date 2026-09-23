"""``configure_process`` binds structlog once, to a stream resolved at write time (O-67)."""
# qualify: platform

import io
import sys

import pytest

from attune_harness import memory_cli

structlog = pytest.importorskip("structlog")


@pytest.fixture
def unconfigured(monkeypatch):
    """Start unconfigured and leave nothing behind: structlog's configuration is
    process-global, and the module flag must agree with it afterwards."""
    structlog.reset_defaults()
    monkeypatch.setattr(memory_cli, "_configured", False)
    yield
    structlog.reset_defaults()


def test_configure_process_binds_structlog_once(monkeypatch, unconfigured):
    calls = []
    monkeypatch.setattr(structlog, "configure", lambda **named: calls.append(named))
    memory_cli.configure_process()
    memory_cli.configure_process()
    assert len(calls) == 1
    assert calls[0]["logger_factory"]._file is memory_cli._STDERR


def test_configure_process_disables_the_usage_ping_every_time(monkeypatch):
    monkeypatch.setattr(memory_cli, "_configured", True)
    monkeypatch.delenv("ATTUNE_USAGE_PING", raising=False)
    memory_cli.configure_process()
    assert memory_cli.os.environ["ATTUNE_USAGE_PING"] == "0"


def test_log_lines_follow_the_current_stderr_not_the_one_at_configure_time(monkeypatch, unconfigured):
    first, second = io.StringIO(), io.StringIO()
    monkeypatch.setattr(sys, "stderr", first)
    memory_cli.configure_process()
    structlog.get_logger("probe").warning("one")
    monkeypatch.setattr(sys, "stderr", second)
    structlog.get_logger("probe").warning("two")
    assert "one" in first.getvalue() and "two" not in first.getvalue()
    assert "two" in second.getvalue()
    first.close()
    third = io.StringIO()
    monkeypatch.setattr(sys, "stderr", third)
    structlog.get_logger("probe").warning("three")
    assert "three" in third.getvalue()


def test_a_missing_or_closed_stderr_drops_the_line_and_never_raises(monkeypatch, unconfigured):
    memory_cli.configure_process()
    monkeypatch.setattr(sys, "stderr", None)
    structlog.get_logger("probe").warning("dropped")
    closed = io.StringIO()
    closed.close()
    monkeypatch.setattr(sys, "stderr", closed)
    structlog.get_logger("probe").warning("dropped too")
    memory_cli._STDERR.flush()


def test_execute_no_longer_configures_the_process(monkeypatch, tmp_path):
    # main owns start-up; execute is what tests drive in-process.
    called = []
    monkeypatch.setattr(memory_cli, "configure_process", lambda: called.append(True))
    config = tmp_path / "memory.json"
    config.write_text("{}", encoding="utf-8")
    import argparse
    parser = argparse.ArgumentParser()
    memory_cli.add_arguments(parser)
    memory_cli.execute(parser.parse_args(["--config", str(config), "capabilities"]))
    assert called == []
    # An empty config is refused, so main exits 2 here; what this asserts is
    # that main, and only main, configured the process on the way.
    assert memory_cli.main(["--config", str(config), "capabilities"]) == 2
    assert called == [True]
