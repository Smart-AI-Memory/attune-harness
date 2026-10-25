"""Selected legacy presentation never becomes saved execution authority."""
# qualify: platform

import json

import pytest

from attune_harness import command_environment as ce
from attune_harness.cli import main
from attune_harness.gui_decisions import Decisions
from attune_harness.gui_build import Builds
from attune_harness.task_cli import present_task
from attune_harness.task_contract import read_task
from attune_harness.task_view import inspect, render
from attune_harness.work_cli import present
from test_command_environment import configuration
from test_review import case, change
from test_task_contract import draft
from test_work_contract import work, make


@pytest.mark.parametrize('selected', [False, True], ids=['unused', 'selected'])
def test_task_intake_notice_is_not_part_of_submission_or_saved_record(case, selected, capsys, recwarn):
    cfg = configuration(); cfg.pop('environment')
    change(case[1], lambda data: data['participants'].update(beta=cfg))
    raw = draft(case, answers={'assessor': 'beta' if selected else 'alpha'})
    before = (case[2]/'record.json').read_bytes()
    shown = present_task(case[2])
    assert shown.get('deprecations', []) == ([ce.NOTICE] if selected else [])
    assert 'deprecations' not in shown['submission'] and 'deprecations' not in raw
    assert main(['status', str(case[2])]) == 0
    assert json.loads(capsys.readouterr().out).get('deprecations', []) == ([ce.NOTICE] if selected else [])
    assert read_task(case[2]) == raw and (case[2]/'record.json').read_bytes() == before
    assert not recwarn.list


def test_review_form_does_not_claim_unselected_registry_usage(case, capsys):
    cfg = configuration(); cfg.pop('environment')
    change(case[1], lambda data: data['participants'].update(beta=cfg))
    assert main(['review-form', '--config', str(case[1])]) == 0
    assert 'deprecations' not in json.loads(capsys.readouterr().out)


@pytest.mark.parametrize('finite', [False, True], ids=['legacy', 'finite'])
def test_work_gui_and_readable_views_keep_raw_binding_bytes(work, finite, recwarn):
    cfg = configuration()
    if not finite:
        cfg.pop('environment')
    change(work[1], lambda data: data['participants'].update(local=cfg))
    record = make(work)
    directory = work[2]['directory']; before = (directory/'record.json').read_bytes()
    expected = [] if finite else [ce.NOTICE]
    shown = present(directory)
    assert shown.get('deprecations', []) == expected
    snapshot = inspect(directory)
    assert snapshot.get('deprecations', []) == expected
    for format in ('html', 'markdown'):
        text = render(snapshot, format)
        assert ('legacy full parent' in text) is not finite
    decisions = Decisions([directory.resolve()])
    try:
        item = decisions.inspect()[0]
        assert item.get('deprecations', []) == expected
        view = decisions.open(item['task'], item['checkpoint'])
        assert view.get('deprecations', []) == expected
        assert 'deprecations' not in decisions.live[item['task']][2]
    finally:
        decisions.close()
    # Opening the existing owner decision may retain it; its digest-bearing
    # record still contains no notice. Repeated inspection adds no other write.
    after_open = (directory/'record.json').read_bytes()
    current = read_task(directory)
    assert 'deprecations' not in current and current['request'] == record['request']
    assert current['checkpoint_digest'] == record['checkpoint_digest']
    assert after_open == before
    assert present(directory).get('deprecations', []) == expected
    assert (directory/'record.json').read_bytes() == after_open and not recwarn.list


def test_build_preview_notice_does_not_change_single_use_grant(work):
    from test_work_build import prepare
    cfg = configuration(); cfg.pop('environment')
    change(work[1], lambda data: data.update(participants={'local': cfg, 'critic': cfg}))
    _, directory, record = prepare(work)
    before = (directory/'record.json').read_bytes()
    decisions = Decisions([directory.resolve()]); builds = Builds(decisions)
    try:
        item = decisions.inspect()[0]
        shown = builds.preview(item['task'], item['checkpoint'])
        assert shown['deprecations'] == [ce.NOTICE]
        from attune_harness.review_contract import digest
        assert builds.previews[item['task']] == (shown['grant'], digest(record))
        assert builds.inspect(item['task'])['deprecations'] == [ce.NOTICE]
        assert (directory/'record.json').read_bytes() == before and read_task(directory) == record
    finally:
        builds.close(); decisions.close()


def test_registered_notice_matches_runtime_constant():
    from pathlib import Path
    register = json.loads((Path(__file__).parents[1]/'docs/deprecations.json').read_text())
    assert ce.NOTICE in register
