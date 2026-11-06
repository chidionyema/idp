#!/usr/bin/env python3
"""Fail-closed proof of operational completion for estate agents.

A dispatch, CI pass or PR cannot substitute for a deployed revision and live probe.
Input is an untrusted JSON evidence document; output is a deterministic verdict.
"""
import argparse
import datetime as dt
import json
import re
import sys

SHA = re.compile(r"^[0-9a-f]{40}$")
REQUIRED = ("mission_id", "source_sha", "promoted_sha", "deployed_sha",
            "greenlane", "independent_review", "deployment", "functional_probe",
            "founder_surface")


def evaluate(evidence, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    reasons = []
    if not isinstance(evidence, dict):
        return {"state": "UNKNOWN", "reasons": ["invalid evidence object"]}
    for field in REQUIRED:
        if field not in evidence:
            reasons.append("missing:" + field)
    for field in ("source_sha", "promoted_sha", "deployed_sha"):
        if not SHA.fullmatch(str(evidence.get(field, ""))):
            reasons.append("invalid:" + field)
    if not evidence.get("mission_id"):
        reasons.append("invalid:mission_id")
    if (evidence.get("promoted_sha") != evidence.get("deployed_sha")
            or evidence.get("source_sha") != evidence.get("promoted_sha")):
        reasons.append("revision_mismatch")
    for field in ("greenlane", "independent_review", "deployment",
                  "functional_probe", "founder_surface"):
        receipt = evidence.get(field)
        if not isinstance(receipt, dict):
            reasons.append("invalid_receipt:" + field)
            continue
        if receipt.get("status") != "success":
            reasons.append("not_success:" + field)
        if receipt.get("sha") != evidence.get("deployed_sha"):
            reasons.append("receipt_revision_mismatch:" + field)
        if not str(receipt.get("url", "")).startswith("https://"):
            reasons.append("missing_evidence_url:" + field)
        try:
            stamp = dt.datetime.fromisoformat(receipt["observed_at"].replace("Z", "+00:00"))
            if stamp.tzinfo is None or not (dt.timedelta(0) <= now - stamp <= dt.timedelta(minutes=10)):
                reasons.append("stale_or_future:" + field)
        except (KeyError, TypeError, ValueError, AttributeError):
            reasons.append("invalid_timestamp:" + field)
    return {"state": "OPERATING" if not reasons else "UNVERIFIED",
            "reasons": sorted(set(reasons))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", help="JSON evidence file")
    args = parser.parse_args()
    try:
        with open(args.evidence, encoding="utf-8") as source:
            verdict = evaluate(json.load(source))
    except (OSError, ValueError) as error:
        verdict = {"state": "UNKNOWN", "reasons": [type(error).__name__]}
    print(json.dumps(verdict, sort_keys=True))
    return 0 if verdict["state"] == "OPERATING" else 1


if __name__ == "__main__":
    sys.exit(main())
