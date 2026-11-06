#!/usr/bin/env python3
"""Untrusted Gemini Drive relay envelope validator. No execution or promotion."""

import hashlib
import hmac
import json
import os
import re
import sys
import time

MAX_BYTES = 32768
ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{7,127}$")
HEX = re.compile(r"^[a-f0-9]{64}$")
ALLOWED_REPOS = frozenset(
    (
        "chidionyema/idp",
        "chidionyema/argon",
        "chidionyema/argon-sync",
        "chidionyema/crew",
        "chidionyema/estate-graph",
    )
)
FIELDS = frozenset(
    (
        "schema_version",
        "event_id",
        "source",
        "source_sha256",
        "document_id",
        "target_repo",
        "intent",
        "issued_at",
        "signature",
    )
)


def reject_duplicate_keys(pairs):
    """Refuse duplicate JSON members instead of silently changing signed data."""
    obj = {}
    for name, value in pairs:
        if name in obj:
            raise ValueError("duplicate JSON field")
        obj[name] = value
    return obj


def signing_bytes(obj):
    """Canonical cross-language signed bytes in exact documented field order."""
    return "\n".join(
        (
            str(obj["schema_version"]),
            obj["event_id"],
            obj["source"],
            obj["source_sha256"],
            obj["document_id"],
            obj["target_repo"],
            obj["intent"],
            str(obj["issued_at"]),
        )
    ).encode("utf-8")


def validate(raw, key=None, now=None):
    if len(raw) > MAX_BYTES:
        raise ValueError("envelope too large")
    obj = json.loads(raw, object_pairs_hook=reject_duplicate_keys)
    if not isinstance(obj, dict) or set(obj) != FIELDS:
        raise ValueError("unexpected envelope fields")
    if (
        type(obj["schema_version"]) is not int
        or obj["schema_version"] != 1
        or obj["source"] != "gemini-web-drive"
    ):
        raise ValueError("invalid source/version")
    if not isinstance(obj["event_id"], str) or not ID.fullmatch(obj["event_id"]):
        raise ValueError("invalid event ID")
    if not isinstance(obj["document_id"], str) or not ID.fullmatch(obj["document_id"]):
        raise ValueError("invalid document ID")
    if not isinstance(obj["source_sha256"], str) or not HEX.fullmatch(
        obj["source_sha256"]
    ):
        raise ValueError("invalid source digest")
    if obj["target_repo"] not in ALLOWED_REPOS:
        raise ValueError("invalid target")
    if obj["intent"] != "review-only":
        raise ValueError("privileged intent refused")
    stamp = obj["issued_at"]
    current = int(time.time()) if now is None else now
    if type(stamp) is not int or abs(current - stamp) > 900:
        raise ValueError("stale/future timestamp")
    key = os.environ.get("GENESIS_DRIVE_RELAY_HMAC_KEY", "") if key is None else key
    if not isinstance(key, str) or len(key.encode("utf-8")) < 32:
        raise ValueError("missing independent sender verification key")
    sig = obj["signature"]
    if not isinstance(sig, str) or not HEX.fullmatch(sig):
        raise ValueError("invalid sender signature")
    expected = hmac.new(
        key.encode("utf-8"), signing_bytes(obj), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise ValueError("sender signature mismatch")
    canonical = json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return {
        "status": "QUARANTINED_AUTHENTICATED_REVIEW_ONLY",
        "event_id": obj["event_id"],
        "envelope_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "source_sha256": obj["source_sha256"],
        "document_ref_sha256": hashlib.sha256(
            obj["document_id"].encode("utf-8")
        ).hexdigest(),
        "target_repo": obj["target_repo"],
        "note": (
            "Authenticated relay sender only; Gemini authorship and source "
            "integrity require independent evidence. No approval or execution"
        ),
    }


def main():
    try:
        raw = sys.stdin.buffer.read(MAX_BYTES + 1)
        print(json.dumps(validate(raw), sort_keys=True))
    except (ValueError, TypeError, KeyError, UnicodeError, json.JSONDecodeError):
        print(
            json.dumps({"status": "REJECTED", "error": "INVALID_ENVELOPE"}),
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
