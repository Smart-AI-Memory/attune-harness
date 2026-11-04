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

import base64
import copy
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import time
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

def _gpg_companion(executable):
    return None if executable is None else shutil.which(str(Path(executable).absolute().with_name('gpgconf')))


GPG = shutil.which('gpg')
GPGCONF = _gpg_companion(GPG)
PLUGIN_GRANTS = {'secrets': ['VOYAGE_API_KEY'], 'paths': ['corpus'], 'scratch': True, 'time': 120,
                 'output': {'result': 65_536, 'diagnostics': 8_192}}
PLUGIN_DECLARES = {'imports': ['voyageai', 'lancedb'], 'network': ['api.voyageai.com'], 'reads': [],
                   'writes': [], 'subprocess': False, 'vendored': []}
GRANT = {'secrets': ['VOYAGE_API_KEY'], 'time': 60}
# Structurally valid trust data for cases where the verifier must never run.
FAKE_ENTRY = {'fingerprint': 'A' * 40,
              'public_key': '-----BEGIN PGP PUBLIC KEY BLOCK-----\n\nbm90IGEga2V5\n-----END PGP PUBLIC KEY BLOCK-----\n'}
QUERY = {'query': 'quartz policy', 'k': 3}


def same_gpg(found):
    """Whether a discovered path names the runner's gpg: Windows spells Git for Windows' binary gpg.EXE or gpg.exe."""
    return os.path.normcase(os.path.realpath(found)) == os.path.normcase(os.path.realpath(GPG))


def gpg_or_fail():
    """The tests never skip: a runner without gpg fails by name, which is R1's platform proof."""
    if GPG is None:
        pytest.fail('gpg is not on PATH; the plugin tests need GnuPG on every platform of the matrix')
    return GPG


STYLE = {}
SIGNER_SETUP_TIMEOUT = 120


def gpg_style():
    """How the runner's gpg spells a path, probed once: Git for Windows' MSYS build wants /c/... (D29.1)."""
    if 'style' not in STYLE:
        home = Path(tempfile.mkdtemp(prefix='hs-probe-'))
        try:
            # Fixture discovery shares the key-generation budget: coverage can
            # delay cold process setup on Windows. Actual verification still
            # probes GPG independently under its own ten-second deadline.
            result = invoke((gpg_or_fail(), '--batch', '--no-tty', '--no-options', '--version'), '',
                            cwd=home, timeout=SIGNER_SETUP_TIMEOUT, max_output_bytes=signing.VERIFIER_OUTPUT,
                            environment=signing._environment())
            assert result.failure is None and result.returncode == 0, result
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            assert lines and lines[0].startswith('gpg'), result
            default_home = next((line[len('Home:'):].strip() for line in lines if line.startswith('Home:')), '')
            STYLE.update(version=lines[0], path_style='posix' if default_home.startswith('/') else 'native')
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
                    cwd=home, timeout=SIGNER_SETUP_TIMEOUT, max_output_bytes=1_048_576)
    assert result.failure in (None, 'nonzero_exit') and result.returncode == 0, (args, result)
    return result


def _guard_msys_agent_sockets(home):
    paths = [home.rstrip('/') + '/' + name for name in
             ('S.gpg-agent', 'S.gpg-agent.extra', 'S.gpg-agent.browser', 'S.gpg-agent.ssh')]
    oversized = [(path, len(path.encode('utf-8'))) for path in paths
                 if len(path.encode('utf-8')) + 1 >= 108]
    assert not oversized, ('GPG agent socket paths exceed MSYS limit', oversized)


def _agent_launch_output(streams, unavailable):
    for index, label in enumerate(('stdout', 'stderr')):
        try:
            if len(streams) != 2:
                detail = '[capture unavailable: ' + str(unavailable) + ']'
            else:
                streams[index].seek(0)
                raw = streams[index].read(8193)
                detail = raw[:8192].decode('utf-8', errors='replace')
                if len(raw) > 8192:
                    detail += '\n[truncated after 8192 bytes]'
        except Exception as error:
            detail = '[read unavailable: ' + type(error).__name__ + ']'
        try:
            print('gpgconf ' + label + ' snapshot:\n' + detail)
        except Exception:
            pass


def launch_agent(home):
    """Start the scratch agent once; retain bounded Windows/MSYS failure output."""
    if GPGCONF is None:
        return
    home_argument = spelled(home)
    msys_windows = os.name == 'nt' and home_argument.startswith('/') and gpg_style() == 'posix'
    streams, unavailable = [], None
    if msys_windows:
        _guard_msys_agent_sockets(home_argument)
        try:
            for _ in range(2):
                streams.append(tempfile.TemporaryFile(mode='w+b', dir=home))
        except Exception as error:
            unavailable = type(error).__name__
    try:
        try:
            launched = subprocess.run([GPGCONF, '--homedir', home_argument, '--launch', 'gpg-agent'], cwd=home, check=False,
                                      stdin=subprocess.DEVNULL, stdout=streams[0] if len(streams) == 2 else subprocess.DEVNULL,
                                      stderr=streams[1] if len(streams) == 2 else subprocess.DEVNULL, timeout=60)
        except BaseException:
            if msys_windows:
                try: _agent_launch_output(streams, unavailable)
                except Exception: pass
            raise
        if msys_windows and launched.returncode:
            try: _agent_launch_output(streams, unavailable)
            except Exception: pass
    finally:
        for stream in streams:
            try: stream.close()
            except Exception: pass
    assert launched.returncode == 0, ('GPG agent startup failed', GPG, GPGCONF, home, launched.returncode)


