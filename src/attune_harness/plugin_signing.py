"""Detached-signature verification for plugin bundles: gpg against the registry's keys only.

The signed bytes are the artifact digest's 64 lowercase hexadecimal characters,
ASCII, with no newline; the signature is the file ``artifact.sig`` beside the
manifest, a detached OpenPGP signature, armoured or binary. Verification runs
``gpg --verify`` through ``process.invoke``, bounded, in a private home
directory the host creates for the call with mode 0700 and removes after it,
with a keyring built from the accepted registry's public key blocks and
nothing else: the user's own keyring, options and agent play no part. The
verdict is read from the ``--status-fd`` lines alone, never from the exit
status, which gpg sets to 0 for a signature by an expired or a revoked key
(executable plugins spec, trust model; D22.1). ``gpg`` is found on PATH first
and then at the known install locations, Git for Windows' among them, and
every receipt records the path used and the version line (D29.1). No
dependency is added.
"""

import os
import re
import shutil
import tempfile
from pathlib import Path

from .features import OVERSIZE, FeatureUnavailable
from .process import invoke

SIGNATURE_NAME = "artifact.sig"
SIGNATURE_LIMIT = 16_384
KEY_BLOCK_LIMIT = 16_384
VERIFIER_TIMEOUT = 30
VERIFIER_OUTPUT = 65_536
FINGERPRINT = r"[A-F0-9]{40}"
KEY_BLOCK_BEGIN = "-----BEGIN PGP PUBLIC KEY BLOCK-----"
KEY_BLOCK_END = "-----END PGP PUBLIC KEY BLOCK-----"
# Where gpg is looked for after PATH, in order. Git for Windows ships gpg.exe
# under usr\bin, outside the default PATH of a service or a runner step; the
# Windows tails are joined to each Program Files root the environment names.
KNOWN_GPG_WINDOWS = (r"Git\usr\bin\gpg.exe", r"Git\mingw64\bin\gpg.exe", r"GnuPG\bin\gpg.exe")
KNOWN_GPG_POSIX = ("/usr/bin/gpg", "/usr/local/bin/gpg", "/opt/homebrew/bin/gpg")

# What the receipt says a signature means, and what a declaration is.
SIGNATURE_SCOPE = (
    "This exact bundle, manifest and skill, was reviewed by the signer under the brief; "
    "not that it is safe in general"
)
DECLARATIONS_SCOPE = "Recorded and not enforced; the host enforces the grant only"

# Refusals, each what happened and a plain next action (D20.1 style).
UNSIGNED = (
    "Plugin bundle carries no signature; sign its artifact digest with a listed key and "
    "write artifact.sig beside the manifest"
)
NOT_A_SIGNATURE = (
    "Plugin artifact.sig is not a detached signature; sign the artifact digest again and "
    "write artifact.sig beside the manifest"
)
UNLISTED = (
    "Plugin signature was made by a key the registry does not list; list that key under "
    "signers or sign with a listed key"
)
NO_PUBKEY = (
    "Plugin signature names a key with no public key in the registry; list its key block "
    "under signers or sign with a listed key"
)
TAMPERED = (
    "Plugin artifact changed after it was signed; review the bundle again and sign its "
    "current artifact digest"
)
GPG_ABSENT = (
    "gpg is absent from PATH and from the known install locations ({searched}), so the "
    "plugin signature cannot be verified; install GnuPG and put gpg on PATH"
)
VERIFIER_FAILED = "Plugin signature verifier failed to run ({failure}); check the gpg installation"
NO_VERDICT = (
    "Plugin signature verifier reported no verdict; check the gpg installation and sign "
    "the artifact digest again"
)
KEY_IMPORT = (
    "Plugin signature verifier could not import a registry key block; check the "
    "public_key entries under signers"
)
EXPIRED_KEY = (
    "Plugin signature was made by a key that has expired; rotate the signer in the "
    "registry and sign again"
)
REVOKED_KEY = (
    "Plugin signature was made by a key that has been revoked; remove that signer from "
    "the registry and sign with a listed key"
)
EXPIRED_SIGNATURE = "Plugin signature has expired; sign the artifact digest again"
SIGNATURE_ERROR = (
    "Plugin signature could not be checked by gpg; sign the artifact digest again "
    "with a listed key"
)

# Status keywords that refuse, in the order they are reported when several appear.
REFUSING_STATUS = (
    ("REVKEYSIG", REVOKED_KEY),
    ("EXPKEYSIG", EXPIRED_KEY),
    ("EXPSIG", EXPIRED_SIGNATURE),
    ("BADSIG", TAMPERED),
    ("NO_PUBKEY", NO_PUBKEY),
    ("ERRSIG", SIGNATURE_ERROR),
    ("NODATA", NOT_A_SIGNATURE),
)
# invoke outcomes that still carry gpg's status lines; anything else is the verifier not running.
REPORTED = (None, "nonzero_exit", "invalid_utf8")


