#!/usr/bin/env python3
"""
bin/zero_repeat_gate.py — Pre-emit & runtime enforcement mirror of harness/zero-repeat-guard.

Enforces:
1. 1-Strike Failure-Class Circuit Breaker & Bot Auto-Merge Cap (SQLite WAL backed)
2. Headless Worker Auto-Continuation (forbids push-and-wait-for-Founder)
3. Superseded-Head Watcher Abort (compares watched SHA against Greenlane state ref head)
4. Durable Consumer-Ack Founder Passkey Sink (stable key reg:founder, refuses purge without 40-hex commit SHA)
5. Pre-Emit 0-Job Workflow Guard & Legion Admission Precondition Preflight
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

MIN_DURABLE_TTL_SECS = 30 * 86_400
HEX_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class GuardViolation(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def init_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS failure_classes (
            class_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            first_sha TEXT,
            repeat_sha TEXT,
            strike_count INTEGER NOT NULL DEFAULT 0,
            wall_check_path TEXT,
            regression_test_path TEXT,
            immunized_sha TEXT
        );
        CREATE TABLE IF NOT EXISTS bot_red_syncs (
            pr_id TEXT PRIMARY KEY,
            red_sync_count INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS worker_handoffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id TEXT NOT NULL,
            lane TEXT NOT NULL,
            head_sha TEXT NOT NULL,
            issue_id TEXT NOT NULL,
            next_action TEXT NOT NULL,
            next_target TEXT
        );
        CREATE TABLE IF NOT EXISTS founder_passkey_sink (
            stable_key TEXT PRIMARY KEY,
            credential_id TEXT NOT NULL,
            public_key_spki_b64 TEXT NOT NULL,
            ttl_seconds INTEGER NOT NULL,
            committed_sha TEXT
        );
        """
    )
    conn.commit()
    return conn


def canonical_class_id(gate: str, rule: str, target: str) -> str:
    return f"{gate.strip()}::{rule.strip()}::{target.strip()}"


def record_failure(
    conn: sqlite3.Connection, gate: str, rule: str, target: str, head_sha: str
) -> dict:
    cid = canonical_class_id(gate, rule, target)
    row = conn.execute(
        "SELECT status, first_sha, strike_count FROM failure_classes WHERE class_id = ?",
        (cid,),
    ).fetchone()
    if row is None or row[0] in ("CLEAR", "IMMUNIZED"):
        status, first_sha, repeat_sha, strikes = (
            "IMMUNIZATION_REQUIRED",
            head_sha,
            None,
            1,
        )
    else:
        status, first_sha, repeat_sha, strikes = (
            "CLASS_QUARANTINE",
            row[1],
            head_sha,
            row[2] + 1,
        )
    conn.execute(
        """
        INSERT INTO failure_classes (class_id, status, first_sha, repeat_sha, strike_count)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(class_id) DO UPDATE SET
            status=excluded.status,
            first_sha=excluded.first_sha,
            repeat_sha=excluded.repeat_sha,
            strike_count=excluded.strike_count
        """,
        (cid, status, first_sha, repeat_sha, strikes),
    )
    conn.commit()
    return {"class_id": cid, "status": status, "strike_count": strikes}


def allow_dispatch(conn: sqlite3.Connection, gate: str, rule: str, target: str) -> None:
    cid = canonical_class_id(gate, rule, target)
    row = conn.execute(
        "SELECT status, strike_count FROM failure_classes WHERE class_id = ?", (cid,)
    ).fetchone()
    if row is None or row[0] in ("CLEAR", "IMMUNIZED"):
        return
    if row[0] == "IMMUNIZATION_REQUIRED":
        raise GuardViolation(
            "ERR_UNIMMUNIZED_RETRY",
            f"{cid} requires immunization before retry (strikes={row[1]})",
        )
    raise GuardViolation(
        "ERR_CLASS_QUARANTINE",
        f"{cid} is quarantined after repeat failure (strikes={row[1]})",
    )