class Signer:
    """One scratch key in a short temporary home directory, deleted with it; never the user's."""

    def __init__(self, name, *, expire='never', at=None):
        # Short on purpose: the agent's socket path in the home has a length limit on macOS.
        self.home = Path(tempfile.mkdtemp(prefix='' if os.name == 'nt' else 'hs-'))
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

    def sign(self, data: bytes, *, at=None, armor=True) -> bytes:
        return self.produce(data, '--detach-sign', at=at, armor=armor)

    def produce(self, data: bytes, *flags, at=None, armor=True) -> bytes:
        """gpg's output over ``data`` for the given flags: a detached signature, or an inline or clearsigned message."""
        source, target = self.home / 'signed.bin', self.home / 'signed.out'
        source.write_bytes(data)
        faked = ('--faked-system-time', at) if at else self.faked
        run_gpg(self.home, *faked, '--passphrase', '', '--pinentry-mode', 'loopback', *(['--armor'] if armor else []),
                '--yes', '--output', spelled(target), *flags, spelled(source))
        return target.read_bytes()

    def block_with(self, other) -> str:
        """One armoured block, one BEGIN line, carrying this key's and another's public key."""
        (self.home / 'other.asc').write_text(other.public_key, encoding='ascii')
        run_gpg(self.home, '--import', spelled(self.home / 'other.asc'))
        target = self.home / 'both.asc'
        run_gpg(self.home, '--armor', '--yes', '--output', spelled(target), '--export', self.fingerprint, other.fingerprint)
        return target.read_bytes().decode('ascii')

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


def two_signatures_one_unlisted(w):
    # Both keys are in the keyring, through one block under a's fingerprint; b's signature is unlisted.
    a, b = w.signers('two-a'), w.signers('two-b')
    w.signature(a.sign(signing.signed_bytes(w.digest), armor=False) + b.sign(signing.signed_bytes(w.digest), armor=False))
    w.section['signers'] = [{'fingerprint': a.fingerprint, 'public_key': a.block_with(b)}]
    return signing.UNLISTED


def inline_signed(w):
    w.signature(w.signer.produce(signing.signed_bytes(w.digest), '--sign', armor=False))
    return signing.NOT_A_SIGNATURE


def clearsigned(w):
    w.signature(w.signer.produce(signing.signed_bytes(w.digest), '--clearsign'))
    return signing.NOT_A_SIGNATURE


def compressed_message(w):
    # gpg --store: a literal packet in a compressed one, no signature; refused before gpg runs.
    w.signature(w.signer.produce(b'\0' * 65_536, '--store', '-z', '9', armor=False))
    return signing.NOT_A_SIGNATURE


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
             two_signatures_one_unlisted, inline_signed, clearsigned, compressed_message, no_public_key,
             revoked_artifact, expired_key, revoked_key, secret_not_declared, time_beyond_declared]


BEFORE_CALL = [unsigned, stale_signature, unlisted_signer, revoked_artifact, revoked_key, secret_not_declared]


@pytest.fixture
def private_tempdir(monkeypatch):
    """A temporary directory of the test's own, made the default when the test calls it, and removed after.

    Never the shared one: another process's live verifier home shows there (an
    xdist worker, a second suite on the machine), and a glob of it failed on
    homes the test never made. Setting ``tempfile.tempdir`` covers every
    tempfile call the verifier could make its home with. Called after the
    signers exist, so their homes stay short and outside it.
    """
    private = Path(tempfile.mkdtemp(prefix='hs-tmp-'))

    def use():
        monkeypatch.setattr(tempfile, 'tempdir', str(private))
        return private
    yield use
    shutil.rmtree(private, ignore_errors=True)


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
    assert same_gpg(verifier['gpg']) and verifier['version'].startswith('gpg') and verifier['exit_status'] == 0
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
    assert result['extension']['plugin']['grant'] is not bindings['evidence']['grant']
    result['extension']['plugin']['grant']['time'] = 999  # a caller's edit never reaches the registry
    assert bindings['evidence']['grant'] == GRANT
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
def test_refused_at_enable(case, plugin, tmp_path, signers, condition, private_tempdir):
    w = World(case, plugin, tmp_path, signers)
    expected = condition(w)
    first = w.install()
    private = private_tempdir()
    with pytest.raises(FeatureUnavailable, match=re.escape(expected)):
        w.enable(first)
    assert ext.inspect_extension(w.directory)['status'] == 'disabled'
    with pytest.raises(FeatureUnavailable, match=re.escape(expected)):
        ext.catalog(w.section)
    assert not list(private.glob('harness-plugin-verify-*'))  # the private home is removed on a refusal too


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
    change(bundle, lambda d: d.update(grants={'time': 120, 'secrets': ['ONE'], 'paths': ['corpus'], 'scratch': False,
                                              'output': {'result': 100, 'diagnostics': 10}}))
    w = World(case, bundle, tmp_path, signers)
    first = w.install()
    for grant, expected in [({'time': 121}, ext.EXCESS_GRANT.format(name='time')),
                            ({'secrets': ['ONE', 'TWO']}, ext.EXCESS_GRANT.format(name='secrets')),
                            ({'paths': ['corpus', 'other']}, ext.EXCESS_GRANT.format(name='paths')),
                            ({'scratch': True}, ext.EXCESS_GRANT.format(name='scratch')),
                            ({'output': {'result': 101, 'diagnostics': 10}}, ext.EXCESS_GRANT.format(name='output')),
                            ({'output': {'result': 100, 'diagnostics': 11}}, ext.EXCESS_GRANT.format(name='output'))]:
        w.section['evidence']['grant'] = grant
        with pytest.raises(FeatureUnavailable, match=re.escape(expected)):
            w.enable(first)
    w.section['evidence']['grant'] = {'time': 120, 'secrets': ['ONE'], 'paths': ['corpus'], 'scratch': False,
                                      'output': {'result': 100, 'diagnostics': 10}}
    state = w.enable(first)
    assert state['plugin']['grant'] == w.section['evidence']['grant'] and state['plugin']['declares'] == {}
    state = ext.mutate(w.directory, state['state_digest'], 'disable')
    del w.section['evidence']['grant']
    assert w.enable(state)['plugin']['grant'] == {}  # nothing granted is a valid grant


