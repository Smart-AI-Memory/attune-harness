"""D29.1: the executable plugins' Windows unknowns, probed on every platform job.

Patrick's ruling D29.1 (docs/specs/release-1.0/addendum-2026-09-23.md): inside
4.3's first cycle, a probe on all three runners finds gpg, verifies a detached
signature by its status lines, and launches the child bootstrap with its finder,
with the receipts kept. This file is in the platform selection and never skips:
what it finds is the fact the ruling asks for, so a runner without gpg fails
with the discovery receipt in the failure message. The receipt is written after
every step to the test's own temporary directory and, when
HARNESS_QUALIFICATION_OUTPUT names one, to the qualification output directory,
where scripts/qualify_platform.py copies it into platform.json as
``plugin_probe``. The child bootstrap is the run binding's shape ahead of its
cycle: the host's interpreter with -I -S -B, sys.path set to the bundle plus the
standard library entries of the host's path, and a meta path finder that
resolves a top-level name from site-packages only inside the declared closure;
a cooperating bundle's guard, not isolation, as the spec says.
"""

# qualify: platform

import hashlib
import importlib.metadata as metadata
import importlib.util
import json
import os
import platform
import shutil
import sys
import sysconfig
from pathlib import Path

import pytest

from attune_harness import plugin_signing as signing
from attune_harness.process import invoke
from test_plugin_signing import signers  # noqa: F401  (fixture)

RECEIPT_NAME = 'plugin-probe.json'
# The declared import is a base dependency, so every install has it; the
# undeclared one is an extra the platform jobs install, present in the host and
# meant to be absent in the child.
DECLARED = 'tiktoken'
UNDECLARED = 'redis'


class Receipt:
    """The probe's receipt, rewritten after every step so a failure keeps what was found."""

    def __init__(self, tmp_path):
        self.value = {'schema_version': 1, 'ruling': 'D29.1', 'system': platform.system(),
                      'machine': platform.machine(), 'python': platform.python_version(),
                      'executable': sys.executable, 'steps': {}}
        self.targets = [tmp_path / RECEIPT_NAME]
        output = os.environ.get('HARNESS_QUALIFICATION_OUTPUT')
        if output:
            self.targets.append(Path(output) / RECEIPT_NAME)
        self.write()

    def write(self):
        for target in self.targets:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(self.value, indent=2) + '\n', encoding='utf-8')

    def record(self, step, outcome='passed', **fields):
        self.value['steps'][step] = {'outcome': outcome, **fields}
        self.write()

    def fail(self, step, message, **fields):
        self.record(step, f'failed: {message}', **fields)
        pytest.fail(f'{message}; the receipt: {json.dumps(self.value, indent=2)}')


@pytest.fixture
def receipt(tmp_path):
    return Receipt(tmp_path)


@pytest.fixture(scope='module')
def shared_receipt(tmp_path_factory):
    # One file for the module's tests, so the two probes land in one receipt.
    return Receipt(tmp_path_factory.mktemp('plugin-probe'))


