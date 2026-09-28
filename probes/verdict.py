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
    """What a gate may conclude from a verdict file. Returns (state, why).

    state is one of PASS, FAIL, BLOCKED, ERROR, UNVERIFIED. UNVERIFIED is every case where the
    verdict cannot be trusted: bad or missing signature, expired, or about a different artifact.
    Fail closed: a verdict the gate cannot check is a verdict that does not exist.
    """
    for k in FIELDS:
        if k not in v:
            return "UNVERIFIED", f"field {k} missing"
    if v["outcome"] not in OUTCOMES:
        return "UNVERIFIED", f"outcome {v['outcome']!r} is not one of {OUTCOMES}"
    if key is not None and not signature_ok(v, key):
        return "UNVERIFIED", "signature does not match the record"
    if key is None and not v.get("sig"):
        return "UNVERIFIED", "record carries no signature"
    now = time.time() if now is None else now
    try:
        age = now - _epoch(v["completed_at"])
    except (ValueError, TypeError):
        return "UNVERIFIED", f"completed_at {v['completed_at']!r} unreadable"
    if age > int(v["ttl_seconds"]):
        return "UNVERIFIED", f"expired: {int(age)}s old, ttl {v['ttl_seconds']}s"
    if age < -60:
        return "UNVERIFIED", f"completed_at is {int(-age)}s in the future"
    if artifact_digest and v["artifact_digest"] != artifact_digest:
        return (
            "UNVERIFIED",
            f"about digest {v['artifact_digest'][:24]}, target runs {artifact_digest[:24]}",
        )
    if not v["artifact_digest"] and v["outcome"] == "PASS":
        return (
            "UNVERIFIED",
            "PASS with no artifact digest: a verdict about a service name is not a verdict",
        )
    bad = [a["name"] for a in v["assertions"] if not a.get("ok")]
    return v["outcome"], (
        "all assertions ok" if not bad else "failed: " + ", ".join(bad)
    )