def record_immunization(
    conn: sqlite3.Connection,
    gate: str,
    rule: str,
    target: str,
    commit_sha: str,
    wall_check_path: str,
    regression_test_path: str,
    failed_before_fix: bool,
    passed_after_fix: bool,
) -> dict:
    if not HEX_SHA_RE.match(commit_sha):
        raise GuardViolation(
            "ERR_INVALID_IMMUNIZATION_PROOF",
            "commit_sha must be 7..40 lowercase hex chars",
        )
    if not wall_check_path.strip() or not regression_test_path.strip():
        raise GuardViolation(
            "ERR_INVALID_IMMUNIZATION_PROOF",
            "wall_check_path and regression_test_path required",
        )
    if not (failed_before_fix and passed_after_fix):
        raise GuardViolation(
            "ERR_INVALID_IMMUNIZATION_PROOF",
            "regression test must fail before fix and pass after fix",
        )
    cid = canonical_class_id(gate, rule, target)
    conn.execute(
        """
        INSERT INTO failure_classes (class_id, status, strike_count, wall_check_path, regression_test_path, immunized_sha)
        VALUES (?, 'IMMUNIZED', 0, ?, ?, ?)
        ON CONFLICT(class_id) DO UPDATE SET
            status='IMMUNIZED',
            wall_check_path=excluded.wall_check_path,
            regression_test_path=excluded.regression_test_path,
            immunized_sha=excluded.immunized_sha
        """,
        (cid, wall_check_path, regression_test_path, commit_sha),
    )
    conn.commit()
    return {"class_id": cid, "status": "IMMUNIZED", "commit_sha": commit_sha}


def record_bot_sync(
    conn: sqlite3.Connection, pr_id: str, ci_is_green: bool, has_new_fix_commit: bool
) -> int:
    if ci_is_green or has_new_fix_commit:
        conn.execute(
            "INSERT INTO bot_red_syncs (pr_id, red_sync_count) VALUES (?, 0) "
            "ON CONFLICT(pr_id) DO UPDATE SET red_sync_count=0",
            (pr_id,),
        )
        conn.commit()
        return 0
    row = conn.execute(
        "SELECT red_sync_count FROM bot_red_syncs WHERE pr_id = ?", (pr_id,)
    ).fetchone()
    count = (row[0] if row else 0) + 1
    conn.execute(
        "INSERT INTO bot_red_syncs (pr_id, red_sync_count) VALUES (?, ?) "
        "ON CONFLICT(pr_id) DO UPDATE SET red_sync_count=excluded.red_sync_count",
        (pr_id, count),
    )
    conn.commit()
    if count > 1:
        raise GuardViolation(
            "ERR_BOT_SYNC_LOOP_QUARANTINED", f"{pr_id} repeated red bot sync #{count}"
        )
    return count


def enforce_headless_handoff(
    conn: sqlite3.Connection,
    worker_id: str,
    lane: str,
    head_sha: str,
    issue_id: str,
    requested_action: str,
    pending_verdict: Optional[tuple[str, str]] = None,
    next_unblocked_ticket: Optional[str] = None,
) -> dict:
    if requested_action == "IDLE_WAIT_FOR_FOUNDER":
        raise GuardViolation(
            "ERR_FOUNDER_EVENT_LOOP_FORBIDDEN",
            f"worker {worker_id} cannot halt waiting for Founder after pushing {lane}@{head_sha}",
        )
    if pending_verdict is not None:
        action, target = (
            "HANDLE_GREENLANE_VERDICT",
            f"{pending_verdict[0]}@{pending_verdict[1]}",
        )
    elif next_unblocked_ticket is not None:
        action, target = "PULL_NEXT_TICKET", next_unblocked_ticket
    else:
        action, target = "IDLE_WAIT_FOR_QUEUE_EVENT", None
    conn.execute(
        "INSERT INTO worker_handoffs (worker_id, lane, head_sha, issue_id, next_action, next_target) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (worker_id, lane, head_sha, issue_id, action, target),
    )
    conn.commit()
    return {
        "worker_id": worker_id,
        "lane": lane,
        "head_sha": head_sha,
        "next_action": action,
        "next_target": target,
    }


def evaluate_lane_watcher(
    watched_sha: str, commit_status: str, greenlane_state_lane_head: Optional[str]
) -> dict:
    if greenlane_state_lane_head is None:
        return {"verdict": "LANE_RETIRED", "continue": False}
    if greenlane_state_lane_head != watched_sha:
        return {
            "verdict": "SUPERSEDED_HEAD",
            "continue": False,
            "watched_sha": watched_sha,
            "current_lane_head": greenlane_state_lane_head,
        }
    if commit_status in ("success", "failure", "error"):
        return {"verdict": "TERMINAL", "status": commit_status, "continue": False}
    return {"verdict": "CONTINUE_WATCHING", "continue": True}


def validate_escalation_channel(channel: str) -> None:
    if channel != "DURABLE_FOUNDER_INBOX":
        raise GuardViolation(
            "ERR_LOCAL_POLLER_OR_TERMINAL_TRAP",
            f"channel {channel!r} forbidden; must route to DURABLE_FOUNDER_INBOX",
        )


