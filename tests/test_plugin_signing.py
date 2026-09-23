"""Plugin signing, revocation and the capability fields: the first cycle of plan task 4.3.

A bundle whose manifest carries ``grants`` or ``declares`` is a plugin. It
enables and is called only when ``artifact.sig`` beside its manifest is a
detached signature over its artifact digest by a key the accepted registry
lists under ``signers``, its digest is not under ``revoked``, and the
registration's grant is a subset of the manifest's grants (executable plugins
spec: T1, T8, T9, R1; D22 decisions 1 to 3). Every key here is a scratch key
the test generates in a short temporary home directory and deletes with it;
no test reads, exports or names the user's own keyring, and the verifier
builds its keyring from the registry's blocks alone. The tests run on every
platform of the matrix and never skip: a runner without ``gpg`` fails by name.
The expired-key and revoked-key refusals come from real gpg status lines, a
key generated under a faked clock and a key revoked with the certificate gpg
wrote at its creation; only the verifier-not-running refusals use a stub.
"""

# qualify: platform

import copy
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

import pytest

from attune_harness import extensions as ext
from attune_harness import plugin_signing as signing
from attune_harness.features import FeatureUnavailable
from attune_harness.process import ProcessResult, invoke
from attune_harness.retrieval import retrieve_sources
from attune_harness.review import review
from attune_harness.review_contract import load_registry
from attune_harness.review_store import read_record
from test_extensions import bundle  # noqa: F401  (fixture)
from test_review import case, change, change_config  # noqa: F401  (fixture: case)

GPG = shutil.which('gpg')
GPGCONF = shutil.which('gpgconf')
PLUGIN_GRANTS = {'secrets': ['VOYAGE_API_KEY'], 'paths': ['corpus'], 'scratch': True, 'time': 120,
                 'output': {'result': 65_536, 'diagnostics': 8_192}}
PLUGIN_DECLARES = {'imports': ['voyageai', 'lancedb'], 'network': ['api.voyageai.com'], 'reads': [],
                   'writes': [], 'subprocess': False, 'vendored': []}
GRANT = {'secrets': ['VOYAGE_API_KEY'], 'time': 60}
# Structurally valid trust data for cases where the verifier must never run.
FAKE_ENTRY = {'fingerprint': 'A' * 40,
              'public_key': '-----BEGIN PGP PUBLIC KEY BLOCK-----\n\nbm90IGEga2V5\n-----END PGP PUBLIC KEY BLOCK-----\n'}
QUERY = {'query': 'quartz policy', 'k': 3}


def gpg_or_fail():
    """The tests never skip: a runner without gpg fails by name, which is R1's platform proof."""
    if GPG is None:
        pytest.fail('gpg is not on PATH; the plugin tests need GnuPG on every platform of the matrix')
    return GPG


STYLE = {}


def gpg_style():
    """How the runner's gpg spells a path, probed once: Git for Windows' MSYS build wants /c/... (D29.1)."""
    if 'style' not in STYLE:
        home = Path(tempfile.mkdtemp(prefix='hs-probe-'))
        try:
            STYLE.update(signing.probe_gpg(gpg_or_fail(), home))
        finally:
            shutil.rmtree(home, ignore_errors=True)
        STYLE['style'] = STYLE['path_style']
    return STYLE['style']


def spelled(path):
    return signing.gpg_path(path, gpg_style())


def run_gpg(home, *args):
    """One bounded gpg call in a scratch home, through the same primitive the host uses.

    Paths reach gpg spelled as the verifier spells them for this build: Git for
    Windows' MSYS gpg treats a backslashed or a C:/ home as relative and cannot
    start its agent from it (D29.1's first two findings).
    """
    result = invoke((gpg_or_fail(), '--batch', '--no-tty', '--homedir', spelled(home), *args), '',
                    cwd=home, timeout=120, max_output_bytes=1_048_576)
    assert result.failure in (None, 'nonzero_exit') and result.returncode == 0, (args, result)
    return result


def launch_agent(home):
    """One gpg-agent for a scratch home, started outside the tests' bounded calls.

    Every gpg call here runs under process.invoke, whose Job Object on Windows
    ends the agent that gpg autostarts with it, so each key generation and each
    signing paid an agent start and the platform job ran past its budget
    (D29.1's third finding). gpgconf launches the agent detached, with no pipe
    it could inherit; close() kills it.
    """
    if GPGCONF is None:
        return
    subprocess.run([GPGCONF, '--homedir', spelled(home), '--launch', 'gpg-agent'], cwd=home, check=False,
                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)


