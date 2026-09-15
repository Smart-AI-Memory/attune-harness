import pytest

from attune_harness.native import NativeExchange
from attune_harness.process import ProcessResult
from attune_harness.review_contract import accept_request, load_registry
from test_review import case, change, change_config
from test_astra_review import as_astra


def test_catalog_budget_keeps_controls_and_model(tmp_path):
    calls=[]
    def runner(argv,prompt,**kwargs):
        calls.append((argv,kwargs));return ProcessResult(argv,1,'','fixture','nonzero_exit')
    x=NativeExchange('codex',cwd=tmp_path,model='gpt-6-astra',reasoning_effort='xhigh',
                     skills_context_tokens=1000,runner=runner)
    with pytest.raises(RuntimeError):x('{"version":1}')
    argv,kwargs=calls[0]
    assert 'skills.max_context_tokens=1000' in argv
    assert 'model_reasoning_effort="xhigh"' in argv
    assert '--sandbox' in argv and 'read-only' in argv
    assert not any(a.startswith('--ignore') or 'dangerously' in a for a in argv)
    assert kwargs['cwd']==tmp_path


@pytest.mark.parametrize('value',[0,-1,10001,True,'1000',None])
def test_invalid_catalog_budget_rejected_by_registry(case,value):
    change_config(case,as_astra)
    change(case[1],lambda d:d['participants']['alpha'].update(skills_context_tokens=value))
    with pytest.raises(ValueError,match='skills_context_tokens'):load_registry(case[1])


def test_budget_changes_acceptance(case):
    change_config(case,as_astra)
    change(case[1],lambda d:d['participants']['alpha'].update(skills_context_tokens=1000))
    with pytest.raises(ValueError,match='Stale form revision'):accept_request(case[0],load_registry(case[1]))


def test_budget_not_silently_ignored_for_claude(tmp_path):
    with pytest.raises(ValueError,match='only for Codex'):
        NativeExchange('claude',cwd=tmp_path,skills_context_tokens=1000)