def put_passkey_registration(
    conn: sqlite3.Connection,
    credential_id: str,
    public_key_spki_b64: str,
    requested_ttl_secs: int = 86_400,
) -> dict:
    if not credential_id.strip() or not public_key_spki_b64.strip():
        raise GuardViolation(
            "ERR_INVALID_PASSKEY_PAYLOAD",
            "credential_id and public_key_spki_b64 required",
        )
    ttl = max(int(requested_ttl_secs), MIN_DURABLE_TTL_SECS)
    conn.execute(
        """
        INSERT INTO founder_passkey_sink (stable_key, credential_id, public_key_spki_b64, ttl_seconds, committed_sha)
        VALUES ('reg:founder', ?, ?, ?, NULL)
        ON CONFLICT(stable_key) DO UPDATE SET
            credential_id=excluded.credential_id,
            public_key_spki_b64=excluded.public_key_spki_b64,
            ttl_seconds=excluded.ttl_seconds,
            committed_sha=NULL
        """,
        (credential_id, public_key_spki_b64, ttl),
    )
    conn.commit()
    return {
        "stable_key": "reg:founder",
        "credential_id": credential_id,
        "ttl_seconds": ttl,
    }


def read_passkey_by_any_nonce(conn: sqlite3.Connection, _nonce: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT stable_key, credential_id, public_key_spki_b64, ttl_seconds, committed_sha "
        "FROM founder_passkey_sink WHERE stable_key = 'reg:founder'"
    ).fetchone()
    if not row:
        return None
    return {
        "stable_key": row[0],
        "credential_id": row[1],
        "public_key_spki_b64": row[2],
        "ttl_seconds": row[3],
        "committed_sha": row[4],
    }


def ack_passkey_committed(conn: sqlite3.Connection, committed_sha: str) -> None:
    if not FULL_SHA_RE.match(committed_sha):
        raise GuardViolation(
            "ERR_INVALID_COMMIT_SHA", "committed_sha must be 40-char lowercase hex"
        )
    cur = conn.execute(
        "UPDATE founder_passkey_sink SET committed_sha = ? WHERE stable_key = 'reg:founder'",
        (committed_sha,),
    )
    if cur.rowcount == 0:
        raise GuardViolation(
            "ERR_UNCONSUMED_FOUNDER_TAP", "no pending registration under reg:founder"
        )
    conn.commit()


def purge_passkey_if_consumed(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        "SELECT committed_sha FROM founder_passkey_sink WHERE stable_key = 'reg:founder'"
    ).fetchone()
    if row is None or not row[0]:
        raise GuardViolation(
            "ERR_UNCONSUMED_FOUNDER_TAP",
            "cannot expire or purge reg:founder without committed_sha",
        )
    conn.execute("DELETE FROM founder_passkey_sink WHERE stable_key = 'reg:founder'")
    conn.commit()


def validate_workflow_yaml_text(workflow_path: str, yaml_text: str) -> None:
    """Deterministic zero-dependency check that a GitHub Actions workflow defines at least one runnable job."""
    lines = yaml_text.splitlines()
    in_jobs = False
    job_count = 0
    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if raw.startswith("jobs:"):
            in_jobs = True
            continue
        if in_jobs:
            if not raw[0].isspace():
                break
            if re.match(r"^\s{2}[A-Za-z0-9_-]+:\s*$", raw):
                job_count += 1
    if job_count == 0:
        raise GuardViolation(
            "ERR_ZERO_JOB_WORKFLOW", f"{workflow_path} defines 0 runnable jobs"
        )


def preflight_legion_admission(
    issue_id: str,
    requested_paths: Iterable[str],
    active_claims: dict[str, list[str]],
    has_acceptance_contract: bool,
    required_tools_available: set[str],
    required_tools_needed: set[str],
    target_merges_cleanly_on_main: bool,
) -> None:
    reasons: list[str] = []
    if not has_acceptance_contract:
        reasons.append(f"issue {issue_id} missing executable acceptance contract")
    if not target_merges_cleanly_on_main:
        reasons.append(f"issue {issue_id} does not merge cleanly onto origin/main")
    missing = sorted(required_tools_needed - required_tools_available)
    for tool in missing:
        reasons.append(f"missing required sandbox tool: {tool}")
    req_list = list(requested_paths)
    for owner, paths in sorted(active_claims.items()):
        for p in req_list:
            if p in paths:
                reasons.append(f"claim conflict on {p} held by {owner}")
    if reasons:
        raise GuardViolation("ERR_ADMISSION_PRECONDITION_FAILED", "; ".join(reasons))