def test_probe_gpg_discovery_and_signature_verdicts(shared_receipt, signers, tmp_path):
    receipt = shared_receipt
    gpg, searched = signing.find_gpg()
    receipt.record('discovery', gpg=gpg, searched=searched, on_path=shutil.which('gpg'),
                   path_entries=len(os.environ.get('PATH', '').split(os.pathsep)))
    if gpg is None:
        receipt.fail('discovery', f'gpg was not found on this runner after searching {searched}')
    # The build's version and how it spells a path, before any home is opened: Git for
    # Windows' MSYS build reports a /-rooted Home and needs /c/... paths.
    probed = signing.probe_gpg(gpg, tmp_path)
    receipt.record('build', **probed, home_spelling=signing.gpg_path(tmp_path, probed['path_style']))
    assert probed['path_style'] in ('posix', 'native'), probed
    signer = signers('probe')
    digest = hashlib.sha256(b'the plugin probe').hexdigest()
    signature = signer.sign(signing.signed_bytes(digest))
    good = signing.inspect_signature(digest, signature, [signer.entry])
    receipt.record('verified', **good, fingerprint=signer.fingerprint)
    assert good['refusal'] is None and good['signer'] == signer.fingerprint, good
    assert good['verifier']['gpg'] == gpg and good['verifier']['version'] == probed['version']
    assert good['verifier']['path_style'] == probed['path_style']
    assert 'GOODSIG' in good['verifier']['status'] and 'VALIDSIG' in good['verifier']['status'], good
    # The verdict is the status lines, never the exit status: an unlisted signer
    # and a revoked key both verify with exit status 0 and are refused; a
    # tampered digest exits 1 with BADSIG.
    unlisted = signing.inspect_signature(digest, signature, [{'fingerprint': 'A' * 40, 'public_key': signer.public_key}])
    receipt.record('unlisted_signer', **unlisted)
    assert unlisted['refusal'] == signing.UNLISTED and unlisted['signer'] is None, unlisted
    assert unlisted['verifier']['exit_status'] == 0 and 'VALIDSIG' in unlisted['verifier']['status'], unlisted
    tampered = signing.inspect_signature('b' * 64, signature, [signer.entry])
    receipt.record('tampered_digest', **tampered)
    assert tampered['refusal'] == signing.TAMPERED and 'BADSIG' in tampered['verifier']['status'], tampered
    assert tampered['verifier']['exit_status'] not in (None, 0), tampered
    revoked = signers('probe-revoked')
    revoked_signature = revoked.sign(signing.signed_bytes(digest))
    revoked.revoke()
    revoked_key = signing.inspect_signature(digest, revoked_signature, [revoked.entry])
    receipt.record('revoked_key', **revoked_key)
    assert revoked_key['refusal'] == signing.REVOKED_KEY, revoked_key
    assert revoked_key['verifier']['exit_status'] == 0 and 'REVKEYSIG' in revoked_key['verifier']['status'], revoked_key
    receipt.record('signature', gpg=gpg, version=good['verifier']['version'],
                   verdict_source='status lines: GOODSIG and VALIDSIG with the listed primary fingerprint',
                   exit_status_of_refused_cases={'unlisted_signer': unlisted['verifier']['exit_status'],
                                                 'revoked_key': revoked_key['verifier']['exit_status'],
                                                 'tampered_digest': tampered['verifier']['exit_status']})


def closure(distribution):
    """The distributions reachable from one through requires(); extras excluded, markers not evaluated.

    The spec's closure evaluates markers with packaging, a later cycle; this probe
    over-approximates, which only ever allows a name that does not exist here.
    """
    seen, queue = set(), [distribution]
    while queue:
        name = queue.pop()
        key = name.lower().replace('_', '-')
        if key in seen:
            continue
        try:
            requirements = metadata.requires(name) or []
        except metadata.PackageNotFoundError:
            continue
        seen.add(key)
        for requirement in requirements:
            spec, _, marker = requirement.partition(';')
            if 'extra' in marker:
                continue
            head = spec.strip()
            for cut in ('===', '==', '!=', '<=', '>=', '<', '>', '~=', ' ', '[', '('):
                if cut in head:
                    head = head[: head.index(cut)]
            queue.append(head.strip())
    return sorted(seen)


def top_level_names(distributions):
    """Top-level import names of the distributions: top_level.txt, else the RECORD's first path parts.

    packages_distributions() reads top_level.txt only on Python 3.10, which
    hatchling wheels do not write, so the RECORD is the fallback.
    """
    names = set()
    wanted = set(distributions)
    for distribution in metadata.distributions():
        name = (distribution.metadata['Name'] or '').lower().replace('_', '-')
        if name not in wanted:
            continue
        text = distribution.read_text('top_level.txt')
        if text:
            names.update(line.strip() for line in text.splitlines() if line.strip())
            continue
        for file in distribution.files or ():
            first = file.parts[0]
            if first.endswith(('.dist-info', '.data', '.pth')) or first.startswith('__'):
                continue
            if first.endswith('.py') and len(file.parts) == 1:
                names.add(first[:-3])
            elif len(file.parts) > 1:
                names.add(first)
    return sorted(names)


def stdlib_entries():
    """The standard library entries of the host's path: under the base prefix, never site-packages."""
    return [entry for entry in sys.path
            if entry and 'site-packages' not in entry and 'dist-packages' not in entry
            and entry.startswith((sys.base_prefix, sys.base_exec_prefix))]


