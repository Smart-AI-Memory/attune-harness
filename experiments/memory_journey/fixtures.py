"""Frozen synthetic journey inputs and injected offline controller answers."""
import json
from pathlib import Path
from copy import deepcopy
from managed_stash import worker

HERE = Path(__file__).resolve().parent


def packet():
    return json.loads((HERE/'cases.json').read_text(encoding='utf-8'))


def answer(stage, bound):
    """Offline fixture only; never used as a live participant response."""
    note = dict(id='rehearsal-note',text='The cedar rehearsal starts at 09:15 on weekdays.',
                scope='cedar',kind='note',source_ids=['N1'])
    if stage == 'correction':
        note.update(text='The cedar rehearsal starts at 10:45 on weekdays.',source_ids=['N2'])
    return dict(operation={'capture':'capture','correction':'amend','forget':'forget'}[stage],
        outcome='update', facts=[] if stage=='forget' else [note],
        reason='Injected offline controller fixture.', evidence_ids=[{'capture':'N1','correction':'N2','forget':'N3'}[stage]],request='')


def participant(stage, calls=None):
    def call(role, model, prompt, schema):
        if calls is not None: calls.append((role,model,deepcopy(prompt)))
        value = (dict(verdict='supported', reason='Injected offline audit fixture.', evidence_ids=['N2'])
                 if role=='audit' else answer(stage,prompt))
        return dict(value=value)
    return call
