#!/usr/bin/env python3
"""Publish only independently validated quarantine receipts to the issue of record."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ISSUE_NUMBER = 7760
REPO = "chidionyema/idp"
HEX = re.compile(r"^[0-9a-f]{64}$")
EVENT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{7,127}$")
BOT_LOGIN = "github-actions[bot]"


def checked_receipt(receipt: dict) -> dict:
    if not isinstance(receipt, dict):
        raise ValueError("receipt not an object")
    if receipt.get("status") != "QUARANTINED_AUTHENTICATED_REVIEW_ONLY":
        raise ValueError("receipt is not independently validated")
    if receipt.get("target_repo") != REPO:
        raise ValueError("wrong receipt repository")
    event_id = receipt.get("event_id")
    if not isinstance(event_id, str) or not EVENT_ID.fullmatch(event_id):
        raise ValueError("invalid event_id")
    checked = {"event_id": event_id}
    for field in ("source_sha256", "document_ref_sha256", "envelope_sha256"):
        value = receipt.get(field)
        if not isinstance(value, str) or not HEX.fullmatch(value):
            raise ValueError("invalid " + field)
        checked[field] = value
    return checked


def marker_for(clean: dict) -> str:
    binding = "|".join(clean[field] for field in (
        "event_id", "source_sha256", "document_ref_sha256", "envelope_sha256"
    ))
    fingerprint = hashlib.sha256(binding.encode("utf-8")).hexdigest()
    return "<!-- genesis-drive-receipt:v1:" + clean["event_id"] + ":" + fingerprint + " -->"


def make_body(clean: dict, run_id: int) -> str:
    if type(run_id) is not int or run_id <= 0:
        raise ValueError("invalid run id")
    return "\n".join((
        marker_for(clean),
        "**Gemini Web relay intake — QUARANTINED, review only.**",
        "",
        "- Event ID: `" + clean["event_id"] + "`",
        "- Source SHA-256: `" + clean["source_sha256"] + "`",
        "- Private Drive document reference SHA-256: `" + clean["document_ref_sha256"] + "`",
        "- Signed envelope SHA-256: `" + clean["envelope_sha256"] + "`",
        "- Verified receiver run: https://github.com/" + REPO + "/actions/runs/" + str(run_id),
        "",
        "HMAC authenticates the configured relay sender, **not Gemini authorship**. "
        "No content, privileged actuation, promotion, or deployment is authorized.",
    ))


def github_api(method: str, path: str, payload: dict | None, token: str):
    req = urllib.request.Request(
        "https://api.github.com/repos/" + REPO + path,
        method=method,
        data=None if payload is None else json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "genesis-drive-receipt/1",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            expected = 200 if method == "GET" else 201
            if resp.status != expected:
                raise RuntimeError("GitHub response status refused")
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        raise RuntimeError("GitHub receipt API HTTP " + str(exc.code)) from None


def publish(receipt: dict, run_id: int, token: str, api=github_api) -> dict:
    clean = checked_receipt(receipt)
    if not isinstance(token, str) or not token:
        raise ValueError("missing GitHub issue token")
    body = make_body(clean, run_id)
    marker = marker_for(clean)
    prefix = "<!-- genesis-drive-receipt:v1:" + clean["event_id"] + ":"
    for page in range(1, 51):
        comments = api("GET", "/issues/" + str(ISSUE_NUMBER) +
                       "/comments?per_page=100&page=" + str(page), None, token)
        if not isinstance(comments, list):
            raise RuntimeError("invalid GitHub comments response")
        for comment in comments:
            if not isinstance(comment, dict):
                continue
            author = comment.get("user") or {}
            if author.get("login") != BOT_LOGIN:
                continue
            existing = comment.get("body") or ""
            if prefix not in existing:
                continue
            if marker in existing:
                return {"status": "ALREADY_RECORDED", "event_id": clean["event_id"],
                        "comment_id": comment.get("id")}
            raise RuntimeError("receipt conflict for immutable event_id")
        if len(comments) < 100:
            break
    else:
        raise RuntimeError("issue comment pagination limit reached; refusing duplicate")
    created = api("POST", "/issues/" + str(ISSUE_NUMBER) + "/comments",
                  {"body": body}, token)
    if not isinstance(created, dict) or not isinstance(created.get("id"), int):
        raise RuntimeError("GitHub comment commit unconfirmed")
    return {"status": "RECORDED_QUARANTINED", "event_id": clean["event_id"],
            "comment_id": created["id"]}


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: genesis_drive_receipt_issue.py receipt.json", file=sys.stderr)
        return 2
    try:
        content = Path(sys.argv[1]).read_bytes()
        if len(content) > 32768:
            raise ValueError("receipt too large")
        receipt = json.loads(content)
        run_id = int(os.environ["GITHUB_RUN_ID"])
        result = publish(receipt, run_id, os.environ.get("GH_TOKEN", ""))
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ValueError, KeyError, TypeError, RuntimeError, OSError, json.JSONDecodeError):
        print('{"status":"REJECTED_OR_UNCONFIRMED"}', file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
