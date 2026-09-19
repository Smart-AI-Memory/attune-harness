"""Freeze and qualify the approved 40-call Luna-only real-module repair screen."""

import argparse
import ast
import copy
import importlib.util
import inspect
from pathlib import Path
import random
import shutil
import tempfile
import textwrap
from unittest.mock import patch

from luna_broader_cases import cases
from routing_eligibility import preservation

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("broader_screen", HERE / "repair_models.py")
screen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(screen)
TARGET = "src/subject.py"
MODEL = "gpt-5.6-luna"
INSTALLED = Path(screen.work_build.__file__).resolve().parents[1]


def test_script(checks, symbol, frozen):
    header = f'''import ast
import copy
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
sys.path.insert(0, {str(INSTALLED)!r})
import attune_harness
TARGET = Path(__file__).resolve().parent / 'src/subject.py'
spec = importlib.util.spec_from_file_location('attune_harness.subject', TARGET)
subject = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = subject
spec.loader.exec_module(subject)
assert Path(subject.__file__).resolve() == TARGET

def observed_case(**overrides):
    observed = dict(collection_errors=0, setup_errors=0, exit_code=0,
                    session_started=True, collect_only=False, failed=0,
                    passed=1, collected=1)
    observed.update(overrides)
    return SimpleNamespace(failure=None, returncode=0), observed
'''
    header += inspect.getsource(preservation)
    header += f'\nFROZEN = {frozen!r}\nSYMBOL = {symbol!r}\nclass FixtureTests(unittest.TestCase):\n'
    return header + ''.join(f'    def test_{i}(self):\n' + textwrap.indent(check + '\n', '        ') for i, check in enumerate(checks)) + '\nif __name__ == "__main__":\n    unittest.main(verbosity=2)\n'


def clearance(payload):
    return {"payload_digest": screen.digest(payload), "inspected_before_execution": True,
            "safe_to_execute": True, "semantic_passed": True,
            "method": "Known local reference/control, not a native grade."}