def child_environment():
    """The allow-list the repair probe requires (repair.validate_probe), SystemRoot on Windows."""
    environment = {'PATH': os.environ.get('PATH', ''), 'LANG': 'C', 'LC_ALL': 'C',
                   'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1'}
    if os.name == 'nt':
        environment['SystemRoot'] = os.environ.get('SystemRoot', r'C:\Windows')
    return environment


def bootstrap_text(bundle, stdlib, site, allowed, imports):
    return (
        'import sys, json, importlib.abc, importlib.machinery\n'
        f'BUNDLE = {str(bundle)!r}\nSTDLIB = {stdlib!r}\nSITE = {site!r}\nALLOWED = {allowed!r}\n'
        'sys.path[:] = [BUNDLE] + STDLIB\n'
        'class Finder(importlib.abc.MetaPathFinder):\n'
        '    """A cooperating bundle\'s guard: a top-level name comes from site-packages only inside the closure."""\n'
        '    def find_spec(self, fullname, path=None, target=None):\n'
        "        if fullname.partition('.')[0] not in ALLOWED:\n"
        '            return None\n'
        '        return importlib.machinery.PathFinder.find_spec(fullname, SITE if path is None else list(path))\n'
        'sys.meta_path.insert(0, Finder())\n'
        'outcomes = {}\n'
        f'for name in {imports!r}:\n'
        '    try:\n'
        '        __import__(name)\n'
        "        outcomes[name] = 'imported'\n"
        '    except Exception as error:\n'
        "        outcomes[name] = type(error).__name__ + ': ' + str(error)\n"
        "print(json.dumps({'sys_path': sys.path, 'outcomes': outcomes, 'flags': sys.flags.isolated}))\n"
    )


def test_probe_child_bootstrap_with_finder(shared_receipt, tmp_path):
    """Cooperation, not isolation: the finder runs in the child, which could remove it (spec, R2)."""
    receipt = shared_receipt
    bundle = tmp_path / 'bundle'
    bundle.mkdir()
    (bundle / 'bundle_module.py').write_text('VALUE = 1\n', encoding='utf-8')
    stdlib = stdlib_entries()
    site = sorted({sysconfig.get_paths()['purelib'], sysconfig.get_paths()['platlib']})
    reach = closure(DECLARED)
    allowed = top_level_names(reach)
    imports = ('json', 'bundle_module', DECLARED, UNDECLARED)
    text = bootstrap_text(bundle, stdlib, site, allowed, imports)
    environment = child_environment()
    receipt.record('bootstrap_prepared', declared=DECLARED, closure=reach, allowed=allowed,
                   undeclared=UNDECLARED, undeclared_installed_in_host=importlib.util.find_spec(UNDECLARED) is not None,
                   stdlib=stdlib, site=site, environment_keys=sorted(environment),
                   bootstrap_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest(), flags=['-I', '-S', '-B'])
    assert DECLARED in allowed, allowed
    result = invoke((sys.executable, '-I', '-S', '-B', '-c', text), '', cwd=bundle, timeout=60,
                    max_output_bytes=65_536, environment=environment)
    payload = json.loads(result.stdout) if result.stdout.strip() else None
    receipt.record('bootstrap_launched', exit_status=result.returncode, failure=result.failure,
                   stderr=result.stderr[-2000:], child=payload)
    if payload is None or result.returncode != 0:
        receipt.fail('bootstrap_launched', f'the child did not report: exit {result.returncode}, {result.failure}')
    outcomes = payload['outcomes']
    assert outcomes['json'] == 'imported', outcomes
    assert outcomes['bundle_module'] == 'imported', outcomes
    assert outcomes[DECLARED] == 'imported', outcomes
    assert outcomes[UNDECLARED].startswith('ModuleNotFoundError'), outcomes
    assert payload['sys_path'][0] == str(bundle) and payload['flags'] == 1
    assert not any('site-packages' in entry or 'dist-packages' in entry for entry in payload['sys_path']), payload
    receipt.record('bootstrap', exit_status=result.returncode, outcomes=outcomes, sys_path=payload['sys_path'])
