"""``scripts/review_prep.sh``: the archive a different-model reviewer works from.

Besides the tree, the diff and the mutation table, it leaves ``report.md`` for
the reviewer to write and ``mutate.sh``, which runs one mutant from inside its
own full copy of the tree. A mutant reached only through ``PYTHONPATH`` is
never imported when pyproject sets pytest's ``pythonpath``, which made eleven
mutants look like survivors on 2026-09-30 (retro items 7 and 9).
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(os.name != 'posix' or shutil.which('bash') is None,
                                reason='review_prep.sh is a bash script')


def git(repo, *args):
    subprocess.run(['git', '-C', str(repo), '-c', 'commit.gpgsign=false', '-c', 'user.name=T',
                    '-c', 'user.email=t@example.invalid', *args], check=True, capture_output=True)


@pytest.fixture
def review(tmp_path):
    """A repository whose test pins ``add``; the reviewed branch changes the source."""
    repo = tmp_path / 'repo'
    (repo / 'src' / 'pkg').mkdir(parents=True)
    (repo / 'tests').mkdir()
    (repo / 'pyproject.toml').write_text('[tool.pytest.ini_options]\npythonpath = ["src"]\n', encoding='utf-8')
    (repo / 'src' / 'pkg' / '__init__.py').write_text('', encoding='utf-8')
    (repo / 'src' / 'pkg' / 'calc.py').write_text('def add(a, b):\n    return a + b\n', encoding='utf-8')
    (repo / 'tests' / 'test_calc.py').write_text('from pkg.calc import add\n\n\ndef test_add():\n'
                                                 '    assert add(2, 2) == 4\n', encoding='utf-8')
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True, capture_output=True)
    git(repo, 'add', '.')
    git(repo, 'commit', '-qm', 'base')
    (repo / 'src' / 'pkg' / 'calc.py').write_text('def add(a, b):\n    return b + a\n', encoding='utf-8')
    git(repo, 'commit', '-qam', 'change')
    shutil.copy(ROOT / 'scripts' / 'review_prep.sh', repo / 'review_prep.sh')
    out = tmp_path / 'out'
    out.mkdir()
    result = subprocess.run(['bash', str(repo / 'review_prep.sh'), 'HEAD', 'HEAD~1'], cwd=repo, capture_output=True,
                            text=True, env={**os.environ, 'REVIEW_PREP_DIR': str(out)}, check=True)
    (made,) = out.iterdir()
    return made, result.stdout


def mutate(made, *args):
    return subprocess.run([str(made / 'mutate.sh'), *args], capture_output=True, text=True,
                          env={**os.environ, 'PYTHON': sys.executable})


def test_the_archive_has_a_report_file_and_a_mutation_runner(review):
    made, stdout = review
    assert (made / 'report.md').is_file() and (made / 'report.md').read_text() == ''
    assert os.access(made / 'mutate.sh', os.X_OK)
    assert f'report:    {made}/report.md' in stdout and 'mutate.sh' in stdout


def test_a_mutant_is_run_from_inside_its_own_copy_and_caught(review):
    made, _ = review
    result = mutate(made, 'minus', 'src/pkg/calc.py', 'return b + a', 'return b - a')
    assert result.returncode == 0 and result.stdout.startswith('minus CAUGHT'), result.stdout + result.stderr
    assert 'return b - a' in (made / 'mutants' / 'minus' / 'src' / 'pkg' / 'calc.py').read_text()
    assert 'return b + a' in (made / 'tree' / 'src' / 'pkg' / 'calc.py').read_text(), 'the tree is never mutated'


def test_an_equivalent_mutant_survives(review):
    made, _ = review
    result = mutate(made, 'swap', 'src/pkg/calc.py', 'return b + a', 'return a + b')
    assert result.stdout.startswith('swap SURVIVED'), result.stdout + result.stderr


def test_a_replacement_that_does_not_match_exactly_once_is_refused(review):
    made, _ = review
    result = mutate(made, 'absent', 'src/pkg/calc.py', 'return 0', 'return 1')
    assert result.returncode == 2 and 'occurs 0 times' in result.stderr, result.stderr
