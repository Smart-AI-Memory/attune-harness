"""Actual CLI walks with inert plan responses; no live route qualification."""
# qualify: platform
import json
import os
import sys

import pytest

from attune_harness import consultation
from attune_harness.cli import main
from attune_harness.review_contract import canonical
from attune_harness.review_store import read_record
from attune_harness.task_contract import read_task
from test_plan_funding import plan, seat, participant, prepare_consultation, tmp_path
from test_review import case, change_config
from test_task_repair_effects import effect_case
from test_task_repair import proposal
from test_test_change import project, outcome


def call(capsys, args, code=0):
    assert main([str(x) for x in args]) == code
    return json.loads(capsys.readouterr().out)


@pytest.mark.parametrize('operation', ['source-review', 'roundtable'])
def test_consultation_cli_walk(tmp_path, plan, capsys, operation):
    directory, record = prepare_consultation(tmp_path, second=operation == 'roundtable')
    config = tmp_path/'seats.json'; config.write_text(canonical(record['contract']['configuration']))
    call(capsys, [operation, 'check', '--config', config], 2)
    assert plan.profiles.resolutions == 0
    # The prepare path was exercised by the real owner; walk the CLI into a fresh run too.
    run = tmp_path/'cli-run'
    prepared = call(capsys, [operation, 'prepare', '--config', config, '--project', tmp_path/'source',
                            '--path', 'x.py', '--run-dir', run])
    call(capsys, [operation, 'status', run])
    paused = call(capsys, [operation, 'run', run, '--accept', prepared['contract_digest'],
                           '--allow-external', '--max-operations', 1])
    if operation == 'roundtable':
        assert paused['status'] == 'paused' and len(plan.runner.calls) == 1
        done = call(capsys, [operation, 'run', run, '--accept', prepared['contract_digest'], '--allow-external'])
    else:
        assert paused['status'] == 'paused' and len(plan.runner.calls) == 1
        done = call(capsys, [operation, 'run', run, '--accept', prepared['contract_digest'], '--allow-external'])
    assert done['status'] == 'completed'
    before = len(plan.runner.calls), plan.profiles.resolutions
    call(capsys, [operation, 'evidence', run]); call(capsys, [operation, 'status', run])
    assert before == (len(plan.runner.calls), plan.profiles.resolutions)


def test_positional_review_and_resume_review_cli(case, plan, capsys):
    change_config(case, lambda v: v['participants'].update(alpha=participant(evidence=True)))
    paused = call(capsys, ['review', case[0], '--config', case[1], '--run-dir', case[2],
                          '--allow-external', '--max-operations', 1], 1)
    assert paused['status'] == 'paused' and not plan.runner.calls
    inspected = call(capsys, ['inspect-review', case[2]], 1)
    done = call(capsys, ['resume-review', case[2], '--request', case[0], '--config', case[1],
                        '--checkpoint', inspected['checkpoint_digest'], '--allow-external'])
    assert done['status'] == 'completed' and len(plan.runner.calls) == 1


def test_task_review_and_resume_cli(case, plan, capsys):
    change_config(case, lambda v: v['participants'].update(alpha=participant()))
    preview = call(capsys, ['review', '--goal', 'Check guide', '--project', case[0].parent,
                  '--config', case[1], '--task-dir', case[2], '--criteria', 'Preserve uncertainty',
                  '--query', 'quartz', '--document', 'project/guide.md', '--context', 'context.json',
                  '--corpus', 'project', '--assessor', 'alpha', '--intake-only'], 1)
    answer = preview['submission']; answer['accepted'] = True; answer['permissions']['external'] = True
    reply = case[0].parent/'response.json'; reply.write_text(canonical(answer))
    paused = call(capsys, ['review', '--task-dir', case[2], '--task-response', reply, '--pause-after', 2], 1)
    assert paused['status'] == 'paused' and not plan.runner.calls
    done = call(capsys, ['resume', case[2], '--checkpoint', paused['checkpoint_digest']])
    assert done['status'] == 'completed' and len(plan.runner.calls) == 1


@pytest.mark.skipif(os.name != 'posix', reason='POSIX frozen repair profile')
def test_fix_and_resume_cli(effect_case, plan, capsys):
    root, probe, _, _ = effect_case
    registry = root.parent/'registry.json'; registry.write_text(canonical({
        'schema_version': 1, 'participants': {n: participant('inert-'+n) for n in ('worker', 'reviewer')}}))
    probe_file = root.parent/'probe.json'; probe_file.write_text(canonical(probe['probe']))
    directory = root.parent/'cli-fix'
    plan.runner.reply = lambda attempt, turn, kw: canonical({
        'schema_version': 1, 'request_digest': turn['request_digest'], 'action': proposal(turn)})
    paused = call(capsys, ['fix', '--goal', 'Repair addition', '--project', root.parent, '--config', registry,
        '--checkout', root, '--scope', 'app.py', '--probe', probe_file, '--criteria', '2+3=5',
        '--worker', 'worker', '--reviewer', 'reviewer', '--review', 'required', '--task-dir', directory,
        '--accept', '--allow-external', '--pause-after', 2], 1)
    assert paused['status'] == 'paused' and len(plan.runner.calls) == 1
    done = call(capsys, ['resume', directory, '--checkpoint', paused['checkpoint_digest']])
    assert done['status'] == 'completed' and len(plan.runner.calls) == 2
    assert done['execution']['integration']['acceptance_status'] == 'verified_within_probe_scope'


def test_deterministic_test_cli_resume_never_resolves_funding(project, tmp_path, plan, capsys):
    directory = tmp_path/'test-task'
    preview = call(capsys, ['test', '--project', project, '--task-dir', directory,
                           '--scope', 'src/demo/logic.py', '--interpreter', sys.executable], 1)
    paused = call(capsys, ['test', '--task-dir', directory, '--accept', '--checkpoint',
                          preview['checkpoint_digest'], '--pause-after', 1], 1)
    assert paused['status'] == 'paused' and plan.profiles.resolutions == 0
    done = call(capsys, ['resume', directory, '--checkpoint', paused['checkpoint_digest']])
    assert done['status'] == 'completed' and outcome(done) == 'passed'
    assert not plan.runner.calls and plan.profiles.resolutions == 0
