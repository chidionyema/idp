"""Founder admission: fail-closed signed-evidence validation.

A caller-controlled verified flag is NEVER evidence. Only signatures from
separately provisioned trust roots can authenticate discovery and proofs.
This is a reusable core; transports must call it at their send boundary.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class AdmissionDenied(ValueError):
    pass


BINDING = ("instruction_id", "claim_id", "target", "revision", "environment")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def preserve_instruction(raw: bytes, recorded_digest: str) -> None:
    if not isinstance(raw, bytes) or not isinstance(recorded_digest, str) or not hmac.compare_digest(digest(raw), recorded_digest):
        raise AdmissionDenied("instruction-integrity")


def _time(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise AdmissionDenied("invalid-time") from exc
    if dt.tzinfo is None:
        raise AdmissionDenied("naive-time")
    return dt.astimezone(timezone.utc)


def _canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def _authenticate(envelope: dict, trust_roots: dict, expected_role: str) -> dict:
    """Only verifier-controlled public keys are accepted; not payload flags."""
    if not isinstance(envelope, dict):
        raise AdmissionDenied("missing-signed-envelope")
    key_id = envelope.get("key_id")
    payload = envelope.get("payload")
    if not isinstance(payload, dict) or not isinstance(key_id, str):
        raise AdmissionDenied("malformed-signed-envelope")
    root = trust_roots.get(key_id)
    if not isinstance(root, dict) or root.get("role") != expected_role:
        raise AdmissionDenied("untrusted-role")
    try:
        pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(root["public_key_hex"]))
        pub.verify(bytes.fromhex(envelope["signature_hex"]), _canonical(payload))
    except (KeyError, TypeError, ValueError, InvalidSignature) as exc:
        raise AdmissionDenied("invalid-signature") from exc
    return payload


def admit(claim: dict, discovery: dict, proofs: list[dict], *, now: datetime, trust_roots: dict) -> None:
    """Admit only signed, bound evidence; actual effects remain verifier responsibility.

    Trust roots MUST be provisioned outside agent control. Signed observations
    must be issued by separately controlled evidence collectors; this function
    cannot prove their physical independence or correctness by itself.
    """
    if now.tzinfo is None:
        raise AdmissionDenied("naive-now")
    if not isinstance(claim, dict) or any(not claim.get(k) for k in BINDING):
        raise AdmissionDenied("missing-claim-binding")
    d = _authenticate(discovery, trust_roots, "discovery")
    if not d.get("searched_sources") or d.get("contradictions"):
        raise AdmissionDenied("missing-or-conflicting-discovery")
    if _time(d.get("expires_at")) <= now:
        raise AdmissionDenied("stale-discovery")
    if any(d.get(k) != claim[k] for k in BINDING):
        raise AdmissionDenied("discovery-binding-mismatch")
    if not isinstance(proofs, list) or len(proofs) != 3:
        raise AdmissionDenied("three-proofs-required")
    required = {"execution", "effect", "independent_verification"}
    kinds, key_ids, digests = set(), set(), set()
    for envelope in proofs:
        p = _authenticate(envelope, trust_roots, "proof")
        if any(p.get(k) != claim[k] for k in BINDING):
            raise AdmissionDenied("proof-binding-mismatch")
        if _time(p.get("expires_at")) <= now:
            raise AdmissionDenied("stale-proof")
        kind = p.get("kind")
        evidence = p.get("evidence_digest")
        if kind not in required or not isinstance(evidence, str) or len(evidence) != 64:
            raise AdmissionDenied("invalid-proof-kind-or-digest")
        if not p.get("observed") or not p.get("evidence_uri"):
            raise AdmissionDenied("missing-observation")
        kinds.add(kind)
        key_ids.add(envelope["key_id"])
        digests.add(evidence)
    if kinds != required or len(key_ids) != 3 or len(digests) != 3:
        raise AdmissionDenied("correlated-or-incomplete-proofs")
    if discovery.get("key_id") in key_ids:
        raise AdmissionDenied("discovery-proof-shared-key")
    cert = _authenticate(claim.get("certificate"), trust_roots, "certifier")
    if any(cert.get(k) != claim[k] for k in BINDING):
        raise AdmissionDenied("certificate-binding-mismatch")
    if _time(cert.get("expires_at")) <= now or cert.get("decision") != "ALLOW":
        raise AdmissionDenied("certificate-denied-or-stale")
    if cert.get("discovery_digest") != digest(_canonical(d)):
        raise AdmissionDenied("certificate-discovery-mismatch")
    expected = sorted(digest(_canonical(_authenticate(p, trust_roots, "proof"))) for p in proofs)
    if cert.get("proof_digests") != expected:
        raise AdmissionDenied("certificate-proof-mismatch")