class Signer:
    """One scratch key in a short temporary home directory, deleted with it; never the user's."""

    def __init__(self, name, *, expire='never', at=None):
        # Short on purpose: the agent's socket path in the home has a length limit on macOS.
        self.home = Path(tempfile.mkdtemp(prefix='hs-'))
        os.chmod(self.home, 0o700)
        launch_agent(self.home)
        self.faked = ('--faked-system-time', at) if at else ()
        created = run_gpg(self.home, '--status-fd', '1', *self.faked, '--passphrase', '', '--pinentry-mode', 'loopback',
                          '--quick-generate-key', f'{name} <{name}@example.invalid>', 'default', 'default', expire)
        # The status line names the new key; a listing call is not needed.
        self.fingerprint = next(line.split()[3] for line in created.stdout.splitlines()
                                if line.startswith('[GNUPG:] KEY_CREATED'))
        self.public_key = self._export()

    def _export(self):
        target = self.home / 'public.asc'
        run_gpg(self.home, '--armor', '--yes', '--output', spelled(target), '--export', self.fingerprint)
        return target.read_bytes().decode('ascii')

    @property
    def entry(self):
        return {'fingerprint': self.fingerprint, 'public_key': self.public_key}

    def sign(self, data: bytes, *, at=None) -> bytes:
        source, target = self.home / 'signed.bin', self.home / 'signed.sig'
        source.write_bytes(data)
        faked = ('--faked-system-time', at) if at else self.faked
        run_gpg(self.home, *faked, '--passphrase', '', '--pinentry-mode', 'loopback', '--armor', '--yes',
                '--output', spelled(target), '--detach-sign', spelled(source))
        return target.read_bytes()

    def revoke(self):
        """Apply the revocation certificate gpg wrote at creation; the exported block then carries it."""
        certificate = self.home / 'openpgp-revocs.d' / f'{self.fingerprint}.rev'
        # gpg guards the certificate with a leading colon so it is never imported by accident.
        armed = certificate.read_text(encoding='utf-8').replace(
            ':-----BEGIN PGP PUBLIC KEY BLOCK-----', '-----BEGIN PGP PUBLIC KEY BLOCK-----')
        (self.home / 'revoke.asc').write_text(armed, encoding='utf-8')
        run_gpg(self.home, '--import', spelled(self.home / 'revoke.asc'))
        self.public_key = self._export()

    def close(self):
        if GPGCONF is not None:  # stop the agent that key generation started, then remove the home
            invoke((GPGCONF, '--homedir', spelled(self.home), '--kill', 'all'), '', cwd=self.home, timeout=30)
        shutil.rmtree(self.home, ignore_errors=True)


@pytest.fixture(scope='module')
def base_signer():
    # The one listed key most tests need, generated once per module and deleted with it;
    # a test that needs a key of its own (another signer, an expired or a revoked one)
    # still generates that key itself. What each test asserts is unchanged; the
    # platform job's budget on Windows is what this fits (D29.1's third finding).
    signer = Signer('scratch')
    yield signer
    signer.close()


@pytest.fixture
def signers(base_signer):
    made = []

    def make(name='scratch', **kwargs):
        if name == 'scratch' and not kwargs:
            return base_signer
        signer = Signer(name, **kwargs)
        made.append(signer)
        return signer
    yield make
    for signer in made:
        signer.close()


@pytest.fixture
def signer(signers):
    return signers()


@pytest.fixture
def plugin(bundle):
    change(bundle, lambda d: d.update(grants=PLUGIN_GRANTS, declares=PLUGIN_DECLARES))
    return bundle


def sign_bundle(manifest, signer, **kwargs):
    """Sign the bundle's current artifact digest, the way a maintainer does, and return the digest."""
    digest = ext.discover(manifest)['artifact_digest']
    (manifest.parent / signing.SIGNATURE_NAME).write_bytes(signer.sign(signing.signed_bytes(digest), **kwargs))
    return digest


def section(directory, digest, *, signers=(), revoked=(), grant=GRANT):
    value = {'evidence': {'state_dir': str(directory), 'artifact_digest': digest}}
    if grant is not None:
        value['evidence']['grant'] = grant
    if signers:
        value['signers'] = [s.entry for s in signers]
    if revoked:
        value['revoked'] = list(revoked)
    return value


def retrieve_for(case):
    return lambda query, k: retrieve_sources(query, case[0].parent / 'project', k=k)


class World:
    """A signed plugin bundle, its state directory and a registry section that lists its signer."""

    def __init__(self, case, manifest, tmp_path, signers):
        self.case, self.manifest = case, manifest
        self.signers, self.signer = signers, signers('scratch')
        self.directory = tmp_path / 'plugin-state'
        self.digest = sign_bundle(manifest, self.signer)
        self.section = section(self.directory, self.digest, signers=[self.signer])

    def write(self):
        """The section into the case's registry file, for enable --registry."""
        change(self.case[1], lambda d: d.update(extensions=copy.deepcopy(self.section)))
        return self.case[1]

    def register(self):
        """The section into the accepted registry with the participants granted the tool."""
        def update(config):
            config['extensions'] = copy.deepcopy(self.section)
            for item in config['participants'].values():
                item['tools'] = ['evidence.search', 'verify']
        change_config(self.case, update)
        return self.case[1]

    def install(self):
        return ext.install(self.manifest, self.directory)

    def enable(self, first):
        return ext.mutate(self.directory, first['state_digest'], 'enable', registry=self.write())

    def signature(self, data):
        (self.manifest.parent / signing.SIGNATURE_NAME).write_bytes(data)


