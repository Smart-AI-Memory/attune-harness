"""Portable report boundary tests independent of optional libraries."""

import json
from pathlib import Path

import pytest

from attune_harness.features import FeatureUnavailable, output_path, read_text, require_feature, write_report


def test_input_bounds_and_encoding(tmp_path):
    source = tmp_path/'input.md'
    source.write_text('é',encoding='utf-8')
    assert read_text(source,2) == 'é'
    with pytest.raises(ValueError,match='exceeds'):
        read_text(source,1)
    source.write_bytes(b'\xff')
    with pytest.raises(UnicodeDecodeError):
        read_text(source)
    with pytest.raises(ValueError,match='regular'):
        read_text(tmp_path)


def test_oversize_input_is_refused_whole_and_says_its_size_and_limit(tmp_path):
    source = tmp_path/'input.md'
    source.write_text('x'*70,encoding='utf-8')
    with pytest.raises(ValueError) as refused:
        read_text(source,64)
    message = str(refused.value)
    assert 'limit of 64 bytes' in message and 'it is 70 bytes' in message and str(source) in message
    assert 'never shortens' in message
    # The error envelopes print the class name; it must stay ValueError.
    assert type(refused.value) is ValueError
    assert read_text(source,70) == 'x'*70


def test_reported_size_is_never_smaller_than_what_was_read(tmp_path,monkeypatch):
    import os
    source = tmp_path/'input.md'
    source.write_text('x'*70,encoding='utf-8')
    shrunk = os.stat_result((0,)*6+(3,)+(0,)*3)
    monkeypatch.setattr('attune_harness.features.os.fstat',lambda descriptor: shrunk)
    with pytest.raises(ValueError,match='it is 65 bytes'):
        read_text(source,64)


def test_oversize_plan_says_to_split_it_without_needing_attune_ai(tmp_path):
    from attune_harness.spec_legacy import legacy_plan
    plan = tmp_path/'plan.md'
    plan.write_text('<task id="1"><objective>'+'x'*65536+'</objective></task>\n',encoding='utf-8')
    with pytest.raises(ValueError) as refused:
        legacy_plan(plan)
    message = str(refused.value)
    assert 'limit of 65536 bytes' in message
    assert 'Split the plan into smaller plan files and import each one as its own task' in message
    with pytest.raises(ValueError,match='regular') as other:
        legacy_plan(tmp_path)
    assert 'Split' not in str(other.value)


def test_output_refuses_symlink_metadata_and_bad_paths(tmp_path):
    protected = tmp_path/'input.json'
    protected.write_text('{}',encoding='utf-8')
    link = tmp_path/'link.json'
    link.symlink_to(protected)
    for path in (link, tmp_path/'.git'/'config.json', tmp_path/'out.md', tmp_path/'missing'/'out.json', protected):
        with pytest.raises(ValueError):
            output_path(path,(protected,))
    assert protected.read_text() == '{}'


def test_atomic_write_cleanup_on_failure(tmp_path,monkeypatch):
    target = tmp_path/'report.json'
    target.write_text('{"old":true}',encoding='utf-8')
    monkeypatch.setattr('attune_harness.features.os.replace',lambda *_: (_ for _ in ()).throw(OSError('cannot replace')))
    with pytest.raises(OSError):
        write_report(target,{'new':True})
    assert json.loads(target.read_text()) == {'old':True}
    assert list(tmp_path.iterdir()) == [target]


def test_broken_dependency_import_is_unavailable(monkeypatch):
    monkeypatch.setattr('attune_harness.features.version',lambda _: '1.0')
    monkeypatch.setattr('attune_harness.features.importlib.import_module',lambda _: (_ for _ in ()).throw(ImportError('broken dependency')))
    with pytest.raises(FeatureUnavailable,match='cannot load'):
        require_feature('example','example','1.0','example')


# --- a co-installed attune-ai and the MCP SDK line ------------------------------


def _neighbour(monkeypatch, *, installed, declared):
    import attune_harness.features as features

    def version(name):
        if name == 'mcp' and installed is not None:
            return installed
        raise features.PackageNotFoundError(name)

    def requires(name):
        if declared is None:
            raise features.PackageNotFoundError(name)
        return list(declared)

    monkeypatch.setattr(features, 'version', version)
    monkeypatch.setattr(features, 'requires', requires)
    return features


def test_neighbor_conflict_names_the_split_when_attune_ai_pins_another_mcp_line(monkeypatch):
    features = _neighbour(monkeypatch, installed='2.2.0', declared=['redis>=5.0.0,<9.0.0', 'mcp==1.29.1'])
    notice = features.neighbor_conflict()
    assert notice.startswith('attune-ai is installed here and requires mcp==1.29.1, but attune-harness installed mcp 2.2.0')
    assert 'pipx install attune-harness' in notice


@pytest.mark.parametrize('installed,declared', [
    ('2.2.0', None),                                    # no attune-ai
    ('2.2.0', ['redis>=5.0.0,<9.0.0']),                 # attune-ai without an mcp requirement
    ('1.29.1', ['mcp==1.29.1']),                        # the requirement is met
    ('2.2.0', ['mcp>=1.0,<3']),                         # a range that admits both lines
    (None, ['mcp==1.29.1']),                            # this install has no mcp at all
    ('2.2.0', ['mcp~=1.29']),                           # an operator the check does not judge
    ('2.2.0', ['mcp==1.29.1; extra == "server"']),      # only under an extra
])
def test_neighbor_conflict_is_silent_unless_certain(monkeypatch, installed, declared):
    features = _neighbour(monkeypatch, installed=installed, declared=declared)
    assert features.neighbor_conflict() is None


def test_neighbor_conflict_reads_the_real_metadata_shape():
    """Against whatever this interpreter holds: the result is a notice or None, never an error."""
    import attune_harness.features as features
    result = features.neighbor_conflict()
    assert result is None or 'cannot share an environment' in result
