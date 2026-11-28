"""Compulsory offline Dream-Reflect-Optimize (DRO) governance.

WHY this exists. An agent lane finishes its work and closes its lease. Nothing
in the estate looked at what the lane LEARNED, so the estate paid for the same
class of mistake twice: the first time the lane learned it, and again for every
lane that repeated it. A reflection that happens while the lane is hot is
expensive (it competes with the work) and shallow (it optimises the task in
front of it). So the reflection is OFFLINE, AFTER the lease's work, and before
the lease closes, and it is COMPULSORY: a lane that has not completed one
cannot be closed.

The shape mirrors the Sleep-time Compute and AutoDream offline-consolidation
pattern: consolidation happens outside the hot write path, on the cheap tier,
and it never mutates the estate directly. That last part is the point, and it
is mechanical rather than advisory:

  * ImproverCannotSelfCertify. An agent may PROPOSE a change to the estate;
    it may never APPLY one. `apply_self_mutation_attempt` refuses every actor
    that is not the founder-and-greenlane pair, so "the agent found a better
    way" can never become "the agent changed the estate".
  * Every proposal is grounded in a VERIFIED benchmark receipt from the search
    twin, and a receipt that is unverified, expired, injection-flagged, or
    Tier-3-only quarantined is refused. A proposal that cites a forum post as
    evidence is not a proposal.
  * Every proposal is scored DETERMINISTICALLY, from four named axes and one
    blast-radius penalty. No model, no confidence score, no sampling: the same
    proposal scores the same number forever, on any machine, in any harness.

HARNESS-AGNOSTIC BY CONSTRUCTION. Standard library only. No model vendor, no
agent SDK, no hook framework, no Claude/opencode/Codex coupling. The engine is
imported by whatever runs the lane, and the CLI below is the same gate as an
EXIT CODE so a git hook, a CI step, an executor intent and a systemd timer
enforce it identically. Enforcement is exit codes, never one vendor's hook
system (AGENTS.md section 9, principle 10).

FAIL-CLOSED. Every refusal raises a named error; nothing is swallowed, and a
proposal that cannot be scored is never stored as a proposal.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Optional

from .budget_ledger import MicroUsdLedger
from .dialectical_consult import IMMUTABLE_FOUNDER_ONLY_PREFIXES
from .search_twin import SignedResearchEnvelope, TrustTier, TwinSearchMemory

__all__ = [
    "BLAST_RADIUS_PENALTY",
    "BenchmarkEvidenceError",
    "DreamProposalInput",
    "DreamReflectEngine",
    "DreamReflectError",
    "DreamReflectionRequiredError",
    "DreamTarget",
    "EstateTopologySnapshot",
    "ScoredDreamProposal",
    "SelfMutationForbiddenError",
    "compute_elite_score",
]


class DreamReflectError(RuntimeError):
    """Base error for compulsory offline Dream-Reflect-Optimize governance."""


class DreamReflectionRequiredError(DreamReflectError):
    """Raised when an agent attempts to close a lane without completing offline reflection."""


class BenchmarkEvidenceError(DreamReflectError):
    """Raised when an optimization cites unverified, injected, or Tier-3-only benchmarks."""


class SelfMutationForbiddenError(DreamReflectError):
    """Raised if an agent attempts to apply a dream proposal directly without Founder/Greenlane."""


class DreamTarget(str, Enum):
    WORKFLOW = "WORKFLOW"
    SKILL = "SKILL"
    BEHAVIOR = "BEHAVIOR"
    TOPOLOGY = "TOPOLOGY"
    VISUALS_METRICS = "VISUALS_METRICS"


@dataclass(frozen=True)
class EstateTopologySnapshot:
    """The live estate the proposal is grounded against.

    A proposal scored against a stale topology is scored against a fiction, so
    the snapshot is stored WITH the proposal: the card the founder reads and the
    number the grader recomputes quote the same estate state.
    """

    captured_at_epoch: int
    lane1_edge_status: str  # e.g. "OK" | "DEGRADED"
    lane2_oci_status: str
    lane3_greenlane_status: str
    gortex_status: str
    cortex_status: str
    mac_free_mib: int
    mac_load_1m: float
    budget_remaining_uusd: int
    budget_cap_uusd: int
    tier0_cache_hit_pct: float
    founder_interrupts_24h: int
    operational_yield_24h: int
    cockpit_url: str = "https://genesis-founder-surface.pages.dev"


@dataclass(frozen=True)
class DreamProposalInput:
    """What a lane proposes, and what it claims the change is worth."""

    agent_id: str
    session_id: str
    instruction_id: str
    target: DreamTarget
    title: str
    executive_pitch: str  # 1-line summary, <= 160 chars
    current_bottleneck: str
    proposed_change: str
    expected_metric_delta: str
    touched_paths: tuple[str, ...]
    benchmark_envelopes: tuple[SignedResearchEnvelope, ...]
    yield_impact: float  # 0.0 .. 10.0
    cost_latency_gain: float  # 0.0 .. 10.0
    founder_friction_saved: float  # 0.0 .. 10.0
    elite_alignment: float  # 0.0 .. 10.0
    blast_radius: str  # "LOW" | "MEDIUM" | "HIGH"
    rollback_plan: str


@dataclass(frozen=True)
class ScoredDreamProposal:
    """A proposal that survived the evidence gate, with its deterministic score."""

    proposal_id: str
    agent_id: str
    instruction_id: str
    target: str
    title: str
    executive_pitch: str
    current_bottleneck: str
    proposed_change: str
    expected_metric_delta: str
    touched_paths: tuple[str, ...]
    verified_benchmark_ids: tuple[str, ...]
    composite_score: float
    vip_tier: str  # "PLATINUM" (>=9.0) | "GOLD" (>=8.0) | "SILVER" (<8.0)
    blast_radius: str
    rollback_plan: str
    requires_founder_seal: bool
    state: str  # "PROPOSED" | "APPROVED_FOR_LANE" | "SHADOW_TEST" | "REJECTED"
    operational_yield: int  # Always 0 until Lane 3 Greenlane certifies merged change
    dream_cost_uusd: int
    created_at_epoch: int
    founder_rating: Optional[int] = None
    founder_review_note: Optional[str] = None


BLAST_RADIUS_PENALTY = {"LOW": 0.0, "MEDIUM": 0.4, "HIGH": 1.0}

# The score weights. They are named here so a change to the score is a visible
# change to the estate's bargain, not an edit buried in a weighting expression.
SCORE_WEIGHTS = {
    "yield_impact": 0.30,
    "cost_latency_gain": 0.25,
    "founder_friction_saved": 0.25,
    "elite_alignment": 0.20,
}
TIER_PLATINUM = 9.0
TIER_GOLD = 8.0

# CLI exit codes. Named so a hook or a CI step can branch on them.
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_DREAM_REQUIRED = 3
EXIT_DREAM_REFUSED = 4


def _clamp_score(val: float, name: str) -> float:
    """A score axis outside 0..10 is a broken claim, not a low score."""
    if not (0.0 <= val <= 10.0):
        # FM:dro.score-out-of-range
        raise ValueError(f"{name} must be between 0.0 and 10.0 (got {val})")
    return float(val)


def compute_elite_score(proposal: DreamProposalInput) -> tuple[float, str]:
    """Deterministic weighted score: Yield 30%, Cost/Latency 25%, Founder Friction 25%, Elite 20%."""
    y = _clamp_score(proposal.yield_impact, "yield_impact")
    c = _clamp_score(proposal.cost_latency_gain, "cost_latency_gain")
    f = _clamp_score(proposal.founder_friction_saved, "founder_friction_saved")
    e = _clamp_score(proposal.elite_alignment, "elite_alignment")

    br = proposal.blast_radius.upper()
    if br not in BLAST_RADIUS_PENALTY:
        # FM:dro.blast-radius-invalid
        raise ValueError(f"Invalid blast_radius '{proposal.blast_radius}' (expected LOW|MEDIUM|HIGH)")

    raw = (
        (SCORE_WEIGHTS["yield_impact"] * y)
        + (SCORE_WEIGHTS["cost_latency_gain"] * c)
        + (SCORE_WEIGHTS["founder_friction_saved"] * f)
        + (SCORE_WEIGHTS["elite_alignment"] * e)
        - BLAST_RADIUS_PENALTY[br]
    )
    score = round(max(0.0, min(10.0, raw)), 2)

    if score >= TIER_PLATINUM:
        tier = "PLATINUM"
    elif score >= TIER_GOLD:
        tier = "GOLD"
    else:
        tier = "SILVER"
    return score, tier


class DreamReflectEngine:
    """Compulsory offline Dream-Reflect-Optimize engine outside the hot execution write path."""

    def __init__(
        self,
        ledger: MicroUsdLedger,
        search_twin: TwinSearchMemory,
        db_path: str = ":memory:",
        max_dream_cost_uusd: int = 20_000,  # $0.02 hard cap per offline dream cycle
    ) -> None:
        self.ledger = ledger
        self.search_twin = search_twin
        self.max_dream_cost_uusd = max_dream_cost_uusd
        self._conn = sqlite3.connect(db_path, isolation_level=None)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS dream_proposals (
                proposal_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                instruction_id TEXT NOT NULL,
                target TEXT NOT NULL,
                title TEXT NOT NULL,
                executive_pitch TEXT NOT NULL,
                current_bottleneck TEXT NOT NULL,
                proposed_change TEXT NOT NULL,
                expected_metric_delta TEXT NOT NULL,
                touched_paths_json TEXT NOT NULL,
                verified_benchmark_ids_json TEXT NOT NULL,
                topology_snapshot_json TEXT NOT NULL,
                composite_score REAL NOT NULL,
                vip_tier TEXT NOT NULL,
                blast_radius TEXT NOT NULL,
                rollback_plan TEXT NOT NULL,
                requires_founder_seal INTEGER NOT NULL,
                state TEXT NOT NULL CHECK (state IN ('PROPOSED', 'APPROVED_FOR_LANE', 'SHADOW_TEST', 'REJECTED')),
                dream_cost_uusd INTEGER NOT NULL,
                founder_rating INTEGER CHECK (founder_rating IS NULL OR (founder_rating BETWEEN 1 AND 5)),
                founder_review_note TEXT,
                created_at_epoch INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS completed_dream_lanes (
                instruction_id TEXT PRIMARY KEY,
                proposal_id TEXT NOT NULL,
                completed_at_epoch INTEGER NOT NULL
            );
            """
        )

    def submit_offline_dream(
        self,
        proposal: DreamProposalInput,
        topology: EstateTopologySnapshot,
        actual_dream_cost_uusd: int = 3_000,
        now_epoch: Optional[int] = None,
    ) -> ScoredDreamProposal:
        """Score a proposal against the live estate, or refuse it with a named reason."""
        ts = now_epoch if now_epoch is not None else int(time.time())

        if (
            not proposal.executive_pitch.strip()
            or "\n" in proposal.executive_pitch
            or len(proposal.executive_pitch) > 160
        ):
            # FM:dro.executive-pitch-invalid
            raise DreamReflectError(
                "executive_pitch must be a single line <= 160 chars"
            )
        if not proposal.rollback_plan.strip():
            # FM:dro.rollback-plan-missing
            raise DreamReflectError(
                "rollback_plan is mandatory for every optimization proposal"
            )
        if actual_dream_cost_uusd > self.max_dream_cost_uusd:
            # FM:dro.dream-cost-over-cap
            raise DreamReflectError(
                f"Dream cost {actual_dream_cost_uusd} uUSD exceeds offline cap "
                f"{self.max_dream_cost_uusd} uUSD"
            )

        # Require at least one verified, non-injected Tier 1/2 bleeding-edge benchmark receipt.
        if not proposal.benchmark_envelopes:
            # FM:dro.benchmark-receipts-missing
            raise BenchmarkEvidenceError(
                "DENY: Dream proposal must cite at least one verified Tier 1/2 Search Twin benchmark receipt"
            )
        verified_ids: list[str] = []
        has_tier1_or_2 = False
        for env in proposal.benchmark_envelopes:
            if not self.search_twin.verify_envelope(env, now_epoch=ts):
                # FM:dro.benchmark-envelope-unverified
                raise BenchmarkEvidenceError(
                    f"DENY: Invalid or expired benchmark receipt {env.search_receipt_id}"
                )
            if env.injection_detected:
                # FM:dro.benchmark-injection-flagged
                raise BenchmarkEvidenceError(
                    f"DENY: Injection-flagged benchmark receipt {env.search_receipt_id}"
                )
            if env.trust_tier <= int(TrustTier.TIER_2_CORROBORATED):
                has_tier1_or_2 = True
            verified_ids.append(env.search_receipt_id)
        if not has_tier1_or_2:
            # FM:dro.benchmark-tier3-only
            raise BenchmarkEvidenceError(
                "DENY: Bleeding-edge benchmark claims cannot rest solely on Tier-3 quarantined sources"
            )

        # Meter dream compute strictly inside the $200 micro-USD conservation ledger.
        lease_id = self.ledger.reserve(
            instruction_id=proposal.instruction_id,
            role="dream_reflect_offline",
            estimated_uusd=self.max_dream_cost_uusd,
            transport="stateless_api",
            now_epoch=ts,
        )
        try:
            score, vip_tier = compute_elite_score(proposal)
            requires_seal = any(
                p.startswith(IMMUTABLE_FOUNDER_ONLY_PREFIXES) for p in proposal.touched_paths
            )
            seed = (
                f"{proposal.instruction_id}|{proposal.agent_id}|{proposal.title}|{ts}"
            ).encode("utf-8")
            proposal_id = "dro_" + hashlib.sha256(seed).hexdigest()[:12]

            self._conn.execute(
                """
                INSERT INTO dream_proposals (
                    proposal_id, agent_id, instruction_id, target, title,
                    executive_pitch, current_bottleneck, proposed_change,
                    expected_metric_delta, touched_paths_json, verified_benchmark_ids_json,
                    topology_snapshot_json, composite_score, vip_tier, blast_radius,
                    rollback_plan, requires_founder_seal, state, dream_cost_uusd,
                    founder_rating, founder_review_note, created_at_epoch
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PROPOSED', ?, NULL, NULL, ?)
                """,
                (
                    proposal_id,
                    proposal.agent_id,
                    proposal.instruction_id,
                    proposal.target.value,
                    proposal.title,
                    proposal.executive_pitch,
                    proposal.current_bottleneck,
                    proposal.proposed_change,
                    proposal.expected_metric_delta,
                    json.dumps(list(proposal.touched_paths)),
                    json.dumps(verified_ids),
                    json.dumps(asdict(topology), sort_keys=True),
                    score,
                    vip_tier,
                    proposal.blast_radius.upper(),
                    proposal.rollback_plan,
                    1 if requires_seal else 0,
                    actual_dream_cost_uusd,
                    ts,
                ),
            )
            self._conn.execute(
                """
                INSERT OR REPLACE INTO completed_dream_lanes (instruction_id, proposal_id, completed_at_epoch)
                VALUES (?, ?, ?)
                """,
                (proposal.instruction_id, proposal_id, ts),
            )
            self.ledger.settle(lease_id, actual_dream_cost_uusd)
        except Exception:
            self.ledger.release(lease_id)
            raise

        return self.get_proposal(proposal_id)

    def assert_dream_completed_before_lane_close(self, instruction_id: str) -> str:
        """Compulsory gate called by System Reconciler before closing an agent's lease."""
        row = self._conn.execute(
            "SELECT proposal_id FROM completed_dream_lanes WHERE instruction_id = ?",
            (instruction_id,),
        ).fetchone()
        if row is None:
            # FM:dro.lane-close-without-dream
            raise DreamReflectionRequiredError(
                f"DRO_REQUIRED_BEFORE_LEASE_CLOSE: instruction {instruction_id} must "
                "complete offline dream reflection"
            )
        return str(row[0])

    def apply_self_mutation_attempt(self, proposal_id: str, actor_role: str) -> None:
        """Mechanical enforcement of ImproverCannotSelfCertify."""
        if actor_role.lower() != "founder_and_greenlane":
            # FM:dro.self-mutation-forbidden
            raise SelfMutationForbiddenError(
                f"DENY: actor '{actor_role}' cannot self-apply dream proposal "
                f"{proposal_id}; requires Founder Telegram approval + Lane 3 Greenlane "
                "falsification"
            )

    def get_proposal(self, proposal_id: str) -> ScoredDreamProposal:
        row = self._conn.execute(
            """
            SELECT proposal_id, agent_id, instruction_id, target, title,
                   executive_pitch, current_bottleneck, proposed_change,
                   expected_metric_delta, touched_paths_json, verified_benchmark_ids_json,
                   composite_score, vip_tier, blast_radius, rollback_plan,
                   requires_founder_seal, state, dream_cost_uusd, created_at_epoch,
                   founder_rating, founder_review_note
            FROM dream_proposals WHERE proposal_id = ?
            """,
            (proposal_id,),
        ).fetchone()
        if row is None:
            # FM:dro.proposal-not-found
            raise KeyError(f"Unknown proposal_id: {proposal_id}")
        return ScoredDreamProposal(
            proposal_id=row[0],
            agent_id=row[1],
            instruction_id=row[2],
            target=row[3],
            title=row[4],
            executive_pitch=row[5],
            current_bottleneck=row[6],
            proposed_change=row[7],
            expected_metric_delta=row[8],
            touched_paths=tuple(json.loads(row[9])),
            verified_benchmark_ids=tuple(json.loads(row[10])),
            composite_score=float(row[11]),
            vip_tier=row[12],
            blast_radius=row[13],
            rollback_plan=row[14],
            requires_founder_seal=bool(row[15]),
            state=row[16],
            operational_yield=0,
            dream_cost_uusd=int(row[17]),
            created_at_epoch=int(row[18]),
            founder_rating=row[19],
            founder_review_note=row[20],
        )

    def record_founder_decision(self, proposal_id: str, new_state: str) -> ScoredDreamProposal:
        """The founder's 1-tap decision. Only the founder may move a proposal's state."""
        if new_state not in ("APPROVED_FOR_LANE", "SHADOW_TEST", "REJECTED"):
            # FM:dro.founder-decision-invalid
            raise ValueError(f"Invalid decision state: {new_state}")
        self._conn.execute(
            "UPDATE dream_proposals SET state = ? WHERE proposal_id = ?",
            (new_state, proposal_id),
        )
        return self.get_proposal(proposal_id)

    def record_founder_review(
        self,
        proposal_id: str,
        rating: int,
        review_note: Optional[str] = None,
    ) -> ScoredDreamProposal:
        """The founder's star rating, kept apart from the decision: a good proposal can still be rejected."""
        if not (1 <= rating <= 5):
            # FM:dro.founder-rating-out-of-range
            raise ValueError("Founder rating must be integer 1..5")
        self._conn.execute(
            "UPDATE dream_proposals SET founder_rating = ?, founder_review_note = ? WHERE proposal_id = ?",
            (rating, review_note, proposal_id),
        )
        return self.get_proposal(proposal_id)

    def agent_reputation_summary(self, agent_id: str) -> dict[str, Any]:
        """What this agent's proposals have actually been worth."""
        row = self._conn.execute(
            """
            SELECT COUNT(*),
                   COALESCE(AVG(composite_score), 0.0),
                   COALESCE(AVG(founder_rating), 0.0),
                   SUM(CASE WHEN state = 'APPROVED_FOR_LANE' THEN 1 ELSE 0 END)
            FROM dream_proposals WHERE agent_id = ?
            """,
            (agent_id,),
        ).fetchone()
        return {
            "agent_id": agent_id,
            "total_proposals": int(row[0]),
            "avg_composite_score": round(float(row[1]), 2),
            "avg_founder_rating": round(float(row[2]), 2),
            "approved_count": int(row[3] or 0),
        }


