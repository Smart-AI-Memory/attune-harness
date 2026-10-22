"""Completed assessment status exposes recorded evidence without dispatch or writes."""
# qualify: platform

from html.parser import HTMLParser
import json
import os
import subprocess
import sys

import pytest
from markdown_it import MarkdownIt

from attune_harness.cli import main
from attune_harness.human_output import document, markdown
from attune_harness.task_contract import accept_task, create_task
from attune_harness.task_policies import execute_task, inspect_task
from test_review import case, scripted
from test_task_repair_effects import effect_case
from test_task_contract import response


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tags, self.text, self.code, self.stack = [], [], [], []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag == 'br':
            self.text.append('\n')
        if tag not in ('br', 'meta', 'img', 'hr', 'input', 'link'):
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag == 'p':
            self.text.append('\n')
        if tag in self.stack:
            self.stack = self.stack[:len(self.stack) - 1 - self.stack[::-1].index(tag)]

    def handle_data(self, data):
        self.text.append(data)
        if 'code' in self.stack:
            self.code.append(data)


def complete(case, *, goal='Check the guide', criteria='Preserve uncertainty', plan='independent-review', narrative=None):
    create_task(case[0].parent, case[1], directory=case[2], goal=goal, plan=plan,
                answers={'criteria': criteria, 'query': 'quartz', 'document': 'project/guide.md',
                         'context': 'context.json', 'corpus': 'project', 'assessor': 'alpha',
                         **({'reviewer': 'beta'} if plan == 'independent-review' else {})})
    accept_task(case[2], response(case[2]))
    return execute_task(case[2], exchange_factory=scripted(narrative or (lambda packet: {
        'kind': 'final', 'text': 'Accept the bounded scope' if packet['turn']['role'] == 'assessor'
        else 'Reject the unsupported conclusion'})))


def status(capsys, directory, format):
    assert main(['status', str(directory), '--format', format]) == 0
    return capsys.readouterr().out


def page(text, format):
    return Page(MarkdownIt().render(text) if format == 'markdown' else text)


@pytest.mark.parametrize('format', ['markdown', 'html'])
@pytest.mark.parametrize(('content', 'verdict'), [
    ('[Quartz policy](reference.md)', 'verified'),
    ('[Quartz policy](missing.md)', 'refuted'),
    ('Quartz prose with no supported claims', 'unknown'),
])
def test_completed_assessment_exposes_actual_verdicts_sources_and_attribution(case, capsys, format, content, verdict):
    (case[0].parent / 'project/guide.md').write_text(content, encoding='utf-8')
    task = complete(case)
    output = status(capsys, case[2], format)
    visible = ''.join(page(output, format).text)
    assert 'Assessment evidence' in visible
    assert 'Check the guide' in visible and 'Preserve uncertainty' in visible
    assert 'Document check verdict' in visible and verdict in visible
    assert 'Semantic acceptance' in visible and 'Unverified' in visible
    assert 'alpha' in visible and 'beta' in visible
    assert 'Accept the bounded scope' in visible and 'Reject the unsupported conclusion' in visible
    assert '/execution/participants/assessor/text' in visible
    assert '/execution/participants/reviewer/text' in visible
    assert '/request/evidence/document' in visible
    assert task['request']['evidence']['document']['sha256'] in visible
    assert task['request']['evidence']['context']['path'] in visible
    for index, claim in enumerate(task['execution']['verification']['result']['claims']):
        assert claim['status'] in visible
        assert claim['evidence'] in ''.join(page(output, format).code)
        assert claim['location'] in ''.join(page(output, format).code)
        assert '/execution/verification/result/claims/' + str(index) in visible
    for index, source in enumerate(task['execution']['initial_retrieval']['sources']):
        assert source['path'] in visible and source['sha256'] in visible
        assert '/execution/initial_retrieval/sources/' + str(index) in visible


@pytest.mark.parametrize('format', ['markdown', 'html'])
def test_literal_prose_preserves_wording_lines_and_cannot_inject_markup(case, capsys, format):
    goal = 'CHECK <img src=x onerror=alert(1)> [Run](javascript:alert(1))\n    Keep THIS wording\n\nSecond paragraph'
    criteria = 'KEEP `literal` *text* & <tags>\n# This is an answer'
    narrative = '<script>alert("owned")</script>\n[click](https://untrusted.invalid)\n```\nFinal LINE'
    complete(case, goal=goal, criteria=criteria, narrative=lambda _: {'kind': 'final', 'text': narrative})
    output = status(capsys, case[2], format)
    parsed = page(output, format)
    visible = ''.join(parsed.text)
    for line in [*goal.split('\n'), *criteria.split('\n'), *narrative.split('\n')]:
        assert line in visible
    assert 'wording\n\nSecond paragraph' in visible
    assert '# This is an answer' in visible
    assert not any(tag in ('img', 'a') or any(name.startswith('on') for name in attrs)
                   for tag, attrs in parsed.tags)
    if format == 'markdown':
        assert not any(tag == 'script' for tag, _ in parsed.tags)
    else:
        assert '<script>alert' not in output
    assert 'CHECK' not in ''.join(parsed.code)
    assert 'KEEP `literal`' not in ''.join(parsed.code)
    assert 'Final LINE' not in ''.join(parsed.code)


