# Disposable Guardian: integrated experiment

**Local result: 20/20 cases passed on macOS.** This demonstrates a bounded check → deterministic assignment → fixture repair → independent verification workflow, with retained state and recovery after a lost acknowledgement.

The worker is ordinary Python code that repairs one deliberately broken arithmetic fixture. It creates a candidate artifact; it does not apply a patch to a real project. No model call or service installation is required. This directory is separate from the Attune Harness package.

## Files

| File | Purpose |
|---|---|
| `DESIGN.md` | Question, frozen behavioral cases and limits |
| `guardian.py` | Durable incident ledger, fixed rule, fixture worker, verification and recovery |
| `host_client.py` | Separate client process that displays retained outcomes |
| `run_experiment.py` | Runs the acceptance cases through separate OS processes and saves evidence |
| `RECEIPT.md` | Results, preservation audit and remaining qualification |

## Run the cases

Requires Python 3.10 or newer and its standard library. The measured runtime was Python 3.10.11. From this directory:

```sh
python3 -B run_experiment.py --out receipts/my-run-01
```

On Windows, the corresponding **unverified** command is:

```powershell
py -3 -B run_experiment.py --out receipts/windows-01
```

Choose a fresh output directory each time. The runner refuses to overwrite a campaign. It saves source snapshots, hashes, each command's output, case results and a platform-labelled summary. A zero exit code requires every case to pass and the source hashes to remain unchanged during that run.

The portability bundle contains these same scripts and a hash manifest. Extract it, enter `guardian_v1`, and use the commands above. The bundle's source is tested on macOS; Windows and Linux need their own retained runs.

## Lost-acknowledgement walkthrough

Use a fresh directory for this sequence:

```sh
python3 -B guardian.py init receipts/my-demo-01
python3 -B guardian.py observe receipts/my-demo-01
python3 -B guardian.py tick receipts/my-demo-01 --fault after-effect
python3 -B guardian.py recover receipts/my-demo-01
python3 -B host_client.py receipts/my-demo-01
```

The third command deliberately exits **77** after the worker finishes but before the coordinator records its acknowledgement. Run the recovery command next. It validates the completion journal, checks the candidate against the original expected values in another process, and returns:

```json
{
  "state": "verified",
  "acceptance": "verified_fixture_repair",
  "verification": {"cases": 4, "failed": 0, "passed": 4},
  "budget": {"cap": 1, "used": 1}
}
```

This is an abbreviated client result. The full output also carries work identity, scope and report schema. The executed equivalent is retained at `receipts/demo-lost-ack`, with raw commands in `receipts/demo-commands.json`. Inspect that saved demonstration without rerunning it:

```sh
python3 -B host_client.py receipts/demo-lost-ack
```

Changing the fault to `after-intent` models a crash with persisted dispatch intent but no completion evidence. Recovery leaves it **unresolved** and retains the reservation. It never blindly replays the worker. `inspect` is read-only; `recover` can resume a pending fixture check or previously unstarted assignment.

## What is qualified

The cases cover concurrent admission and dispatch, duplicate events, four crash boundaries, changed inputs, malformed or mismatched completion evidence, false worker success, artifact tampering, exhausted budget, repeated recovery, and paths containing spaces and Unicode. Source fixtures use explicit UTF-8/LF bytes.

| Platform | Evidence |
|---|---|
| macOS 26.6.2, ARM64 | 20/20 cases; separate lost-acknowledgement walkthrough |
| Windows | Not run |
| Linux | Not run |

The synthetic budget unit measures a permitted dispatch, not money or tokens. These cases establish no model ranking, cost per verified repair or monitoring savings.

## Boundaries and next qualification

This is not an unattended daemon or a host connector for the active Claude Code/Codex conversation. It does not implement MCP/A2A, mixed teams, human forms, GitHub monitoring, authentication, service supervision, lease fencing or process-tree containment. The source revision is a content digest of the built-in fixture, not a Git commit. Passing verification accepts a candidate artifact; it does not install that artifact or certify a live repository head.

Crashes are injected at named boundaries using abrupt process exit. They do not establish power-loss durability, disk-failure recovery, hostile-process isolation, or exactly-once effects for arbitrary tools. Run recovery after the previous coordinator has stopped; this disposable interface has no lease that proves a live process is dead. Keep the SQLite ledger on local storage. It uses DELETE journaling and FULL synchronization.

Next: run this frozen campaign on native Windows and Linux. Then qualify each platform's service restart, cancellation, descendant cleanup and sleep/logout behavior separately. A native fixture pass alone will not qualify those lifecycle features.
