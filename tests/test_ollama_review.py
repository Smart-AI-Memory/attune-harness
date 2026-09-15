import copy
import json
from types import SimpleNamespace

import pytest

from attune_harness.ollama_review import respond, projected_evidence
from attune_harness.review_contract import digest


class Model:
    pin = SimpleNamespace(name='local', digest='a'*64, server_version='1')
    last_response = None
    last_request = None
    generation_attempted = False

    def __init__(self, value=None):
        self.calls = []
        self.value = {'review': 'Evidence remains unknown.'} if value is None else value

    def generate(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        self.last_request = {'prompt': prompt, **kwargs}
        self.generation_attempted = True
        self.last_response = {'response': json.dumps(self.value)}
        return self.last_response


def turn():
    return {'objective':'Review documentation', 'query':'evidence',
            'document':{'path':'guide.md','text':'A claim.'}, 'history':[],
            'tools':['retrieve','verify'], 'remaining_tool_calls':2,'remaining_turns':3,
            'role':'reviewer', 'turn_id':'do-not-use-as-path',
            'initial_retrieval':{'lead_narrative':'Never give this to the reviewer'}}


def wire(value):
    return json.dumps({'schema_version':1,'request_digest':digest(value),'turn':value})


def history():
    return [{'action':{'name':'retrieve'}, 'result':{'operation':'retrieve','status':'retrieved',
                'sources':[{'path':'source.md','sha256':'a'*64,'excerpt':'source evidence'}],
                'corpus':{'version':'v1'}}},
            {'action':{'name':'verify'},'result':{'operation':'verify','status':'unknown',
                'result':{'coverage':{'total':1,'unknown':1},'semantic_ran':False,
                    'claims':[{'id':'claim','kind':'links','subject':'missing.md','status':'unknown',
                               'location':'line 1','detail':'not projected, kept in the native record'}]}}}]


def test_requests_granted_tools_before_inference(tmp_path):
    value, model = turn(), Model()
    assert json.loads(respond(wire(value),model,tmp_path,1))['action'] == {
        'kind':'tool','name':'retrieve','arguments':{'query':'evidence','k':3}}
    value['history']=history()[:1];value['remaining_tool_calls']=1;value['remaining_turns']=2
    assert json.loads(respond(wire(value),model,tmp_path,1))['action']['name']=='verify'
    assert not model.calls and not list(tmp_path.iterdir())


def test_extension_retrieval_uses_accepted_binding(tmp_path):
    value=turn();value['tools']=['evidence.search'];value['tool_contracts']={'evidence.search':{'binding':'retrieve'}}
    assert json.loads(respond(wire(value),Model(),tmp_path,1))['action']['arguments']=={'query':'evidence','k':3}


def test_complete_review_persists_evidence_and_prevents_duplicate_generation(tmp_path):
    value,model=turn(),Model();value['history']=history()
    result=json.loads(respond(wire(value),model,tmp_path,1))
    assert result['request_digest']==digest(value)
    assert result['action']['text'].startswith('Local model review (unverified proposal):')
    prompt=json.loads(model.calls[0][0])
    assert prompt['document']==value['document']
    assert prompt['evidence'][1]['claims'][0]['status']=='unknown'
    assert prompt['evidence'][1]['coverage']=={'total':1,'unknown':1}
    assert 'lead_narrative' not in model.calls[0][0] and 'initial_retrieval' not in prompt
    saved=json.loads((tmp_path/digest(value)/'record.json').read_text())
    assert saved['status']=='completed' and saved['generation_request']==model.last_request
    with pytest.raises((ValueError,FileExistsError)):
        respond(wire(value),model,tmp_path,1)
    assert len(model.calls)==1


@pytest.mark.parametrize('change',[
    lambda v:v.update(remaining_tool_calls=1),lambda v:v.update(remaining_turns=2),
    lambda v:v.update(tools=['ungranted']),lambda v:v.update(history=[{'action':{'name':'verify'}}])])
def test_invalid_budget_or_history_never_generates(tmp_path,change):
    value,model=turn(),Model();change(value)
    with pytest.raises(ValueError):respond(wire(value),model,tmp_path,1)
    assert not model.calls


def test_bad_correlation_never_generates(tmp_path):
    value=json.loads(wire(turn()));value['request_digest']='b'*64;model=Model()
    with pytest.raises(ValueError,match='digest'):respond(json.dumps(value),model,tmp_path,1)
    assert not model.calls


@pytest.mark.parametrize('output',[{'review':''},{'review':'x'*32769},{'review':False},{'review':'x','extra':True}])
def test_bad_model_output_is_retained_as_failure(tmp_path,output):
    value,model=turn(),Model(output);value['history']=history()
    with pytest.raises(ValueError):respond(wire(value),model,tmp_path,1)
    saved=json.loads((tmp_path/digest(value)/'record.json').read_text())
    assert saved['status']=='failed' and saved['generation']==model.last_response
    assert len(model.calls)==1


def test_projection_preserves_all_claims_and_does_not_mutate_input():
    value=turn();value['history']=history();before=copy.deepcopy(value)
    assert len(projected_evidence(value)['evidence'][1]['claims'])==1
    assert value==before
