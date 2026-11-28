"""Multi-plane asymmetric epistemic attestation for QUAD + SPIFFE + OIDC + Ed25519 (idp#8759, D11).

Why this replaces symmetric HMAC custody:
  Symmetric HMAC requires the verifier to hold every signer's secret key, so a single job
  that verifies three receipts can also forge all three. True multi-plane independence requires
  asymmetric signatures where the verifier holds ONLY public trust policy (public keys / OIDC
  issuers / SPIFFE trust domain) and ZERO signing secrets.

Design (R43 provider-independent, options open):
  Each operational effect requires >= 3 independent attestations across distinct principals
  AND distinct control planes:
    - landed:   GitHub Actions OIDC / Sigstore bundle (or Ed25519 signer bound to git plane)
    - running:  SPIFFE/SPIRE SVID (spiffe://estate.internal/..., checked against revocation)
    - observed: Independent edge/external prober (tempo-node Ed25519 quorum or edge worker key)

No external crypto library is required to verify structural/policy invariants, and real
Ed25519 verification uses `cryptography` (or `openssl` fallback) when available, failing closed
if neither is present so a verifier can never fail open (AGENTS.md section 9 R1).
"""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

OPENSSL = shutil.which("openssl") or "/usr/bin/openssl"

SCHEMA = "EPISTEMIC-ATTEST-V2"
PROXY_SOURCE_HOSTS = frozenset(
    {
        "github.com",
        "api.github.com",
        "raw.githubusercontent.com",
        "gist.githubusercontent.com",
    }
)
ALLOWED_PROOF_KINDS = frozenset(
    {
        "ed25519",
        "sigstore-oidc",
        "spiffe-svid",
    }
)


def canonical_bytes(obj: Any) -> bytes:
    """Deterministic UTF-8 canonical JSON so every language/plane signs identical bytes."""
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _parse_iso(ts: str) -> datetime | None:
    if not isinstance(ts, str) or not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo is not None else None


def sign_ed25519_pem(private_pem: bytes, payload: dict[str, Any]) -> str:
    """Sign canonical_bytes(payload) with an Ed25519 PEM private key -> base64 signature."""
    data = canonical_bytes(payload)
    try:
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        key = load_pem_private_key(private_pem, password=None)
        return base64.b64encode(key.sign(data)).decode("ascii")
    except ImportError:
        with tempfile.TemporaryDirectory() as td:
            kp = Path(td) / "priv.pem"
            dp = Path(td) / "msg.bin"
            sp = Path(td) / "sig.bin"
            kp.write_bytes(private_pem)
            dp.write_bytes(data)
            res = subprocess.run(  # noqa: S603 -- fixed openssl argv on private temp files
                [
                    OPENSSL,
                    "pkeyutl",
                    "-sign",
                    "-inkey",
                    str(kp),
                    "-rawin",
                    "-in",
                    str(dp),
                    "-out",
                    str(sp),
                ],
                capture_output=True,
                check=False,
            )
            if res.returncode != 0:
                raise RuntimeError(
                    f"openssl ed25519 sign failed: {res.stderr.decode('utf-8', 'replace')}"
                ) from None
            return base64.b64encode(sp.read_bytes()).decode("ascii")


def verify_ed25519_pem(
    public_pem: bytes, payload: dict[str, Any], sig_b64: str
) -> bool:
    """Verify a base64 Ed25519 signature over canonical_bytes(payload). Fails closed."""
    if not isinstance(sig_b64, str) or not sig_b64:
        return False
    try:
        sig = base64.b64decode(sig_b64, validate=True)
    except (ValueError, TypeError):
        return False
    data = canonical_bytes(payload)
    try:
        from cryptography.hazmat.primitives.serialization import load_pem_public_key

        pub = load_pem_public_key(public_pem)
        pub.verify(sig, data)
        return True
    except ImportError:
        with tempfile.TemporaryDirectory() as td:
            kp = Path(td) / "pub.pem"
            dp = Path(td) / "msg.bin"
            sp = Path(td) / "sig.bin"
            kp.write_bytes(public_pem)
            dp.write_bytes(data)
            sp.write_bytes(sig)
            res = subprocess.run(  # noqa: S603 -- fixed openssl argv on private temp files
                [
                    OPENSSL,
                    "pkeyutl",
                    "-verify",
                    "-pubin",
                    "-inkey",
                    str(kp),
                    "-rawin",
                    "-in",
                    str(dp),
                    "-sigfile",
                    str(sp),
                ],
                capture_output=True,
                check=False,
            )
            return res.returncode == 0
    except Exception:
        return False


