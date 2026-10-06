"""Fixtures shared across the test modules."""

import itertools

import pytest


@pytest.fixture
def unmake_checkout():
    """Turn a checkout into a plain directory by renaming its ``.git`` beside it, never deleting it.

    Deleting ``.git`` races Git's background maintenance on macOS (a vanishing
    ``maintenance.lock``) and is refused on Windows, where Git's objects are
    read-only; both failed CI on #193 and #194.
    """
    def unmake(root):
        for n in itertools.count():
            moved = root.parent / f'{root.name}-moved-git-{n}'
            if not moved.exists():
                (root / '.git').rename(moved)
                return moved
    return unmake


@pytest.fixture
def gui_development_profile(monkeypatch):
    """Exercise retained 1.4.0 development code; never qualify release availability.

    Release-policy tests intentionally do not select this fixture. No shipped
    flag/environment can enable this test-only substitution.
    """
    from attune_harness import gui
    monkeypatch.setattr(gui, '_development_profile', lambda: True)