# Each condition puts the bundle or the registry into one refused state and names the refusal.
def unsigned(w):
    (w.manifest.parent / signing.SIGNATURE_NAME).unlink()
    return signing.UNSIGNED


def not_a_signature(w):
    w.signature(b'not a signature')
    return signing.NOT_A_SIGNATURE


def stale_signature(w):
    w.signature(w.signer.sign(signing.signed_bytes('b' * 64)))
    return signing.TAMPERED


def signed_with_a_newline(w):
    # The signed bytes are the digest's 64 hex characters and nothing else.
    w.signature(w.signer.sign(signing.signed_bytes(w.digest) + b'\n'))
    return signing.TAMPERED


def unlisted_signer(w):
    w.section['signers'] = [{'fingerprint': 'A' * 40, 'public_key': w.signer.public_key}]
    return signing.UNLISTED


def no_public_key(w):
    w.section['signers'] = [w.signers('other').entry]
    return signing.NO_PUBKEY


def revoked_artifact(w):
    w.section['revoked'] = [w.digest]
    return ext.REVOKED_ARTIFACT


def expired_key(w):
    # A key created under a faked clock in 2020 that expired a minute later, signing while valid.
    expiring = w.signers('expiring', at='20200101T000000!', expire='seconds=60')
    w.signature(expiring.sign(signing.signed_bytes(w.digest), at='20200101T000030!'))
    w.section['signers'] = [expiring.entry]
    return signing.EXPIRED_KEY


def revoked_key(w):
    revoked = w.signers('revoked')
    w.signature(revoked.sign(signing.signed_bytes(w.digest)))
    revoked.revoke()
    w.section['signers'] = [revoked.entry]
    return signing.REVOKED_KEY


def secret_not_declared(w):
    w.section['evidence']['grant'] = {'secrets': ['OTHER_SECRET']}
    return ext.EXCESS_GRANT.format(name='secrets')


def time_beyond_declared(w):
    w.section['evidence']['grant'] = {'time': PLUGIN_GRANTS['time'] + 1}
    return ext.EXCESS_GRANT.format(name='time')


AT_ENABLE = [unsigned, not_a_signature, stale_signature, signed_with_a_newline, unlisted_signer,
             no_public_key, revoked_artifact, expired_key, revoked_key, secret_not_declared, time_beyond_declared]
BEFORE_CALL = [unsigned, stale_signature, unlisted_signer, revoked_artifact, revoked_key, secret_not_declared]


def test_signed_plugin_enables_runs_and_is_receipted(case, plugin, tmp_path, signers):
    w = World(case, plugin, tmp_path, signers)
    first = w.install()
    assert 'plugin' not in first and first['status'] == 'disabled'
    config = w.register()
    state = ext.mutate(w.directory, first['state_digest'], 'enable', registry=config)
    receipt = state['plugin']
    assert {k: v for k, v in receipt.items() if k != 'verifier'} == {
        'signer': w.signer.fingerprint, 'grant': GRANT, 'declares': PLUGIN_DECLARES,
        'signature_scope': signing.SIGNATURE_SCOPE, 'declarations_scope': signing.DECLARATIONS_SCOPE}
    verifier = receipt['verifier']
    assert verifier['gpg'] == GPG and verifier['version'].startswith('gpg') and verifier['exit_status'] == 0
    assert verifier['path_style'] in ('posix', 'native')
    assert 'GOODSIG' in verifier['status'] and 'VALIDSIG' in verifier['status'] and 'BADSIG' not in verifier['status']
    assert 'reviewed by the signer under the brief' in receipt['signature_scope']
    assert 'not enforced' in receipt['declarations_scope']
    assert ext.inspect_extension(w.directory) == state
    bindings = load_registry(config)['extensions']
    assert set(ext.catalog(bindings, enabled=True)) == {'evidence.search'}
    calls = []

    def retrieve(query, k):
        calls.append(query)
        return retrieve_for(case)(query, k)
    result = ext.invoke_tool(bindings, 'evidence.search', QUERY, retrieve)
    assert calls == ['quartz policy'] and result['status'] == 'retrieved' and result['sources']
    assert result['extension']['plugin'] == receipt and result['extension']['artifact_digest'] == w.digest
    # The review path: every contributed call carries the receipt.
    outcome = review(*case)
    assert outcome['status'] == 'completed' and outcome['document_outcome'] == 'verified'
    events = [e for e in outcome['events'] if e['kind'] == 'tool' and e['action']['name'] == 'evidence.search']
    assert len(events) == 2 and all(e['result']['extension']['plugin'] == receipt for e in events)
    # Disabling ends the grant: the receipt leaves the state, and enabling again needs the registry.
    disabled = ext.mutate(w.directory, state['state_digest'], 'disable')
    assert 'plugin' not in disabled
    with pytest.raises(FeatureUnavailable, match=re.escape(ext.PLUGIN_NEEDS_REGISTRY)):
        ext.mutate(w.directory, disabled['state_digest'], 'enable')


