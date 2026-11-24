"""Canonical JSON and digests shared by the custody modules (ESTATE-P0)."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_of(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


# Signed effect witnesses use the estate's existing Ed25519 dependency.
# A public key embedded in a receipt is NEVER an authority: keys must be
# registered by the trusted MissionStore host, outside agent control.
VERIFIER_FIELD = "_meridian_verifier"


def effect_receipt_subject(
    effect_id: str,
    receipt: dict,
    verified_by: str,
    observed_state: str = "OBSERVED",
    reconciliation_status: str = "RECONCILED",
) -> bytes:
    """Exact bytes an independent observer signs after checking external state."""
    if not isinstance(receipt, dict) or not receipt or VERIFIER_FIELD in receipt:
        raise ValueError("external receipt must be a nonempty unwrapped mapping")
    return canonical(
        {
            "schema": "meridian/external-effect-witness-v1",
            "effect_id": effect_id,
            "receipt": receipt,
            "verified_by": verified_by,
            "observed_state": observed_state,
            "reconciliation_status": reconciliation_status,
        }
    ).encode("utf-8")


def verify_effect_receipt(
    effect_id: str,
    stored: dict,
    verified_by: str,
    trusted_keys,
    observed_state: str = "OBSERVED",
    reconciliation_status: str = "RECONCILED",
) -> dict:
    """Return the observed payload only for a pinned-key Ed25519 witness.

    No unsigned receipt, claimed verifier name, self-selected public key or
    mismatched effect/receipt can confer independent operational proof.
    """
    import base64
    import binascii

    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    if not isinstance(stored, dict):
        raise ValueError("external receipt is not an object")
    proof = stored.get(VERIFIER_FIELD)
    if not isinstance(proof, dict) or set(proof) != {"key_id", "signature"}:
        raise ValueError("independent Ed25519 verifier signature required")
    if proof.get("key_id") != verified_by:
        raise ValueError("verifier key ID differs from recorded observer")
    key = trusted_keys.get(verified_by)
    if not isinstance(key, bytes) or len(key) != 32:
        raise ValueError("verifier is not registered with trusted store")
    payload = {k: v for k, v in stored.items() if k != VERIFIER_FIELD}
    subject = effect_receipt_subject(
        effect_id, payload, verified_by, observed_state, reconciliation_status
    )
    try:
        signature = base64.b64decode(proof["signature"], validate=True)
        Ed25519PublicKey.from_public_bytes(key).verify(signature, subject)
    except (InvalidSignature, ValueError, TypeError, KeyError, binascii.Error) as exc:
        raise ValueError("invalid independent Ed25519 receipt signature") from exc
    return payload
