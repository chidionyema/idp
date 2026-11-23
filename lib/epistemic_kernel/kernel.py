"""Core deterministic Epistemic Provenance & Mandatory Falsification Kernel.

Implements RFC-8785-compatible canonical JSON serialization and HMAC-SHA256
receipt verification so Rust, Python, and TypeScript runtimes produce byte-for-byte
identical digests and deterministic verdicts.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlparse


class EvidenceTier(str, Enum):
    TIER_0_RAW_MACHINE_RECEIPT = "TIER_0_RAW_MACHINE_RECEIPT"
    TIER_1_CORROBORATED_OBSERVATION = "TIER_1_CORROBORATED_OBSERVATION"
    TIER_2_AGENT_INFERENCE = "TIER_2_AGENT_INFERENCE"


class ExecutionPlane(str, Enum):
    PLANE_SOURCE_FLOW = "PLANE_SOURCE_FLOW"
    PLANE_CI_BUILD = "PLANE_CI_BUILD"
    PLANE_CONTROL_AUTH = "PLANE_CONTROL_AUTH"
    PLANE_PRODUCTION_RUNTIME = "PLANE_PRODUCTION_RUNTIME"


PROXY_SOURCE_HOSTS = frozenset(
    {
        "raw.githubusercontent.com",
        "api.github.com",
        "github.com",
        "gist.githubusercontent.com",
    }
)

# Universal-scope claims that CANNOT be inferred from a single job-local empty env var.
SCOPE_HIERARCHY: Dict[str, int] = {
    "job_env": 1,
    "workflow_run": 2,
    "repo_secrets": 3,
    "vault_store": 4,
    "provider_account": 5,
    "estate_global": 6,
}

# Required store scopes that MUST each have an independent TIER_0 receipt before
# claiming global non-existence of a credential in the estate.
REQUIRED_ESTATE_EXISTENCE_SCOPES = frozenset(
    {
        "repo_secrets",
        "vault_store",
        "provider_account",
    }
)


class EpistemicError(Exception):
    def __init__(
        self, code: str, message: str, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
        self.details = details or {}


def canonical_json(obj: Any) -> str:
    """Deterministic UTF-8 JSON representation shared across Rust/Python/TypeScript."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def parse_utc(ts: str) -> datetime:
    if not isinstance(ts, str) or not ts:
        raise EpistemicError(
            "ERR_INVALID_TIMESTAMP", "Timestamp must be a non-empty RFC3339 UTC string."
        )
    normalized = ts.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise EpistemicError(
            "ERR_INVALID_TIMESTAMP", f"Malformed RFC3339 timestamp: {ts}"
        ) from exc
    if dt.tzinfo is None:
        raise EpistemicError(
            "ERR_INVALID_TIMESTAMP", f"Timestamp missing timezone: {ts}"
        )
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class SignedReceipt:
    receipt_id: str
    tier: str
    plane: str
    capture_authority: str
    subject_agent_id: str
    observer_scope: str
    target_uri: str
    observed_at_utc: str
    fencing_token: int
    exit_code: int
    http_status: Optional[int]
    raw_payload: str
    raw_payload_sha256: str
    signature_alg: str = "HMAC-SHA256"
    signature: str = ""

    def unsigned_payload_dict(self) -> Dict[str, Any]:
        return {
            "capture_authority": self.capture_authority,
            "exit_code": self.exit_code,
            "fencing_token": self.fencing_token,
            "http_status": self.http_status,
            "observed_at_utc": self.observed_at_utc,
            "observer_scope": self.observer_scope,
            "plane": self.plane,
            "raw_payload_sha256": self.raw_payload_sha256,
            "receipt_id": self.receipt_id,
            "signature_alg": self.signature_alg,
            "subject_agent_id": self.subject_agent_id,
            "target_uri": self.target_uri,
            "tier": self.tier,
        }

    def canonical_signing_string(self) -> str:
        return canonical_json(self.unsigned_payload_dict())