def prepare(out):
    out.mkdir(parents=True, exist_ok=False)
    prior = {str(p.relative_to(ROOT)): screen.sha(p) for p in (ROOT / "docs/receipts").rglob("*")
             if p.is_file() and out not in p.parents and "__pycache__" not in p.parts}
    screen.write(out / "prior-receipts.json", prior)
    prepared = cases()
    qualified = []
    with patch.object(screen.review_participants, "NativeExchange", screen.forbidden):
        for case in prepared:
            folder = out / "cases" / case["id"]
            temporary = Path(tempfile.mkdtemp(prefix="luna-broader-", dir="/private/tmp"))
            root = screen.driver.comparison.prep.fixture(temporary)
            (root / TARGET).write_text(case["correct"])
            frozen = preservation(case["broken"], case["symbol"])
            guards = [
                'self.assertEqual(preservation(TARGET.read_text(), SYMBOL)["outside"], FROZEN["outside"])',
                'self.assertEqual(preservation(TARGET.read_text(), SYMBOL)["interface"], FROZEN["interface"])',
            ]
            (root / "run_supplemental.py").write_text(test_script(case["checks"][:4], case["symbol"], frozen))
            (root / "acceptance.py").write_text(test_script(case["checks"][4:] + guards, case["symbol"], frozen))
            objective = case["behavior"] + f' Repair only the body of {case["symbol"]} in {TARGET}, a complete real module. Preserve its signature, imports, constants and all unrelated definitions and behavior. Return the complete file under the supplied response contract.'
            (root / "plan.md").write_text(objective + "\n")
            baseline = [screen.standalone_probe(root, TARGET, [script], folder / "baseline" / name)
                        for name, script in (("supplemental", "run_supplemental.py"), ("protected", "acceptance.py"))]
            assert all(r["passed"] for r in baseline), (case["id"], [(r["passed"],r["stderr"][-3000:]) for r in baseline])
            (root / TARGET).write_text(case["broken"])
            before = [screen.standalone_probe(root, TARGET, [script], folder / "before" / name)
                      for name, script in (("supplemental", "run_supplemental.py"), ("protected", "acceptance.py"))]
            assert all(not r["passed"] for r in before), (case["id"], "Defect must fail both suites")
            hashes = screen.fixture_files(root)
            for name in hashes:
                destination = folder / "fixture" / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(root / name, destination)
            screen.write(folder / "case.json", {"id":case["id"], "output":TARGET, "kind":"seeded-real-module",
                         "origin":case["origin"], "origin_sha256":case["origin_sha256"],
                         "source_bytes":len(case["correct"].encode()), "symbol":case["symbol"], "seed_count":case["seed_count"],
                         "objective":objective, "failure_excerpts":[r["stderr"][-1400:] for r in before], "fixture_sha256":hashes})
            screen.write(folder / "reference.json", {"local_reference_only":True,"path":TARGET,"text":case["correct"]})
            screen.construct(folder, folder / "owner")
            payload = screen.proposal(folder, case["correct"])
            positive = screen.evaluate(folder, payload, folder / "reference-evaluation", clearance(payload))
            assert positive["passed"], (case["id"], positive)
            unchanged = screen.proposal(folder, case["broken"] + "\n# still defective\n")
            unfixed = screen.evaluate(folder, unchanged, folder / "unfixed-control", clearance(unchanged))
            assert not unfixed["passed"] and unfixed.get("incomplete_rejected")
            # A behaviorally correct repair cannot add unrelated executable code.
            unrelated = screen.proposal(folder, case["correct"] + "\nUNRELATED_NEW_BEHAVIOR = True\n")
            rejected = screen.evaluate(folder, unrelated, folder / "preservation-control", clearance(unrelated))
            assert not rejected["passed"] and rejected.get("incomplete_rejected")
            assert rejected["probes"][0]["passed"] and not rejected["probes"][1]["passed"]
            # Exercise the signature oracle independently from unrelated preservation.
            tree = ast.parse(case["correct"])
            target = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == case["symbol"])
            target.args.kwonlyargs.append(ast.arg(arg="unexpected"))
            target.args.kw_defaults.append(ast.Constant(None))
            interface = screen.proposal(folder, ast.unparse(tree) + "\n")
            rejected_interface = screen.evaluate(folder, interface, folder / "interface-control", clearance(interface))
            assert not rejected_interface["passed"] and rejected_interface.get("incomplete_rejected")
            qualified.append({"case":case["id"], "source_bytes":len(case["correct"].encode()),
                              "baseline_passed":True,"defect_reproduced_both_suites":True,"reference_passed":True,
                              "unfixed_rejected":True,"unrelated_regression_rejected":True,"interface_regression_rejected":True,
                              "no_repeat":positive["no_repeat"],"stale_rejected":positive["stale_rejected"]})
            print(screen.canonical(qualified[-1]),flush=True)
    protocol = copy.deepcopy(screen.read(ROOT / "docs/receipts/plan-build-routing-eligibility-preparation-2026-09-18/protocol.json"))
    trials=[]
    rng=random.Random(9184020)
    for repetition in (1,2):
        names=[c["id"] for c in prepared]
        rng.shuffle(names)
        for name in names:
            trials.append({"id":f"lb{len(trials)+1:02d}","case":name,"model":MODEL,"repetition":repetition})
    protocol.update(status="prepared-for-approved-allocation",profiles={MODEL:protocol["profiles"][MODEL]},trials=trials,
                    case_turn_sha256={c["id"]:screen.sha(out / "cases" / c["id"] / "owner/turn.json") for c in prepared},
                    native_calls=0,native_authorization=False,
                    preparation_instruction="Patrick said ok then go after 40 Luna calls / 10–20-credit estimate / 30-credit planning ceiling.",
                    scoring={"candidate_floor":"40/40 original passes, including preservation and response contract. This earns further qualification, not production adoption.",
                             "analysis":"Report all original failures, per-case/model credits and latency. No pooling with prior trials or population reliability claim."},
                    limits="20 seeded repairs in complete current real modules, 2 repeats each; all Luna. No production routing, native final reviewer or Task 8 acceptance.")
    protocol["source_sha256"].update({str(p.relative_to(ROOT)):screen.sha(p) for p in (HERE / "luna_broader_cases.py",Path(__file__))})
    # Protected tests import dependencies from this qualified installed copy.
    protocol["source_sha256"].update({str(p):screen.sha(p) for p in (INSTALLED / "attune_harness").glob("*.py")})
    protocol["budget"].update(max_calls=40,max_calls_by_model={MODEL:40},expected_credits=[10,20],
                             codex_credit_planning_ceiling=30,reserve_before_next_call={MODEL:1},
                             assumed_tokens_per_call={"input":[30000,50000],"output":[3500,8000],"cached":0},
                             estimate_basis="40 Luna calls; uncached 30k/3.5k to 50k/8k input/output estimates 10.20–19.60 credits. Earlier 27-call Luna mean projects 6.54; larger sources justify margin. Session grading excluded; not an invoice cap.",
                             scope="New 40-call Luna allocation explicitly approved with go; earlier allocations remain closed.")
    screen.write(out / "protocol.json",protocol)
    screen.write(out / "qualification.json",{"passed":True,"native_calls":0,"cases":qualified,
                 "distinct_origin_modules":len({c["origin"] for c in prepared}),"two_defect_cases":sum(c["seed_count"]>1 for c in prepared)})
    assert all(screen.sha(ROOT/name)==value for name,value in prior.items())
    print(screen.canonical({"prepared":str(out),"cases":len(qualified),"planned_calls":40,"native_calls":0}),flush=True)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    prepare(parser.parse_args().output.resolve())
