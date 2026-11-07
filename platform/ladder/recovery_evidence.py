"""Verify an independent recovery certificate before auto-closing a DoF incident.

This verifier does not sign receipts or run privileged recovery. The only
accepted trust root is an externally provisioned Ed25519 public key pinned by
the trusted runtime. A missing key/receipt or any unproved observation holds
the outage open. A certificate is NOT a substitute for DoF gate enforcement:
the gate itself must also verify receipts before it stops restricting writes.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import re
from pathlib import Path
from time import time

SERVICE = re.compile(r"^[a-z0-9-]{1,64}$")
SHA = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
MAX_BYTES = 65_536
MAX_AGE = 300
MIN_SEPARATION = 30


class RecoveryProofRefused(ValueError):
    pass


def _b64(data: str) -> bytes:
    try:
        if not isinstance(data, str):
            raise ValueError("not base64")
        return base64.b64decode(data, validate=True)
    except (ValueError, TypeError) as exc:
        raise RecoveryProofRefused("INVALID_BASE64") from exc


def _canonical(data: dict) -> bytes:
    return json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def verify_recovery_receipt(
    service: str, rows: list, *, receipt_dir: str, verifier_key_b64: str,
    now: float | None = None,
) -> tuple[bool, str]:
    """Validate a signed two-round, multi-provider functional recovery proof.

    Observe the current service independently *as well*: neither a signed but
    stale note nor unsigned current health output can grant release. Receipt
    signer must reside outside the affected service's credential/failure domain.
    """
    if not SERVICE.fullmatch(service or ""):
        return False, "INVALID_SERVICE_ID"
    if not receipt_dir or not verifier_key_b64:
        return False, "INDEPENDENT_RECOVERY_TRUST_NOT_CONFIGURED"
    try:
        moment = time() if now is None else float(now)
        if not math.isfinite(moment):
            return False, "INVALID_CLOCK"
        p = Path(receipt_dir) / (service + ".json")
        if not p.is_file() or p.stat().st_size < 10 or p.stat().st_size > MAX_BYTES:
            return False, "RECOVERY_RECEIPT_UNAVAILABLE"
        envelope = json.loads(p.read_bytes())
        if not isinstance(envelope, dict) or set(envelope) != {
            "format", "payload_b64", "signature_b64",
        } or envelope["format"] != "genesis.recovery.ed25519.v1":
            return False, "INVALID_RECOVERY_ENVELOPE"
        payload_bytes = _b64(envelope["payload_b64"])
        signature = _b64(envelope["signature_b64"])
        pubkey = _b64(verifier_key_b64)
        if len(pubkey) != 32 or len(signature) != 64 or len(payload_bytes) > MAX_BYTES:
            return False, "INVALID_SIGNATURE_SHAPE"
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        Ed25519PublicKey.from_public_bytes(pubkey).verify(signature, payload_bytes)
        payload = json.loads(payload_bytes)
        if not isinstance(payload, dict) or payload_bytes != _canonical(payload):
            return False, "NONCANONICAL_SIGNED_RECOVERY_PAYLOAD"
    except (OSError, ValueError, TypeError, KeyError, ImportError, AttributeError) as exc:
        return False, "RECOVERY_RECEIPT_INVALID_OR_UNREADABLE"
    except Exception:
        # Signature forgery, inaccessible hardware/verifier, or a failed
        # cryptographic primitive must NEVER become an all-clear.
        return False, "RECOVERY_SIGNATURE_NOT_VERIFIED"

    if (payload.get("schema") != "genesis.recovery.v1"
            or payload.get("service") != service
            or not isinstance(payload.get("observer"), str)
            or not payload["observer"].startswith("independent:")
            or not SHA.fullmatch(str(payload.get("deployment_sha", "")))
            or not isinstance(payload.get("run_id"), str)
            or not payload["run_id"].isdigit()):
        return False, "RECOVERY_IDENTITY_OR_DEPLOYMENT_UNBOUND"
    issued = payload.get("issued_at")
    expires = payload.get("expires_at")
    if (type(issued) not in (int, float) or type(expires) not in (int, float)
            or not all(math.isfinite(v) for v in (issued, expires))
            or issued > moment + 10 or issued < moment - MAX_AGE
            or expires <= moment or expires > issued + MAX_AGE):
        return False, "STALE_OR_FUTURE_RECOVERY_RECEIPT"
    actual = {(r.get("leg"), r.get("provider")) for r in rows}
    if not actual or len(actual) != len(rows):
        return False, "AMBIGUOUS_PROBED_LANES"
    if any(r.get("verdict") != "MEASURED_OK" or
           r.get("probe_kind") != "functional" for r in rows):
        return False, "CURRENT_FUNCTIONAL_READINESS_UNPROVEN"
    probes = payload.get("observations")
    if not isinstance(probes, list) or not 2 * len(actual) <= len(probes) <= 4 * len(actual):
        return False, "INCOMPLETE_RECOVERY_OBSERVATIONS"
    grouped = {key: [] for key in actual}
    expected_urls = {
        (r["leg"], r["provider"]): r.get("url") for r in rows
    }
    for probe in probes:
        if not isinstance(probe, dict):
            return False, "INVALID_RECOVERY_OBSERVATION"
        key = (probe.get("leg"), probe.get("provider"))
        t = probe.get("observed_at")
        if (key not in grouped or probe.get("result") != "FUNCTIONAL_READY"
                or probe.get("url") != expected_urls.get(key)
                or not isinstance(probe.get("check"), str)
                or not probe["check"].startswith("authenticated-functional:")
                or not DIGEST.fullmatch(str(probe.get("evidence_sha256", "")))
                or type(t) not in (int, float) or not math.isfinite(t)
                or t > issued + 10 or t < issued - MAX_AGE):
            return False, "UNTRUSTED_RECOVERY_OBSERVATION"
        grouped[key].append(t)
    for key, times in grouped.items():
        if len(times) < 2 or max(times) - min(times) < MIN_SEPARATION:
            return False, "RECOVERY_NOT_SUSTAINED"
    if len({r.get("provider") for r in rows}) < 2:
        return False, "INDEPENDENT_FAILURE_DOMAINS_UNPROVEN"
    return True, "SIGNED_RECOVERY_PROVEN"