def generate_ed25519_keypair() -> tuple[bytes, bytes]:
    """Generate an Ed25519 (private_pem, public_pem) pair using cryptography or openssl."""
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        priv = Ed25519PrivateKey.generate()
        priv_pem = priv.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        pub_pem = priv.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return priv_pem, pub_pem
    except ImportError:
        with tempfile.TemporaryDirectory() as td:
            kp = Path(td) / "priv.pem"
            pp = Path(td) / "pub.pem"
            subprocess.run(  # noqa: S603 -- fixed openssl argv on private temp files
                [OPENSSL, "genpkey", "-algorithm", "ED25519", "-out", str(kp)],
                check=True,
                capture_output=True,
            )
            subprocess.run(  # noqa: S603 -- fixed openssl argv on private temp files
                [OPENSSL, "pkey", "-in", str(kp), "-pubout", "-out", str(pp)],
                check=True,
                capture_output=True,
            )
            return kp.read_bytes(), pp.read_bytes()


@dataclass(frozen=True)
class TrustAuthority:
    """Public-only trust anchor for one independent plane (verifier holds ZERO private keys)."""

    name: str
    principal: str
    control_plane: str
    proof_kind: str
    public_key_pem: bytes
    spiffe_id: str | None = None
    oidc_issuer: str | None = None


@dataclass(frozen=True)
class Verdict:
    allowed: bool
    error_codes: tuple[str, ...]
    verified_authorities: tuple[str, ...]
    bundle_sha256: str


def make_attestation(
    *,
    authority: str,
    role: str,
    proof_kind: str,
    revision: str,
    target_url: str,
    http_status: int,
    body_sha256: str,
    fencing_token: int,
    issued_at: str,
    expires_at: str,
    private_pem: bytes,
    spiffe_id: str | None = None,
    oidc_issuer: str | None = None,
    rekor_log_index: int | None = None,
) -> dict[str, Any]:
    """Produce one signed asymmetric attestation for a single plane."""
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": authority,
        "role": role,
        "proof_kind": proof_kind,
        "revision": revision,
        "target_url": target_url,
        "http_status": http_status,
        "body_sha256": body_sha256,
        "fencing_token": fencing_token,
        "issued_at": issued_at,
        "expires_at": expires_at,
    }
    if spiffe_id is not None:
        payload["spiffe_id"] = spiffe_id
    if oidc_issuer is not None:
        payload["oidc_issuer"] = oidc_issuer
    if rekor_log_index is not None:
        payload["rekor_log_index"] = rekor_log_index
    return {
        "payload": payload,
        "signature": sign_ed25519_pem(private_pem, payload),
    }