def signed_bytes(artifact_digest: str) -> bytes:
    """The exact bytes a signer signs: the digest's 64 lowercase hex characters, no newline."""
    if not isinstance(artifact_digest, str) or not re.fullmatch(r"[a-f0-9]{64}", artifact_digest):
        raise ValueError("Expected a SHA-256 digest")
    return artifact_digest.encode("ascii")


def read_signature(directory: Path) -> bytes:
    """The bundle's detached signature, bounded and never through a symlink."""
    path = directory / SIGNATURE_NAME
    if path.is_symlink():
        raise ValueError("Plugin artifact.sig cannot be a symlink")
    if not path.is_file():
        raise FeatureUnavailable(UNSIGNED)
    with path.open("rb") as stream:
        raw = stream.read(SIGNATURE_LIMIT + 1)
        if len(raw) > SIGNATURE_LIMIT:
            size = max(os.fstat(stream.fileno()).st_size, len(raw))
            raise ValueError(
                f"{OVERSIZE} of {SIGNATURE_LIMIT} bytes; it is {size} bytes: {path}. "
                "It was refused whole. Harness never shortens an input to fit."
            )
    return raw


def find_gpg():
    """The gpg to run, PATH first and then the known install locations; and what was searched."""
    searched = ["PATH"]
    found = shutil.which("gpg")
    if found:
        return found, searched
    if os.name == "nt":
        roots = []
        for variable in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
            value = os.environ.get(variable)
            if value and value not in roots:
                roots.append(value)
        for fallback in (r"C:\Program Files", r"C:\Program Files (x86)"):
            if fallback not in roots:
                roots.append(fallback)
        candidates = [os.path.join(root, tail) for root in roots for tail in KNOWN_GPG_WINDOWS]
    else:
        candidates = list(KNOWN_GPG_POSIX)
    for candidate in candidates:
        searched.append(candidate)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate, searched
    return None, searched


def _environment() -> dict:
    # The verifier sees PATH and a C locale only, plus what Windows needs to run
    # anything; never GNUPGHOME or another pointer at the user's keyring.
    names = ("PATH", "SystemRoot", "TEMP", "TMP") if os.name == "nt" else ("PATH",)
    environment = {name: os.environ[name] for name in names if os.environ.get(name)}
    environment.update(LANG="C", LC_ALL="C")
    return environment


def _run(argv: tuple, home: Path):
    result = invoke(
        argv,
        "",
        cwd=home,
        timeout=VERIFIER_TIMEOUT,
        max_output_bytes=VERIFIER_OUTPUT,
        environment=_environment(),
    )
    if result.failure not in REPORTED:
        raise FeatureUnavailable(VERIFIER_FAILED.format(failure=result.failure))
    return result


def _status(stdout: str) -> list:
    """gpg's status lines as token lists, keyword first; everything else on stdout is ignored."""
    lines = []
    for line in stdout.splitlines():
        if line.startswith("[GNUPG:] "):
            tokens = line.split()[1:]
            if tokens:
                lines.append(tokens)
    return lines


def verdict(lines: list, listed: set) -> str:
    """The listed primary-key fingerprint the status lines prove signed the bytes, or a refusal.

    A GOODSIG and a VALIDSIG whose primary-key fingerprint (its tenth field) is
    listed, and no expiry, revocation, bad, error or no-data line; the exit
    status is not consulted.
    """
    keywords = [tokens[0] for tokens in lines]
    for keyword, refusal in REFUSING_STATUS:
        if keyword in keywords:
            raise FeatureUnavailable(refusal)
    primaries = [
        tokens[10] if len(tokens) > 10 else tokens[1]
        for tokens in lines
        if tokens[0] == "VALIDSIG" and len(tokens) > 1
    ]
    if "GOODSIG" not in keywords or not primaries:
        raise FeatureUnavailable(NO_VERDICT)
    if any(fingerprint not in listed for fingerprint in primaries):
        raise FeatureUnavailable(UNLISTED)
    return primaries[0]


def gpg_path(path: Path, style: str = "native") -> str:
    """A path as this gpg spells it: forward slashes, and ``/c/Users/...`` for a POSIX-styled build.

    Git for Windows' gpg is an MSYS build whose lock-file code treats any path
    that does not start with ``/`` as relative: given ``C:\\Users\\...`` or
    ``C:/Users/...`` as ``--homedir`` it composed the lock name from the working
    directory plus the whole string and could not start its agent (the first
    two D29.1 findings, windows-latest, September 23, 2026). Such a build is
    told by ``probe_gpg``; it is given the drive as ``/c/`` and the rest with
    forward slashes, which is how that runtime spells the same directory. A
    native gpg keeps ``C:/Users/...``; on POSIX the path is unchanged.
    """
    spelled = Path(path).as_posix()
    if style == "posix" and os.name == "nt":
        drive, rest = os.path.splitdrive(spelled)
        if len(drive) == 2 and drive[1] == ":":
            return "/" + drive[0].lower() + rest
    return spelled