def test_mcp_session_records_the_plugin_receipt(case, plugin, tmp_path, signers):
    from attune_harness import mcp_server
    w = World(case, plugin, tmp_path, signers)
    first = w.install()
    config = w.register()
    ext.mutate(w.directory, first['state_digest'], 'enable', registry=config)
    change_config(case, lambda d: [p.update(tools=['evidence.search']) for p in d['participants'].values()])
    scope = mcp_server.RetrievalSession(case[0], config, 'alpha', case[2])
    with scope.store.lease():
        scope.save()
        found = scope.invoke('harness.evidence.search', QUERY)
        scope.finish()
    assert found['status'] == 'retrieved' and found['extension']['plugin']['signer'] == w.signer.fingerprint
    saved = read_record(case[2])
    assert saved['status'] == 'completed'
    assert saved['events'][0]['result']['extension']['plugin']['grant'] == GRANT


@pytest.mark.parametrize('condition', AT_ENABLE, ids=lambda c: c.__name__)
def test_refused_at_enable(case, plugin, tmp_path, signers, condition):
    w = World(case, plugin, tmp_path, signers)
    expected = condition(w)
    first = w.install()
    with pytest.raises(FeatureUnavailable, match=re.escape(expected)):
        w.enable(first)
    assert ext.inspect_extension(w.directory)['status'] == 'disabled'
    with pytest.raises(FeatureUnavailable, match=re.escape(expected)):
        ext.catalog(w.section)


@pytest.mark.parametrize('condition', BEFORE_CALL, ids=lambda c: c.__name__)
def test_refused_before_every_call(case, plugin, tmp_path, signers, condition):
    w = World(case, plugin, tmp_path, signers)
    w.enable(w.install())
    assert ext.invoke_tool(w.section, 'evidence.search', QUERY, retrieve_for(case))['status'] == 'retrieved'
    expected = condition(w)
    with pytest.raises(FeatureUnavailable, match=re.escape(expected)):
        ext.invoke_tool(w.section, 'evidence.search', QUERY, lambda *a: pytest.fail('the call ran'))
    with pytest.raises(FeatureUnavailable, match=re.escape(expected)):
        ext.catalog(w.section, enabled=True)


def test_signature_withdrawn_during_a_call_discards_its_result(case, plugin, tmp_path, signers):
    w = World(case, plugin, tmp_path, signers)
    w.enable(w.install())

    def withdraw(query, k):
        result = retrieve_for(case)(query, k)
        (w.manifest.parent / signing.SIGNATURE_NAME).unlink()
        return result
    with pytest.raises(FeatureUnavailable, match=re.escape(signing.UNSIGNED)):
        ext.invoke_tool(w.section, 'evidence.search', QUERY, withdraw)


def test_artifact_edited_after_signing_is_refused(case, plugin, tmp_path, signers):
    w = World(case, plugin, tmp_path, signers)
    with (w.manifest.parent / 'SKILL.md').open('a', encoding='utf-8') as stream:
        stream.write('\nEdited after the signer reviewed it.\n')
    w.digest = ext.discover(w.manifest)['artifact_digest']
    w.section['evidence']['artifact_digest'] = w.digest
    first = w.install()
    with pytest.raises(FeatureUnavailable, match=re.escape(signing.TAMPERED)):
        w.enable(first)
    sign_bundle(w.manifest, w.signer)
    assert w.enable(first)['plugin']['signer'] == w.signer.fingerprint


