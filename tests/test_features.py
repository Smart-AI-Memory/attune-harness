"""Portable report boundary tests independent of optional libraries."""

import json
from pathlib import Path

import pytest

from attune_harness.features import (FeatureUnavailable, InputTooLarge, output_path, read_text,
                                     require_feature, write_report)


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
    with pytest.raises(InputTooLarge) as refused:
        read_text(source,64)
    message = str(refused.value)
    assert 'limit of 64 bytes' in message and 'it is 70 bytes' in message and str(source) in message
    assert 'never shortens' in message
    # Callers that catch ValueError keep working.
    assert isinstance(refused.value,ValueError)
    assert read_text(source,70) == 'x'*70


def test_oversize_plan_says_to_split_it_without_needing_attune_ai(tmp_path):
    from attune_harness.spec_bridge import legacy_plan
    plan = tmp_path/'plan.md'
    plan.write_text('<task id="1"><objective>'+'x'*65536+'</objective></task>\n',encoding='utf-8')
    with pytest.raises(ValueError) as refused:
        legacy_plan(plan)
    message = str(refused.value)
    assert 'limit of 65536 bytes' in message and 'Split the plan into smaller plan files' in message
    assert isinstance(refused.value.__cause__,InputTooLarge)


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
