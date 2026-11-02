"""Offline T1 witnesses; never execute a provider CLI or load its credentials.

These checks establish existing subprocess isolation and expose preflight's
information loss. They do not implement a funding selector or qualify billing.
Run with Python 3.12+ from any directory; only this checkout's source is loaded.
"""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from attune_harness import process
from attune_harness.consultation_preflight import _signed_in


WITNESS = r'''
import json, os, sys
request = json.loads(sys.stdin.read())
if request["operation"] == "status":
    # Inert reproduction of the version-pinned Codex login-status contract.
    print("Logged in using ChatGPT")
elif request["operation"] == "environment":
    key = os.environ.get("CODEX_API_KEY")
    print(json.dumps({
        "key_matches": key == request.get("expected_synthetic_key"),
        "api_override_present": bool(key),
        "label": os.environ.get("HARNESS_T1_LABEL"),
    }))
else:
    sys.exit(2)
'''


def require(condition, description):
    if not condition:
        raise RuntimeError(description)


def witness_checks(baseline):
    checks = []
    # main has replaced only the Python mapping with synthetic values. Never
    # snapshot the actual credential-bearing process environment.
    before = dict(os.environ)
    api = {**baseline, "CODEX_API_KEY": "synthetic-t1-only", "HARNESS_T1_LABEL": "api"}
    subscription = {**baseline, "HARNESS_T1_LABEL": "subscription"}
    api_before, subscription_before = dict(api), dict(subscription)

    with tempfile.TemporaryDirectory(prefix="harness-funding-t1-") as name:
        directory = Path(name)
        witness = directory / "witness.py"
        witness.write_text(WITNESS, encoding="utf-8")

        def invoke(environment, request):
            result = process.invoke(
                (sys.executable, "-I", "-S", str(witness)), json.dumps(request),
                cwd=directory, environment=environment, timeout=10, max_output_bytes=4096)
            require(result.failure is None and result.returncode == 0, "witness subprocess failed")
            require(not result.stderr, "witness wrote an unexpected diagnostic")
            return result.stdout

        def environment_report(environment):
            return json.loads(invoke(environment, {
                "operation": "environment", "expected_synthetic_key": "synthetic-t1-only"}))

        with ThreadPoolExecutor(max_workers=2) as pool:
            api_future = pool.submit(environment_report, api)
            subscription_future = pool.submit(environment_report, subscription)
            a, s = api_future.result(), subscription_future.result()
        require(a == {"key_matches": True, "api_override_present": True, "label": "api"},
                "API witness did not receive its selected synthetic key and label")
        checks.append("api_child_environment")
        require(s == {"key_matches": False, "api_override_present": False, "label": "subscription"},
                "subscription witness inherited an API override")
        checks.append("concurrent_child_environment_separation")
        require(dict(os.environ) == before and api == api_before and subscription == subscription_before,
                "parent environment or caller dictionaries changed")
        checks.append("parent_and_input_environments_unchanged")

        # Both status witnesses intentionally report the same stored login even
        # though their exec environments differ. Do not mistake this for proof
        # of a real provider's route: that fact comes from the pinned source.
        status_a = invoke(api, {"operation": "status"})
        status_s = invoke(subscription, {"operation": "status"})
        require(status_a == status_s == "Logged in using ChatGPT\n",
                "status counterexample did not reproduce")
        checks.append("same_status_different_exec_environments")

        # Exercise the actual current parser rather than duplicating it here.
        for status in ("Logged in using ChatGPT", "Logged in using an API key - synthetic"):
            parsed = _signed_in("codex", process.ProcessResult((), 0, status, ""))
            require(parsed is True, "current parser no longer collapses both login methods")
        checks.append("current_parser_collapses_funding_modes")
        malformed = _signed_in("codex", process.ProcessResult((), 0, "unrecognized", ""))
        require(malformed is None, "unrecognized status became verified")
        checks.append("unknown_status_is_not_verified")

    print(json.dumps({
        "schema_version": 1, "profile": "participant-funding-t1-witnesses-v2",
        "checks": checks, "passed": len(checks), "failed": 0,
        "provider_calls": 0, "qualification": "offline_process_and_parser_only",
        "subscription_route_enforcement": "not_qualified",
    }, indent=2))


def main():
    if sys.version_info < (3, 12):
        raise RuntimeError("T1 witnesses require Python 3.12 or later")
    real_environment = os.environ
    # Read only named OS startup variables. Do not inspect auth/config values.
    baseline = {key: real_environment[key] for key in ("SystemRoot", "TEMP", "TMP")
                if key in real_environment}
    try:
        os.environ = {**baseline, "CODEX_API_KEY": "synthetic-parent-only"}
        witness_checks(baseline)
    finally:
        # Reattach the original mapping without reading, changing or printing
        # any of its credential-bearing entries.
        os.environ = real_environment


if __name__ == "__main__":
    main()