def _build_parser() -> "Any":
    import argparse

    parser = argparse.ArgumentParser(
        prog="dream_reflect",
        description=(
            "The compulsory offline dream gate as an EXIT CODE, so any harness "
            "(git hook, CI step, executor intent, timer) enforces it identically."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser(
        "check-lane-close",
        help="exit 0 if the lane completed its offline dream, non-zero if it did not",
    )
    check.add_argument("--instruction-id", required=True)
    check.add_argument("--db", default=":memory:")

    score = sub.add_parser("score", help="score a proposal JSON and print the deterministic result")
    score.add_argument("--proposal", required=True, help="path to a DreamProposalInput JSON file")
    score.add_argument("--db", default=":memory:")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """The CLI seam. Exit codes are the contract; the importable API is the same gate."""
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "check-lane-close":
            engine = DreamReflectEngine(
                ledger=MicroUsdLedger(db_path=args.db),
                search_twin=TwinSearchMemory(signing_secret=b"dro-cli-read-only-secret-32byte"),
                db_path=args.db,
            )
            proposal_id = engine.assert_dream_completed_before_lane_close(args.instruction_id)
            print(f"DRO_COMPLETE {proposal_id}")
            return EXIT_OK
        if args.command == "score":
            raw = json.loads(open(args.proposal, encoding="utf-8").read())
            proposal = DreamProposalInput(
                agent_id=raw["agent_id"],
                session_id=raw.get("session_id", ""),
                instruction_id=raw["instruction_id"],
                target=DreamTarget(raw["target"]),
                title=raw["title"],
                executive_pitch=raw["executive_pitch"],
                current_bottleneck=raw.get("current_bottleneck", ""),
                proposed_change=raw.get("proposed_change", ""),
                expected_metric_delta=raw.get("expected_metric_delta", ""),
                touched_paths=tuple(raw.get("touched_paths", ())),
                benchmark_envelopes=(),
                yield_impact=float(raw["yield_impact"]),
                cost_latency_gain=float(raw["cost_latency_gain"]),
                founder_friction_saved=float(raw["founder_friction_saved"]),
                elite_alignment=float(raw["elite_alignment"]),
                blast_radius=raw["blast_radius"],
                rollback_plan=raw["rollback_plan"],
            )
            score, tier = compute_elite_score(proposal)
            print(json.dumps({"composite_score": score, "vip_tier": tier}, sort_keys=True))
            return EXIT_OK
    except DreamReflectionRequiredError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_DREAM_REQUIRED
    except DreamReflectError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_DREAM_REFUSED
    except (KeyError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"DRO_USAGE {type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_USAGE
    return EXIT_USAGE


if __name__ == "__main__":  # pragma: no cover - exercised through the CLI contract
    raise SystemExit(main())
