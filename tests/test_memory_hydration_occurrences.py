"""Complete occurrences within each existing parser; no new YAML grammar."""
# qualify: platform

import base64
import sys

import pytest

from attune_harness.memory_hydration_secrets import REFUSAL, check_secrets
from attune_harness.memory_reader import source_labels

ROOT = dict(tier='curated', owner='fixture-user', scope='demo', classification='internal')
TOKEN = 'sk-' + 'Ab1' * 7
ESCAPED = '\\u0073' + TOKEN[1:]


def inspected(inner, *, budget=lambda: None):
    text = '---\n' + inner + '\n---\nordinary'
    check_secrets(text, check_budget=budget)
    occurrences = []
    labels = source_labels(ROOT, text, {}, _observe=occurrences.append, _check_budget=budget)
    check_secrets('', occurrences, check_budget=budget)
    check_secrets('', labels, check_budget=budget)
    return labels, occurrences


@pytest.mark.parametrize('inner', [
    'future: "' + ESCAPED + '"\nfuture: ordinary',
    'future: ordinary\nfuture: "' + ESCAPED + '"',
    '"' + ESCAPED + '": ordinary\nfuture: ordinary',
    'future:\n  nested: "' + ESCAPED + '"\n  nested: ordinary',
    'future: {nested: "' + ESCAPED + '", nested: ordinary}',
    'future: !!binary ' + base64.b64encode(TOKEN.encode()).decode() + '\nfuture: ordinary',
    'future: !!omap\n  - item: "' + ESCAPED + '"\n  - item: ordinary\nfuture: ordinary',
    'future: !!pairs\n  - item: "' + ESCAPED + '"\n  - item: ordinary\nfuture: ordinary',
    'future: !!set\n  ? "' + ESCAPED + '"\nfuture: ordinary',
    'future:\n  <<: &base {nested: "' + ESCAPED + '"}\n  nested: ordinary\nfuture: ordinary',
    'safe: &shared ["' + ESCAPED + '"]\nsafe: ordinary\nfuture: *shared\nfuture: ordinary',
])
def test_yaml_overwritten_decoded_occurrences_refuse_without_echo(inner):
    pytest.importorskip('yaml')
    with pytest.raises(ValueError) as caught:
        inspected(inner)
    assert str(caught.value) == REFUSAL
    assert TOKEN not in str(caught.value) and ESCAPED not in str(caught.value)


def test_shared_yaml_alias_is_checked_in_every_label_context():
    pytest.importorskip('yaml')
    inner = ('safe: &shared ["' + 'Ab1' * 9 + '"]\n'
             '"access_\\u0074oken": *shared\n"access_\\u0074oken": ordinary')
    with pytest.raises(ValueError, match=REFUSAL):
        inspected(inner)


@pytest.mark.parametrize('inner', [
    'future: first\nfuture: second',
    'future: {same: first, same: second}\nfuture: ordinary',
    'safe: &shared [one, two]\nother: *shared',
    'base: &base {owner: elsewhere, future: ordinary}\n<<: *base\nowner: fixture-user',
    'future: !!binary /2hhcm1sZXNzgA==\nfuture: ordinary',
    'future: !!omap\n  - item: first\n  - item: second',
    'future: !!pairs\n  - item: first\n  - item: second',
    'future: !!set\n  ? ordinary',
    '= : ordinary\nfuture: harmless',
])
def test_safe_yaml_occurrences_preserve_effective_authority_and_formats(inner):
    pytest.importorskip('yaml')
    text = '---\n' + inner + '\n---\nordinary'
    original = source_labels(ROOT, text, {})
    labels, occurrences = inspected(inner)
    assert labels == original
    assert occurrences


def test_yaml_cycle_refuses_without_expanding_aliases():
    pytest.importorskip('yaml')
    with pytest.raises(ValueError, match='cyclic alias'):
        inspected('future: &loop [*loop]\nfuture: ordinary')


def test_yaml_inspection_graph_preserves_shared_identity():
    pytest.importorskip('yaml')
    labels, occurrences = inspected('first: &shared [one, two]\nsecond: *shared')
    graph, = occurrences
    assert graph[0][1] is graph[1][1]
    assert labels['first'] is labels['second']


