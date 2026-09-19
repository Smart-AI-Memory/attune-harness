"""Freeze and qualify the direct Luna/Sol routing experiment; no native calls."""

import argparse
import copy
import importlib.util
import inspect
from pathlib import Path
import random
import shutil
import tempfile
import time
from unittest.mock import patch

from routing_cases import cases
from routing_eligibility import preservation, route

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("eligibility_screen", HERE / "repair_models.py")
screen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(screen)
TARGET = "src/subject.py"
MODELS = ("gpt-5.6-luna", "gpt-5.6-sol")


def test_script(checks, symbol, frozen):
    header = '''import ast
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
import subject
assert Path(subject.__file__).resolve() == Path(__file__).resolve().parent / 'src/subject.py'
'''
    # The oracle is inside a protected file; workers cannot alter its baseline.
    header += inspect.getsource(preservation)
    header += f'\nFROZEN = {frozen!r}\nSYMBOL = {symbol!r}\nclass FixtureTests(unittest.TestCase):\n'
    return header + ''.join(f'    def test_{i}(self):\n        {check}\n' for i, check in enumerate(checks)) + '\nif __name__ == "__main__":\n    unittest.main(verbosity=2)\n'


def clearance(payload):
    return {"payload_digest": screen.digest(payload), "inspected_before_execution": True,
            "safe_to_execute": True, "semantic_passed": True,
            "method": "Known local reference or negative control, not a native grade."}