def test_grant_names_only_what_the_manifest_declares(case, bundle, tmp_path, signers):
    change(bundle, lambda d: d.update(grants={'time': 120, 'secrets': ['ONE']}))
    w = World(case, bundle, tmp_path, signers)
    first = w.install()
    for grant, expected in [({'scratch': True}, ext.OVER_GRANT.format(name='scratch')),
                            ({'output': {'result': 1, 'diagnostics': 1}}, ext.OVER_GRANT.format(name='output')),
                            ({'time': 121}, ext.EXCESS_GRANT.format(name='time')),
                            ({'secrets': ['ONE', 'TWO']}, ext.EXCESS_GRANT.format(name='secrets'))]:
        w.section['evidence']['grant'] = grant
        with pytest.raises(FeatureUnavailable, match=re.escape(expected)):
            w.enable(first)
    w.section['evidence']['grant'] = {'time': 120, 'secrets': ['ONE']}
    state = w.enable(first)
    assert state['plugin']['grant'] == {'time': 120, 'secrets': ['ONE']} and state['plugin']['declares'] == {}
    state = ext.mutate(w.directory, state['state_digest'], 'disable')
    del w.section['evidence']['grant']
    assert w.enable(state)['plugin']['grant'] == {}  # nothing granted is a valid grant


def test_gpg_absent_from_path_is_a_named_refusal(case, plugin, tmp_path, signers, monkeypatch):
    w = World(case, plugin, tmp_path, signers)
    first = w.install()
    empty = tmp_path / 'no-gpg'
    empty.mkdir()
    monkeypatch.setenv('PATH', str(empty))
    monkeypatch.setattr(signing, 'KNOWN_GPG_POSIX', ())
    monkeypatch.setattr(signing, 'KNOWN_GPG_WINDOWS', ())
    monkeypatch.setattr(signing, 'invoke', lambda *a, **k: pytest.fail('a verifier was launched with no gpg on PATH'))
    expected = signing.GPG_ABSENT.format(searched='none known')
    with pytest.raises(FeatureUnavailable, match=re.escape(expected)):
        w.enable(first)
    with pytest.raises(FeatureUnavailable, match=re.escape(expected)):
        ext.catalog(w.section)
    assert signing.find_gpg() == (None, ['PATH'])
    assert ext.inspect_extension(w.directory)['status'] == 'disabled'


@pytest.mark.parametrize('outcome,expected', [
    (ProcessResult(('gpg',), None, '', 'no such file', 'launch_failed'),
     signing.VERIFIER_FAILED.format(failure='launch_failed')),
    (ProcessResult(('gpg',), None, '', '', 'timeout_effects_unknown'),
     signing.VERIFIER_FAILED.format(failure='timeout_effects_unknown')),
    (ProcessResult(('gpg',), 0, '', '', None), signing.NO_VERDICT),
    (ProcessResult(('gpg',), 0, '[GNUPG:] GOODSIG 0123456789ABCDEF Someone\n', '', None), signing.NO_VERDICT),
    (ProcessResult(('gpg',), 2, '', 'gpg: fatal', 'nonzero_exit'), signing.NO_VERDICT),
], ids=['launch_failed', 'timeout', 'exit_0_silent', 'goodsig_without_validsig', 'exit_2_silent'])
def test_verifier_that_does_not_run_or_says_nothing_never_passes(case, plugin, tmp_path, signers, monkeypatch,
                                                                 outcome, expected):
    """A stub stands in for gpg here: these are the outcomes a real gpg cannot be made to produce on demand."""
    w = World(case, plugin, tmp_path, signers)
    first = w.install()

    def stub(argv, prompt, **kwargs):
        if '--version' in argv:
            return ProcessResult(argv, 0, 'gpg (GnuPG) 0.0.0-stub\nHome: /stub\n', '', None)
        if '--import' in argv:
            return ProcessResult(argv, 0, f'[GNUPG:] IMPORT_OK 1 {w.signer.fingerprint}\n', '', None)
        return outcome
    monkeypatch.setattr(signing, 'invoke', stub)
    with pytest.raises(FeatureUnavailable, match=re.escape(expected)):
        w.enable(first)


def test_key_block_the_verifier_cannot_import_is_refused(case, plugin, tmp_path, signers):
    w = World(case, plugin, tmp_path, signers)
    w.section['signers'] = [{'fingerprint': w.signer.fingerprint, 'public_key': FAKE_ENTRY['public_key']}]
    with pytest.raises(FeatureUnavailable, match=re.escape(signing.KEY_IMPORT)):
        w.enable(w.install())


