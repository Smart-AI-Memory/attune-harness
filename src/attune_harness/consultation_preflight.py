"""Advisory, no-model-call consultation checks; never create a run or authority."""

import re
import shutil
from pathlib import Path

from .consultation import configuration
from .process import invoke
from .review_contract import parse_json


def _probe(binary, *arguments):
    # Only callers below choose arguments. Never execute a configured wrapper,
    # a prompt, a model selection, login, or an undocumented status fallback.
    return invoke((binary, *arguments), '', cwd=Path.cwd(), timeout=10,
                  max_output_bytes=8192)


def _version(binary):
    result = _probe(binary, '--version')
    if result.failure or result.returncode != 0:
        return None
    match = re.fullmatch(r'(?:codex-cli )?(\d+\.\d+\.\d+(?:[-+][\w.-]+)?)(?: \(Claude Code\))?\s*', result.stdout)
    return match.group(1) if match else None


def _signed_in(adapter, result):
    # Only a completed, recognized status report establishes an auth state.
    if result.failure not in (None, 'nonzero_exit') or result.returncode is None:
        return None
    if adapter == 'claude':
        try:
            status = parse_json(result.stdout, 8192)
        except ValueError:
            return None
        if isinstance(status, dict) and type(status.get('loggedIn')) is bool:
            if status['loggedIn'] is False:
                return False
            if result.returncode == 0:
                return True
    else:
        lines = (result.stdout + '\n' + result.stderr).splitlines()
        if result.returncode == 0 and any(
                line == 'Logged in using ChatGPT' or line.startswith('Logged in using an API key')
                for line in lines):
            return True
        if result.returncode != 0 and 'Not logged in' in lines:
            return False
    return None


def preflight(config):
    """Return {participant: {state, binary, version, fix}} without model calls.

    Validate with prepare's checks before launching any status process. The
    public config has no operation: one seat uses the source-review rules, two
    or three use roundtable rules. CLI callers also validate their chosen verb.
    ``ready`` is reserved for proof of the configured model via a free probe;
    current local login probes do not supply that proof, so login stays unknown
    for model availability. No credentials or raw auth diagnostics are returned.
    """
    operation = 'source-review' if isinstance(config, dict) and isinstance(
        config.get('participants'), dict) and len(config['participants']) == 1 else 'roundtable'
    configuration(config, operation)
    reports = {}
    for name, seat in config['participants'].items():
        adapter = seat['adapter']
        executable = seat['command'][0] if adapter == 'command' else (
            'agy' if adapter == 'antigravity' else adapter)
        binary = shutil.which(executable)
        report = {'state': 'unknown', 'binary': binary, 'version': None, 'fix': ''}
        reports[name] = report
        if binary is None:
            report.update(state='missing_binary', fix=f'Install {executable} and add it to PATH; rerun check.')
            continue
        if adapter in ('command', 'antigravity'):
            report['fix'] = ('Check the configured wrapper or signed-in Antigravity host and explicit model '
                             'manually; no verified local auth/version probe is available. Do not make a '
                             'paid model call without separate authority.')
            continue
        try:
            report['version'] = _version(binary)
            arguments = ('auth', 'status', '--json') if adapter == 'claude' else ('login', 'status')
            signed_in = _signed_in(adapter, _probe(binary, *arguments))
        except (OSError, ValueError, NotImplementedError):
            signed_in = None
        if signed_in is False:
            login = 'claude auth login' if adapter == 'claude' else 'codex login'
            report.update(state='not_signed_in', fix=f'Run {login}, then rerun check.')
        elif signed_in is True:
            report['fix'] = ('Host reports signed in; configured model availability and token freshness '
                             'remain unknown. Confirm access separately; a paid probe requires authority.')
        else:
            status = 'claude auth status --json' if adapter == 'claude' else 'codex login status'
            report['fix'] = f'Inspect {status}; its local result was unavailable or unrecognized. Rerun check.'
    return reports
