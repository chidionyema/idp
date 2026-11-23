"""Founder outbound admission: deterministic, fail-closed evidence validator.

This module does not claim that a transport is wired to it. Call admit() at
the actual outbound send boundary. Founder text is never normalised.
"""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone


class AdmissionDenied(ValueError):
    pass


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def preserve_instruction(raw: bytes, recorded_digest: str) -> None:
    """Verify exact original bytes, not an assistant paraphrase."""
    if not isinstance(raw, bytes) or not hmac.compare_digest(digest(raw), recorded_digest):
        raise AdmissionDenied("instruction-integrity")


def _time(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise AdmissionDenied("invalid-time") from exc
    if dt.tzinfo is None:
        raise AdmissionDenied("naive-time")
    return dt.astimezone(timezone.utc)


def admit(claim: dict, discovery: dict, proofs: list[dict], *, now: datetime) -> None:
    """Validate proof *structure*. Cryptographic trust requires a separate verifier.

    No output from this function is a production certification. Transport callers
    MUST additionally verify signatures, issuers, evidence digests and real-world
    observations before sending; this core never assumes those checks succeeded.
    """
    if now.tzinfo is None:
        raise AdmissionDenied("naive-now")
    keys = ("instruction_id", "claim_id", "target", "revision", "environment")
    if any(not claim.get(k) for k in keys):
        raise AdmissionDenied("missing-claim-binding")
    if not discovery or not discovery.get("searched_sources") or not discovery.get("verified"):
        raise AdmissionDenied("no-verified-reality-discovery")
    if any(discovery.get(k) != claim[k] for k in keys):
        raise AdmissionDenied("discovery-binding-mismatch")
    if discovery.get("contradictions"):
        raise AdmissionDenied("unresolved-reality-contradiction")
    if _time(discovery.get("expires_at")) <= now:
        raise AdmissionDenied("stale-discovery")
    if len(proofs) != 3:
        raise AdmissionDenied("three-proofs-required")
    if {p.get("kind") for p in proofs} != {"execution", "effect", "independent_verification"}:
        raise AdmissionDenied("wrong-proof-kinds")
    for p in proofs:
        if any(p.get(k) != claim[k] for k in keys):
            raise AdmissionDenied("proof-binding-mismatch")
        if not p.get("verified") or not p.get("evidence_digest") or not p.get("issuer"):
            raise AdmissionDenied("unverified-proof")
        if _time(p.get("expires_at")) <= now:
            raise AdmissionDenied("stale-proof")
    if len({p["evidence_digest"] for p in proofs}) != 3:
        raise AdmissionDenied("correlated-evidence")
    if len({p["issuer"] for p in proofs}) != 3:
        raise AdmissionDenied("shared-proof-issuer")
    if not claim.get("independent_verifier_approved"):
        raise AdmissionDenied("independent-certification-required")
