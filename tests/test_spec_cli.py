"""Intake form and presentation seams have no legacy provider dependency."""
# qualify: platform
import io
import json
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


@pytest.mark.parametrize('raw',['[]','{','{"outcome":1}', '[['*5000, 'x'*65537, '{"outcome":"x","done_when":"y","unknown":"z"}'])
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
