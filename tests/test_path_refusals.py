"""Review intake path refusals say how each path was read (first-run journey T4, R3).

Paths resolve exactly as before: ``--document``, ``--context`` and
``--corpus`` against ``--project``, ``--config`` against the working
directory. Only the words of a refusal change.
"""
# qualify: platform

import json
from pathlib import Path

import pytest

from attune_harness.cli import main
from attune_harness.task_contract import RESOLUTION_RULE

REGISTRY = Path(__file__).resolve().parents[1] / 'examples' / 'review' / 'participants.json'


@pytest.fixture
def project(tmp_path):
    root = tmp_path.resolve() / 'project'
    (root / 'docs').mkdir(parents=True)
    (root / 'docs' / 'guide.md').write_text('# Guide\n', encoding='utf-8')
    (root / 'participants.json').write_text(REGISTRY.read_text(encoding='utf-8'), encoding='utf-8')
    return root


def refusal(capsys, project, **answers):
    argv = ['review', '--goal', 'Check the guide', '--project', str(project),
            '--config', str(project / 'participants.json'), '--task-dir', str(project.parent / 'task'),
            '--intake-only']
    for name, value in answers.items():
        argv += [f'--{name}', str(value)]
    code = main(argv)
    envelope = json.loads(capsys.readouterr().out)
    assert code == 2 and envelope['status'] == 'failed', envelope
    return envelope['error']['detail']


def test_a_missing_document_names_its_base_and_resolved_path(project, capsys):
    detail = refusal(capsys, project, document='guide.md')
    assert detail == (f"document is not a regular file: document 'guide.md' resolves against --project "
                      f"{project} to {project / 'guide.md'}. {RESOLUTION_RULE}")


def test_an_absolute_path_says_so(project, capsys):
    absent = project / 'absent.md'
    detail = refusal(capsys, project, document=absent)
    assert f"document {str(absent)!r} is absolute to {absent}" in detail


def test_a_path_outside_the_project_keeps_its_old_words_and_adds_the_resolution(project, capsys):
    detail = refusal(capsys, project, document='../elsewhere.md')
    assert detail.startswith('document must be inside the project and outside task state: ')
    assert f"resolves against --project {project} to {project.parent / 'elsewhere.md'}" in detail


def test_a_missing_corpus_names_its_resolution(project, capsys):
    detail = refusal(capsys, project, document='docs/guide.md', corpus='missing')
    assert detail.startswith('Corpus must be an existing directory: ')
    assert str(project / 'missing') in detail and RESOLUTION_RULE in detail
