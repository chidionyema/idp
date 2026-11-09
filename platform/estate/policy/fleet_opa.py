"""OPA effect-enforcement adapter; no agent-controlled policy administration.

OPA is the upstream decision engine. A trusted runner configures the endpoint.
When unconfigured, coverage is UNENROLLED rather than falsely called enforced.
Once enrolled, malformed responses and outages deny the affected effect.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import subprocess
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Verdict:
    allowed: bool
    status: str
    reason: str
    revision: str | None = None


class FleetPolicyRefusal(PermissionError):
    def __init__(self, verdict: Verdict):
        self.verdict = verdict
        super().__init__(verdict.reason)


def _endpoint() -> str | None:
    value = os.environ.get("ESTATE_OPA_DECISION_URL", "").strip()
    if not value:
        return None
    parsed = urllib.parse.urlsplit(value)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("OPA endpoint contains credentials, query or fragment")
    if parsed.path != "/v1/data/estate/fleet/decision":
        raise ValueError("OPA endpoint must use pinned fleet decision path")
    if not parsed.hostname:
        raise ValueError("OPA endpoint has no host")
    if parsed.scheme != "https":
        if parsed.scheme != "http":
            raise ValueError("OPA endpoint requires HTTPS")
        try:
            local = ipaddress.ip_address(parsed.hostname).is_loopback
        except ValueError:
            local = parsed.hostname == "localhost"
        if not local:
            raise ValueError("plain HTTP OPA requires loopback")
    return value


def evaluate(
    *, intent: str, step: str, command: str, session: str,
    open_url: Callable[..., Any] | None = None,
) -> Verdict:
    """Only restricts actions; existing permissions cannot be widened by OPA."""
    try:
        endpoint = _endpoint()
    except (ValueError, TypeError) as exc:
        return Verdict(False, "INVALID_CONFIG", str(exc))
    if endpoint is None:
        return Verdict(True, "UNENROLLED", "OPA endpoint not configured")
    action = {
        "contract_version": "estate.effect.v1",
        "intent": intent,
        "step": step,
        "command_sha256": hashlib.sha256(command.encode("utf-8")).hexdigest(),
        # An observed session string is not a verified principal or permission.
        "session_observed": session,
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps({"input": action}, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with (open_url or urllib.request.urlopen)(request, timeout=1.0) as response:
            if response.status != 200:
                raise ValueError(f"OPA HTTP status {response.status}")
            payload = response.read(65537)
            if len(payload) > 65536:
                raise ValueError("OPA response too large")
        decision = json.loads(payload)["result"]
        if not isinstance(decision, dict):
            raise ValueError("OPA decision not an object")
        allowed, revision = decision["allow"], decision["revision"]
        if type(allowed) is not bool or not isinstance(revision, str) or not revision:
            raise ValueError("OPA decision missing strict boolean or revision")
        if len(revision) > 128:
            raise ValueError("OPA revision too long")
        reason = decision.get("reason", "")
        if not isinstance(reason, str):
            raise ValueError("OPA reason not string")
        return Verdict(allowed, "ENFORCED",
                       reason or ("allowed" if allowed else "founder-policy-denied"), revision)
    except (OSError, TimeoutError, ValueError, KeyError, TypeError) as exc:
        return Verdict(False, "UNKNOWN_DENY", f"OPA unavailable: {type(exc).__name__}")


def run_shell(
    *, intent: str, step: str, command: str, session: str, timeout: int,
    run: Callable[..., Any] | None = None,
    open_url: Callable[..., Any] | None = None,
) -> tuple[Verdict, subprocess.CompletedProcess[str]]:
    """Enforce immediately before effect; never execute denied/unknown effects."""
    verdict = evaluate(intent=intent, step=step, command=command,
                       session=session, open_url=open_url)
    if not verdict.allowed:
        raise FleetPolicyRefusal(verdict)
    result = (run or subprocess.run)(
        command, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return verdict, result
