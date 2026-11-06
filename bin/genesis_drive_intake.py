#!/usr/bin/env python3
"""Untrusted Gemini Drive relay envelope validator. No execution or promotion."""
import hashlib
import json
import re
import sys

MAX_BYTES = 32768
ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{7,127}$")
HEX = re.compile(r"^[a-f0-9]{64}$")
ALLOWED_REPOS = frozenset(("chidionyema/idp", "chidionyema/argon",
                           "chidionyema/argon-sync", "chidionyema/crew",
                           "chidionyema/estate-graph"))
FIELDS = frozenset(("schema_version", "event_id", "source", "source_sha256",
                    "document_id", "target_repo", "intent"))

def validate(raw):
    if len(raw) > MAX_BYTES:
        raise ValueError("envelope too large")
    obj = json.loads(raw)
    if not isinstance(obj, dict) or set(obj) != FIELDS:
        raise ValueError("unexpected envelope fields")
    if obj["schema_version"] != 1 or obj["source"] != "gemini-web-drive":
        raise ValueError("invalid source/version")
    if not isinstance(obj["event_id"], str) or not ID.fullmatch(obj["event_id"]):
        raise ValueError("invalid event ID")
    if not isinstance(obj["document_id"], str) or not ID.fullmatch(obj["document_id"]):
        raise ValueError("invalid document ID")
    if not isinstance(obj["source_sha256"], str) or not HEX.fullmatch(obj["source_sha256"]):
        raise ValueError("invalid source digest")
    if obj["target_repo"] not in ALLOWED_REPOS:
        raise ValueError("invalid target")
    if obj["intent"] != "review-only":
        raise ValueError("privileged intent refused")
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return {"status": "QUARANTINED_REVIEW_ONLY", "event_id": obj["event_id"],
            "envelope_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
            "source_sha256": obj["source_sha256"], "target_repo": obj["target_repo"],
            "note": "Transport receipt only; no source authentication, approval, or execution"}

def main():
    try:
        raw = sys.stdin.buffer.read(MAX_BYTES + 1)
        print(json.dumps(validate(raw), sort_keys=True))
    except (ValueError, TypeError, KeyError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "REJECTED", "error": str(exc)}), file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
