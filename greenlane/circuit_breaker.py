from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class ShipContract:
    issue_number: int
    owner: str
    target_service: str
    probe_url: str
    expected_metric: str
    rollback_capable: bool = True

    def validate(self) -> List[str]:
        errs: List[str] = []
        if self.issue_number <= 0:
            errs.append("ship_contract.issue_number must be > 0")
        if not self.owner.strip():
            errs.append("ship_contract.owner is required")
        if not self.target_service.strip():
            errs.append("ship_contract.target_service is required")
        if not self.probe_url.startswith("https://"):
            errs.append("ship_contract.probe_url must be an https:// Zone B endpoint")
        if not self.expected_metric.strip():
            errs.append("ship_contract.expected_metric is required")
        return errs


@dataclass(frozen=True)
class AdmissionDecision:
    admitted: bool
    state: str  # ADMITTED | REJECTED_NO_CONTRACT | PARKED_RETRY_CAP
    reason: str
    actions: List[Dict[str, Any]]


@dataclass(frozen=True)
class OperationalVerdict:
    commit_sha: str
    issue_number: int
    verdict: str  # FLOW_PENDING | OPERATIONAL | NOT_OPERATIONAL
    operational_yield: int
    actions: List[Dict[str, Any]]


class GreenlaneCircuitBreaker:
    """Deterministic control-plane state machine for Greenlane (#8350, #8289, #8331, #8303, #8301)."""

    def __init__(self, db_path: Path, max_retries_across_mains: int = 2) -> None:
        self.db_path = Path(db_path)
        self.max_retries = max_retries_across_mains
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS lane_failures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lane_branch TEXT NOT NULL,
                    lane_sha TEXT NOT NULL,
                    main_sha TEXT NOT NULL,
                    failure_signature TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS parked_lanes (
                    lane_branch TEXT PRIMARY KEY,
                    failure_signature TEXT NOT NULL,
                    parked_at TEXT NOT NULL,
                    reason TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS open_incidents (
                    signature_hash TEXT PRIMARY KEY,
                    target_service TEXT NOT NULL,
                    last_commit_sha TEXT NOT NULL,
                    occurrences INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    def admit_lane(
        self,
        lane_branch: str,
        lane_sha: str,
        contract: Optional[ShipContract],
        hand_raised_pr_numbers: Optional[List[int]] = None,
    ) -> AdmissionDecision:
        actions: List[Dict[str, Any]] = []

        # #8350: No lane enters Greenlane without a valid post-merge Ship Contract
        if contract is None:
            return AdmissionDecision(
                admitted=False,
                state="REJECTED_NO_CONTRACT",
                reason="Missing ShipContract at admission (#8350)",
                actions=[],
            )
        contract_errors = contract.validate()
        if contract_errors:
            return AdmissionDecision(
                admitted=False,
                state="REJECTED_NO_CONTRACT",
                reason="; ".join(contract_errors),
                actions=[
                    {
                        "type": "COMMENT_CLAIM_ISSUE",
                        "issue_number": contract.issue_number,
                        "owner": contract.owner,
                        "body": f"ADMISSION_REJECTED ({lane_branch}@{lane_sha[:7]}): {'; '.join(contract_errors)}",
                    }
                ],
            )

        # #8289: Refuse lanes already parked after hitting retry cap across advancing mains
        with self._connect() as conn:
            row = conn.execute(
                "SELECT failure_signature, reason FROM parked_lanes WHERE lane_branch = ?",
                (lane_branch,),
            ).fetchone()
            if row:
                return AdmissionDecision(
                    admitted=False,
                    state="PARKED_RETRY_CAP",
                    reason=f"Lane parked ({row[1]}); push a new head SHA fixing '{row[0]}' to unpark",
                    actions=[],
                )

        # #8331: Close adopted hand-raised PRs so duplicate bot-sync PRs never spam red checks
        for pr_num in hand_raised_pr_numbers or []:
            actions.append(
                {
                    "type": "CLOSE_ADOPTED_PR",
                    "pr_number": pr_num,
                    "reason": f"Adopted by Greenlane lane {lane_branch}@{lane_sha[:7]} (#8331)",
                }
            )

        return AdmissionDecision(
            admitted=True,
            state="ADMITTED",
            reason="ShipContract verified and lane unparked",
            actions=actions,
        )

    def record_lane_failure(
        self,
        lane_branch: str,
        lane_sha: str,
        main_sha: str,
        verdict: str,  # RED | CONFLICT
        failure_signature: str,
        issue_number: int,
        owner: str,
    ) -> Dict[str, Any]:
        """Records a lane failure across advancing mains, notifies claim owner (#8303), and parks on cap (#8289)."""
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO lane_failures (lane_branch, lane_sha, main_sha, failure_signature, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (lane_branch, lane_sha, main_sha, failure_signature, now),
            )
            distinct_mains = conn.execute(
                """
                SELECT COUNT(DISTINCT main_sha) FROM lane_failures
                WHERE lane_branch = ? AND lane_sha = ?
                """,
                (lane_branch, lane_sha),
            ).fetchone()[0]

            parked = False
            if distinct_mains >= self.max_retries:
                parked = True
                conn.execute(
                    """
                    INSERT OR REPLACE INTO parked_lanes (lane_branch, failure_signature, parked_at, reason)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        lane_branch,
                        failure_signature,
                        now,
                        f"failed across {distinct_mains} distinct main SHAs without new lane head",
                    ),
                )

        actions: List[Dict[str, Any]] = [
            {
                "type": "COMMENT_CLAIM_ISSUE",
                "issue_number": issue_number,
                "owner": owner,
                "verdict": "PARKED" if parked else verdict,
                "body": (
                    f"GREENLANE_{'PARKED' if parked else verdict}: lane={lane_branch} head={lane_sha[:7]} "
                    f"main={main_sha[:7]} sig={failure_signature} distinct_mains={distinct_mains}"
                ),
            }
        ]
        return {"parked": parked, "distinct_mains": distinct_mains, "actions": actions}

    def unpark_on_new_head(self, lane_branch: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM parked_lanes WHERE lane_branch = ?", (lane_branch,)
            )

    def evaluate_post_merge_receipt(
        self,
        commit_sha: str,
        contract: ShipContract,
        release_receipt: Optional[Dict[str, Any]],
    ) -> OperationalVerdict:
        """
        KARMA Firewall enforcement (#8350):
        Merged commit != OPERATIONAL until an independent blackbox release receipt proves
        matching commit_sha, status == OPERATIONAL, and 3/3 passed probe rounds.
        """
        if release_receipt is None:
            return OperationalVerdict(
                commit_sha=commit_sha,
                issue_number=contract.issue_number,
                verdict="FLOW_PENDING",
                operational_yield=0,
                actions=[],
            )

        probes = release_receipt.get("probes") or []
        passed_rounds = sum(1 for p in probes if p.get("passed") is True)
        sha_matches = release_receipt.get("commit_sha") == commit_sha
        is_operational = (
            sha_matches
            and release_receipt.get("status") == "OPERATIONAL"
            and passed_rounds >= 3
        )

        if is_operational:
            return OperationalVerdict(
                commit_sha=commit_sha,
                issue_number=contract.issue_number,
                verdict="OPERATIONAL",
                operational_yield=1,
                actions=[
                    {
                        "type": "MARK_ISSUE_OPERATIONAL",
                        "issue_number": contract.issue_number,
                        "commit_sha": commit_sha,
                        "passed_rounds": passed_rounds,
                    }
                ],
            )

        # Deduplicated incident emission (#8301) + rollback alert
        sig_raw = f"{contract.target_service}:{release_receipt.get('error') or 'probe_failed'}"
        sig_hash = hashlib.sha256(sig_raw.encode("utf-8")).hexdigest()[:12]
        now = _utc_now()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT occurrences FROM open_incidents WHERE signature_hash = ?",
                (sig_hash,),
            ).fetchone()
            if existing:
                occurrences = existing[0] + 1
                conn.execute(
                    "UPDATE open_incidents SET last_commit_sha = ?, occurrences = ?, updated_at = ? WHERE signature_hash = ?",
                    (commit_sha, occurrences, now, sig_hash),
                )
                incident_action = "UPDATE_INCIDENT"
            else:
                occurrences = 1
                conn.execute(
                    "INSERT INTO open_incidents VALUES (?, ?, ?, ?, ?)",
                    (sig_hash, contract.target_service, commit_sha, occurrences, now),
                )
                incident_action = "OPEN_INCIDENT"

        return OperationalVerdict(
            commit_sha=commit_sha,
            issue_number=contract.issue_number,
            verdict="NOT_OPERATIONAL",
            operational_yield=0,
            actions=[
                {
                    "type": "COMMENT_CLAIM_ISSUE",
                    "issue_number": contract.issue_number,
                    "owner": contract.owner,
                    "verdict": "NOT_OPERATIONAL",
                    "rollback_executed": bool(release_receipt.get("rollback_executed")),
                    "rollback_verified": bool(release_receipt.get("rollback_verified")),
                },
                {
                    "type": incident_action,
                    "signature_hash": sig_hash,
                    "target_service": contract.target_service,
                    "occurrences": occurrences,
                },
            ],
        )
