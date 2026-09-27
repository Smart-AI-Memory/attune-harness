"""D27.3: current forms stay unchanged; aliases retain behavior and emit notices."""

# qualify: platform
import json
from importlib.metadata import version
from pathlib import Path

import pytest

from attune_harness.features import deprecation_entry, report, with_deprecation

ROOT = Path(__file__).resolve().parents[1]
NOTICE = dict(surface='CLI', form='old-name', since='1.1.0', removal='1.2.0',
              replacement='new-name')


def test_active_register_has_valid_unique_not_overdue_entries():
    # docs is a source-controlled register, not a runtime file dependency.
    entries = json.loads((ROOT / 'docs/deprecations.json').read_text())
    assert isinstance(entries, list)
    from packaging.version import Version
    current = Version(version('attune-harness'))
    identities = []
    for entry in entries:
        assert deprecation_entry(entry) == entry
        identities.append((entry['surface'], entry['form']))
        assert current < Version(entry['removal']), 'Remove expired active forms and register entries together'
    assert len(identities) == len(set(identities))


def test_synthetic_alias_keeps_behavior_and_only_old_form_emits_notice():
    def command(form):
        if form not in ('new-name', 'old-name'):
            raise ValueError('Unknown command')
        result = report('example', 'completed', result=4)
        return with_deprecation(result, NOTICE) if form == 'old-name' else result

    current, old = command('new-name'), command('old-name')
    assert current['result'] == old['result'] == 4
    assert current['status'] == old['status'] == 'completed'
    assert 'deprecations' not in current
    assert old['deprecations'] == [NOTICE]


def test_multiple_notices_do_not_mutate_or_duplicate_inputs():
    original = report('example', 'completed')
    first = with_deprecation(original, NOTICE)
    second_notice = {**NOTICE, 'form': 'another-old-name'}
    second = with_deprecation(first, second_notice)
    assert with_deprecation(second, NOTICE) == second
    second['deprecations'][0]['form'] = 'changed'
    assert first['deprecations'] == [NOTICE]
    assert 'deprecations' not in original


@pytest.mark.parametrize('changes', [
    {'removal': '1.1.9'}, {'removal': '1.0.0'}, {'since': '1.1.0rc1'},
    {'since': '01.1.0'}, {'since': True}, {'replacement': ''}, {'unexpected': 'field'},
])
def test_invalid_notices_are_refused_before_mutating(changes):
    original = {'status': 'completed'}
    with pytest.raises(ValueError):
        with_deprecation(original, {**NOTICE, **changes})
    assert original == {'status': 'completed'}


def test_later_minor_or_major_removal_satisfies_minimum():
    assert deprecation_entry({**NOTICE, 'since': '1.1.9'})['removal'] == '1.2.0'
    assert deprecation_entry({**NOTICE, 'removal': '2.0.0'})['removal'] == '2.0.0'


def test_changelog_and_retention_rule_are_documented():
    text = (ROOT / 'docs/compatibility.md').read_text()
    assert 'old form still working for one minor release' in text
    assert 'changelog line' in text
    assert 'docs/deprecations.json' in text
