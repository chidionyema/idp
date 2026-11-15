#!/usr/bin/env python3
"""Compile a scoped GitHub App token request from reviewed lane policy.

Only the canary lane is narrowed here; neither per-job authorization nor provider
revocation is implemented by this compiler.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

LANES = Path(__file__).with_name("lanes.json")
SCOPES = Path(__file__).with_name("job-token-scopes.json")
PERMISSION_LEVELS = {"read", "write"}


class ScopeError(ValueError):
    pass


def compile_request(
    lane: str, lanes: dict[str, Any], scopes: dict[str, Any]
) -> dict[str, Any]:
    """Return a provider token request; refuse invalid or ambiguous scopes."""
    permissions = lanes.get(lane)
    if not isinstance(permissions, dict) or not permissions:
        raise ScopeError(f"unknown or empty GitHub App lane: {lane!r}")
    if not all(
        isinstance(key, str) and isinstance(level, str) and level in PERMISSION_LEVELS
        for key, level in permissions.items()
    ):
        raise ScopeError("invalid GitHub App permission declaration")
    if "metadata" not in permissions:
        raise ScopeError("lane must explicitly declare metadata permission")
    if not isinstance(scopes, dict) or scopes.get("schema") != "job-token-scopes/v1":
        raise ScopeError("job token scopes registry unreadable or unknown schema")
    enrolled = scopes.get("enrolled_lanes")
    if not isinstance(enrolled, dict):
        raise ScopeError("enrolled_lanes must be an object")
    if lane not in enrolled:
        return {"permissions": permissions}
    rule = enrolled[lane]
    if not isinstance(rule, dict) or set(rule) != {"repository_ids"}:
        raise ScopeError("enrolled lane scope must declare only repositories")
    ids = rule["repository_ids"]
    if not isinstance(ids, list) or not ids or len(ids) > 100:
        raise ScopeError("repository_ids must be a nonempty bounded list")
    if not all(isinstance(i, int) and not isinstance(i, bool) and i > 0 for i in ids):
        raise ScopeError(
            "repository_ids must contain only positive immutable GitHub IDs"
        )
    if len(set(ids)) != len(ids):
        raise ScopeError("repository_ids must be deduplicated")
    return {"permissions": permissions, "repository_ids": ids}



def verify_issued_token(request: dict[str, Any], receipt: dict[str, Any]) -> None:
    """Reject a scope the provider did not independently attest at issuance.

    The receipt may include a bearer secret; never print its content or include
    its values in an exception. The shell keeps the credential out of the model.
    """
    if not isinstance(receipt, dict):
        raise ScopeError("provider token receipt is not an object")
    expected = request.get("repository_ids")
    if expected is None:
        # Legacy lanes are not enrolled in this repository-scope canary.
        return
    if receipt.get("repository_selection") != "selected":
        raise ScopeError("provider did not attest selected-repository scope")
    repositories = receipt.get("repositories")
    if not isinstance(repositories, list):
        raise ScopeError("provider did not return repository membership evidence")
    ids = [entry.get("id") for entry in repositories if isinstance(entry, dict)]
    if len(ids) != len(repositories) or any(
        not isinstance(value, int) or isinstance(value, bool) or value <= 0
        for value in ids
    ):
        raise ScopeError("provider repository receipt contains invalid identities")
    if len(ids) != len(set(ids)) or set(ids) != set(expected):
        raise ScopeError("provider repository scope differs from approved set")
    if receipt.get("permissions") != request["permissions"]:
        raise ScopeError("provider permissions differ from approved envelope")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile scoped GitHub App token request"
    )
    parser.add_argument("lane")
    parser.add_argument("--verify-response", action="store_true")
    args = parser.parse_args()
    try:
        lanes = json.loads(LANES.read_text(encoding="utf-8"))
        scopes = json.loads(SCOPES.read_text(encoding="utf-8"))
        result = compile_request(args.lane, lanes, scopes)
        if args.verify_response:
            verify_issued_token(result, json.load(sys.stdin))
            return 0
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(3, f"REFUSED github-app token scope: {exc}\n")
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
