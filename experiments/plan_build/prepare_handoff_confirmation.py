"""Freeze a six-call proposal without admitting or dispatching native work."""

import argparse
import copy
import importlib.util
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "confirmation_meter", HERE / "run_connected.py"
)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
ROOT = native.ROOT
ORIGINAL = ROOT / "docs/receipts/plan-build-connected-native-2026-09-18"
QUALIFIED = ROOT / "docs/receipts/plan-build-handoff-correction-2026-09-18"
ORACLE_QUALIFIED = ROOT / "docs/receipts/plan-build-default-compatibility-2026-09-18"
PREVIOUS = ROOT / "docs/receipts/plan-build-handoff-confirmation-native-2026-09-18"

FORM = """# Task 8 — fresh connected confirmation

One fresh journey, **six calls maximum: Luna 4, Astra 2**,
**15–30 estimated Codex credits**, a **40-credit additional planning allowance**,
existing ChatGPT and **$0 new API dollars**. Patrick explicitly authorized
40 more credits and continuation. The previous 7.744460 credits stay separate;
there is no unsettled option to ask again.

Luna plans and implements the three ordered exporter, CLI and supplemental-test
stages. Astra critiques the plan and reviews the final artifacts. Use the repaired
protected runner, captured pre-change output oracle and actual Spec collector. Retain
synthetic pending-task correction/reacceptance, preserved completed output,
no-repeat completion and stale-source rejection. Inspect generated code before
execution. Stop at an original contract, test, review, usage or authority failure;
no response repair, automatic retry, replacement or provider fallback.

The four earlier passed review controls are retained evidence, not new calls.
Acceptance of this experiment requires the complete original journey to pass,
including semantic inspection of the plan and tests. A correct claim stays
accepted; legitimate unknowns and optional advice remain distinct from defects.
Record call/token estimates, native response timing, semantic grading and local
check output separately. Actual desktop/human timing remains unknown.

The local source and installed checks qualify the corrected oracle; connected
native completion still needs evidence. The strongest counter-case: one synthetic journey cannot
establish reliability, changed-intent adaptation or a model cost/speed ranking.
The scripted correction may repeat a check already chosen by the planner.

The previous allocation is closed, with two calls deliberately unused. This is
a fresh six-call admission under the additional credit ceiling. It covers only the bounded
confirmation, including synthetic decisions and disposable file effects. It
does not accept Task 8, activate an installation, touch live memories or release
the product. Estimates and pre-call reservations are not a hard invoice limit.

The raw user instruction and frozen packet are retained with admission.
"""


def prepare(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    protocol = copy.deepcopy(native.read(native.PREP / "protocol.json"))
    protocol["journeys"] = [protocol["journeys"][0]]
    protocol["controls_first"] = []
    protocol["retained_controls"] = (
        "Four original passed controls; no fresh control dispatch"
    )
    protocol["budget"].update(
        max_calls=6,
        max_calls_by_model={"gpt-5.6-luna": 4, "gpt-6-astra": 2},
        expected_credits=[15, 30],
        codex_credit_planning_ceiling=40,
        estimate_basis="Observed Astra critique 6.9645 credits, allow larger final review; four earlier Luna role calls cost 0.57568. Wider 15–30 estimate allows full CLI/test outputs and startup variability.",
    )
    paths = [ROOT / name for name in protocol["source_sha256"]]
    paths += [
        HERE / "run_connected.py",
        HERE / "connected_journey.py",
        HERE / "qualify_handoffs.py",
        HERE / "fixtures/run_supplemental.py",
        Path(__file__),
    ]
    protocol["source_sha256"] = {str(p.relative_to(ROOT)): native.sha(p) for p in paths}
    native.write(output / "protocol.json", protocol)
    template = output / "qualified/luna-routine/turns.json"
    template.parent.mkdir(parents=True)
    shutil.copyfile(native.PREP / "qualified/luna-routine/turns.json", template)
    for name in ("control-grades.json",):
        shutil.copyfile(ORIGINAL / name, output / name)
    for name in ("case-a", "case-b", "case-c", "case-d"):
        shutil.copytree(
            ORIGINAL / "calls" / ("control-" + name),
            output / "retained-controls" / name,
        )
    (output / "decision-form.md").write_text(FORM)
    native.write(
        output / "decision-binding.json",
        {
            "artifacts": {
                str(p.relative_to(ROOT)): native.sha(p)
                for p in (
                    ROOT / "docs/specs/plan-build/connected-handoff-correction.md",
                    QUALIFIED / "installed-identity.json",
                    QUALIFIED / "guard-removal.json",
                    ROOT / "docs/specs/plan-build/fresh-journey-qualification.md",
                    ORACLE_QUALIFIED / "manifest.json",
                    PREVIOUS / "ledger.json",
                )
            },
            "native_calls": 0,
        },
    )
    native.write(
        output / "manifest.json",
        {
            "sha256": {
                str(p.relative_to(output)): native.sha(p)
                for p in sorted(output.rglob("*"))
                if p.is_file()
            }
        },
    )
    return {"prepared": str(output), "native_calls": 0, "requires_admission": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    print(prepare(parser.parse_args().output))
