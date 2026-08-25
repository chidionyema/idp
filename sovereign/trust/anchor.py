"""HardwareTrustAnchor: one interface, backends behind it (cp20). Platform
detection (platform.system() / sys.platform) is confined to this file --
nowhere else in sovereign/ may branch on the OS (a founder-presence gateway
under sovereign/presence/ is the only other place cp20 permits it, and
none exists in this build).

This module never imports sovereign.config at module load time: it is
imported *by* sovereign/config.py (config.py's merge step does
`from sovereign.trust.config_keys import TRUST_KEYS`, which first runs
this package's __init__.py, which imports this file). A module-level
`from sovereign import config` here would try to read attributes
sovereign/config.py has not defined yet at that point in its own
execution -- see sovereign/trust/README.md. Every function below either
uses sovereign.trust.config_keys directly (env-or-default, no cycle) or
imports sovereign.config lazily inside a method body, by which point
sovereign.config has always finished loading.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import platform
import secrets
import subprocess
from pathlib import Path
from typing import Any

from sovereign.trust import config_keys as ck

BACKENDS = ("secure_enclave", "windows_hello", "fido2", "software_key")


def _estate_home() -> Path:
    env = os.environ.get("ESTATE_HOME")
    if env:
        return Path(env)
    return Path.home() / ck.get("trust.default_estate_home_dirname")


def _bin_dir() -> Path:
    return _estate_home() / ck.get("trust.bin_dirname")


def _swift_source_path() -> Path:
    return Path(__file__).resolve().parent / ck.get("trust.swift_source_filename")


def _swift_helper_path() -> Path:
    return _bin_dir() / ck.get("trust.swift_helper_binname")


def _ensure_swift_helper_compiled() -> Path | None:
    """Compiles sovereign/trust/presence_helper.swift into
    $ESTATE_HOME/bin on first use; the binary is then cached there.
    Returns None (never raises) if swiftc is unavailable, the source is
    missing, or compilation fails -- callers fall back to software_key."""
    out = _swift_helper_path()
    if out.exists():
        return out
    src = _swift_source_path()
    if not src.exists():
        return None
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            ["xcrun", "swiftc", str(src), "-o", str(out)],
            capture_output=True, text=True, timeout=ck.get("trust.compile_timeout_s"),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0 or not out.exists():
        return None
    out.chmod(ck.get("trust.helper_file_mode"))
    return out


def _run_helper(args: list[str], timeout: float) -> dict[str, Any] | None:
    helper = _ensure_swift_helper_compiled()
    if helper is None:
        return None
    try:
        result = subprocess.run([str(helper), *args], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    try:
        return json.loads(result.stdout.strip() or "{}")
    except json.JSONDecodeError:
        return None


def _detect_macos_backend() -> str:
    detected = _run_helper(["--detect"], ck.get("trust.detect_timeout_s"))
    if detected and detected.get("secure_enclave"):
        return "secure_enclave"
    return "software_key"


def _detect_windows_backend() -> str:
    try:
        from winrt.windows.security.credentials.ui import (  # type: ignore
            UserConsentVerifier,
            UserConsentVerifierAvailability,
        )
    except ImportError:
        return "software_key"
    try:
        availability = UserConsentVerifier.check_availability_async().get()
    except Exception:
        return "software_key"
    if availability == UserConsentVerifierAvailability.AVAILABLE:
        return "windows_hello"
    return "software_key"


def _detect_fido2_backend() -> str:
    try:
        from fido2.hid import CtapHidDevice  # type: ignore
    except ImportError:
        return "software_key"
    try:
        devices = list(CtapHidDevice.list_devices())
    except Exception:
        return "software_key"
    return "fido2" if devices else "software_key"


def _detect_backend() -> str:
    system = platform.system()
    if system == "Darwin":
        return _detect_macos_backend()
    if system == "Windows":
        backend = _detect_windows_backend()
        return backend if backend != "software_key" else _detect_fido2_backend()
    return _detect_fido2_backend()


def _software_key_path() -> Path:
    return _estate_home() / ck.get("trust.sovereign_dirname") / ck.get("trust.software_key_filename")


def _get_or_create_software_key() -> bytes:
    path = _software_key_path()
    if path.exists():
        return bytes.fromhex(path.read_text().strip())
    key = secrets.token_hex(int(ck.get("trust.hmac_key_bytes")))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(key)
    path.chmod(ck.get("trust.software_key_file_mode"))
    return bytes.fromhex(key)


class HardwareTrustAnchor:
    """One interface over the platform's root of trust. `.backend` is one
    of BACKENDS, resolved once per instance from config key trust.backend:
    "auto" triggers the one platform-detection call this module makes
    (cp20); any backend name pins it directly (used by tests, and by an
    operator who knows their hardware better than the detector does)."""

    def __init__(self, backend: str | None = None) -> None:
        requested = backend or self._configured_backend()
        if requested == "auto":
            self.backend = _detect_backend()
        elif requested in BACKENDS:
            self.backend = requested
        else:
            self.backend = "software_key"

    @staticmethod
    def _configured_backend() -> str:
        try:
            from sovereign import config  # lazy: see module docstring
            return config.get("trust.backend").value
        except Exception:
            return os.environ.get("SB_TRUST_BACKEND", "auto")

    def verify_founder_presence(self, reason: str | None = None) -> bool:
        """True if the founder is present at the keyboard right now,
        proved by this instance's backend. software_key has no hardware
        to check and always returns True -- callers learn which backend
        produced the answer from `.backend`, and a caller that requires a
        hardware-backed answer checks `.backend != "software_key"` first."""
        reason = reason or ck.get("trust.reason_default")
        if self.backend == "secure_enclave":
            result = _run_helper(["--verify", reason], ck.get("trust.presence_timeout_s"))
            return bool(result and result.get("ok"))
        if self.backend == "windows_hello":
            return self._verify_windows_hello(reason)
        if self.backend == "fido2":
            return self._verify_fido2()
        return True  # software_key

    def _verify_windows_hello(self, reason: str) -> bool:
        try:
            from winrt.windows.security.credentials.ui import (  # type: ignore
                UserConsentVerificationResult,
                UserConsentVerifier,
            )
        except ImportError:
            return False
        try:
            result = UserConsentVerifier.request_verification_async(reason).get()
        except Exception:
            return False
        return result == UserConsentVerificationResult.VERIFIED

    def _verify_fido2(self) -> bool:
        try:
            from fido2.hid import CtapHidDevice  # type: ignore
        except ImportError:
            return False
        try:
            return bool(list(CtapHidDevice.list_devices()))
        except Exception:
            return False

    def sign(self, digest: str) -> tuple[str, str]:
        """Sign `digest` (a hex string, typically a receipt line's own
        hash) with this instance's backend. Returns (signature_hex,
        backend_actually_used) -- the second element is what a caller
        records on the receipt (cp20: "the chosen backend is recorded in
        every signed receipt"), and it is the backend that really
        produced the bytes, not necessarily `self.backend`: a hardware
        path that turns out unusable at sign time (no swiftc, no winrt,
        no fido2 runtime) falls back to software_key rather than fabricate
        a signature under a backend name that did not produce it. The
        signing key never leaves the keystore: the secure_enclave path
        signs inside CryptoKit's SecureEnclave and only a Keychain-opaque
        blob is ever written to disk; software_key signs with a 0600
        file key, the same fallback class receipts.py already uses."""
        if self.backend == "secure_enclave":
            result = _run_helper(["--sign", digest], ck.get("trust.presence_timeout_s"))
            if result and result.get("ok") and result.get("sig"):
                return str(result["sig"]), "secure_enclave"
        elif self.backend in ("windows_hello", "fido2"):
            pass  # no signing path implemented yet for these two (README.md residual)
        key = _get_or_create_software_key()
        sig = hmac.new(key, digest.encode(), hashlib.sha256).hexdigest()
        return sig, "software_key"

    # ------------------------------------------------------------------
    # R11/R22: verifying a signature, not just producing one.
    #
    # `sign()` above was enough while the only consumer was a receipt the
    # same process had just written. An approval arrives from outside the
    # process that will act on it, so the acting side has to be able to
    # say no. That needs two things sign() never had: a public key that
    # was enrolled once (not whichever key answers today), and a check
    # against it.
    #
    # The check itself is CryptoKit's -- presence_helper.swift grew a
    # `--verify-sig` mode. Nothing about P256 is re-implemented in Python:
    # sovereign/requirements.txt carries no crypto library, and adding a
    # hand-rolled curve check to avoid one is the exact move LAW 43 bans.
    # ------------------------------------------------------------------

    def enrolled_pubkey(self) -> str | None:
        """The public key this estate pinned, base64. Read from
        $ESTATE_HOME/sovereign/<trust.enrolled_pubkey_filename>. None when
        nothing has been enrolled yet -- callers treat that as "cannot
        verify", never as "verifies"."""
        path = _enrolled_pubkey_path()
        if not path.exists():
            return None
        text = path.read_text().strip()
        return text or None

    def enroll(self) -> str | None:
        """Pin this backend's public key as the estate's enrolled key, and
        return it. Idempotent: an existing enrolment is returned unchanged
        rather than silently replaced, because replacing it would make
        every signature already in the intervention log unverifiable."""
        existing = self.enrolled_pubkey()
        if existing:
            return existing
        if self.backend != "secure_enclave":
            return None
        result = _run_helper(["--pubkey"], ck.get("trust.presence_timeout_s"))
        if not (result and result.get("ok") and result.get("pubkey")):
            return None
        path = _enrolled_pubkey_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(result["pubkey"]))
        path.chmod(ck.get("trust.software_key_file_mode"))
        return str(result["pubkey"])

    def verify(self, digest: str, signature: str, backend: str) -> bool:
        """True only if `signature` really is `digest` signed by `backend`.

        Fails closed on every unknown: an unenrolled estate, a helper that
        will not compile, a backend name that has no verification path.
        `backend` is the one the signature claims -- taken from the
        envelope, never from self.backend -- so a software_key signature
        can never be waved through as an enclave one."""
        if not digest or not signature:
            return False
        if backend == "secure_enclave":
            pubkey = self.enrolled_pubkey()
            if not pubkey:
                return False
            result = _run_helper(
                ["--verify-sig", digest, signature, pubkey], ck.get("trust.presence_timeout_s")
            )
            return bool(result and result.get("ok"))
        if backend == "software_key":
            key = _get_or_create_software_key()
            expected = hmac.new(key, digest.encode(), hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected, signature)
        return False


