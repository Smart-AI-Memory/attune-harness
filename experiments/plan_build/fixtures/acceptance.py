"""Frozen acceptance for a JSON Lines export; generated tests cannot replace it."""

import argparse
from dataclasses import asdict
import importlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "src"))
docs = importlib.import_module("attune_harness.documentation")

# Host fixture preparation replaces this once, before any worker runs. The
# existing protected-oracle hash binds these pre-change output bytes too.
CAPTURED_DEFAULT_OUTPUTS = {}


def invoke(*args):
    return subprocess.run(
        [sys.executable, "-B", "-m", "attune_harness.documentation", *args],
        cwd=ROOT,
        env={
            "PATH": "/usr/bin:/bin",
            "PYTHONPATH": str(ROOT / "src"),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        },
        capture_output=True,
        text=True,
        timeout=10,
    )


class Baseline(unittest.TestCase):
    def test_existing_json_output_and_static_scope(self):
        outputs = {}
        for module in ("samples/api.py", "samples/empty.py"):
            with self.subTest(module=module):
                result = invoke(module)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(module, CAPTURED_DEFAULT_OUTPUTS)
                self.assertEqual(result.stdout, CAPTURED_DEFAULT_OUTPUTS[module])
                outputs[module] = json.loads(result.stdout)
        bundle = outputs["samples/api.py"]
        expected = docs.generate(ROOT, "samples/api.py")
        self.assertEqual(
            bundle, {"markdown": expected.markdown(), "receipt": expected.to_dict()}
        )
        self.assertEqual(bundle["receipt"]["status"], "verified")
        self.assertIn("behavior is not certified", bundle["receipt"]["scope"])

    def test_unknown_is_retained_in_existing_evidence(self):
        evidence = docs.snapshot(ROOT, "samples/api.py")
        claim = docs.Claim("behavior", "add", "Always safe", "samples/api.py", 1, 2)
        finding = docs.check_claim(evidence, claim)
        self.assertEqual(finding.status, "unknown")


class Feature(unittest.TestCase):
    def test_cli_jsonl_preserves_the_complete_receipt(self):
        result = invoke("samples/api.py", "--format", "jsonl")
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads(line) for line in result.stdout.splitlines()]
        expected = docs.generate(ROOT, "samples/api.py").to_dict()
        findings = expected.pop("findings")
        self.assertEqual(records[0], {**expected, "kind": "documentation-header"})
        self.assertEqual(
            records[1:],
            [
                {"schema_version": 1, "kind": "finding", "finding": finding}
                for finding in findings
            ],
        )
        self.assertTrue(result.stdout.endswith("\n"))

    def test_unknown_refuted_and_advisory_notes_survive(self):
        exporter = importlib.import_module("attune_harness.documentation_export")
        evidence = docs.snapshot(ROOT, "samples/api.py")
        known = docs.api_claims(evidence)[0]
        unknown = docs.Claim(
            "behavior", "add", "Unproven\nclaim", "samples/api.py", 1, 2
        )
        wrong = docs.Claim("symbol", "missing", "missing", "samples/api.py", 1, 2)
        findings = tuple(docs.check_claim(evidence, c) for c in (known, unknown, wrong))
        self.assertEqual(
            [f.status for f in findings], ["verified", "unknown", "refuted"]
        )
        document = docs.Documentation(
            evidence, findings, 'Advisory only: "review"\nsecond line'
        )
        records = [
            json.loads(line) for line in exporter.json_lines(document).splitlines()
        ]
        self.assertEqual(records[0]["reviewer_notes"], document.reviewer_notes)
        self.assertEqual(records[0]["status"], "refuted")
        self.assertEqual(
            [r["finding"] for r in records[1:]], [asdict(f) for f in findings]
        )

    def test_empty_document_has_one_unknown_header(self):
        result = invoke("samples/empty.py", "--format", "jsonl")
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["status"], "unknown")

    def test_default_json_remains_compatible(self):
        Baseline(
            "test_existing_json_output_and_static_scope"
        ).test_existing_json_output_and_static_scope()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", action="store_true")
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        Baseline if args.baseline else Feature
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