@pytest.mark.parametrize('format', ['markdown', 'html'])
def test_readable_inspection_keeps_json_bytes_records_and_execution_unchanged(case, capsys, monkeypatch, format):
    task = complete(case)
    expected = json.dumps(task, ensure_ascii=False, allow_nan=False, indent=2) + '\n'
    assert main(['status', str(case[2])]) == 0
    assert capsys.readouterr().out == expected
    before = {p: p.read_bytes() for p in case[2].rglob('*') if p.is_file()}
    from attune_harness import task_policies, review_participants, features
    def poison(*args, **kwargs):
        pytest.fail('Status attempted dispatch, verification or dependency loading')
    monkeypatch.setattr(task_policies, 'execute_task', poison)
    monkeypatch.setattr(review_participants, 'ReviewExchange', poison)
    monkeypatch.setattr(features, 'require_feature', poison)
    status(capsys, case[2], format)
    assert main(['status', str(case[2])]) == 0
    assert capsys.readouterr().out == expected
    assert {p: p.read_bytes() for p in case[2].rglob('*') if p.is_file()} == before


@pytest.mark.parametrize('format', ['markdown', 'html'])
def test_saved_evidence_is_inspectable_after_sources_change_without_claiming_freshness(case, capsys, format):
    task = complete(case)
    (case[0].parent / 'project/reference.md').unlink()
    output = status(capsys, case[2], format)
    visible = ''.join(page(output, format).text)
    assert task['request']['evidence']['document']['sha256'] in visible
    assert 'does not rerun checks or establish current source freshness' in visible
    assert 'Freshness checked' not in visible


@pytest.mark.parametrize('format', ['markdown', 'html'])
def test_no_retrieval_hits_remains_explicit(case, capsys, format):
    (case[0].parent / 'project/guide.md').write_text('No matching words here', encoding='utf-8')
    (case[0].parent / 'project/reference.md').write_text('No matching words here', encoding='utf-8')
    task = complete(case)
    assert task['execution']['initial_retrieval']['sources'] == []
    visible = ''.join(page(status(capsys, case[2], format), format).text)
    assert 'no_results' in visible
    assert 'Retrieved source 1' not in visible


@pytest.mark.parametrize('format', ['markdown', 'html'])
def test_structured_participant_results_are_literal_technical_input(case, capsys, format):
    from test_assessment_repair_handoff import complete_assessment
    task = complete_assessment(case)
    parsed = page(status(capsys, case[2], format), format)
    assert task['execution']['participants']['assessor']['text'] in ''.join(parsed.code)
    assert 'Unverified' in ''.join(parsed.text)
    assert 'not host-verified conclusions or execution permission' in ''.join(parsed.text)


@pytest.mark.parametrize('format', ['markdown', 'html'])
@pytest.mark.parametrize('state', ['draft', 'accepted', 'paused', 'failed'])
def test_incomplete_assessments_keep_existing_generic_presentation(case, capsys, format, state):
    from test_task_contract import draft
    draft(case)
    if state != 'draft':
        accept_task(case[2], response(case[2]))
    if state == 'paused':
        execute_task(case[2], max_operations=1)
    elif state == 'failed':
        execute_task(case[2], exchange_factory=scripted({'kind': 'tool', 'name': 'verify', 'arguments': {}}))
    task = inspect_task(case[2])
    assert task['status'] == state
    expected = markdown(task) if format == 'markdown' else document(task)
    assert status(capsys, case[2], format) == expected


@pytest.mark.parametrize('format', ['markdown', 'html'])
def test_legacy_review_keeps_existing_generic_presentation(case, capsys, format):
    from attune_harness.review import review
    task = review(*case)
    expected = markdown(task) if format == 'markdown' else document(task)
    assert status(capsys, case[2], format) == expected


def test_status_uses_the_actual_cli_from_outside_the_checkout(case):
    task = complete(case, plan='solo')
    before = (case[2] / 'record.json').read_bytes()
    result = subprocess.run([sys.executable, '-I', '-B', '-m', 'attune_harness', 'status', str(case[2]),
                             '--format', 'markdown'], cwd=case[0].parent,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'Assessment evidence' in result.stdout
    assert task['request']['task_id'] in result.stdout
    assert (case[2] / 'record.json').read_bytes() == before


@pytest.mark.parametrize('format', ['json', 'markdown', 'html'])
def test_invalid_record_preserves_existing_refusal(case, capsys, format):
    complete(case)
    path = case[2] / 'record.json'
    task = json.loads(path.read_text(encoding='utf-8'))
    task['status'] = 'failed'
    path.write_text(json.dumps(task), encoding='utf-8')
    before = path.read_bytes()
    assert main(['status', str(case[2]), '--format', format]) == 2
    failure = json.loads(capsys.readouterr().out)
    assert failure['error']['detail'] == 'Run checkpoint digest does not match its contents'
    assert path.read_bytes() == before


@pytest.mark.skipif(os.name != 'posix', reason='Existing repair fixture uses the POSIX handle profile')
@pytest.mark.parametrize('format', ['markdown', 'html'])
def test_completed_repairs_keep_existing_generic_presentation(effect_case, capsys, format):
    from test_task_repair import prepare, proposal
    directory = prepare(effect_case)
    task = execute_task(directory, exchange_factory=scripted(proposal))
    assert task['status'] == 'completed'
    expected = markdown(task) if format == 'markdown' else document(task)
    assert status(capsys, directory, format) == expected
