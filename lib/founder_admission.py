"""Single founder-outbound proof enforcement point (PEP), governed by idp#8478.

Only the transport owner may call send_checked at the final send boundary.  This
module authenticates evidence, not an agent's assertion that it searched, nor a
source/CI result offered as a production effect.  Its trust roots and evidence
reader MUST be separately provisioned by the runtime's verifier identity.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Callable
from urllib.parse import urlsplit

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from lib.epistemic_kernel import EvidenceTier, ExecutionPlane
from lib.epistemic_kernel.kernel import PROXY_SOURCE_HOSTS, SCOPE_HIERARCHY


class AdmissionDenied(ValueError):
    """Machine-readable denial cause; caller must conserve the original duty."""


BINDING = (
    "instruction_id",
    "obligation_id",
    "claim_id",
    "actor_id",
    "target",
    "revision",
    "environment",
    "observation_window",
)
PROOF_ROLES = ("execution", "effect", "independent_verification")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
GITSHA = re.compile(r"^[a-f0-9]{40}$")
MAX_AGE = timedelta(hours=1)


def _canonical(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def preserve_instruction(raw: bytes, recorded_digest: str) -> None:
    if (
        not isinstance(raw, bytes)
        or not isinstance(recorded_digest, str)
        or not hmac.compare_digest(digest(raw), recorded_digest)
    ):
        raise AdmissionDenied("instruction-integrity")


def _time(value: object) -> datetime:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise AdmissionDenied("invalid-time") from exc
    if dt.tzinfo is None:
        raise AdmissionDenied("naive-time")
    return dt.astimezone(timezone.utc)


def _url(value: object, *, runtime: bool) -> str:
    try:
        parsed = urlsplit(str(value))
        host = parsed.hostname
        if (
            parsed.scheme != "https"
            or not host
            or parsed.username
            or parsed.password
            or not parsed.path.startswith("/")
        ):
            raise ValueError("invalid target")
        if runtime and (
            host.lower() in PROXY_SOURCE_HOSTS
            or host.lower().endswith(".githubusercontent.com")
        ):
            raise ValueError("source proxy cannot certify operational effect")
        return str(value)
    except (TypeError, ValueError) as exc:
        raise AdmissionDenied(
            "invalid-runtime-target" if runtime else "invalid-evidence-uri"
        ) from exc


def _authenticate(
    envelope: object,
    trust_roots: dict,
    expected_role: str,
) -> tuple[dict, dict, str]:
    """Verifier-supplied Ed25519 root: role alone or a model flag is never authority."""
    if not isinstance(envelope, dict):
        raise AdmissionDenied("missing-signed-envelope")
    key_id, payload = envelope.get("key_id"), envelope.get("payload")
    if not isinstance(key_id, str) or not isinstance(payload, dict):
        raise AdmissionDenied("malformed-signed-envelope")
    root = trust_roots.get(key_id)
    if not isinstance(root, dict) or root.get("role") != expected_role:
        raise AdmissionDenied("untrusted-role")
    if not root.get("control_plane") or root.get("control_plane") == "agent":
        raise AdmissionDenied("unisolated-authority")
    try:
        raw_key = bytes.fromhex(root["public_key_hex"])
        pub = Ed25519PublicKey.from_public_bytes(raw_key)
        pub.verify(bytes.fromhex(envelope["signature_hex"]), _canonical(payload))
    except (KeyError, TypeError, ValueError, InvalidSignature) as exc:
        raise AdmissionDenied("invalid-signature") from exc
    return payload, root, digest(raw_key)


def _fresh(payload: dict, now: datetime, start: datetime, end: datetime) -> None:
    seen, expires = _time(payload.get("observed_at")), _time(payload.get("expires_at"))
    if not start <= seen <= end or seen > now or expires <= now or now - seen > MAX_AGE:
        raise AdmissionDenied("stale-future-or-out-of-window")


def _independent_evidence(
    payload: dict, role: str, reader: Callable[[str], bytes]
) -> dict:
    uri = _url(payload.get("evidence_uri"), runtime=False)
    hash_value = payload.get("evidence_digest")
    if not isinstance(hash_value, str) or not SHA256.fullmatch(hash_value):
        raise AdmissionDenied("invalid-evidence-digest")
    try:
        raw = reader(uri)
        if not isinstance(raw, bytes) or not hmac.compare_digest(
            digest(raw), hash_value
        ):
            raise AdmissionDenied("evidence-digest-mismatch")
        document = json.loads(raw)
    except AdmissionDenied:
        raise
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        raise AdmissionDenied("evidence-not-independently-readable") from exc
    if not isinstance(document, dict):
        raise AdmissionDenied("invalid-evidence-document")
    if role != "execution" and urlsplit(uri).hostname in PROXY_SOURCE_HOSTS:
        raise AdmissionDenied("proxy-green-substitution")
    return document


def _diagnosis(claim: dict, proofs: list[dict]) -> None:
    """E2: no negative global assertion based on only a job-local observation."""
    diag = claim.get("diagnosis")
    if not diag:
        if claim.get("asserts_nonexistence") or claim.get("requests_mutation"):
            raise AdmissionDenied("unfalsified-negation-or-mutation")
        return
    if not isinstance(diag, dict):
        raise AdmissionDenied("invalid-diagnosis")
    hypotheses = diag.get("competing_hypotheses")
    if not isinstance(hypotheses, list) or len(hypotheses) < 2:
        raise AdmissionDenied("no-competing-hypotheses")
    for h in hypotheses:
        if not isinstance(h, dict) or any(
            not h.get(k) for k in ("statement", "falsified_by", "discriminating_probe")
        ):
            raise AdmissionDenied("unfalsifiable-hypothesis")
    if len({h.get("statement") for h in hypotheses}) < 2:
        raise AdmissionDenied("duplicate-hypotheses")
    if claim.get("requests_mutation") and not diag.get("discrimination_receipt"):
        raise AdmissionDenied("mutation-before-discrimination")
    observed = diag.get("observed_scope", "job_env")
    asserted = diag.get("asserted_scope", observed)
    if observed not in SCOPE_HIERARCHY or asserted not in SCOPE_HIERARCHY:
        raise AdmissionDenied("unknown-evidence-scope")
    if SCOPE_HIERARCHY[asserted] > SCOPE_HIERARCHY[observed]:
        covered = set().union(*(set(p.get("covered_scopes", [])) for p in proofs))
        if not {"repo_secrets", "vault_store", "provider_account"}.issubset(covered):
            raise AdmissionDenied("scope-leaping-negation")


def admit(
    claim: dict,
    discovery: dict,
    proofs: list[dict],
    *,
    now: datetime,
    trust_roots: dict,
    read_evidence: Callable[[str], bytes] | None = None,
) -> None:
    """Prove status before a send.  No independent observer => DENY, not a waiver.

    The runtime MUST inject an independently authenticated evidence reader and
    independently provisioned, immutable trust roots, never values from a model
    or from the submitted claim.  This code cannot certify physical custody by
    simply seeing distinct names; root *public keys and control planes* differ.
    """
    if now.tzinfo is None:
        raise AdmissionDenied("naive-now")
    now = now.astimezone(timezone.utc)
    if not callable(read_evidence) or not isinstance(trust_roots, dict):
        raise AdmissionDenied("no-independent-evidence-reader")
    if not isinstance(claim, dict) or any(not claim.get(k) for k in BINDING):
        raise AdmissionDenied("missing-claim-binding")
    if not GITSHA.fullmatch(str(claim["revision"])):
        raise AdmissionDenied("missing-exact-revision")
    target = _url(claim["target"], runtime=True)
    if not isinstance(claim.get("expected_body"), str) or not claim["expected_body"]:
        raise AdmissionDenied("missing-runtime-body-invariant")
    if not isinstance(claim.get("expected_http_status"), int):
        raise AdmissionDenied("missing-expected-http-status")
    window = claim["observation_window"]
    if not isinstance(window, dict):
        raise AdmissionDenied("invalid-observation-window")
    start, end = _time(window.get("start")), _time(window.get("end"))
    if not start <= end or end < now - MAX_AGE:
        raise AdmissionDenied("expired-observation-window")

    # The original founder instruction is immutable and byte-verified, not rephrased.
    raw_instruction = claim.get("original_instruction_bytes")
    if not isinstance(raw_instruction, bytes):
        raise AdmissionDenied("original-instruction-unavailable")
    preserve_instruction(raw_instruction, claim.get("original_instruction_sha256", ""))

    d, d_root, d_key = _authenticate(discovery, trust_roots, "discovery")
    _fresh(d, now, start, end)
    if not d.get("searched_sources") or d.get("contradictions"):
        raise AdmissionDenied("undiscovered-or-contradictory-reality")
    if any(d.get(k) != claim[k] for k in BINDING):
        raise AdmissionDenied("discovery-binding-mismatch")
    if not isinstance(proofs, list) or len(proofs) != 3:
        raise AdmissionDenied("three-proofs-required")
    documents: list[dict] = []
    root_keys = {d_key}
    root_planes = {d_root["control_plane"]}
    proof_hashes = []
    proof_uris = set()
    proof_payloads = []
    for index, role in enumerate(PROOF_ROLES):
        p, root, key = _authenticate(proofs[index], trust_roots, role)
        if key in root_keys or root["control_plane"] in root_planes:
            raise AdmissionDenied("correlated-evidence-custody")
        root_keys.add(key)
        root_planes.add(root["control_plane"])
        if any(p.get(k) != claim[k] for k in BINDING):
            raise AdmissionDenied("proof-binding-mismatch")
        _fresh(p, now, start, end)
        if p.get("tier") != EvidenceTier.TIER_0_RAW_MACHINE_RECEIPT.value:
            raise AdmissionDenied("epistemic-laundering")
        if (
            role != "execution"
            and p.get("plane") != ExecutionPlane.PLANE_PRODUCTION_RUNTIME.value
        ):
            raise AdmissionDenied("proxy-green-substitution")
        if (
            p.get("capture_authority") != proofs[index]["key_id"]
            or p.get("capture_authority") == claim["actor_id"]
        ):
            raise AdmissionDenied("self-attested-claim")
        uri = p.get("evidence_uri")
        if uri in proof_uris:
            raise AdmissionDenied("duplicate-evidence-lineage")
        proof_uris.add(uri)
        obs = _independent_evidence(p, role, read_evidence)
        if role == "execution":
            if (
                obs.get("actor_id") != claim["actor_id"]
                or not obs.get("operation")
                or not obs.get("output_sha256")
            ):
                raise AdmissionDenied("unauthenticated-execution")
        else:
            if (
                obs.get("target") != target
                or obs.get("revision") != claim["revision"]
                or obs.get("status") != claim["expected_http_status"]
                or claim["expected_body"] not in str(obs.get("body", ""))
            ):
                raise AdmissionDenied("runtime-effect-contradicted")
        documents.append(obs)
        proof_payloads.append(p)
        proof_hashes.append(digest(_canonical(p)))
    _diagnosis(claim, proof_payloads)
    certificate, root, key = _authenticate(
        claim.get("certificate"), trust_roots, "certifier"
    )
    if key in root_keys or root["control_plane"] in root_planes:
        raise AdmissionDenied("self-certified-outcome")
    _fresh(certificate, now, start, end)
    if certificate.get("decision") != "ALLOW" or any(
        certificate.get(k) != claim[k] for k in BINDING
    ):
        raise AdmissionDenied("certificate-denied-or-mismatched")
    # The certifier commits to the original instruction, whole claim, fresh discovery
    # and all three exact proof payloads, never only their role names.
    original = {
        k: v
        for k, v in claim.items()
        if k not in {"certificate", "original_instruction_bytes"}
    }
    if (
        certificate.get("claim_digest") != digest(_canonical(original))
        or certificate.get("discovery_digest") != digest(_canonical(d))
        or certificate.get("proof_digests") != sorted(proof_hashes)
    ):
        raise AdmissionDenied("certificate-evidence-mismatch")


def send_checked(
    sender: Callable[[bytes], object],
    payload: bytes,
    claim: dict,
    discovery: dict,
    proofs: list[dict],
    *,
    now: datetime,
    trust_roots: dict,
    read_evidence: Callable[[str], bytes] | None,
    conserve_obligation: Callable[[dict], object] | None,
) -> object:
    """Single PEP for automated founder-status send: DENY before transport IO.

    The transport is responsible for passing through human-origin or emergency
    warnings via its separately authorised safe path; it must never mislabel an
    automated status as human.  No local 'verified' flag can bypass this call.
    """
    if not callable(conserve_obligation):
        raise AdmissionDenied("no-durable-obligation-conservation")
    try:
        admit(
            claim,
            discovery,
            proofs,
            now=now,
            trust_roots=trust_roots,
            read_evidence=read_evidence,
        )
    except AdmissionDenied as exc:
        conserve_obligation(
            {
                "verdict": "DENY",
                "reason": str(exc),
                "instruction_id": claim.get("instruction_id")
                if isinstance(claim, dict)
                else None,
                "obligation_id": claim.get("obligation_id")
                if isinstance(claim, dict)
                else None,
                "claim_id": claim.get("claim_id") if isinstance(claim, dict) else None,
            }
        )
        raise
    return sender(payload)
