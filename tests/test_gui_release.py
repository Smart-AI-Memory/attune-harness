"""1.3.0 release boundary, independent of GUI development-profile tests.
# qualify: platform
"""
import subprocess
import sys

import pytest
from attune_harness import gui
from attune_harness.features import FeatureUnavailable


@pytest.mark.parametrize('flags', [[], ['--task', '/missing', '--edit', '--allow-build-commands']])
def test_launcher_refuses_before_any_effect(monkeypatch, capsys, flags):
    def forbidden(*args, **kwargs):
        pytest.fail('GUI release refusal must precede owner/listener/browser effects')
    monkeypatch.setattr(gui.task_view, 'inspect_saved_tasks', forbidden)
    monkeypatch.setattr(gui.HTTPServer, '__init__', forbidden)
    monkeypatch.setattr(gui.webbrowser, 'open', forbidden)
    assert gui.main(flags) == 2
    assert 'unavailable in 1.3.0' in capsys.readouterr().err


@pytest.mark.parametrize('kwargs', [{}, {'edit': True}, {'edit': True, 'allow_build_commands': True}])
def test_imported_server_refuses_before_task_iteration_or_bind(monkeypatch, kwargs):
    class Untouched:
        def __iter__(self):
            pytest.fail('Release refusal must precede task iteration')
    def forbidden(*args, **kw):
        pytest.fail('Release refusal must precede listener/owner effects')
    monkeypatch.setattr(gui.HTTPServer, '__init__', forbidden)
    monkeypatch.setattr(gui.task_view, 'inspect_saved_tasks', forbidden)
    with pytest.raises(FeatureUnavailable, match='deferred to 1.4.0'):
        gui.CompanionServer(Untouched(), **kwargs)


def test_installed_module_refuses_without_creating_task_state(tmp_path):
    task = tmp_path / 'absent-task'
    result = subprocess.run([sys.executable, '-I', '-m', 'attune_harness.gui',
                             '--task', str(task), '--edit', '--allow-build-commands'],
                            cwd=tmp_path, text=True, capture_output=True, timeout=10)
    assert result.returncode == 2
    assert 'deferred to 1.4.0' in result.stderr
    assert not result.stdout
    assert not task.exists()