@pytest.mark.parametrize('home,style', [('/c/Users/fixture/gnupg', 'posix'), ('C:/fixture/gnupg', 'native')])
def test_signer_setup_probe_has_own_budget(monkeypatch, tmp_path, home, style):
    """Slow instrumented fixture setup must not relax the production verifier deadline."""
    monkeypatch.setitem(globals(), 'STYLE', {})
    monkeypatch.setattr(signing, 'PROBED', {})
    monkeypatch.setenv('GNUPGHOME', str(tmp_path / 'never-open-this-keyring'))
    monkeypatch.setitem(globals(), 'GPG', 'fixture-gpg')
    calls = []

    def slow_probe(argv, prompt, **kwargs):
        calls.append((argv, kwargs))
        assert argv == ('fixture-gpg', '--batch', '--no-tty', '--no-options', '--version')
        assert prompt == '' and kwargs['cwd'].is_dir()
        assert kwargs['max_output_bytes'] == signing.VERIFIER_OUTPUT
        assert 'GNUPGHOME' not in kwargs['environment'] and kwargs['environment']['LC_ALL'] == 'C'
        if kwargs['timeout'] <= 10:
            return ProcessResult(argv, None, '', '', 'timeout_effects_unknown')
        return ProcessResult(argv, 0, f'gpg (GnuPG) fixture\nHome: {home}\n', '')

    monkeypatch.setitem(globals(), 'invoke', slow_probe)
    monkeypatch.setattr(signing, 'invoke', slow_probe)
    assert gpg_style() == gpg_style() == style
    assert len(calls) == 1 and calls[0][1]['timeout'] == 120
    assert not calls[0][1]['cwd'].exists()
    assert signing.PROBED == {}  # fixture setup does not pre-populate the actual verifier's cache
    assert signing.VERIFIER_TIMEOUT == 10
    with pytest.raises(FeatureUnavailable, match='timeout_effects_unknown'):
        signing.probe_gpg('fixture-gpg', tmp_path)
    assert len(calls) == 2 and calls[1][1]['timeout'] == 10
    assert not (tmp_path / 'never-open-this-keyring').exists()


@pytest.mark.parametrize('failure,stdout,returncode', [
    ('timeout_effects_unknown', '', None), (None, 'not a GPG version', 0), ('nonzero_exit', '', 2),
])
def test_signer_setup_probe_refuses_failure_without_caching(monkeypatch, failure, stdout, returncode):
    monkeypatch.setitem(globals(), 'STYLE', {})
    monkeypatch.setattr(signing, 'PROBED', {})
    homes = []

    def failed_probe(argv, prompt, **kwargs):
        homes.append(kwargs['cwd'])
        return ProcessResult(argv, returncode, stdout, '', failure)

    monkeypatch.setitem(globals(), 'invoke', failed_probe)
    monkeypatch.setattr(signing, 'invoke', failed_probe)
    with pytest.raises(AssertionError):
        gpg_style()
    assert STYLE == signing.PROBED == {}
    assert len(homes) == 1 and not homes[0].exists()


