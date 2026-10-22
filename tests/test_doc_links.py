"""Documentation gates reject broken links without rewriting historical evidence."""

# qualify: platform

import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'check_doc_links.py'
spec = importlib.util.spec_from_file_location('check_doc_links', SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


@pytest.fixture
def repository(tmp_path):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)

    def write(name, text, *, tracked=True):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        if tracked:
            subprocess.run(['git', '-C', str(tmp_path), 'add', '--', name], check=True)
        return path

    write('docs/README.md', '[Guide](guide.md)\n')
    write('docs/guide.md', '# Guide\n')
    write('src/example.py', 'first = 1\nsecond = 2\nthird = 3\n')
    return tmp_path, write


@pytest.mark.parametrize('target', [
    '../src/example.py', '../src/example.py#L1', '../src/example.py#L1-L3',
    '/src/example.py#L3', './guide.md#guide', '#guide', '#',
    'guide.md?plain=1#L1',
])
def test_valid_local_destinations(repository, target):
    root, write = repository
    write('docs/guide.md', '# Guide\n[Go](' + target + ')\n')
    assert checker.check(root) == []


@pytest.mark.parametrize('target,problem', [
    ('../src/missing.py', 'dead link'),
    ('missing.md', 'dead link'),
    ('#missing', 'unknown heading'),
    ('guide.md#missing', 'unknown heading'),
    ('../src/example.py#L4', 'invalid source line'),
    ('../src/example.py#L3-L1', 'invalid source line'),
    ('../src/example.py#L0', 'invalid source line'),
    ('../src/example.py#L1-L4', 'invalid source line'),
    ('../src/example.py#function-name', 'invalid source line'),
    ('../src/example.py:1', 'dead link'),
    ('missing.py:1', 'dead link'),
    ('guide.md?plain=1#L900', 'invalid source line'),
])
def test_broken_targets_and_fragments_fail(repository, target, problem):
    root, write = repository
    write('docs/guide.md', '# Guide\n[Broken](' + target + ')\n')
    findings = checker.check(root)
    assert len(findings) == 1
    assert findings[0].startswith('docs/guide.md:2: ')
    assert problem in findings[0]


def test_untracked_source_does_not_publish_a_working_link(repository):
    root, write = repository
    write('src/local.py', 'value = 1\n', tracked=False)
    write('docs/guide.md', '# Guide\n[Local](../src/local.py)\n')
    assert 'exists on disk but is untracked' in checker.check(root)[0]


def test_heading_markup_unicode_duplicates_setext_and_html_anchors(repository):
    root, write = repository
    write('docs/guide.md', '''# Guide
## **Use** `plan` & Café!
## Repeated
## Repeated-1
## Repeated
Another section
===============
<a id="Legacy-ID"></a><a name="named-anchor"></a>
[Formatted](#use-plan--caf%C3%A9)
[First](#repeated)
[Collision](#repeated-1)
[Duplicate](#repeated-2)
[Setext](#another-section)
[HTML](#Legacy-ID)
[Named](#named-anchor)
''')
    assert checker.check(root) == []


def test_code_and_comments_supply_neither_links_nor_anchors(repository):
    root, write = repository
    write('docs/guide.md', '''# Guide
```markdown
## Fenced
[Ignored](absent.md)
<a id="fenced-id"></a>
```
~~~markdown
[Ignored](absent.md)
~~~
    [Ignored](absent.md)
<!-- [Ignored](absent.md)
## Comment
-->
`[Ignored](absent.md)` and `<a id="inline-id"></a>`.
[Broken](#fenced)
[Broken](#fenced-id)
[Broken](#comment)
[Broken](#inline-id)
''')
    findings = checker.check(root)
    assert len(findings) == 4
    assert all('unknown heading' in item for item in findings)


def test_reference_links_and_inline_title_are_checked(repository):
    root, write = repository
    write('docs/guide.md', '''# Guide
[Source][source] and [source][] and [source].
[Heading](#guide "A title")
[Bad][broken]
[source]: ../src/example.py#L2
[broken]: ../src/absent.py
''')
    findings = checker.check(root)
    assert len(findings) == 1
    assert findings[0].startswith('docs/guide.md:4: dead link')


def test_nested_label_is_checked_but_escaped_markup_is_not_a_link(repository):
    root, write = repository
    write('docs/guide.md', '# Guide\n[See [source]](../src/missing.py)\n'
          r'\[Literal](absent.md)' + '\n')
    findings = checker.check(root)
    assert findings == ['docs/guide.md:2: dead link to src/missing.py']


def test_first_reference_definition_wins(repository):
    root, write = repository
    write('docs/guide.md', '# Guide\n[Label][REF]\n[ref]: #guide\n[ref]: absent.md\n')
    assert checker.check(root) == []


