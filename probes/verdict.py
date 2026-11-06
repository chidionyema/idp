"""The verdict record (crew#631 CP1).

A verdict is a signed statement by the prover about one running artifact at one moment. It is
useless as prose: every field below is read by a gate, none by a person's eye. Five fields close
five specific holes and each is named next to the field.
"""

import calendar
import hashlib
import hmac
import json
import time
import uuid

OUTCOMES = ("PASS", "FAIL", "BLOCKED", "ERROR")
FIELDS = (
    "verdict_id",
    "check_id",
    "target",
    "commit_sha",
    "artifact_digest",  # the image digest that was running; a redeploy voids the verdict
    "config_revision",  # the release revision under test, same reason
    "nonce",  # issued per request; an old PASS cannot be pointed at again
    "started_at",
    "completed_at",
    "ttl_seconds",  # after this the verdict is UNVERIFIED, not PASS
    "outcome",
    "assertions",
    "evidence_ref",
    "prover_id",
    "prover_run_id",
)


def assertion(name, expected, actual, ok):
    return {
        "name": name,
        "expected": str(expected),
        "actual": str(actual)[:400],
        "ok": bool(ok),
    }


def canonical(v):
    """The bytes the signature covers: every field but sig, sorted keys, no whitespace."""
    body = {k: v.get(k) for k in FIELDS}
    return json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()


def sign(v, key):
    v = dict(v)
    v["sig"] = hmac.new(
        key.encode() if isinstance(key, str) else key, canonical(v), hashlib.sha256
    ).hexdigest()
    return v


def signature_ok(v, key):
    want = hmac.new(
        key.encode() if isinstance(key, str) else key, canonical(v), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(want, str(v.get("sig", "")))


def build(
    check_id,
    target,
    commit_sha,
    artifact_digest,
    config_revision,
    assertions,
    *,
    nonce=None,
    started_at=None,
    ttl_seconds=900,
    prover_id="",
    prover_run_id="",
    evidence_ref=None,
    blocked=None,
):
    """Assemble a verdict. `blocked` names why the target could not be measured (digest unknown,
    credentials absent): the outcome is then BLOCKED whatever the assertions say, because a
    verdict about an unknown artifact is a verdict about nothing."""
    now = time.time()
    if blocked:
        outcome = "BLOCKED"
        assertions = list(assertions) + [
            assertion("prover.blocked", "measurable target", blocked, False)
        ]
    elif not assertions:
        outcome = "ERROR"
    else:
        outcome = "PASS" if all(a["ok"] for a in assertions) else "FAIL"
    return {
        "verdict_id": str(uuid.uuid4()),
        "check_id": check_id,
        "target": target,
        "commit_sha": commit_sha,
        "artifact_digest": artifact_digest or "",
        "config_revision": config_revision or "",
        "nonce": nonce or str(uuid.uuid4()),
        "started_at": _iso(started_at or now),
        "completed_at": _iso(now),
        "ttl_seconds": int(ttl_seconds),
        "outcome": outcome,
        "assertions": list(assertions),
        "evidence_ref": evidence_ref,
        "prover_id": prover_id,
        "prover_run_id": prover_run_id,
    }


def _iso(t):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def _epoch(s):
    return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))


def grade(v, key=None, *, now=None, artifact_digest=None):
    """Authenticate an HMAC verdict, then inspect its claims.

    Without the independently held verification key there is NO authenticated
    PASS, even when the record contains a non-empty sig field. This primitive
    must never depend on the claimed verifier ID or a workflow's prose.
    For a separately authenticated Sigstore attestation, call
    inspect_claims_after_external_authentication only AFTER validating that
    attestation with its trusted verifier.
    """
    if not isinstance(key, (bytes, str)) or not key:
        return "UNVERIFIED", "authenticating key unavailable; signature bytes are not proof"
    if not isinstance(v, dict) or not signature_ok(v, key):
        return "UNVERIFIED", "signature does not match the record"
    return inspect_claims_after_external_authentication(
        v, now=now, artifact_digest=artifact_digest
    )


def inspect_claims_after_external_authentication(v, *, now=None, artifact_digest=None):
    """Check the authenticated record's declared outcome and freshness.

    THIS DOES NOT AUTHENTICATE ITS CALLER. Never call it on an unverified
    download or a raw agent-produced record: the only production call site
    verifies the GitHub Sigstore attestation for the exact downloaded bytes,
    signer workflow, repository and source SHA before calling this function.
    A PASS claim with a failed or absent assertion is UNVERIFIED, not PASS.
    """
    if not isinstance(v, dict):
        return "UNVERIFIED", "verdict is not an object"
    for k in FIELDS:
        if k not in v:
            return "UNVERIFIED", f"field {k} missing"
    if v["outcome"] not in OUTCOMES:
        return "UNVERIFIED", f"outcome {v['outcome']!r} is not one of {OUTCOMES}"
    if isinstance(v["ttl_seconds"], bool) or not isinstance(v["ttl_seconds"], int):
        return "UNVERIFIED", "TTL must be an integer number of seconds"
    if not 1 <= v["ttl_seconds"] <= 3600:
        return "UNVERIFIED", "TTL exceeds the 3600-second verifier ceiling or is invalid"
    if not isinstance(v["assertions"], list) or not v["assertions"]:
        return "UNVERIFIED", "no verifier assertions to substantiate the outcome"
    if any(
        not isinstance(a, dict)
        or not isinstance(a.get("ok"), bool)
        or not isinstance(a.get("name"), str)
        or not a["name"]
        for a in v["assertions"]
    ):
        return "UNVERIFIED", "verifier assertions have an invalid schema"
    if not isinstance(v["artifact_digest"], str):
        return "UNVERIFIED", "artifact digest must be a string"
    if not isinstance(v["nonce"], str) or not v["nonce"].strip():
        return "UNVERIFIED", "nonce missing"
    now = time.time() if now is None else now
    try:
        age = now - _epoch(v["completed_at"])
        duration = _epoch(v["completed_at"]) - _epoch(v["started_at"])
    except (ValueError, TypeError, OverflowError):
        return "UNVERIFIED", "verdict timestamps are invalid"
    if duration < -60 or duration > 3600:
        return "UNVERIFIED", "verdict run duration is implausible"
    if age > v["ttl_seconds"]:
        return "UNVERIFIED", f"expired: {int(age)}s old, ttl {v['ttl_seconds']}s"
    if age < -60:
        return "UNVERIFIED", f"completed_at is {int(-age)}s in the future"
    if artifact_digest and v["artifact_digest"] != artifact_digest:
        return (
            "UNVERIFIED",
            f"about digest {v['artifact_digest'][:24]}, target runs {artifact_digest[:24]}",
        )
    if not v["artifact_digest"] and v["outcome"] == "PASS":
        return "UNVERIFIED", "PASS with no artifact digest"
    bad = [a["name"] for a in v["assertions"] if not a["ok"]]
    if v["outcome"] == "PASS" and bad:
        return "UNVERIFIED", "PASS contradicted by failed assertions: " + ", ".join(bad)
    return v["outcome"], (
        "all assertions ok" if not bad else "failed: " + ", ".join(bad)
    )
