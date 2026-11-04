"""Decoded shapes from the existing optional YAML parser; no grammar changes."""
# qualify: platform

import base64

import pytest

from attune_harness.memory_hydration_secrets import REFUSAL, check_secrets
from attune_harness.memory_reader import source_labels

ROOT = dict(tier='curated', owner='fixture-user', scope='demo', classification='internal')
TOKEN = 'sk-' + 'Ab1' * 7
ESCAPED = '\\u0073' + TOKEN[1:]


@pytest.mark.parametrize('inner', [
    'future: !!set\n  ? "' + ESCAPED + '"',
    'future: !!omap\n  - item: "' + ESCAPED + '"',
    'future: !!pairs\n  - item: "' + ESCAPED + '"',
    'future: !!binary ' + base64.b64encode(TOKEN.encode()).decode(),
    'future: !!binary ' + base64.b64encode(b'\xff' + TOKEN.encode() + b'\x80').decode(),
    'future: !!omap\n  - "access_\\u0074oken": "' + 'Ab1' * 9 + '"',
    'future: !!pairs\n  - "access_\\u0074oken": "' + 'Ab1' * 9 + '"',
])
def test_supported_decoded_shapes_cannot_hide_blocking_secrets(inner):
    pytest.importorskip('yaml')
    raw = '---\n' + inner + '\n---\nordinary'
    check_secrets(raw)
    with pytest.raises(ValueError, match=REFUSAL):
        check_secrets(raw, source_labels(ROOT, raw, {}))


@pytest.mark.parametrize('inner', [
    'future: !!set\n  ? harmless', 'future: !!omap\n  - item: harmless',
    'future: !!pairs\n  - item: harmless',
    'future: !!binary ' + base64.b64encode(b'harmless').decode(),
    'future: !!binary ' + base64.b64encode(b'\xffharmless\x80').decode(),
])
def test_safe_existing_decoded_shapes_keep_their_accepted_format(inner):
    pytest.importorskip('yaml')
    raw = '---\n' + inner + '\n---\nordinary'
    check_secrets(raw, source_labels(ROOT, raw, {}))


def test_active_path_cycle_detection_includes_tuples_but_not_shared_aliases():
    sequence = []
    sequence.append((sequence,))
    with pytest.raises(ValueError, match='cyclic alias'):
        check_secrets('', sequence)
    shared = ('ordinary',)
    check_secrets('', [shared, shared, {'ordinary', 'words'}, frozenset({'ordinary'})])


@pytest.mark.parametrize('kind', ['mapping', '!!omap', '!!pairs'])
@pytest.mark.parametrize('binary_value', [False, True], ids=['text-value', 'binary-value'])
def test_binary_keys_and_values_use_the_same_decoded_label_context(kind, binary_value):
    pytest.importorskip('yaml')
    value = 'Ab1' * 9
    if binary_value:
        value = '!!binary ' + base64.b64encode(value.encode()).decode()
    encoded_key = base64.b64encode(b'access_token').decode()
    inner = ('future:\n  ? !!binary ' + encoded_key + '\n  : ' + value if kind == 'mapping'
             else 'future: ' + kind + '\n  - ? !!binary ' + encoded_key + '\n    : ' + value)
    raw = '---\n' + inner + '\n---\nordinary'
    check_secrets(raw)
    with pytest.raises(ValueError, match=REFUSAL):
        check_secrets(raw, source_labels(ROOT, raw, {}))
