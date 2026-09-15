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