def probe_gpg(gpg: str, cwd: Path) -> dict:
    """This gpg's version line and path style, from ``--version`` alone: no home directory is opened.

    The ``Home:`` line names the default home as the build spells it: a
    ``/``-rooted one is an MSYS or Cygwin build (Git for Windows), which needs
    POSIX-styled paths; anything else is native. The user's keyring is not read.
    """
    result = _run((gpg, "--batch", "--no-tty", "--version"), cwd)
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines or not lines[0].startswith("gpg"):
        raise FeatureUnavailable(VERIFIER_FAILED.format(failure="no version line"))
    home = next((line[len("Home:"):].strip() for line in lines if line.startswith("Home:")), "")
    return {"version": lines[0], "path_style": "posix" if home.startswith("/") else "native"}


def inspect_signature(artifact_digest: str, signature: bytes, signers) -> dict:
    """Verify ``signature`` over the digest against the registry's ``signers`` only, without raising.

    Returns ``signer`` (the listed fingerprint that made it, or None), ``refusal``
    (the refusal text, or None) and ``verifier``: the gpg path and version line
    used, the status keywords gpg reported in order, and the exit status, which
    is recorded and never consulted. Every step that does not end in a verdict
    is its own refusal: gpg absent, the verifier not running, a key block gpg
    cannot import, no verdict in the status lines.
    """
    signers = list(signers)
    data = signed_bytes(artifact_digest)
    gpg, searched = find_gpg()
    verifier = {"gpg": gpg, "version": None, "path_style": None, "status": [], "exit_status": None}
    if gpg is None:
        refusal = GPG_ABSENT.format(searched=", ".join(searched[1:]) or "none known")
        return {"signer": None, "refusal": refusal, "verifier": verifier}
    listed = {entry["fingerprint"] for entry in signers}
    home = Path(tempfile.mkdtemp(prefix="harness-plugin-verify-"))
    try:
        os.chmod(home, 0o700)
        # An existing common.conf keeps gpg on the file keyring, so no keyboxd or
        # agent is started in the private home; --no-autostart says so as well.
        (home / "common.conf").write_bytes(b"")
        (home / "artifact.digest").write_bytes(data)
        (home / SIGNATURE_NAME).write_bytes(signature)
        probed = probe_gpg(gpg, home)
        verifier.update(probed)
        base = (
            gpg,
            "--batch",
            "--no-tty",
            "--no-autostart",
            "--homedir",
            gpg_path(home, probed["path_style"]),
            "--status-fd",
            "1",
        )
        style = probed["path_style"]
        if signers:
            (home / "signers.asc").write_bytes(
                b"".join(entry["public_key"].strip().encode("utf-8") + b"\n" for entry in signers)
            )
            imported = _status(_run(base + ("--import", gpg_path(home / "signers.asc", style)), home).stdout)
            keywords = [tokens[0] for tokens in imported]
            if "IMPORT_PROBLEM" in keywords or keywords.count("IMPORT_OK") < len(signers):
                raise FeatureUnavailable(KEY_IMPORT)
        verified = _run(
            base + ("--verify", gpg_path(home / SIGNATURE_NAME, style), gpg_path(home / "artifact.digest", style)),
            home,
        )
        lines = _status(verified.stdout)
        verifier["status"] = [tokens[0] for tokens in lines]
        verifier["exit_status"] = verified.returncode
        return {"signer": verdict(lines, listed), "refusal": None, "verifier": verifier}
    except FeatureUnavailable as refused:
        return {"signer": None, "refusal": str(refused), "verifier": verifier}
    finally:
        shutil.rmtree(home, ignore_errors=True)


def verify_signature(artifact_digest: str, signature: bytes, signers) -> dict:
    """``inspect_signature`` with every refusal raised; returns ``signer`` and ``verifier``."""
    result = inspect_signature(artifact_digest, signature, signers)
    if result["refusal"] is not None:
        raise FeatureUnavailable(result["refusal"])
    return {"signer": result["signer"], "verifier": result["verifier"]}


def verify_bundle(directory: Path, artifact_digest: str, signers) -> dict:
    """The bundle's ``artifact.sig`` verified over its in-memory artifact digest."""
    return verify_signature(artifact_digest, read_signature(directory), signers)