def prepare(out):
    out.mkdir(parents=True, exist_ok=False)
    prior = {str(p.relative_to(ROOT)): screen.sha(p) for p in (ROOT / "docs/receipts").rglob("*")
             if p.is_file() and out not in p.parents}
    screen.write(out / "prior-receipts.json", prior)
    qualified = []
    with patch.object(screen.review_participants, "NativeExchange", screen.forbidden):
        for case in cases():
            folder = out / "cases" / case["id"]
            temporary = Path(tempfile.mkdtemp(prefix="routing-eligibility-", dir="/private/tmp"))
            root = screen.driver.comparison.prep.fixture(temporary)
            (root / TARGET).write_text(case["correct"])
            frozen = preservation(case["broken"], case["symbol"])
            guards = [
                'self.assertEqual(preservation(Path(subject.__file__).read_text(), SYMBOL)["outside"], FROZEN["outside"])',
                'self.assertEqual(preservation(Path(subject.__file__).read_text(), SYMBOL)["interface"], FROZEN["interface"])',
            ]
            (root / "run_supplemental.py").write_text(test_script(case["checks"][:4], case["symbol"], frozen))
            (root / "acceptance.py").write_text(test_script(case["checks"][4:] + guards, case["symbol"], frozen))
            objective = case["behavior"] + f' Change only the body of {case["symbol"]} in {TARGET}. Preserve its signature, imports, constants and all other definitions and behavior. Return the complete file under the supplied contract.'
            (root / "plan.md").write_text(objective + "\n")
            baseline = [screen.standalone_probe(root, TARGET, [script], folder / "baseline" / name)
                        for name, script in (("supplemental", "run_supplemental.py"), ("protected", "acceptance.py"))]
            assert all(r["passed"] for r in baseline), (case["id"], baseline)
            (root / TARGET).write_text(case["broken"])
            before = [screen.standalone_probe(root, TARGET, [script], folder / "before" / name)
                      for name, script in (("supplemental", "run_supplemental.py"), ("protected", "acceptance.py"))]
            assert all(not r["passed"] for r in before), case["id"]
            hashes = screen.fixture_files(root)
            for name in hashes:
                destination = folder / "fixture" / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(root / name, destination)
            routing_input = {"target_path": TARGET, "target_symbol": case["symbol"],
                             "source_sha256": hashes[TARGET], "writable_files": [TARGET],
                             "expected_behavior": case["behavior"],
                             "required_checks": {name: hashes[name] for name in ("run_supplemental.py", "acceptance.py")}}
            start = time.perf_counter()
            selected = route(case["broken"], routing_input, hashes)
            route_seconds = time.perf_counter() - start
            assert selected["model"] == MODELS[case["variant"] == "embedded"], (case["id"], selected)
            screen.write(folder / "routing-input.json", routing_input)
            screen.write(folder / "routing-result.json", {**selected, "elapsed_seconds": route_seconds})
            screen.write(folder / "case.json", {"id": case["id"], "family": case["family"], "variant": case["variant"],
                         "output": TARGET, "kind": "fresh-structural-routing", "objective": objective,
                         "failure_excerpts": [r["stderr"][-1400:] for r in before], "fixture_sha256": hashes})
            screen.write(folder / "reference.json", {"local_reference_only": True, "path": TARGET, "text": case["correct"]})
            screen.construct(folder, folder / "owner")
            payload = screen.proposal(folder, case["correct"])
            positive = screen.evaluate(folder, payload, folder / "reference-evaluation", clearance(payload))
            assert positive["passed"], (case["id"], positive)
            negative = screen.proposal(folder, case["broken"] + "\n# defect remains\n")
            rejected = screen.evaluate(folder, negative, folder / "unfixed-control", clearance(negative))
            assert not rejected["passed"] and rejected.get("incomplete_rejected")
            # A functional fix with an unauthorized interface edit must fail.
            corrupted = case["correct"].replace("):\n", ", unexpected=None):\n", 1)
            bad = screen.proposal(folder, corrupted)
            guard = screen.evaluate(folder, bad, folder / "preservation-control", clearance(bad))
            assert not guard["passed"] and guard.get("incomplete_rejected")
            assert any(not p["passed"] for p in guard["probes"])
            if case["variant"] == "embedded":
                changed = screen.proposal(folder, case["correct"].replace("ensure_ascii=False", "ensure_ascii=True"))
                unrelated = screen.evaluate(folder, changed, folder / "unrelated-control", clearance(changed))
                assert not unrelated["passed"] and unrelated.get("incomplete_rejected")
            qualified.append({"case": case["id"], "selected_model": selected["model"], "baseline_passed": True,
                              "defect_reproduced_both_suites": True, "reference_passed": True,
                              "unfixed_rejected": True, "preservation_regression_rejected": True,
                              "no_repeat": positive["no_repeat"], "stale_rejected": positive["stale_rejected"]})
            print(screen.canonical(qualified[-1]), flush=True)
    base = screen.read(ROOT / "docs/receipts/plan-build-repair-contenders-preparation-2026-09-18/protocol.json")
    protocol = copy.deepcopy(base)
    trials = []
    rng = random.Random(918326)
    for repetition in (1, 2):
        names = [row["case"] for row in qualified]
        rng.shuffle(names)
        for name in names:
            models = list(MODELS)
            rng.shuffle(models)
            for model in models:
                trials.append({"id": f"ne{len(trials)+1:02d}", "case": name, "model": model, "repetition": repetition})
    protocol.update(trials=trials, case_turn_sha256={r["case"]: screen.sha(out / "cases" / r["case"] / "owner/turn.json") for r in qualified},
                    native_calls=0, native_authorization=False,
                    preparation_instruction="run: narrow eligibility experiment; paid amount not yet approved",
                    scoring={"policy_floor": "All 8 Luna-selected and all 16 selected attempts pass; no preservation miss; at least 25% fewer credits than always-Sol.",
                             "analysis": "Report all paired outcomes including unnecessary Sol selections. No deployed-routing, cascade or population reliability claim."},
                    limits="Eight matched synthetic source cases in four behavior families, two repeats per worker; no production routing or Task 8 acceptance.")
    protocol["source_sha256"].update({str(p.relative_to(ROOT)): screen.sha(p) for p in
                                     (HERE / "routing_eligibility.py", HERE / "routing_cases.py", Path(__file__))})
    protocol["budget"].update(max_calls=32, max_calls_by_model=dict.fromkeys(MODELS, 16), expected_credits=[50, 105],
                             codex_credit_planning_ceiling=120,
                             assumed_tokens_per_call={"input": [24000, 32000], "output": [1000, 6000], "cached": 0},
                             estimate_basis="16/model; prior measured prompts 24–32k tokens, assumed output 1–6k without caching: 48.8–104.64 credits; rounded 50–105. Current Standard rates verified September 18. Session grading excluded; not an invoice cap.",
                             scope="New proposed allocation. All earlier worker allocations closed; no headroom transfer.")
    screen.write(out / "protocol.json", protocol)
    screen.write(out / "qualification.json", {"passed": True, "native_calls": 0, "cases": qualified})
    assert all(screen.sha(ROOT / name) == value for name, value in prior.items())
    print(screen.canonical({"prepared": str(out), "cases": len(qualified), "planned_calls": len(trials), "native_calls": 0}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    prepare(parser.parse_args().output.resolve())
