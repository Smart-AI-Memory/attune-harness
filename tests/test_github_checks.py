import pytest
from attune_harness.github_checks import check_suggestions


def payload(conclusion='failure',status='completed'):
    return {'total_count':1,'check_runs':[{'id':12,'app':{'id':9},'name':'unit tests',
        'head_sha':'a'*40,'status':status,'conclusion':conclusion}]}


def check(p):
    return check_suggestions(p,repository='fixture/project',revision='a'*40)


@pytest.mark.parametrize('conclusion,expected',[('success','observe'),('failure','human_review'),
    ('timed_out','reconcile'),('cancelled','reconcile'),('skipped','human_review'),('neutral','human_review'),('action_required','human_review')])
def test_check_conclusions_never_authorize_repairs(conclusion,expected):
    r=check(payload(conclusion));s=r['checks'][0]['suggestion']
    assert s['action']==expected and not s['dispatch_authorized'] and not r['repair_verified']
    assert r['all_checks_passed']==(conclusion=='success')


def test_pending_and_empty_are_not_success():
    assert check(payload(None,'queued'))['checks'][0]['suggestion']['action']=='wait'
    assert not check({'total_count':0,'check_runs':[]})['all_checks_passed']


@pytest.mark.parametrize('mutation',['revision','pagination','duplicate','missing_app','nonterminal_conclusion'])
def test_wrong_or_incomplete_exports_rejected(mutation):
    p=payload()
    if mutation=='revision':p['check_runs'][0]['head_sha']='b'*40
    if mutation=='pagination':p['total_count']=2
    if mutation=='duplicate':p['check_runs']*=2;p['total_count']=2
    if mutation=='missing_app':p['check_runs'][0]['app']={}
    if mutation=='nonterminal_conclusion':p['check_runs'][0]['status']='queued'
    with pytest.raises(ValueError):check(p)