def sign_receipt(receipt: SignedReceipt, secret_key: bytes) -> SignedReceipt:
    """Sign a receipt with the isolated non-agent verifier key."""
    computed_hash = sha256_hex(receipt.raw_payload)
    if receipt.raw_payload_sha256 != computed_hash:
        raise EpistemicError(
            "ERR_PAYLOAD_HASH_MISMATCH",
            "raw_payload_sha256 does not match SHA-256 of raw_payload.",
        )
    sig = hmac.new(
        secret_key,
        receipt.canonical_signing_string().encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    data = asdict(receipt)
    data["signature"] = sig
    return SignedReceipt(**data)


def verify_receipt_signature(
    receipt: SignedReceipt,
    secret_key: bytes,
    trusted_authorities: Iterable[str],
    now_utc: Optional[datetime] = None,
    max_age_seconds: int = 3600,
    min_fencing_token: int = 1,
) -> Tuple[bool, Optional[str]]:
    """Verify receipt authenticity, payload integrity, authority isolation, TTL, and fence."""
    # 1. Authority isolation: an agent CANNOT sign its own primary receipt.
    if (
        not receipt.capture_authority
        or receipt.capture_authority == receipt.subject_agent_id
    ):
        return False, "ERR_FORGED_OR_SELF_SIGNED_RECEIPT"
    if receipt.capture_authority not in set(trusted_authorities):
        return False, "ERR_UNTRUSTED_CAPTURE_AUTHORITY"

    # 2. Tier check: secondary agent inferences are never cryptographically primary.
    if receipt.tier == EvidenceTier.TIER_2_AGENT_INFERENCE.value:
        return False, "ERR_EPISTEMIC_LAUNDERING_BLOCKED"
    if receipt.tier not in {
        EvidenceTier.TIER_0_RAW_MACHINE_RECEIPT.value,
        EvidenceTier.TIER_1_CORROBORATED_OBSERVATION.value,
    }:
        return False, "ERR_UNKNOWN_EVIDENCE_TIER"

    # 3. Payload integrity check (defeats stdout/body tampering after capture).
    if sha256_hex(receipt.raw_payload) != receipt.raw_payload_sha256:
        return False, "ERR_PAYLOAD_TAMPERED"

    # 4. Fencing token check (defeats zombie-lane split-brain replay).
    if receipt.fencing_token < min_fencing_token:
        return False, "ERR_STALE_FENCING_TOKEN"

    # 5. Freshness / TTL check.
    try:
        obs_dt = parse_utc(receipt.observed_at_utc)
    except EpistemicError as exc:
        return False, exc.code
    ref_now = now_utc or datetime.now(timezone.utc)
    age = (ref_now - obs_dt).total_seconds()
    if age > max_age_seconds:
        return False, "ERR_STALE_RECEIPT"
    if age < -30:
        return False, "ERR_FUTURE_TIMESTAMP"

    # 6. Constant-time HMAC verification over ALL metadata + payload hash.
    expected = hmac.new(
        secret_key,
        receipt.canonical_signing_string().encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, receipt.signature or ""):
        return False, "ERR_SIGNATURE_MISMATCH"

    return True, None


@dataclass
class FalsificationDecision:
    allowed: bool
    verdict: str
    error_codes: List[str] = field(default_factory=list)
    operational_yield: int = 0
    verified_receipt_ids: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EpistemicKernel:
    """Stateless fail-closed policy gate evaluating claims, diagnoses, and state transitions."""

    def __init__(
        self,
        secret_key: bytes,
        trusted_authorities: Iterable[str],
        max_receipt_age_seconds: int = 3600,
        authority_keys: Optional[Dict[str, bytes]] = None,
    ):
        self._secret_key = secret_key
        self._trusted_authorities = frozenset(trusted_authorities)
        # Optional per-authority keys MUST be held by independent verifier principals,
        # not supplied inside an agent-controlled envelope. Shared-key v1 is single-proof only.
        self._authority_keys = dict(authority_keys) if authority_keys else {}
        self._max_age = max_receipt_age_seconds

    def _verify_all_receipts(
        self,
        receipts: Sequence[SignedReceipt],
        now_utc: Optional[datetime] = None,
        min_fencing_token: int = 1,
    ) -> Tuple[Dict[str, SignedReceipt], List[str]]:
        verified: Dict[str, SignedReceipt] = {}
        errors: List[str] = []
        seen_ids = set()
        for r in receipts:
            if not r.receipt_id or r.receipt_id in seen_ids:
                errors.append(f"{r.receipt_id}:ERR_DUPLICATE_OR_EMPTY_RECEIPT_ID")
                continue
            seen_ids.add(r.receipt_id)
            if self._authority_keys and r.capture_authority not in self._authority_keys:
                errors.append(f"{r.receipt_id}:ERR_AUTHORITY_KEY_NOT_CONFIGURED")
                continue
            ok, err = verify_receipt_signature(
                r,
                self._authority_keys.get(r.capture_authority, self._secret_key),
                self._trusted_authorities,
                now_utc=now_utc,
                max_age_seconds=self._max_age,
                min_fencing_token=min_fencing_token,
            )
            if ok:
                verified[r.receipt_id] = r
            else:
                errors.append(f"{r.receipt_id}:{err}")
        return verified, errors

    def evaluate_diagnosis(
        self,
        envelope: Dict[str, Any],
        receipts: Sequence[SignedReceipt],
        now_utc: Optional[datetime] = None,
        min_fencing_token: int = 1,
    ) -> FalsificationDecision:
        """Gate an incident diagnosis or remediation claim (Enforces E1 + E2)."""
        errors: List[str] = []
        verified_map, receipt_errors = self._verify_all_receipts(
            receipts, now_utc=now_utc, min_fencing_token=min_fencing_token
        )
        errors.extend(receipt_errors)

        # E1: Reject any attempt to cite TIER_2 agent artifacts as primary proof.
        claimed_sources = envelope.get("cited_sources", [])
        for src in claimed_sources:
            if src.get("tier") == EvidenceTier.TIER_2_AGENT_INFERENCE.value and src.get(
                "used_as_primary_fact", False
            ):
                errors.append("ERR_EPISTEMIC_LAUNDERING_BLOCKED")

        # Require at least one verified TIER_0 observed fact.
        observed_facts = envelope.get("observed_facts", [])
        if not observed_facts:
            errors.append("ERR_NO_OBSERVED_FACTS")

        verified_fact_scopes = set()
        for fact in observed_facts:
            rid = fact.get("receipt_id")
            if rid not in verified_map:
                errors.append(f"ERR_UNVERIFIED_FACT_RECEIPT:{rid}")
                continue
            r = verified_map[rid]
            if r.tier != EvidenceTier.TIER_0_RAW_MACHINE_RECEIPT.value:
                errors.append(f"ERR_NON_PRIMARY_FACT_RECEIPT:{rid}")
                continue
            verified_fact_scopes.add(r.observer_scope)

        # E2: Scope-bounded negation check.
        # Reject promoting local job_env absence into estate_global / repo_secrets / vault_store non-existence.
        for claim in envelope.get("promoted_claims", []):
            claim_scope = claim.get("claim_scope", "estate_global")
            claim_type = claim.get("claim_type", "assertion")
            supporting_ids = claim.get("supporting_receipt_ids", [])
            supporting_scopes = {
                verified_map[rid].observer_scope
                for rid in supporting_ids
                if rid in verified_map
            }
            if not supporting_scopes:
                errors.append(f"ERR_UNSUPPORTED_CLAIM:{claim.get('id', 'unknown')}")
                continue

            if claim_type == "existential_negation":
                if claim_scope == "estate_global":
                    if not REQUIRED_ESTATE_EXISTENCE_SCOPES.issubset(supporting_scopes):
                        errors.append("ERR_INVALID_NEGATION_SCOPE_LEAP")
                else:
                    max_observed_rank = max(
                        SCOPE_HIERARCHY.get(s, 0) for s in supporting_scopes
                    )
                    claimed_rank = SCOPE_HIERARCHY.get(claim_scope, 99)
                    if claimed_rank > max_observed_rank:
                        errors.append("ERR_INVALID_NEGATION_SCOPE_LEAP")
            else:
                max_observed_rank = max(
                    SCOPE_HIERARCHY.get(s, 0) for s in supporting_scopes
                )
                claimed_rank = SCOPE_HIERARCHY.get(claim_scope, 99)
                if claimed_rank > max_observed_rank:
                    errors.append("ERR_SCOPE_OVERCLAIM")

        # E2: Mandatory dual-sided falsification matrix.
        hypotheses = envelope.get("competing_hypotheses", [])
        if len(hypotheses) < 2:
            errors.append("ERR_CONFIRMATION_BIAS_NO_ALTERNATIVE")

        for idx, hyp in enumerate(hypotheses):
            if (
                not hyp.get("statement")
                or not hyp.get("falsified_by")
                or not hyp.get("discriminating_probe")
            ):
                errors.append(f"ERR_UNFALSIFIABLE_HYPOTHESIS:{idx}")

        # E2: Mutating remediation requires discriminating probe evidence unless explicitly scoped.
        if envelope.get("requests_mutation", False):
            discriminated = any(
                h.get("status") == "FALSIFIED"
                and h.get("falsifying_receipt_id") in verified_map
                for h in hypotheses
            )
            # A caller-controlled boolean cannot turn a mutating effect into a read-only probe.
            if not discriminated:
                errors.append("ERR_PREMATURE_MUTATION_BEFORE_DISCRIMINATION")

        if errors:
            return FalsificationDecision(
                allowed=False,
                verdict="REJECTED_EPISTEMIC_DEFECT",
                error_codes=sorted(set(errors)),
                operational_yield=0,
                verified_receipt_ids=sorted(verified_map.keys()),
            )

        return FalsificationDecision(
            allowed=True,
            verdict="VERIFIED_DIAGNOSIS_PENDING_DISCRIMINATOR",
            error_codes=[],
            operational_yield=0,  # Diagnosis alone is FLOW, never operational yield.
            verified_receipt_ids=sorted(verified_map.keys()),
            details={"verified_scopes": sorted(verified_fact_scopes)},
        )

    def evaluate_operational_transition(
        self,
        contract: Dict[str, Any],
        receipts: Sequence[SignedReceipt],
        now_utc: Optional[datetime] = None,
        min_fencing_token: int = 1,
    ) -> FalsificationDecision:
        """Gate any transition to OPERATIONAL / yield=1 (Enforces E1 + E3 + E4)."""
        errors: List[str] = []
        verified_map, receipt_errors = self._verify_all_receipts(
            receipts, now_utc=now_utc, min_fencing_token=min_fencing_token
        )
        errors.extend(receipt_errors)

        # No caller-supplied empty/defaulted contract can certify arbitrary hosts or bodies.
        try:
            required_host = contract["expected_host"].lower().strip()
            required_path = contract["expected_path"]
            required_status = contract["expected_http_status"]
            required_body_substring = contract["expected_body_contains"]
            required_min_proofs = contract["min_independent_proofs"]
        except (KeyError, AttributeError, TypeError):
            required_host = ""
            required_path = ""
            required_status = None
            required_body_substring = ""
            required_min_proofs = 1
            errors.append("ERR_INVALID_OPERATIONAL_CONTRACT")
        if (
            not isinstance(required_host, str)
            or not required_host
            or ":" in required_host
            or "/" in required_host
            or not isinstance(required_path, str)
            or not required_path.startswith("/")
            or type(required_status) is not int
            or not (100 <= required_status <= 599)
            or not isinstance(required_body_substring, str)
            or not required_body_substring
            or type(required_min_proofs) is not int
            or not (1 <= required_min_proofs <= 10)
        ):
            errors.append("ERR_INVALID_OPERATIONAL_CONTRACT")
            required_min_proofs = (
                max(1, required_min_proofs) if type(required_min_proofs) is int else 1
            )

        matching_proofs: List[str] = []
        independent_authorities = set()

        for rid, r in verified_map.items():
            try:
                parsed = urlparse(r.target_uri)
                host = (parsed.hostname or "").lower()
                port = parsed.port
            except ValueError:
                errors.append(f"ERR_INVALID_RUNTIME_TARGET:{rid}")
                continue
            if (
                parsed.scheme != "https"
                or parsed.username is not None
                or parsed.password is not None
                or port not in (None, 443)
                or parsed.query
                or parsed.fragment
            ):
                errors.append(f"ERR_INVALID_RUNTIME_TARGET:{rid}")
                continue
            if (
                r.tier != EvidenceTier.TIER_0_RAW_MACHINE_RECEIPT.value
                or r.exit_code != 0
            ):
                errors.append(f"ERR_NON_PRIMARY_OR_FAILED_PROBE:{rid}")
                continue

            # E3: Hard ban on source-plane / GitHub raw proxy substitution.
            if (
                r.plane != ExecutionPlane.PLANE_PRODUCTION_RUNTIME.value
                or host in PROXY_SOURCE_HOSTS
            ):
                errors.append(f"ERR_PROXY_GREEN_SUBSTITUTION:{rid}")
                continue

            if required_host and host != required_host:
                errors.append(f"ERR_TARGET_HOST_MISMATCH:{rid}")
                continue

            if required_path and parsed.path != required_path:
                errors.append(f"ERR_TARGET_PATH_MISMATCH:{rid}")
                continue

            if r.http_status != required_status:
                errors.append(
                    f"ERR_RUNTIME_STATUS_MISMATCH:{rid}:got_{r.http_status}_want_{required_status}"
                )
                continue

            if required_body_substring and required_body_substring not in r.raw_payload:
                errors.append(f"ERR_RUNTIME_INVARIANT_MISSING:{rid}")
                continue

            matching_proofs.append(rid)
            independent_authorities.add(r.capture_authority)

        if len(matching_proofs) < required_min_proofs:
            errors.append(
                f"ERR_INSUFFICIENT_RUNTIME_PROOFS:got_{len(matching_proofs)}_want_{required_min_proofs}"
            )
        if len(independent_authorities) < required_min_proofs:
            errors.append(
                f"ERR_INSUFFICIENT_INDEPENDENT_AUTHORITIES:got_{len(independent_authorities)}_want_{required_min_proofs}"
            )
        # A single HMAC key with three arbitrary issuer labels is NOT three proofs.
        # Distinct keys only establish cryptographic separation, not physical control-plane
        # independence (that requires external custody attestation from existing QUAD).
        if required_min_proofs > 1:
            candidate_keys = [
                self._authority_keys.get(a) for a in independent_authorities
            ]
            distinct_key_digests = {
                hashlib.sha256(key).hexdigest()
                for key in candidate_keys
                if isinstance(key, bytes) and key
            }
            if len(distinct_key_digests) < required_min_proofs:
                errors.append("ERR_INDEPENDENT_KEY_CUSTODY_NOT_PROVEN")
        expected_revision = contract.get("expected_revision")
        if expected_revision is not None:
            if not isinstance(expected_revision, str) or not re.fullmatch(
                r"[a-f0-9]{40}", expected_revision
            ):
                errors.append("ERR_INVALID_EXPECTED_REVISION")
            else:
                for rid in matching_proofs:
                    try:
                        observed_revision = json.loads(verified_map[rid].raw_payload)[
                            "commit_sha"
                        ]
                    except (ValueError, TypeError, KeyError):
                        observed_revision = None
                    if observed_revision != expected_revision:
                        errors.append(f"ERR_RUNTIME_REVISION_MISMATCH:{rid}")

        if errors or len(matching_proofs) < required_min_proofs:
            return FalsificationDecision(
                allowed=False,
                verdict="NOT_OPERATIONAL",
                error_codes=sorted(set(errors)),
                operational_yield=0,
                verified_receipt_ids=matching_proofs,
            )

        return FalsificationDecision(
            allowed=True,
            verdict="VERIFIED_OPERATIONAL_YIELD",
            error_codes=[],
            operational_yield=1,
            verified_receipt_ids=sorted(matching_proofs),
            details={"independent_authorities": sorted(independent_authorities)},
        )
