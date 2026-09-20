#!/usr/bin/env python3
"""RedTeam control loop: payload generation and injection.

Implements ControlLoop protocol.
Shadow-only in staging. Post-verdict hook scans execution against payloads.
"""

from platform.eval.protocol import ControlLoop, GateDecision, LoopHealth
from platform.eval.red_team_payloads import PayloadCatalog
from datetime import datetime
import json
import os
import socket
import time

# The subject the promoter consumes (bin/redteam_promoter/promoter.py). One subject family, one
# schema -- the same rule platform/event-bus/contract enforces for every other event.
DEFEATED_SUBJECT = os.environ.get(
    "VN_REDTEAM_DEFEATED_SUBJECT", "estate.eval.redteam.defeated"
)


def publish_defeated(payload, evidence: str) -> bool:
    """Emit a defeating payload onto the estate bus so the proxy can learn to block it.

    This is the PUBLISHER half of the loop. Before it existed the promoter had nothing to
    consume: a payload the red team proved got through stayed a finding and never became a
    signature, so the same hole had to be re-learned from a live incident.

    One PUB to one subject, wire protocol by hand -- the same shape
    `platform/router-events/publisher.py` uses, so no NATS client library is needed in an image
    built small. Returns False (and the caller logs it) when the bus is unreachable: a red-team
    run must not fail because the bus is down, but the miss is reported rather than passed over.
    """
    nats_url = os.environ.get("NATS_URL", "")
    if not nats_url:
        return False
    host, port = nats_url.rsplit(":", 1)
    body = json.dumps(
        {
            "id": payload.id,
            "attack_class": payload.attack_class,
            "tool_target": payload.tool_target,
            "content": payload.content,
            "severity": payload.severity,
            "evidence": evidence,
            "detected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    ).encode()
    try:
        with socket.create_connection((host, int(port)), timeout=5) as s:
            s.sendall(b'CONNECT {"verbose":false,"pedantic":false}\r\n')
            s.sendall(f"PUB {DEFEATED_SUBJECT} {len(body)}\r\n".encode() + body + b"\r\n")
            s.sendall(b"PING\r\n")
            s.settimeout(3)
            s.recv(64)
        return True
    except (OSError, socket.timeout):
        return False


class RedTeamLoop(ControlLoop):
    """
    RedTeam as a ControlLoop.
    Shadow-only: payloads execute against orchestrator in staging.
    Verdicts flow through post_verdict, results land in drift ledger.
    Prod enforcement is separate flag, default off.
    """

    name = "red_team"

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.environ.get("QUEUE_DB_PATH", "state/queue.db")
        self.catalog = PayloadCatalog(db_path=self.db_path)
        self.last_run_at = None
        self.last_error = None
        self.mode = "off"  # Default off; must be explicitly enabled per payload
        self.vulnerabilities_found = []

    def pre_llm(self, state: dict) -> GateDecision:
        """RedTeam doesn't gate on pre_llm. Return allow."""
        return GateDecision(action="allow")

    def post_verdict(self, state: dict, verdict: dict) -> None:
        """
        Called after verdict.
        In shadow mode: scan transcript against payloads, log findings.
        In enforce mode: block on vulnz (per-class flag).
        """
        self.last_run_at = datetime.now().isoformat()

        if self.mode == "off":
            return

        try:
            # Shadow mode: passive scanning
            if self.mode == "shadow":
                self._scan_for_vulnerabilities(state, verdict)

            # Enforce mode: active blocking (per-payload flag, default off)
            elif self.mode == "enforce":
                self._check_enforced_payloads(state, verdict)

        except Exception as e:
            self.last_error = str(e)
            # Don't raise; log and continue

    def periodic(self) -> None:
        """
        Periodic maintenance: weekly payload refresh.
        Generate + mutate + retire payloads.
        """
        self.last_run_at = datetime.now().isoformat()

        try:
            self.catalog.run_weekly_refresh()
            # Log summary: generated, mutated, retired
            self.last_error = None  # Success

        except Exception as e:
            self.last_error = str(e)

    def health(self) -> LoopHealth:
        """Report loop health."""
        return LoopHealth(
            name=self.name,
            mode=self.mode,
            last_run_at=self.last_run_at or "never",
            last_error=self.last_error or "none",
            is_healthy=self.last_error is None,
        )

    def _scan_for_vulnerabilities(self, state: dict, verdict: dict) -> None:
        """
        Shadow scanning: check if any active payloads were triggered.
        In staging only; prod enforcement is separate flag.
        """
        # Get agent transcript
        messages = state.get("messages", [])

        # Get active payloads
        payloads = self.catalog.get_active_payloads()

        for payload in payloads:
            # Check if payload content appears in transcript
            for msg in messages:
                msg_text = (
                    str(msg.get("content", "")) if isinstance(msg, dict) else str(msg)
                )
                if payload.content in msg_text:
                    # Payload was triggered
                    self.catalog.record_detection(payload.id)
                    evidence = "payload content detected in agent output"
                    # Publish the defeat so the promoter can turn it into a banned signature --
                    # the wire that was missing. A bus that is down is reported, never silent.
                    published = publish_defeated(payload, evidence)
                    self.vulnerabilities_found.append(
                        {
                            "payload_id": payload.id,
                            "attack_class": payload.attack_class,
                            "severity": payload.severity,
                            "evidence": evidence,
                            "published": published,
                        }
                    )

    def _check_enforced_payloads(self, state: dict, verdict: dict) -> None:
        """
        Enforce mode: check if any enforced payloads were triggered.
        Default off per payload; admin must explicitly flip to enforce.
        """
        # In production, check per-payload enforce flag
        # For now, skip (default off)
        pass