def test_verdict_is_read_from_status_lines_never_from_exit_status():
    fpr, other = 'F' * 40, 'E' * 40
    valid = ['VALIDSIG', fpr, '2026-09-23', '1790193974', '0', '4', '0', '22', '10', '00', fpr]
    good = ['GOODSIG', fpr[-16:], 'Scratch <scratch@example.invalid>']
    assert signing.verdict([['NEWSIG'], good, valid, ['TRUST_UNDEFINED', '0', 'pgp']], {fpr}) == fpr
    # A subkey signature reports the subkey first and the primary key last; the primary is what is listed.
    assert signing.verdict([good, ['VALIDSIG', other, '2026-09-23', '1', '0', '4', '0', '22', '10', '00', fpr]], {fpr}) == fpr
    for lines, refusal in [
        ([good, valid], signing.UNLISTED),
        ([['NEWSIG'], ['KEYEXPIRED', '1577836860'], ['EXPKEYSIG', fpr[-16:], 'x'], valid], signing.EXPIRED_KEY),
        ([['REVKEYSIG', fpr[-16:], 'x'], valid, ['KEYREVOKED']], signing.REVOKED_KEY),
        ([good, valid, ['EXPSIG', fpr[-16:], 'x']], signing.EXPIRED_SIGNATURE),
        ([['BADSIG', fpr[-16:], 'x']], signing.TAMPERED),
        ([['ERRSIG', fpr[-16:], '22', '10', '00', '1', '9', fpr], ['NO_PUBKEY', fpr[-16:]]], signing.NO_PUBKEY),
        ([['ERRSIG', fpr[-16:], '22', '10', '00', '1', '4', fpr]], signing.SIGNATURE_ERROR),
        ([['NODATA', '1'], ['NODATA', '2']], signing.NOT_A_SIGNATURE),
        ([['NEWSIG'], good], signing.NO_VERDICT),
        ([['NEWSIG'], valid], signing.NO_VERDICT),
        ([], signing.NO_VERDICT),
    ]:
        listed = {other} if refusal is signing.UNLISTED else {fpr}
        with pytest.raises(FeatureUnavailable, match=re.escape(refusal)):
            signing.verdict(lines, listed)
    assert signing.signed_bytes('a' * 64) == b'a' * 64
    with pytest.raises(ValueError, match='SHA-256'):
        signing.signed_bytes('A' * 64)


def test_verifier_home_is_private_built_from_the_registry_and_removed(case, plugin, tmp_path, signers, monkeypatch):
    w = World(case, plugin, tmp_path, signers)
    seen = []
    real = signing.invoke

    def spy(argv, prompt, **kwargs):
        home = kwargs['cwd']
        if '--version' in argv:
            assert '--homedir' not in argv  # the build's own spelling of a path, before any home is named
        else:
            assert argv[argv.index('--homedir') + 1] == signing.gpg_path(home, gpg_style())
        if os.name != 'nt':
            assert stat.S_IMODE(home.stat().st_mode) == 0o700
        assert (home / 'common.conf').read_bytes() == b''
        if '--import' in argv:  # bytes, since gpg on Windows may armour with CRLF
            assert (home / 'signers.asc').read_bytes() == w.signer.public_key.strip().encode('ascii') + b'\n'
        seen.append((argv, kwargs, home))
        return real(argv, prompt, **kwargs)
    monkeypatch.setattr(signing, 'invoke', spy)
    monkeypatch.setattr(signing, 'PROBED', {})  # so the build probe runs again and is observed
    monkeypatch.setenv('GNUPGHOME', str(tmp_path / 'users-keyring'))  # a canary the verifier must not see
    verified = signing.verify_bundle(w.manifest.parent, w.digest, [w.signer.entry])
    assert verified['signer'] == w.signer.fingerprint and verified['verifier']['gpg'] == GPG
    assert [argv[-1] if '--version' in argv else argv[argv.index('--status-fd') + 2] for argv, _, _ in seen] == [
        '--version', '--import', '--verify']
    assert verified['verifier']['path_style'] == gpg_style()
    for argv, kwargs, home in seen:
        assert argv[0] == GPG
        if '--version' not in argv:
            assert '--no-autostart' in argv and argv[argv.index('--status-fd') + 1] == '1'
        assert not home.exists() and not (tmp_path / 'users-keyring').exists()
        environment = kwargs['environment']
        assert 'GNUPGHOME' not in environment and environment['LC_ALL'] == 'C'
        assert kwargs['timeout'] == signing.VERIFIER_TIMEOUT and kwargs['max_output_bytes'] == signing.VERIFIER_OUTPUT
    assert len(seen) == 3


def test_data_only_bundle_is_untouched_by_the_trust_data(case, bundle, tmp_path, monkeypatch):
    directory = tmp_path / 'state'
    first = ext.install(bundle, directory)
    state = ext.mutate(directory, first['state_digest'], 'enable')  # no registry, no signature, as today
    assert 'plugin' not in state and not ext.is_plugin(ext.discover(bundle)['declaration'])
    monkeypatch.setattr(signing, 'invoke', lambda *a, **k: pytest.fail('gpg ran for a data-only bundle'))
    bindings = {'signers': [FAKE_ENTRY], 'revoked': ['b' * 64],
                'evidence': {'state_dir': str(directory), 'artifact_digest': state['artifact_digest']}}
    assert set(ext.catalog(bindings, enabled=True)) == {'evidence.search'}
    result = ext.invoke_tool(bindings, 'evidence.search', QUERY, retrieve_for(case))
    assert result['status'] == 'retrieved' and 'plugin' not in result['extension']
    assert ext.registrations(bindings) == {'evidence': bindings['evidence']}
    assert ext.trust(bindings) == {'signers': [FAKE_ENTRY], 'revoked': ['b' * 64]}
    # A grant on a data-only registration is refused: the manifest declares nothing.
    bindings['evidence']['grant'] = {'time': 10}
    with pytest.raises(FeatureUnavailable, match=re.escape(ext.OVER_GRANT.format(name='time'))):
        ext.catalog(bindings, enabled=True)
    # The revocation list applies to any registered bundle.
    bindings['evidence'].pop('grant')
    bindings['revoked'] = [state['artifact_digest']]
    with pytest.raises(FeatureUnavailable, match=re.escape(ext.REVOKED_ARTIFACT)):
        ext.invoke_tool(bindings, 'evidence.search', QUERY, lambda *a: pytest.fail('the call ran'))


