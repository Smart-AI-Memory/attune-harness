"""Intake form and presentation seams have no legacy provider dependency."""
# qualify: platform
import io
import json
import os
from pathlib import Path
import pytest
from attune_harness.cli import main
from attune_harness.spec_intake import build_spec_intake_form
from test_spec_tasks import FULL


def test_intake_preserves_form_without_global_registration(tmp_path,capsys):
    from attune_forms.intake_template import PROVIDERS,TEMPLATES
    before=(dict(PROVIDERS),dict(TEMPLATES))
    form=build_spec_intake_form(['src/example'])
    assert [q.id for q in form.questions]==['outcome','done_when','area','slug']
    assert 'src/example' in form.questions[2].options
    assert (PROVIDERS,TEMPLATES)==before
    assert main(['spec','intake','--project',str(tmp_path)])==0
    value=json.loads(capsys.readouterr().out)
    assert value['areas']==[] and len(value['form']['fields'])==4


@pytest.mark.parametrize('raw',['[]','{','{"outcome":1}', '[['*5000, 'x'*65537, '{"outcome":"x","done_when":"y","unknown":"z"}'],
    ids=['array', 'malformed', 'wrong-type', 'deep-nesting', 'oversize', 'unknown-field'])
def test_compose_refuses_bad_answers(tmp_path,monkeypatch,capsys,raw):
    monkeypatch.setattr('sys.stdin',io.StringIO(raw))
    assert main(['spec','intake','--project',str(tmp_path),'--compose'])==2
    captured=capsys.readouterr();assert not captured.out and captured.err


def test_compose_collision_and_presenters(tmp_path,monkeypatch,capsys):
    (tmp_path/'docs/specs/demo').mkdir(parents=True)
    monkeypatch.setattr('sys.stdin',io.StringIO(json.dumps({'outcome':'working','done_when':'tested','slug':'demo'})))
    assert main(['spec','intake','--project',str(tmp_path),'--compose'])==0
    assert 'WARNING' in capsys.readouterr().out
    plan=tmp_path/'plan.md';plan.write_text(FULL)
    for view,extra,expected in [('tasks',[],'add-auth'),('task',['--task','1'],'returns 401'),('progress',[],'0/1')]:
        assert main(['spec','present',view,'--plan',str(plan),*extra])==0
        assert expected in capsys.readouterr().out
    assert main(['spec','present','result','--plan',str(plan),'--task','1','--test-run',str(tmp_path/'absent')])==2
    assert not capsys.readouterr().out


from test_connected_journey import journey  # noqa: F401


@pytest.mark.skipif(os.name != 'posix', reason='Actual Harness test-task receipts require the POSIX producer')
def test_result_requires_exact_persisted_acceptance(journey, capsys, tmp_path):
    from test_connected_journey import complete, run_linked
    from attune_harness.spec_handoff import bind_test_evidence
    from attune_harness.spec_state import SpecState, save_state
    complete(journey,capsys)
    tested=run_linked(journey)
    directory=Path(tested['record_path']).parent
    evidence=bind_test_evidence(directory)
    plan=tmp_path/'accepted.md';plan.write_text(FULL)
    args=['spec','present','result','--plan',str(plan),'--task','1','--test-run',str(directory)]
    assert main(args)==2  # A real test run alone does not associate it with a Spec task.
    capsys.readouterr()
    receipt={'task_id':'1','severity':'low','score':100,'probes':[evidence['record_path']],
             'detail':'Previously accepted fixture evidence','test_evidence':evidence,'disposition':'approve_task'}
    state=SpecState(plan_path=str(plan),completed=['1'],task_receipts=[receipt])
    save_state(state)
    assert main(args)==0
    assert 'PASSED' in capsys.readouterr().out
    state.task_receipts[0]['test_evidence']={**evidence,'task_id':'unrelated-testing-run'}
    save_state(state)
    assert main(args)==2
    assert 'differs' in capsys.readouterr().err

@pytest.mark.skipif(os.name != 'nt', reason='Windows-specific explicit testing refusal')
def test_windows_test_receipt_producer_is_explicitly_unsupported(tmp_path):
    from attune_harness.test_change import create_test_task
    import sys
    with pytest.raises(ValueError, match='POSIX execution profile'):
        create_test_task(tmp_path, tmp_path / 'tested', scope=['app.py'], interpreter=sys.executable)
    assert not (tmp_path / 'tested').exists()