@pytest.mark.parametrize('fallback', [False, True], ids=['yaml', 'subset'])
def test_observation_is_private_and_authority_conflicts_keep_precedence(monkeypatch, fallback):
    if fallback:
        monkeypatch.setitem(sys.modules, 'yaml', None)
    else:
        pytest.importorskip('yaml')
    # Observation collects; it cannot introduce a secret refusal before the
    # unchanged effective authority owner has checked its fields.
    seen = []
    text = '---\nowner: elsewhere\nfuture: ordinary\n---\nbody'
    with pytest.raises(ValueError, match='conflicts with root authority'):
        source_labels(ROOT, text, {}, _observe=seen.append)
    assert seen
    assert source_labels(ROOT, 'ordinary', {'future': 'retained'}, _observe=seen.append) == {'future': 'retained'}


@pytest.mark.parametrize('inner,expected', [
    ('future: first\nfuture: second', [('future', 'first'), ('future', 'second')]),
    ('future:\n  - first\n  - second\nfuture: last', [('future', None), ('future', 'last')]),
    ('future: |\n  first\n  second\nfuture: last', [('future', 'first\nsecond\n'), ('future', 'last')]),
    ('future: >\n  first\n  second\nfuture: last', [('future', 'first second\n'), ('future', 'last')]),
    ('future: [one, two]\nfuture: last', [('future', ['one', 'two']), ('future', 'last')]),
    ('"future": "\\u0073afe"\nfuture: last', [('"future"', '\\u0073afe'), ('future', 'last')]),
    ('future:\n  nested: ignored\nfuture: last', [('future', None), ('future', 'last')]),
])
def test_subset_observes_existing_completed_values_without_changing_grammar(monkeypatch, inner, expected):
    monkeypatch.setitem(sys.modules, 'yaml', None)
    plain = source_labels(ROOT, '---\n' + inner + '\n---\nordinary', {})
    labels, occurrences = inspected(inner)
    assert labels == plain
    assert occurrences == [expected]


def test_subset_overwritten_label_context_is_inspected(monkeypatch):
    monkeypatch.setitem(sys.modules, 'yaml', None)
    with pytest.raises(ValueError, match=REFUSAL):
        inspected('access_token: [' + 'Ab1' * 9 + ']\naccess_token: ordinary')


def test_occurrence_construction_honors_shared_budget():
    calls = 0
    def exhausted():
        nonlocal calls
        calls += 1
        raise TimeoutError('shared budget exhausted')
    with pytest.raises(TimeoutError, match='shared budget exhausted'):
        source_labels(ROOT, '---\nfuture: ordinary\n---\nbody', {},
                      _observe=lambda value: None, _check_budget=exhausted)
    assert calls == 1


@pytest.mark.parametrize('inner', [
    'future: !!binary {=: ' + base64.b64encode(TOKEN.encode()).decode() + '}\nfuture: ordinary',
    'future: !!str {=: "' + ESCAPED + '"}\nfuture: ordinary',
    '"access_\\u0074oken": !!str {=: ' + 'Ab1' * 9 + '}\n"access_\\u0074oken": ordinary',
    '? !!str {=: "access_\\u0074oken"}\n: ' + 'Ab1' * 9 + '\n"access_\\u0074oken": ordinary',
])
def test_safe_scalar_constructors_keep_value_and_key_context_on_mapping_nodes(inner):
    pytest.importorskip('yaml')
    with pytest.raises(ValueError, match=REFUSAL):
        inspected(inner)


@pytest.mark.parametrize('tag', ['null', 'str'])
def test_safe_constructor_ignored_nodes_do_not_acquire_new_decoding_policy(tag):
    pytest.importorskip('yaml')
    inner = 'future: !!' + tag + ' {=: ordinary, ignored: !unknown ordinary}'
    text = '---\n' + inner + '\n---\nbody'
    original = source_labels(ROOT, text, {})
    labels, _ = inspected(inner)
    assert labels == original