def test_plugin_enable_needs_the_registry_that_registers_it(case, plugin, tmp_path, signers):
    w = World(case, plugin, tmp_path, signers)
    first = w.install()
    with pytest.raises(FeatureUnavailable, match=re.escape(ext.PLUGIN_NEEDS_REGISTRY)):
        ext.mutate(w.directory, first['state_digest'], 'enable')
    registration = w.section.pop('evidence')
    w.section['other'] = registration
    with pytest.raises(FeatureUnavailable, match=re.escape(ext.NOT_REGISTERED.format(id='evidence'))):
        w.enable(first)
    w.section['evidence'] = dict(w.section.pop('other'), state_dir=str(tmp_path / 'elsewhere'))
    with pytest.raises(FeatureUnavailable, match=re.escape(ext.REGISTERED_ELSEWHERE.format(id='evidence'))):
        w.enable(first)
    w.section['evidence'] = dict(registration, artifact_digest='c' * 64)
    with pytest.raises(FeatureUnavailable, match='artifact changed'):
        w.enable(first)
    change(case[1], lambda d: d.pop('extensions'))
    with pytest.raises(ValueError, match='no extensions section'):
        ext.mutate(w.directory, first['state_digest'], 'enable', registry=case[1])
    with pytest.raises(ValueError, match='Only enable accepts a registry'):
        ext.mutate(w.directory, first['state_digest'], 'disable', registry=case[1])
    assert ext.inspect_extension(w.directory)['status'] == 'disabled'
    w.section['evidence'] = registration
    assert w.enable(first)['status'] == 'enabled'


def test_cli_enable_takes_the_registry(case, plugin, tmp_path, signers, capsys):
    from attune_harness.cli import main
    w = World(case, plugin, tmp_path, signers)
    config = w.write()
    assert main(['extension', 'install', str(plugin), '--state-dir', str(w.directory)]) == 0
    first = json.loads(capsys.readouterr().out)
    assert main(['extension', 'enable', '--state-dir', str(w.directory), '--checkpoint', first['state_digest']]) == 2
    refused = json.loads(capsys.readouterr().out)
    assert refused['status'] == 'unavailable' and refused['error']['detail'] == ext.PLUGIN_NEEDS_REGISTRY
    assert main(['extension', 'enable', '--state-dir', str(w.directory), '--checkpoint', first['state_digest'],
                 '--registry', str(config)]) == 0
    state = json.loads(capsys.readouterr().out)
    assert state['status'] == 'enabled' and state['plugin']['signer'] == w.signer.fingerprint
    assert main(['extension', 'inspect', '--state-dir', str(w.directory)]) == 0
    assert json.loads(capsys.readouterr().out) == state
    assert main(['extension', 'disable', '--state-dir', str(w.directory), '--checkpoint', state['state_digest']]) == 0
    assert 'plugin' not in json.loads(capsys.readouterr().out)