def test_gpg_absent_from_path_is_a_named_refusal(case, plugin, tmp_path, signers, monkeypatch):
    w = World(case, plugin, tmp_path, signers)
    first = w.install()
    empty = tmp_path / 'no-gpg'
    empty.mkdir()
    monkeypatch.setenv('PATH', str(empty))
    monkeypatch.setattr(signing, 'known_gpg_locations', lambda: [])
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
    (ProcessResult(('gpg',), 0, '[GNUPG:] NEWSIG\n[GNUPG:] GOODSIG 0123456789ABCDEF Someone\n', '', None), signing.NO_VERDICT),
    (ProcessResult(('gpg',), 2, '', 'gpg: fatal', 'nonzero_exit'), signing.NO_VERDICT),
    (ProcessResult(('gpg',), 2, '[GNUPG:] FAILURE gpg-exit 33554434\n', 'not a detached signature', 'nonzero_exit'),
     signing.NOT_A_SIGNATURE),
], ids=['launch_failed', 'timeout', 'exit_0_silent', 'goodsig_without_validsig', 'exit_2_silent', 'failure_without_newsig'])
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
    assert signing.verdict([['NEWSIG'], good, ['VALIDSIG', other, '2026-09-23', '1', '0', '4', '0', '22', '10', '00', fpr]], {fpr}) == fpr
    for lines, refusal in [
        ([['NEWSIG'], good, valid], signing.UNLISTED),
        ([['NEWSIG'], good, valid, ['NEWSIG'], good, ['VALIDSIG', other, '2026-09-23', '1', '0', '4', '0', '22', '10', '00', other]],
         signing.UNLISTED),
        ([good, valid], signing.NOT_A_SIGNATURE),  # gpg reported without checking a signature
        ([['FAILURE', 'gpg-exit', '33554434']], signing.NOT_A_SIGNATURE),
        ([['NEWSIG'], ['KEYEXPIRED', '1577836860'], ['EXPKEYSIG', fpr[-16:], 'x'], valid], signing.EXPIRED_KEY),
        ([['REVKEYSIG', fpr[-16:], 'x'], valid, ['KEYREVOKED']], signing.REVOKED_KEY),
        ([good, valid, ['EXPSIG', fpr[-16:], 'x']], signing.EXPIRED_SIGNATURE),
        ([['BADSIG', fpr[-16:], 'x']], signing.TAMPERED),
        ([['ERRSIG', fpr[-16:], '22', '10', '00', '1', '9', fpr], ['NO_PUBKEY', fpr[-16:]]], signing.NO_PUBKEY),
        ([['ERRSIG', fpr[-16:], '22', '10', '00', '1', '4', fpr]], signing.SIGNATURE_ERROR),
        ([['NODATA', '1'], ['NODATA', '2']], signing.NOT_A_SIGNATURE),
        # A good signature followed by junk: gpg reports NODATA after the verdict lines, and that refuses
        # on its own, although the packet walk stops such a file before gpg runs.
        ([['NEWSIG'], good, valid, ['NODATA', '1']], signing.NOT_A_SIGNATURE),
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
    # Status lines are split on newlines only: a user ID may carry U+2028 (finding 7).
    parsed = signing._status('[GNUPG:] GOODSIG 0123456789ABCDEF x\u2028[GNUPG:] KEYEXPIRED 1\n[GNUPG:] NEWSIG\n')
    assert [tokens[0] for tokens in parsed] == ['GOODSIG', 'NEWSIG']


def test_only_definite_signature_packets_reach_gpg(signer, monkeypatch):
    """Finding 1: a compressed message inside the 16 KiB bound cost 27 s of gpg on every check."""
    digest = 'a' * 64
    data = signing.signed_bytes(digest)
    armoured, binary = signer.sign(data), signer.sign(data, armor=False)
    assert signing.signature_packets(armoured) == 1 and signing.signature_packets(binary) == 1
    assert signing.signature_packets(binary + binary) == 2
    stored = signer.produce(b'\0' * 65_536, '--store', '-z', '9', armor=False)
    refused = [stored, signer.produce(data, '--sign', armor=False), signer.produce(data, '--sign'),
               signer.produce(data, '--clearsign'),
               bytes([0xC8, 0x05, 0x01, 0x78, 0x9C, 0x03, 0x00]),  # a compressed packet, new format
               bytes([0xCB, 0x03, 0x62, 0x00, 0x00]),  # a literal packet
               bytes([0xC2, 0xE0]) + b'x' * 32,  # a signature packet with a partial body length
               bytes([0x8B]) + b'x' * 8,  # an old-format signature packet of indeterminate length
               bytes([0xCA, 0x03]) + b'PGP' + binary,  # a marker packet before a real signature
               binary[:-1],  # a truncated signature
               b'', b'\x00', b'-----BEGIN PGP SIGNATURE-----\n\n!!!!\n-----END PGP SIGNATURE-----\n']
    monkeypatch.setattr(signing, 'invoke', lambda *a, **k: pytest.fail('gpg ran for a file that is not a detached signature'))
    for raw in refused:
        with pytest.raises(FeatureUnavailable, match=re.escape(signing.NOT_A_SIGNATURE)):
            signing.signature_packets(raw)
    started = time.perf_counter()
    outcome = signing.inspect_signature(digest, stored, [signer.entry])
    assert outcome['refusal'] == signing.NOT_A_SIGNATURE and outcome['verifier']['gpg'] is None
    assert time.perf_counter() - started < 1.0


@pytest.mark.parametrize('form', ['binary', 'armour', 'crlf', 'headers', 'no-crc', 'outer-space'])
def test_gpg_reads_exactly_the_validated_signature_bytes(signer, monkeypatch, form):
    """A real verdict and the subprocess file must use the entire packet guard's buffer."""
    digest = 'a' * 64
    armoured = signer.sign(signing.signed_bytes(digest)).replace(b'\r\n', b'\n')
    payload = armoured.split(b'\n\n', 1)[1].split(b'\n=', 1)[0]
    binary = base64.b64decode(payload)
    forms = {
        'binary': binary,
        'armour': armoured,
        'crlf': armoured.replace(b'\n', b'\r\n'),
        'headers': armoured.replace(b'\n\n', b'\nVersion: Harness test\nComment: byte binding\n\n', 1),
        'no-crc': b'\n'.join(line for line in armoured.split(b'\n') if not line.startswith(b'=')),
        'outer-space': b' \t\r\n' + armoured + b'\r\n \t',
    }
    guarded, received = [], []
    real_guard, real_invoke = signing.signature_packets, signing.invoke

    def guard(raw):
        guarded.append(raw)
        return real_guard(raw)

    def spy(argv, prompt, **kwargs):
        if '--verify' in argv:
            received.append((kwargs['cwd'] / signing.SIGNATURE_NAME).read_bytes())
        return real_invoke(argv, prompt, **kwargs)

    monkeypatch.setattr(signing, 'signature_packets', guard)
    monkeypatch.setattr(signing, 'invoke', spy)
    outcome = signing.inspect_signature(digest, forms[form], [signer.entry])
    assert outcome['refusal'] is None and outcome['signer'] == signer.fingerprint
    assert outcome['verifier']['packets'] == 1
    assert guarded == received == [binary]


@pytest.mark.parametrize('case', [
    'message-tail', 'second-signature', 'raw-tail', 'leading-message', 'end-before-begin',
    'duplicate-end', 'damaged-begin', 'damaged-end', 'missing-end', 'missing-separator',
    'invalid-header', 'non-ascii', 'non-ascii-header',
    'unicode-line-break', 'invalid-base64', 'base64-after-padding', 'bad-crc', 'short-crc',
    'duplicate-crc', 'crc-before-payload', 'near-bound-tail',
])
def test_malformed_or_extra_armour_is_refused_before_gpg(monkeypatch, case):
    """New fixtures reproduce #118's seam without expanding a compressed message."""
    begin, end = b'-----BEGIN PGP SIGNATURE-----', b'-----END PGP SIGNATURE-----'
    # A structurally valid Signature packet, not a cryptographic claim.
    binary = b'\xc2\x09' + b'123456789'
    payload = base64.b64encode(binary)
    armour = begin + b'\n\n' + payload + b'\n' + end + b'\n'
    message = b'-----BEGIN PGP MESSAGE-----\n\nyAAD\n-----END PGP MESSAGE-----\n'
    cases = {
        'message-tail': armour + message,
        'second-signature': armour + armour,
        'raw-tail': armour + binary,
        'leading-message': message + armour,
        'end-before-begin': end + b'\n' + armour,
        'duplicate-end': armour + end + b'\n',
        'damaged-begin': armour.replace(begin, begin + b'x'),
        'damaged-end': armour.replace(end, end + b'x'),
        'missing-end': armour.replace(end, b''),
        'missing-separator': armour.replace(b'\n\n', b'\n'),
        'invalid-header': armour.replace(b'\n\n', b'\nnot a header\n\n'),
        'non-ascii': armour.replace(payload, payload + b'\xff'),
        'non-ascii-header': armour.replace(b'\n\n', b'\nComment: caf\xc3\xa9\n\n'),
        'unicode-line-break': armour.replace(b'\n\n', b'\xe2\x80\xa8\n\n'),
        'invalid-base64': armour.replace(payload, payload + b'!'),
        'base64-after-padding': armour.replace(payload, payload + b'AAAA'),
        'bad-crc': armour.replace(end, b'=AAAA\n' + end),
        'short-crc': armour.replace(end, b'=AAA\n' + end),
        'duplicate-crc': armour.replace(end, b'=AAAA\n=AAAA\n' + end),
        'crc-before-payload': armour.replace(b'\n\n', b'\n\n=AAAA\n'),
        'near-bound-tail': armour + b'x' * (signing.SIGNATURE_LIMIT - len(armour)),
    }
    raw = cases[case]
    assert len(raw) <= signing.SIGNATURE_LIMIT
    monkeypatch.setattr(signing, 'find_gpg', lambda: pytest.fail('GPG discovery ran for malformed armor'))
    monkeypatch.setattr(signing, 'invoke', lambda *a, **k: pytest.fail('GPG ran for malformed armor'))
    outcome = signing.inspect_signature('a' * 64, raw, [FAKE_ENTRY])
    assert outcome['refusal'] == signing.NOT_A_SIGNATURE
    assert outcome['verifier']['gpg'] is None
    with pytest.raises(FeatureUnavailable, match=re.escape(signing.NOT_A_SIGNATURE)):
        signing.signature_packets(raw)


def test_armour_crc24_known_vector_and_optional_footer():
    """Check CRC24 against the published vector, independently of GPG's encoder."""
    assert signing._crc24(b'123456789') == 0x21CF02
    assert signing._crc24(b'') == 0xB704CE
    binary = b'\xc2\x09' + b'123456789'
    encoded = base64.b64encode(binary)
    armour = b'-----BEGIN PGP SIGNATURE-----\n\n' + encoded + b'\n-----END PGP SIGNATURE-----\n'
    assert signing.dearmour(armour) == binary
    assert signing.signature_packets(binary) == 1


def test_signature_file_bounds(case, plugin, tmp_path, signers):
    """Finding 2: the symlink refusal and the 16 KiB bound on artifact.sig."""
    w = World(case, plugin, tmp_path, signers)
    first = w.install()
    path = w.manifest.parent / signing.SIGNATURE_NAME
    path.write_bytes(b'x' * (signing.SIGNATURE_LIMIT + 1))
    with pytest.raises(ValueError, match='exceeds its limit of 16384 bytes; it is 16385 bytes'):
        w.enable(first)
    path.write_bytes(b'x' * signing.SIGNATURE_LIMIT)  # within the bound: read, then refused as not a signature
    with pytest.raises(FeatureUnavailable, match=re.escape(signing.NOT_A_SIGNATURE)):
        w.enable(first)
    real = w.signer.sign(signing.signed_bytes(w.digest))
    (w.manifest.parent / 'elsewhere.sig').write_bytes(real)
    path.unlink()
    try:
        path.symlink_to(w.manifest.parent / 'elsewhere.sig')
    except OSError as error:  # Windows without the symlink privilege (Windows traps): the bound above still holds
        path.write_bytes(real)
        assert os.name == 'nt', error
    else:
        with pytest.raises(ValueError, match='artifact.sig cannot be a symlink'):
            w.enable(first)
        path.unlink()
        path.write_bytes(real)
    assert w.enable(first)['status'] == 'enabled'


def test_declares_only_bundle_is_a_plugin_that_needs_a_signature(case, bundle, tmp_path, signers):
    """Finding 2: either capability field makes a plugin; R1 covers a declares-only bundle."""
    change(bundle, lambda d: d.update(declares={'network': ['api.example.com']}))
    assert ext.is_plugin(ext.discover(bundle)['declaration'])
    w = World(case, bundle, tmp_path, signers)
    del w.section['evidence']['grant']
    first = w.install()
    (w.manifest.parent / signing.SIGNATURE_NAME).unlink()
    with pytest.raises(FeatureUnavailable, match=re.escape(signing.UNSIGNED)):
        w.enable(first)
    with pytest.raises(FeatureUnavailable, match=re.escape(ext.PLUGIN_NEEDS_REGISTRY)):
        ext.mutate(w.directory, first['state_digest'], 'enable')
    sign_bundle(w.manifest, w.signer)
    state = w.enable(first)
    assert state['plugin']['declares'] == {'network': ['api.example.com']} and state['plugin']['grant'] == {}


def test_known_install_locations_are_searched_after_path(case, plugin, tmp_path, signers, monkeypatch):
    """Finding 12: the fallback past PATH, and finding 6: a present gpg that cannot run is named."""
    w = World(case, plugin, tmp_path, signers)
    first = w.install()
    empty = tmp_path / 'no-gpg'
    empty.mkdir()
    monkeypatch.setenv('PATH', str(empty))
    monkeypatch.setattr(signing, 'known_gpg_locations', lambda: [str(tmp_path / 'missing-gpg'), GPG])
    monkeypatch.setattr(signing, 'PROBED', {})
    assert signing.find_gpg() == (GPG, ['PATH', str(tmp_path / 'missing-gpg'), GPG])
    state = w.enable(first)
    assert state['plugin']['verifier']['gpg'] == GPG
    stub = empty / 'gpg'
    stub.write_text('#!/bin/sh\necho hi\n', encoding='utf-8')
    os.chmod(stub, 0o644)
    monkeypatch.setattr(signing, 'known_gpg_locations', lambda: [])
    if os.name == 'nt':
        # A Windows executable needs an extension, so a bare gpg file is no candidate: absent, not unrunnable.
        assert signing.find_gpg() == (None, ['PATH'])
    else:
        with pytest.raises(FeatureUnavailable) as refused:
            signing.find_gpg()
        assert str(refused.value) == signing.GPG_NOT_EXECUTABLE.format(path=str(stub))
    monkeypatch.setattr(signing, 'known_gpg_locations', lambda: [GPG])
    assert signing.find_gpg() == (GPG, ['PATH', GPG])  # a present but unusable gpg does not stop the search


def test_state_with_a_plugin_receipt_must_be_enabled(case, plugin, tmp_path, signers):
    """Finding 12 (M40): a plugin block on a disabled or removed state is not a valid state."""
    from attune_harness.review_contract import digest as state_digest
    w = World(case, plugin, tmp_path, signers)
    state = w.enable(w.install())
    for status in ('disabled', 'removed'):
        broken = {**{k: v for k, v in state.items() if k != 'state_digest'}, 'status': status}
        broken['state_digest'] = state_digest(broken)
        (w.directory / 'record.json').write_text(json.dumps(broken), encoding='utf-8')
        with pytest.raises(ValueError, match='Unsupported extension state'):
            ext.inspect_extension(w.directory)


def test_verifier_home_is_private_built_from_the_registry_and_removed(case, plugin, tmp_path, signers, monkeypatch):
    w = World(case, plugin, tmp_path, signers)
    seen = []
    real = signing.invoke

    def spy(argv, prompt, **kwargs):
        home = kwargs['cwd']
        assert '--no-options' in argv  # the invoking user's option files play no part (finding 3)
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
    assert verified['signer'] == w.signer.fingerprint and same_gpg(verified['verifier']['gpg'])
    assert [argv[-1] if '--version' in argv else argv[argv.index('--status-fd') + 2] for argv, _, _ in seen] == [
        '--version', '--import', '--verify']
    assert verified['verifier']['path_style'] == gpg_style()
    for argv, kwargs, home in seen:
        assert same_gpg(argv[0]) and os.path.isabs(argv[0])
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
    ('grants', {'secrets': ['PATH']}, 'host sets itself: PATH'),
    ('grants', {'secrets': ['systemroot']}, 'host sets itself: systemroot'),
    ('grants', {'secrets': ['PYTHONNOUSERSITE']}, 'host sets itself'),
    ('id', 'signers', 'Reserved extension identity'),
    ('id', 'revoked', 'Reserved extension identity'),
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
    ({'signers': [{'fingerprint': 'A' * 40, 'public_key': FAKE_ENTRY['public_key'] * 2}]}, 'one ASCII-armoured'),
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


@pytest.mark.parametrize('form,companion', [(None, None), ('absolute', None), ('absolute', 'paired-gpgconf'),
                                           ('relative', 'paired-gpgconf'), ('basename', 'paired-gpgconf')])
def test_signer_companion_uses_explicit_sibling(monkeypatch, tmp_path, form, companion):
    monkeypatch.chdir(tmp_path)
    selected = {None: None, 'absolute': str(tmp_path / 'GPG Tools' / 'gpg.exe'),
                'relative': str(Path('GPG Tools') / 'gpg.exe'), 'basename': 'gpg.exe'}[form]
    expected = str(tmp_path / 'gpgconf') if form == 'basename' else str(tmp_path / 'GPG Tools' / 'gpgconf')
    calls = []
    monkeypatch.setenv('PATH', str(tmp_path / 'unrelated-tools'))
    monkeypatch.setattr(shutil, 'which', lambda command: calls.append(command) or companion)
    assert _gpg_companion(selected) == companion
    assert calls == ([expected] if selected is not None else [])
    if companion is None:
        monkeypatch.setitem(globals(), 'GPGCONF', None)
        monkeypatch.setattr(subprocess, 'run', lambda *a, **kw: pytest.fail('optional startup dispatched'))
        assert launch_agent(tmp_path) is None


def test_signer_companion_ignores_unrelated_cwd_and_path(monkeypatch, tmp_path):
    selected, unrelated = tmp_path / 'GPG Tools', tmp_path / 'unrelated-tools'
    name = 'gpgconf.exe' if os.name == 'nt' else 'gpgconf'
    for directory in (selected, unrelated):
        directory.mkdir()
        marker = directory / name
        marker.write_text('synthetic lookup marker; never execute')
        marker.chmod(0o700)
    monkeypatch.chdir(unrelated)
    monkeypatch.setenv('PATH', str(unrelated))
    assert Path(_gpg_companion(str(selected / 'gpg.exe'))) == selected / name


@pytest.mark.parametrize('returncode', [0, 2])
def test_signer_agent_startup_gates_key_generation(monkeypatch, tmp_path, returncode):
    home = tmp_path / 'synthetic-signer'
    home.mkdir()
    monkeypatch.setattr(tempfile, 'mkdtemp', lambda **kw: str(home))
    monkeypatch.setitem(globals(), 'GPG', 'selected-gpg')
    monkeypatch.setitem(globals(), 'GPGCONF', 'paired-gpgconf')
    monkeypatch.setitem(globals(), 'spelled', str)
    calls, keys = [], []
    monkeypatch.setattr(subprocess, 'run', lambda argv, **kw: calls.append((argv, kw)) or subprocess.CompletedProcess(argv, returncode))
    monkeypatch.setitem(globals(), 'run_gpg', lambda *a: keys.append(a) or ProcessResult((), 0, '[GNUPG:] KEY_CREATED B ABC\n', ''))
    monkeypatch.setattr(Signer, '_export', lambda self: 'synthetic-public-key')
    if returncode:
        with pytest.raises(AssertionError, match='GPG agent startup failed'):
            Signer('synthetic')
    else:
        assert Signer('synthetic').fingerprint == 'ABC'
    assert len(keys) == (0 if returncode else 1)
    assert calls == [(['paired-gpgconf', '--homedir', str(home), '--launch', 'gpg-agent'],
                     {'cwd': home, 'check': False, 'stdin': subprocess.DEVNULL,
                      'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL, 'timeout': 60})]


@pytest.mark.parametrize('home,accepted', [
    ('/d/a/_temp/coverage-result-runtime/harness-installed-coverage-qzyq51_x/0-temp/hs-pgwrnlf2', False),
    ('/d/a/_temp/coverage-result-runtime/harness-installed-coverage-qzyq51_x/0-temp/pgwrnlf2', True),
    ('/' + 'a' * 85, True), ('/' + 'a' * 86, False),
    ('/' + 'a' * 83 + 'é', True), ('/' + 'a' * 84 + 'é', False)])
def test_msys_agent_socket_guard_counts_full_utf8_paths(home, accepted):
    if accepted:
        assert _guard_msys_agent_sockets(home) is None
    else:
        with pytest.raises(AssertionError, match='GPG agent socket paths exceed MSYS limit'):
            _guard_msys_agent_sockets(home)


@pytest.fixture
def synthetic_msys_agent(tmp_path, monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setitem(globals(), 'os', SimpleNamespace(name='nt', chmod=os.chmod))
    monkeypatch.setitem(globals(), 'GPG', 'selected-gpg')
    monkeypatch.setitem(globals(), 'GPGCONF', 'paired-gpgconf')
    monkeypatch.setitem(globals(), 'spelled', lambda _path: '/d/fixture')
    monkeypatch.setitem(globals(), 'STYLE', {'style': 'posix'})
    return tmp_path


@pytest.mark.parametrize('system,argument,guarded,rejected', [
    ('posix', '/' + 'a' * 100, False, False), ('nt', 'C:/native-home', False, False),
    ('nt', '/d/fixture', True, False), ('nt', '/' + 'a' * 87, True, True)])
def test_agent_socket_guard_and_capture_apply_only_to_windows_msys(
        synthetic_msys_agent, monkeypatch, system, argument, guarded, rejected):
    from types import SimpleNamespace
    monkeypatch.setitem(globals(), 'os', SimpleNamespace(name=system))
    monkeypatch.setitem(globals(), 'spelled', lambda _path: argument)
    checked, calls = [], []
    guard = _guard_msys_agent_sockets
    monkeypatch.setitem(globals(), '_guard_msys_agent_sockets', lambda path: checked.append(path) or guard(path))
    monkeypatch.setattr(subprocess, 'run', lambda argv, **kw: calls.append(kw) or subprocess.CompletedProcess(argv, 0))
    if rejected:
        with pytest.raises(AssertionError, match='MSYS limit'): launch_agent(synthetic_msys_agent)
    else:
        assert launch_agent(synthetic_msys_agent) is None
    assert checked == ([argument] if guarded else [])
    assert len(calls) == (0 if rejected else 1)
    if calls:
        assert calls[0]['stdin'] == subprocess.DEVNULL and calls[0]['timeout'] == 60
        assert calls[0]['cwd'] == synthetic_msys_agent and calls[0]['check'] is False
        for label in ('stdout', 'stderr'):
            assert (calls[0][label] != subprocess.DEVNULL) == guarded
            assert calls[0][label] != subprocess.PIPE


@pytest.mark.parametrize('system,prefix', [('nt', ''), ('posix', 'hs-')])
def test_signer_keeps_tempfile_parent_and_shortens_only_windows_name(tmp_path, monkeypatch, system, prefix):
    from types import SimpleNamespace
    home = tmp_path / 'owned-home'; home.mkdir()
    monkeypatch.setitem(globals(), 'os', SimpleNamespace(name=system, chmod=os.chmod))
    calls = []
    monkeypatch.setattr(tempfile, 'mkdtemp', lambda **kw: calls.append(kw) or str(home))
    monkeypatch.setitem(globals(), 'launch_agent', lambda _home: None)
    monkeypatch.setitem(globals(), 'run_gpg', lambda *a: ProcessResult((), 0, '[GNUPG:] KEY_CREATED B ABC\n', ''))
    monkeypatch.setattr(Signer, '_export', lambda self: 'synthetic-public-key')
    assert Signer('synthetic').home == home
    assert calls == [{'prefix': prefix}]


@pytest.mark.parametrize('outcome', ['zero', 'nonzero', 'timeout', 'interrupt', 'exit'])
def test_agent_launch_retains_bounded_output_and_original_outcome(synthetic_msys_agent, monkeypatch, capsys, outcome):
    errors = {'timeout': subprocess.TimeoutExpired(['paired-gpgconf'], 60),
              'interrupt': KeyboardInterrupt(), 'exit': SystemExit(7)}
    calls = []
    def native(argv, **kw):
        calls.append((argv, kw))
        kw['stdout'].write(b'out-marker' + b'X' * 8192 + b'EXCESS_SENTINEL')
        kw['stderr'].write(b'err-marker')
        if outcome in errors: raise errors[outcome]
        return subprocess.CompletedProcess(argv, 0 if outcome == 'zero' else 1)
    monkeypatch.setattr(subprocess, 'run', native)
    if outcome in errors:
        with pytest.raises(type(errors[outcome])) as caught: launch_agent(synthetic_msys_agent)
        assert caught.value is errors[outcome]
    elif outcome == 'nonzero':
        with pytest.raises(AssertionError, match='GPG agent startup failed'): launch_agent(synthetic_msys_agent)
    else:
        assert launch_agent(synthetic_msys_agent) is None
    output = capsys.readouterr().out
    assert len(calls) == 1
    assert calls[0][0] == ['paired-gpgconf', '--homedir', '/d/fixture', '--launch', 'gpg-agent']
    if outcome == 'zero': assert output == ''
    else:
        assert 'gpgconf stdout snapshot:\nout-marker' in output and 'err-marker' in output
        assert '[truncated after 8192 bytes]' in output and 'EXCESS_SENTINEL' not in output
    assert all(calls[0][1][label].closed for label in ('stdout', 'stderr'))


@pytest.mark.parametrize('fault', ['open', 'read', 'close', 'emit'])
def test_agent_capture_faults_cannot_replace_native_error(synthetic_msys_agent, monkeypatch, fault):
    original = subprocess.TimeoutExpired(['paired-gpgconf'], 60)
    factory = tempfile.TemporaryFile
    class Capture:
        def __init__(self, backing): self.backing = backing
        def __getattr__(self, name): return getattr(self.backing, name)
        def read(self, count):
            if fault == 'read': raise OSError('synthetic diagnostic read')
            return self.backing.read(count)
        def close(self):
            self.backing.close()
            if fault == 'close': raise OSError('synthetic diagnostic close')
    def capture(**kwargs):
        if fault == 'open': raise OSError('synthetic diagnostic open')
        return Capture(factory(**kwargs))
    monkeypatch.setattr(tempfile, 'TemporaryFile', capture)
    if fault == 'emit':
        def broken_print(*_args, **_kwargs): raise OSError('synthetic diagnostic emit')
        monkeypatch.setitem(globals(), 'print', broken_print)
    calls = []
    def native(*args, **kwargs):
        calls.append((args, kwargs))
        raise original
    monkeypatch.setattr(subprocess, 'run', native)
    with pytest.raises(subprocess.TimeoutExpired) as caught: launch_agent(synthetic_msys_agent)
    assert caught.value is original and len(calls) == 1
    if fault == 'open':
        assert calls[0][1]['stdout'] == calls[0][1]['stderr'] == subprocess.DEVNULL


@pytest.mark.parametrize('argument', ['//server/share/home', '//server/share/' + 'a' * 100])
def test_native_unc_agent_home_keeps_original_launch_route(synthetic_msys_agent, monkeypatch, argument):
    monkeypatch.setitem(globals(), 'STYLE', {'style': 'native'})
    monkeypatch.setitem(globals(), 'spelled', lambda _home: argument)
    monkeypatch.setitem(globals(), 'invoke', lambda *a, **kw: pytest.fail('cached style dispatched a probe'))
    monkeypatch.setitem(globals(), '_guard_msys_agent_sockets', lambda _home: pytest.fail('native UNC reached MSYS guard'))
    monkeypatch.setattr(tempfile, 'TemporaryFile', lambda **kw: pytest.fail('native UNC opened MSYS capture'))
    calls = []
    monkeypatch.setattr(subprocess, 'run', lambda argv, **kw: calls.append((argv, kw)) or subprocess.CompletedProcess(argv, 0))
    assert launch_agent(synthetic_msys_agent) is None
    assert calls == [(['paired-gpgconf', '--homedir', argument, '--launch', 'gpg-agent'],
                     {'cwd': synthetic_msys_agent, 'check': False, 'stdin': subprocess.DEVNULL,
                      'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL, 'timeout': 60})]
