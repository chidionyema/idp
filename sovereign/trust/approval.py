"""A signed approval, and the three ways one can be refused (cp29).

Spec v1.0 4.1: "No signature, no act." Before this module `sb approve`
took a `--by` string and nothing else, so anything that could reach the
Temporal frontend could approve anything -- the founder's name was the
only credential and it is not a secret. An approval now travels as an
envelope: what is being approved, when, under which counter, and a
signature over exactly those fields.

Three refusals, and each one exists because the other two do not cover it:

  signature required   -- no signature at all (cp29 scenario 1)
  counter already used -- a real signature, replayed (cp29 scenario 2)
  approval expired     -- a real, unused signature captured and held

The counter is the receipt chain's own monotonic counter
(sovereign/engine/receipts.py), not a second sequence invented here. The
chain already increments once per line under a file lock, so an approval
bound to "the counter the chain is about to reach" is bound to something
that never repeats and that the audit trail already records. A spent
counter is written to a replay ledger under $ESTATE_HOME/sovereign before
the approval is acted on, so a crash between the two leaves an approval
refused, never an approval spent twice.

Degraded mode (cp29 scenario 3) is not a bypass. When the enclave is gone
the envelope is signed by `trust.multisig_threshold` distinct members of
the `trust.multisig_signers` set instead -- 2-of-3 by default -- and the
receipt carries attestation:fallback so the log says which root of trust
was standing when the act happened. One signer alone is refused exactly
like no signer at all.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any

from sovereign import config
from sovereign.trust import anchor as anchor_mod
from sovereign.trust import config_keys as ck
from sovereign.trust.anchor import HardwareTrustAnchor

# The refusal strings are the contract cp29 names, so they live in one
# place and the CLI, the tests and the feature file cannot drift apart.
REFUSED_UNSIGNED = "signature required"
REFUSED_REPLAY = "counter already used"
REFUSED_EXPIRED = "approval expired"
REFUSED_BAD_SIGNATURE = "signature does not verify"
REFUSED_QUORUM = "fallback quorum not met"

# Fields the digest is taken over. `sig`, `signers` and `attestation` are
# excluded for the obvious reason; listing the included set explicitly (as
# opposed to excluding a blacklist) means a field added later cannot
# silently fall outside the signature.
SIGNED_FIELDS = ("session_id", "action", "by", "counter", "nonce", "issued_at")


def _used_counters_path() -> Path:
    return config.SOVEREIGN_HOME / ck.get("trust.used_counters_filename")


def _spent_counters() -> set[int]:
    path = _used_counters_path()
    if not path.exists():
        return set()
    out: set[int] = set()
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            out.add(int(line))
    return out


def _next_counter() -> int:
    """The next counter no approval has used. Read, not reserved:
    reserving would need the receipt chain's own lock and would strand the
    counter if the founder never signs.

    It is the max of two sequences, and it has to be. The receipt chain's
    counter is the monotonic one, but two challenges issued back to back
    -- before either is acted on and appends a line -- would read the same
    chain counter and the second would then be refused as a replay of the
    first. The replay ledger is the other half: a counter already spent is
    never offered again. (Defect found by the cp29 smoke run, 2026-08-25:
    a fallback challenge issued after a hardware approval was refused with
    "counter already used" for exactly this reason.)"""
    from sovereign.engine import receipts as receipts_mod

    rows = receipts_mod.read_all()
    chain_last = int(rows[-1].get("counter", 0)) if rows else 0
    spent = _spent_counters()
    return max(chain_last, max(spent) if spent else 0) + 1


def digest_of(envelope: dict[str, Any]) -> str:
    body = {k: envelope.get(k) for k in SIGNED_FIELDS}
    return hashlib.sha256(config.canonical_json(body)).hexdigest()


def challenge(session_id: str, action: str, by: str) -> dict[str, Any]:
    """The thing to be signed. Carries a nonce as well as a counter so two
    approvals of the same action, in the same second, under the same
    counter still have different digests."""
    envelope: dict[str, Any] = {
        "session_id": session_id,
        "action": action,
        "by": by,
        "counter": _next_counter(),
        "nonce": secrets.token_hex(int(ck.get("trust.approval_nonce_bytes"))),
        "issued_at": time.time(),
    }
    envelope["digest"] = digest_of(envelope)
    return envelope


def sign(envelope: dict[str, Any], trust_anchor: HardwareTrustAnchor | None = None) -> dict[str, Any]:
    """Sign a challenge with the hardware root of trust. On macOS with an
    enclave this prompts for Touch ID inside presence_helper.swift and the
    private key never leaves it. Returns the envelope with `sig`,
    `backend` and `attestation` filled in."""
    trust_anchor = trust_anchor or HardwareTrustAnchor()
    digest = digest_of(envelope)
    signature, backend_used = trust_anchor.sign(digest)
    out = dict(envelope)
    out["digest"] = digest
    out["sig"] = signature
    out["backend"] = backend_used
    # Label the attestation by what actually signed, never by what was
    # asked for. software_key is a 0600 file, not hardware, and a receipt
    # that called it hardware would be the one lie the whole chain exists
    # to prevent.
    out["attestation"] = str(ck.get(
        "trust.attestation_hardware_label" if backend_used != "software_key"
        else "trust.attestation_fallback_label"
    ))
    if backend_used == "secure_enclave":
        trust_anchor.enroll()
    return out


def sign_fallback(envelope: dict[str, Any], signer_ids: list[str] | None = None) -> dict[str, Any]:
    """cp29 scenario 3: the enclave is unavailable, so the configured
    multi-signature set signs instead. Returns the envelope with a
    `signers` map and attestation:fallback."""
    ids = signer_ids if signer_ids is not None else anchor_mod.signer_ids()
    digest = digest_of(envelope)
    out = dict(envelope)
    out["digest"] = digest
    out["signers"] = {sid: anchor_mod.sign_as(sid, digest) for sid in ids}
    out["backend"] = "multisig"
    out["attestation"] = str(ck.get("trust.attestation_fallback_label"))
    return out


def _counter_used(counter: int) -> bool:
    return counter in _spent_counters()


def spend(counter: int) -> None:
    """Mark a counter used. Called by the caller that is about to act,
    before it acts."""
    path = _used_counters_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(str(counter) + os.linesep)


def _fallback_quorum(envelope: dict[str, Any], digest: str) -> tuple[int, list[str]]:
    signers = envelope.get("signers") or {}
    if not isinstance(signers, dict):
        return 0, []
    good = [sid for sid, sig in signers.items() if anchor_mod.verify_signer(str(sid), digest, str(sig))]
    return len(good), sorted(good)


def verify(
    envelope: dict[str, Any] | None,
    trust_anchor: HardwareTrustAnchor | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    """Returns {"ok", "reason", "attestation", "counter", "signers"}.

    Fails closed on every path. `reason` is None only when ok is True, and
    is one of the REFUSED_* strings otherwise, so a caller never has to
    parse prose to know which refusal fired."""
    threshold = int(ck.get("trust.multisig_threshold"))
    refused = {"ok": False, "attestation": None, "counter": None, "signers": []}

    if not envelope:
        return {**refused, "reason": REFUSED_UNSIGNED}
    has_hw_sig = bool(envelope.get("sig"))
    has_signers = bool(envelope.get("signers"))
    if not (has_hw_sig or has_signers):
        return {**refused, "reason": REFUSED_UNSIGNED}

    counter = envelope.get("counter")
    if counter is None:
        return {**refused, "reason": REFUSED_UNSIGNED}
    counter = int(counter)

    digest = digest_of(envelope)
    if envelope.get("digest") and str(envelope["digest"]) != digest:
        # The envelope was edited after signing: the digest it carries no
        # longer matches its own signed fields.
        return {**refused, "reason": REFUSED_BAD_SIGNATURE, "counter": counter}

    ttl = float(ck.get("trust.approval_ttl_s"))
    issued_at = float(envelope.get("issued_at") or 0)
    if (now if now is not None else time.time()) - issued_at > ttl:
        return {**refused, "reason": REFUSED_EXPIRED, "counter": counter}

    if _counter_used(counter):
        return {**refused, "reason": REFUSED_REPLAY, "counter": counter}

    if has_hw_sig:
        trust_anchor = trust_anchor or HardwareTrustAnchor()
        backend = str(envelope.get("backend") or trust_anchor.backend)
        if not trust_anchor.verify(digest, str(envelope["sig"]), backend):
            return {**refused, "reason": REFUSED_BAD_SIGNATURE, "counter": counter}
        return {
            "ok": True,
            "reason": None,
            "attestation": str(ck.get(
                "trust.attestation_hardware_label" if backend != "software_key"
                else "trust.attestation_fallback_label"
            )),
            "counter": counter,
            "signers": [],
        }

    good, ids = _fallback_quorum(envelope, digest)
    if good < threshold:
        return {**refused, "reason": REFUSED_QUORUM, "counter": counter, "signers": ids}
    return {
        "ok": True,
        "reason": None,
        "attestation": str(ck.get("trust.attestation_fallback_label")),
        "counter": counter,
        "signers": ids,
    }


def load(raw: str | None) -> dict[str, Any] | None:
    """Parse an envelope handed in on the command line. A malformed
    envelope is None -- indistinguishable from absent, and refused the
    same way, so a mangled paste can never read as a valid approval."""
    if not raw:
        return None
    candidate = Path(raw)
    try:
        if candidate.exists():
            raw = candidate.read_text()
    except OSError:
        return None
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None
