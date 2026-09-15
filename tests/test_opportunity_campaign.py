import copy
import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('opportunity_campaign',Path(__file__).parents[1]/'experiments/opportunities/campaign.py')
campaign=importlib.util.module_from_spec(spec);spec.loader.exec_module(campaign)


@pytest.mark.parametrize('bad',['duplicate','missing','wrong','bool_count'])
def test_grading_is_complete_and_strict(bad):
    row={'id':'a','critical_misses':0,'unsupported_assertions':0,'uncertainty_preserved':True,
         'sufficient_review':True,'explanation':'Evidence matches.'}
    rows=[row,{**row,'id':'b'}]
    if bad=='duplicate':rows[1]['id']='a'
    if bad=='missing':rows.pop()
    if bad=='wrong':rows[1]['id']='c'
    if bad=='bool_count':rows[1]['critical_misses']=True
    with pytest.raises(ValueError):campaign.validate_grades({'grades':rows},{'a','b'})


def test_failed_or_absent_usage_stays_unknown():
    assert campaign.usage('{"type":"turn.failed"}')['input_tokens'] is None
    assert campaign.usage('broken')['output_tokens'] is None
    assert campaign.usage('{"type":"turn.completed","usage":{"input_tokens":10,"output_tokens":5}}')=={
        'input_tokens':10,'output_tokens':5,'reasoning_output_tokens':None}