def _enrolled_pubkey_path() -> Path:
    return _estate_home() / ck.get("trust.sovereign_dirname") / ck.get("trust.enrolled_pubkey_filename")


# ---------------------------------------------------------------------------
# R24: the enrolled fallback signer set (the "3" of 2-of-3).
#
# Each signer is a separate 0600 key file under
# $ESTATE_HOME/sovereign/<trust.signers_dirname>/. Separate files, not one
# file with three keys in it, because the whole point of a threshold is
# that compromising one signer is not compromising the set -- and a single
# file is a single thing to steal.
#
# These are HMAC keys, which means the verifier can also sign. That is a
# real limit and it is stated in sovereign/trust/README.md rather than
# hidden: it is the same key class sovereign/engine/receipts.py already
# falls back to, and swapping a signer to an asymmetric hardware token is
# a change to sign_as()/verify_signer() alone. What it does buy today is
# the property cp29 asks for: no ONE key, including the enclave's, can
# authorise an override on its own once the enclave is gone.
# ---------------------------------------------------------------------------


def signer_ids() -> list[str]:
    raw = str(ck.get("trust.multisig_signers"))
    return [s.strip() for s in raw.split(",") if s.strip()]


def _signer_key_path(signer_id: str) -> Path:
    if signer_id not in signer_ids():
        raise ValueError(f"not an enrolled signer: {signer_id!r}")
    name = signer_id + str(ck.get("trust.signer_key_suffix"))
    return _estate_home() / ck.get("trust.sovereign_dirname") / ck.get("trust.signers_dirname") / name


def _get_or_create_signer_key(signer_id: str) -> bytes:
    path = _signer_key_path(signer_id)
    if path.exists():
        return bytes.fromhex(path.read_text().strip())
    key = secrets.token_hex(int(ck.get("trust.hmac_key_bytes")))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(key)
    path.chmod(ck.get("trust.software_key_file_mode"))
    return bytes.fromhex(key)


def sign_as(signer_id: str, digest: str) -> str:
    """One member of the fallback set signs `digest`."""
    key = _get_or_create_signer_key(signer_id)
    return hmac.new(key, digest.encode(), hashlib.sha256).hexdigest()


def verify_signer(signer_id: str, digest: str, signature: str) -> bool:
    """True only if `signature` is `digest` signed by that enrolled signer.
    An id outside the configured set is False, never an exception -- an
    attacker choosing the signer id must not be able to pick the error."""
    try:
        path = _signer_key_path(signer_id)
    except ValueError:
        return False
    if not path.exists():
        return False
    key = bytes.fromhex(path.read_text().strip())
    expected = hmac.new(key, digest.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