def verify_multiplane_bundle(
    *,
    attestations: list[dict[str, Any]],
    trust_policy: dict[str, TrustAuthority],
    expected_revision: str,
    expected_target_url: str,
    expected_http_status: int = 200,
    min_fencing_token: int = 1,
    min_planes: int = 3,
    require_spiffe_plane: bool = True,
    now: datetime | None = None,
    is_spiffe_revoked: Callable[[str], bool] | None = None,
) -> Verdict:
    """Verify >= min_planes independent asymmetric attestations with zero verifier secrets."""
    check_now = now or datetime.now(timezone.utc)
    bundle_sha = hashlib.sha256(canonical_bytes(attestations)).hexdigest()
    errors: list[str] = []

    host = urlsplit(expected_target_url).hostname or ""
    if not host or host in PROXY_SOURCE_HOSTS:
        return Verdict(
            False,
            ("ERR_PROXY_GREEN_SUBSTITUTION",),
            (),
            bundle_sha,
        )

    if not isinstance(attestations, list) or len(attestations) < min_planes:
        return Verdict(
            False,
            ("ERR_INSUFFICIENT_ATTESTATIONS",),
            (),
            bundle_sha,
        )

    verified_names: list[str] = []
    seen_principals: set[str] = set()
    seen_planes: set[str] = set()
    seen_pubkeys: set[bytes] = set()
    has_spiffe = False

    for idx, item in enumerate(attestations):
        if not isinstance(item, dict) or not isinstance(item.get("payload"), dict):
            errors.append(f"ERR_MALFORMED_ATTESTATION_{idx}")
            continue
        payload = item["payload"]
        sig = item.get("signature", "")

        if payload.get("schema") != SCHEMA:
            errors.append("ERR_UNKNOWN_SCHEMA")
            continue
        proof_kind = payload.get("proof_kind")
        if proof_kind == "hmac" or proof_kind not in ALLOWED_PROOF_KINDS:
            errors.append("ERR_SYMMETRIC_OR_UNSUPPORTED_PROOF_KIND")
            continue

        auth_name = payload.get("authority")
        anchor = trust_policy.get(str(auth_name))
        if anchor is None:
            errors.append(f"ERR_UNTRUSTED_AUTHORITY:{auth_name}")
            continue
        if anchor.proof_kind != proof_kind:
            errors.append(f"ERR_PROOF_KIND_MISMATCH:{auth_name}")
            continue

        if payload.get("revision") != expected_revision:
            errors.append(f"ERR_REVISION_MISMATCH:{auth_name}")
            continue
        if payload.get("target_url") != expected_target_url:
            errors.append(f"ERR_TARGET_MISMATCH:{auth_name}")
            continue
        if payload.get("http_status") != expected_http_status:
            errors.append(f"ERR_STATUS_MISMATCH:{auth_name}")
            continue
        fence = payload.get("fencing_token")
        if not isinstance(fence, int) or fence < min_fencing_token:
            errors.append(f"ERR_FENCING_TOKEN_TOO_LOW:{auth_name}")
            continue

        expires = _parse_iso(str(payload.get("expires_at", "")))
        issued = _parse_iso(str(payload.get("issued_at", "")))
        if expires is None or issued is None or expires <= issued:
            errors.append(f"ERR_INVALID_VALIDITY_WINDOW:{auth_name}")
            continue
        if expires <= check_now:
            errors.append(f"ERR_ATTESTATION_EXPIRED:{auth_name}")
            continue

        if proof_kind == "spiffe-svid":
            sid = payload.get("spiffe_id")
            if not isinstance(sid, str) or not sid.startswith("spiffe://"):
                errors.append(f"ERR_SPIFFE_ID_MISSING:{auth_name}")
                continue
            if anchor.spiffe_id and sid != anchor.spiffe_id:
                errors.append(f"ERR_SPIFFE_ID_MISMATCH:{auth_name}")
                continue
            if "/dev/" in sid:
                errors.append(f"ERR_SPIFFE_DEV_FALLBACK_NOT_ATTESTED:{auth_name}")
                continue
            if is_spiffe_revoked is not None and is_spiffe_revoked(sid):
                errors.append(f"ERR_SPIFFE_SVID_REVOKED:{auth_name}")
                continue
            has_spiffe = True

        if proof_kind == "sigstore-oidc":
            issuer = payload.get("oidc_issuer")
            if anchor.oidc_issuer and issuer != anchor.oidc_issuer:
                errors.append(f"ERR_OIDC_ISSUER_MISMATCH:{auth_name}")
                continue

        if not verify_ed25519_pem(anchor.public_key_pem, payload, sig):
            errors.append(f"ERR_INVALID_SIGNATURE:{auth_name}")
            continue

        if (
            anchor.principal in seen_principals
            or anchor.control_plane in seen_planes
            or anchor.public_key_pem in seen_pubkeys
        ):
            errors.append(f"ERR_QUAD_CUSTODY_NOT_ISOLATED:{auth_name}")
            continue

        seen_principals.add(anchor.principal)
        seen_planes.add(anchor.control_plane)
        seen_pubkeys.add(anchor.public_key_pem)
        verified_names.append(anchor.name)

    if require_spiffe_plane and not has_spiffe:
        errors.append("ERR_SPIFFE_PLANE_REQUIRED")

    if len(verified_names) < min_planes:
        errors.append("ERR_INSUFFICIENT_INDEPENDENT_PLANES")

    return Verdict(
        allowed=len(errors) == 0,
        error_codes=tuple(errors),
        verified_authorities=tuple(verified_names),
        bundle_sha256=bundle_sha,
    )
