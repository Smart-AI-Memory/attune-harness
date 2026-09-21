"""Counterexamples and evidence boundaries for the disposable routing candidate."""

import copy
import hashlib
import importlib.util
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / "experiments/plan_build/routing_eligibility.py"
spec = importlib.util.spec_from_file_location("routing_candidate", PATH)
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)
SOURCE = 'def value(item):\n    return item\n'
ARTIFACTS = {"supplemental.py": "a" * 64, "protected.py": "b" * 64}


def request(source=SOURCE):
    return {"source_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "target_path": "src/subject.py", "writable_files": ["src/subject.py"],
            "target_symbol": "value", "expected_behavior": "Return item unchanged",
            "required_checks": copy.deepcopy(ARTIFACTS)}


@pytest.mark.parametrize("prefix", ["", "import argparse\n", 'LABEL = "é"\n'])
def test_import_names_do_not_force_sol(prefix):
    source = prefix + SOURCE
    assert router.route(source, request(source), ARTIFACTS)["model"] == "gpt-5.6-luna"


@pytest.mark.parametrize("extra", [
    '\ndef other():\n    return 1\n', '\nasync def send():\n    return 1\n',
    '\nclass Buffer:\n    pass\n', '\nSTATE = []\n', '\nprint("loaded")\n',
])
def test_unrelated_behavior_uses_sol(extra):
    source = SOURCE + extra
    assert router.route(source, request(source), ARTIFACTS)["model"] == "gpt-5.6-sol"


@pytest.mark.parametrize("body", [
    '    def nested():\n        return item\n    return nested()\n',
    '    global STATE\n    return item\n',
    '    yield item\n',
    '    try:\n        return item\n    finally:\n        pass\n',
])
def test_target_control_flow_outside_the_profile_uses_sol(body):
    source = 'def value(item):\n' + body
    assert router.route(source, request(source), ARTIFACTS)["model"] == "gpt-5.6-sol"


@pytest.mark.parametrize("count,model", [(12, "gpt-5.6-luna"), (13, "gpt-5.6-sol")])
def test_frozen_statement_boundary(count, model):
    source = 'def value(item):\n' + '    item = item\n' * (count - 1) + '    return item\n'
    assert router.route(source, request(source), ARTIFACTS)["model"] == model


@pytest.mark.parametrize("field", ["source_sha256", "expected_behavior", "target_symbol", "target_path", "required_checks"])
def test_missing_required_evidence_blocks_both_workers(field):
    entry = request()
    del entry[field]
    assert router.route(SOURCE, entry, ARTIFACTS)["blocked"]


def test_stale_evidence_blocks_and_optional_missing_evidence_does_not():
    assert router.route(SOURCE + '# edit\n', request(), ARTIFACTS)["blocked"]
    assert router.route(SOURCE, request(), {**ARTIFACTS, "protected.py": "c" * 64})["blocked"]
    entry = request()
    entry["optional_attachment"] = "absent.md"
    assert router.route(SOURCE, entry, ARTIFACTS)["model"] == "gpt-5.6-luna"


@pytest.mark.parametrize("checks", [["a", "b"], {"a": "", "b": ""}, {"a": "g" * 64, "b": "b" * 64}])
def test_malformed_check_bindings_block(checks):
    entry = {**request(), "required_checks": checks}
    assert router.route(SOURCE, entry, ARTIFACTS)["blocked"]


def test_missing_and_ambiguous_declared_target_block():
    entry = {**request(), "target_symbol": "missing"}
    assert router.route(SOURCE, entry, ARTIFACTS)["blocked"]
    duplicate = SOURCE + SOURCE
    assert router.route(duplicate, request(duplicate), ARTIFACTS)["blocked"]


def test_function_body_alternatives_preserve_interface_but_other_changes_do_not():
    baseline = router.preservation(SOURCE, "value")
    assert router.preservation(SOURCE.replace('return item', 'result = item\n    return result'), "value") == baseline
    assert router.preservation(SOURCE.replace('item):', 'item, extra=None):'), "value") != baseline
    assert router.preservation(SOURCE.replace('def value', 'async def value'), "value") != baseline
    assert router.preservation('LABEL = "changed"\n' + SOURCE, "value") != baseline
