"""Readable output on request: ``--format markdown`` on the task verbs (first-run journey R5).

JSON stays the default and the contract: every verb still builds its one
envelope, and ``--format markdown`` only changes how that envelope is printed.
It prints the Markdown the envelope already carries (``presentation.markdown``
or ``markdown``), or, where a state has none, its status, summary, error and
next action as text, then where the record is saved and what to do next. The
exit code is always the one the JSON path returns.
"""

import contextlib
import html
import io
import json
import sys

VERBS = ('plan', 'build', 'review', 'fix', 'test', 'resume')


def add_format(parser):
    parser.add_argument('--format', choices=('json', 'markdown'), default='json',
                        help='Output format; markdown prints the envelope for people, with the same exit code')


def _literal(value):
    return str(value).replace('\n', ' ').strip()


def markdown(envelope: dict) -> str:
    """One envelope as Markdown. It never prints nothing, and it never invents an outcome."""
    presentation = envelope.get('presentation') if isinstance(envelope.get('presentation'), dict) else {}
    text = presentation.get('markdown') or envelope.get('markdown')
    lines = [text.rstrip()] if isinstance(text, str) and text.strip() else []
    if not lines:
        title = envelope.get('task_profile') or envelope.get('operation') or 'attune-harness'
        lines = [f'## {_literal(title)}', '', f'**Status:** {_literal(envelope.get("status", "unknown"))}']
        if envelope.get('summary'):
            lines += ['', _literal(envelope['summary'])]
        result = presentation.get('current_result') or envelope.get('current_result')
        if isinstance(result, dict) and result.get('outcome'):
            lines += ['', f'**Outcome:** {_literal(result["outcome"])}: {_literal(result.get("detail", ""))}']
    error = envelope.get('error')
    if isinstance(error, dict) and error.get('detail'):
        lines += ['', f'**Refused ({_literal(error.get("type", "error"))}):** {_literal(error["detail"])}']
    record = envelope.get('record_path') or envelope.get('task_directory')
    if record:
        lines += ['', f'**Saved record:** {_literal(record)}']
    if envelope.get('next_action'):
        lines += ['', f'**Next:** {_literal(envelope["next_action"])}']
    return '\n'.join(lines) + '\n'


def document(envelope: dict) -> str:
    """The same text as a self-contained HTML page, for ``status --format html`` on any task."""
    from .task_view import _document
    return _document(f'<pre>{html.escape(markdown(envelope))}</pre>', title='Task status')


def run(dispatch) -> int:
    """Run a verb with its JSON captured, then print that envelope as Markdown."""
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            code = dispatch()
    except SystemExit:
        # A refusal that exits (as argparse's did) still printed its envelope: show it, then exit.
        _emit(buffer.getvalue())
        raise
    return _emit(buffer.getvalue(), code)


def _emit(captured, code=None):
    try:
        envelope = json.loads(captured)
    except ValueError:
        # Not one envelope: pass it through untouched rather than hide it.
        sys.stdout.write(captured)
        return code
    sys.stdout.write(markdown(envelope) if isinstance(envelope, dict) else captured)
    return code