def test_quoted_and_list_fences_do_not_hide_later_real_links(repository):
    root, write = repository
    write('docs/guide.md', '''# Guide
> ```markdown
> [Example](absent.md)
> ## Fake
> ```
- ```markdown
  [Example](absent.md)
  ```
[Real](#fake)
''')
    assert checker.check(root) == ['docs/guide.md:9: unknown heading or anchor: docs/guide.md#fake']


@pytest.mark.parametrize('example', [
    '```html\n<!-- literal comment\n```\n',
    '`<!-- literal comment`\n',
    '<!-- actual comment\n```\n-->\n',
    '> ```html\n> <!-- literal comment\n> ```\n',
])
def test_comments_and_code_cannot_hide_the_following_link(repository, example):
    root, write = repository
    write('docs/guide.md', '# Guide\n' + example + '[Broken](../src/missing.py)\n')
    findings = checker.check(root)
    assert len(findings) == 1 and 'dead link to src/missing.py' in findings[0]


def test_encoded_and_escaped_source_paths(repository):
    root, write = repository
    write('src/space name.py', 'value = 1\n')
    write('src/paren(name).py', 'value = 1\n')
    write('docs/guide.md', '# Guide\n'
          '[Encoded](../src/space%20name.py#L1)\n'
          '[Angle](<../src/space name.py#L1>)\n'
          '[Balanced](../src/paren(name).py#L1)\n'
          r'[Escaped](../src/paren\(name\).py#L1)' + '\n')
    assert checker.check(root) == []


def test_external_urls_and_non_source_artifacts_remain_outside_scope(repository):
    root, write = repository
    write('docs/guide.md', '''# Guide
[External](https://example.invalid/missing.py#L900)
[Protocol relative](//example.invalid/missing.md)
[Mail](mailto:someone@example.invalid)
[Receipt](receipts/historical.json)
''')
    assert checker.check(root) == []


def test_historical_exception_is_exact_and_cannot_hide_a_new_bad_link(repository):
    root, write = repository
    write('docs/guide.md', '# Guide\n[Historical](../src/old.py)\n[New](#bad)\n')
    write('scripts/' + checker.HISTORICAL_NAME, 'docs/guide.md\t../src/old.py\n')
    findings = checker.check(root)
    assert len(findings) == 1 and 'unknown heading' in findings[0]
    write('docs/README.md', '[Guide](guide.md)\n[New](../src/old.py)\n')
    assert len(checker.check(root)) == 2


def test_repeating_a_historical_bad_link_is_a_new_failure(repository):
    root, write = repository
    write('docs/guide.md', '# Guide\n[Old](../src/old.py)\n[New](../src/old.py)\n')
    write('scripts/' + checker.HISTORICAL_NAME, 'docs/guide.md\t../src/old.py\n')
    assert checker.check(root) == ['docs/guide.md:3: dead link to src/old.py']


def test_source_line_bounds_count_newlines_not_other_control_characters(repository):
    root, write = repository
    write('src/example.py', '# First\vstill the first line\n')
    write('docs/guide.md', '# Guide\n[Not a second line](../src/example.py#L2)\n')
    assert 'invalid source line fragment' in checker.check(root)[0]


@pytest.mark.parametrize('rows', ['invalid\n', 'docs/guide.md\t#bad\ndocs/guide.md\t#bad\n'])
def test_malformed_and_duplicate_exception_records_fail(repository, rows):
    root, write = repository
    write('scripts/' + checker.HISTORICAL_NAME, rows)
    assert any(checker.HISTORICAL_NAME in item for item in checker.check(root))


@pytest.mark.parametrize('resolved', [True, False])
def test_resolved_or_unused_historical_exception_must_be_removed(repository, resolved):
    root, write = repository
    write('scripts/' + checker.HISTORICAL_NAME, 'docs/guide.md\t../src/old.py\n')
    if resolved:
        write('src/old.py', 'value = 1\n')
        write('docs/guide.md', '# Guide\n[Now valid](../src/old.py)\n')
    assert 'exception is resolved or unused' in checker.check(root)[0]


def test_existing_shrinking_known_dead_list_and_index_gate_remain(repository):
    root, write = repository
    write('scripts/' + checker.KNOWN_NAME, 'docs/old.md\n')
    write('docs/guide.md', '# Guide\n[Historical](old.md)\n')
    assert checker.check(root) == []
    write('docs/old.md', '# Old\n')
    findings = checker.check(root)
    assert any('exists now; remove' in item for item in findings)
    assert any('no row for docs/old.md' in item for item in findings)


def test_readme_pypi_policy_and_actual_command_exit_status(repository):
    root, write = repository
    write('README.md', '# Main\n[Relative](docs/guide.md)\n')
    result = subprocess.run([sys.executable, '-I', str(SCRIPT)], cwd=root,
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 1
    assert 'link will not resolve on PyPI' in result.stdout
    write('README.md', '# Main\n[Local](#main)\n')
    result = subprocess.run([sys.executable, '-I', str(SCRIPT)], cwd=root,
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