@pytest.mark.parametrize('field,value,text', [
    ('grants', {'network': ['api.example.com']}, 'manifest schema version 2 material'),
    ('grants', {'run': True}, 'no grant named run; that is manifest schema version 2 material'),
    ('declares', {'secrets': ['X']}, 'no declaration named secrets; that is manifest schema version 2 material'),
    ('grants', [], 'grants must be an object'),
    ('declares', 'imports', 'declares must be an object'),
    ('grants', {'time': 301}, '1..300'),
    ('grants', {'time': 0}, '1..300'),
    ('grants', {'time': True}, '1..300'),
    ('grants', {'output': {'result': 1_048_577, 'diagnostics': 1}}, 'output result'),
    ('grants', {'output': {'result': 1, 'diagnostics': 65_537}}, 'output diagnostics'),
    ('grants', {'output': {'result': 1}}, 'Expected fields'),
    ('grants', {'secrets': ['not-a-name']}, 'environment variables'),
    ('grants', {'secrets': ['KEY=1']}, 'environment variables'),
    ('grants', {'secrets': ['Key', 'KEY']}, 'ignoring case'),
    ('grants', {'secrets': ['KEY', 'KEY']}, 'unique list'),
    ('grants', {'secrets': ['K%d' % i for i in range(9)]}, 'at most 8'),
    ('grants', {'paths': ['Corpus']}, 'lowercase identifiers'),
    ('grants', {'scratch': 'yes'}, 'true or false'),
    ('declares', {'network': ['Api.Example.Com']}, 'lowercase host names'),
    ('declares', {'network': ['a' * 254]}, 'network host'),
    ('declares', {'network': ['a-.example']}, 'lowercase host names'),
    ('declares', {'imports': ['bad name']}, 'distributions'),
    ('declares', {'imports': [42]}, 'unique list'),
    ('declares', {'vendored': ['pkg[extra]']}, 'distributions'),
    ('declares', {'subprocess': 1}, 'true or false'),
    ('declares', {'reads': ['']}, 'reads entry'),
    ('declares', {'writes': ['w%d' % i for i in range(33)]}, 'at most 32'),
])
def test_manifest_vocabulary_is_version_one(bundle, field, value, text):
    change(bundle, lambda d: d.update({field: value}))
    with pytest.raises(ValueError, match=re.escape(text)):
        ext.discover(bundle)


def test_manifest_fields_are_bound_into_the_artifact(bundle):
    plain = ext.discover(bundle)
    change(bundle, lambda d: d.update(grants=PLUGIN_GRANTS, declares=PLUGIN_DECLARES))
    full = ext.discover(bundle)
    assert ext.is_plugin(full['declaration']) and not ext.is_plugin(plain['declaration'])
    assert full['artifact_digest'] != plain['artifact_digest']
    assert full['declaration']['grants'] == PLUGIN_GRANTS and full['declaration']['declares'] == PLUGIN_DECLARES
    change(bundle, lambda d: d.update(grants={}, declares={'imports': ['requests[socks]', 'requests_toolbelt']}))
    assert ext.is_plugin(ext.discover(bundle)['declaration'])
    change(bundle, lambda d: d.update(grants={'time': 121}))
    assert ext.discover(bundle)['artifact_digest'] != full['artifact_digest']


@pytest.mark.parametrize('trust,text', [
    ({'signers': []}, '1–8 keys'),
    ({'signers': [FAKE_ENTRY] * 9}, '1–8 keys'),
    ({'signers': [{'fingerprint': 'a' * 40, 'public_key': FAKE_ENTRY['public_key']}]}, '40 uppercase'),
    ({'signers': [{'fingerprint': 'A' * 40, 'public_key': 'not a block'}]}, 'armoured'),
    ({'signers': [{'fingerprint': 'A' * 40, 'public_key': 'x' * 16_385}]}, 'public_key'),
    ({'signers': [FAKE_ENTRY, FAKE_ENTRY]}, 'once'),
    ({'signers': [{'fingerprint': 'A' * 40}]}, 'Expected fields'),
    ({'revoked': ['short']}, 'SHA-256'),
    ({'revoked': 'x'}, 'unique list'),
    ({'revoked': ['a' * 64] * 2}, 'unique list'),
])
def test_trust_lists_are_validated_without_opening_a_bundle(tmp_path, trust, text):
    value = {'evidence': {'state_dir': 'nowhere', 'artifact_digest': 'a' * 64}, **trust}
    with pytest.raises(ValueError, match=text):
        ext.validate_bindings(value, tmp_path)


def test_registration_grant_and_reserved_keys(tmp_path):
    good = {'evidence': {'state_dir': 'nowhere', 'artifact_digest': 'a' * 64, 'grant': {'time': 5}},
            'signers': [FAKE_ENTRY], 'revoked': ['b' * 64]}
    assert ext.validate_bindings(good, tmp_path) is good
    assert ext.registrations(good) == {'evidence': good['evidence']}
    assert good['evidence']['state_dir'] == str(tmp_path / 'nowhere')
    with pytest.raises(ValueError, match='1–8 explicit registrations'):
        ext.validate_bindings({'signers': [FAKE_ENTRY]}, tmp_path)
    with pytest.raises(ValueError, match='manifest schema version 2'):
        ext.validate_bindings({'evidence': {'state_dir': 'x', 'artifact_digest': 'a' * 64, 'grant': {'network': []}}}, tmp_path)
    with pytest.raises(ValueError, match='Expected fields'):
        ext.validate_bindings({'evidence': {'state_dir': 'x', 'artifact_digest': 'a' * 64, 'extra': 1}}, tmp_path)
    with pytest.raises(PermissionError, match='not in the accepted registry'):
        ext.invoke_tool(good, 'signers.search', QUERY, lambda *a: pytest.fail('the call ran'))
