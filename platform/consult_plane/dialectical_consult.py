"""The dialectical consultation engine: Brief -> Lead -> Blind Challenge -> Veto.

LAW_ZERO_MODEL_SOVEREIGNTY. A Class B model that reads a brief and proposes a
change produces FLOW, never operational yield. `operational_yield` is 0 on
every path out of this module, by construction: the only thing a consultation
can do is return a verdict and a set of substantiated objections. Whether a
proposal actually took effect is decided by Lane 3's deterministic gate, never
by the model that proposed it.

The pipeline:

  1. VERIFY every external receipt; an unverified receipt is not evidence.
  2. TIER-0 CACHE. An identical digest (invariant version + intent + evidence
     hashes) is served from cache at zero cost with zero model calls.
  3. LEAD. One frontier proposal, cost metered against the budget ledger.
  4. DETERMINISTIC PRE-CHECK. An uncited external claim, or one cited only to
     quarantined sources, is rejected here -- before any challenger is paid.
  5. BLIND CHALLENGE. The challengers see the proposal with the lead's model
     identity stripped. Prestige is not evidence.
  6. ASYMMETRIC FALSIFICATION. One substantiated objection vetoes a majority
     of approvals. Vague opinion is discarded, not counted.
  7. FOUNDER SEAL. A proposal touching an immutable founder-only path is
     escalated, never self-certified.

Standard library only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from .budget_ledger import MicroUsdLedger
from .search_twin import TrustTier, TwinSearchMemory

INVARIANT_VERSION = "v0.9.1-SOVEREIGN-IOC"

PINNED_INVARIANTS_PREFIX = (
    "[PINNED_ESTATE_INVARIANTS v0.9.1]\n"
    "I1: No effect without live Instruction ID.\n"
    "I2: No closure without deterministic test + signed receipt.\n"
    "I3: No self-certification; Class B models output FLOW (operational_yield=0).\n"
    "I4: No replay of closed/expired instructions.\n"
    "I5: Immutable founder-only paths require Founder ES256 seal.\n"
    "I6: External bleeding-edge claims must cite verified Tier 1/2 search_receipt_id.\n"
)

# Paths whose modification needs the founder's own seal. A consultation may
# PROPOSE touching one of them; it may not approve it.
IMMUTABLE_FOUNDER_ONLY_PREFIXES = (
    ".githooks/",
    ".github/workflows/",
    "bin/idp-ci-guarded-paths",
    "bin/idp-guarded-paths",
    "bin/idp-auth",
    "bin/idp-auth-verify",
    "docs/keys/",
)

VALID_INVARIANT_IDS = frozenset(
    {
        "I1",
        "I2",
        "I3",
        "I4",
        "I5",
        "I6",
        "LAW_ZERO_MODEL_SOVEREIGNTY",
        "DARWIN_THIN_CLIENT",
        "FOUNDER_ONLY_PATH",
        "BUDGET_CAP",
        "CLASS_C_TRUST",
    }
)

CHALLENGE_MANDATES = (
    "invariant_security",
    "freshness_evidence",
    "complexity_asset",
)


@dataclass(frozen=True)
class ExternalClaim:
    """A claim about the world outside the estate, and the receipt that backs it."""

    claim: str
    search_receipt_id: Optional[str]


@dataclass(frozen=True)
class LeadProposal:
    summary: str
    diff_plan: str
    touched_paths: tuple
    invariant_bindings: tuple
    falsification_hooks: tuple
    external_claims: tuple
    lead_model_id: str  # Internal audit field only; stripped before blind challenge.


@dataclass(frozen=True)
class ChallengerVerdict:
    challenger_id: str
    mandate: str
    decision: str  # "APPROVE" | "OBJECT"
    rationale: str
    invariant_id: Optional[str] = None
    counterexample: Optional[str] = None
    receipt_id: Optional[str] = None


@dataclass(frozen=True)
class ConsultOutcome:
    status: str  # APPROVED_FOR_GREENLANE | ESCALATED_FOUNDER_SEAL | VETOED_FALSIFIED
    #             | REJECTED_UNCITED_OR_UNTRUSTED_CLAIM
    state: str  # FLOW | BLOCKED_FOUNDER_SEAL | REJECTED
    operational_yield: int  # Always 0 from Class B consultation.
    tier_served: str  # TIER_0_CACHE | TIER_2_FRONTIER
    consult_digest: str
    total_cost_uusd: int
    proposal_summary: str
    substantiated_objections: tuple = field(default_factory=tuple)
    discarded_noise_count: int = 0
    requires_founder_seal: bool = False
    revision_attempted: bool = False


LeadCallable = Callable[[str, str, list, Optional[list]], tuple]
ChallengerCallable = Callable[[str, dict], tuple]


def is_substantiated_objection(
    verdict: ChallengerVerdict,
    valid_receipt_ids: set,
) -> bool:
    """An objection counts only if it carries a counterexample AND grounds.

    "Feels risky" is noise. A counterexample that names a known invariant, or
    a receipt that is actually in evidence, is a falsification.
    """
    if verdict.decision != "OBJECT":
        return False
    if not verdict.counterexample or len(verdict.counterexample.strip()) < 12:
        return False
    has_valid_invariant = verdict.invariant_id in VALID_INVARIANT_IDS
    has_valid_receipt = bool(
        verdict.receipt_id and verdict.receipt_id in valid_receipt_ids
    )
    return has_valid_invariant or has_valid_receipt


class DialecticalConsultEngine:
    """System-first consultation gate: a frontier lead, judged by a blind fleet."""

    def __init__(
        self,
        ledger: MicroUsdLedger,
        search_twin: TwinSearchMemory,
        max_brief_chars: int = 8000,
    ) -> None:
        self.ledger = ledger
        self.search_twin = search_twin
        self.max_brief_chars = max_brief_chars

    def _compress_brief(
        self,
        instruction_id: str,
        intent: str,
        memory_hits: list,
        envelopes: list,
    ) -> str:
        """The brief the lead reads. Bounded, and it carries receipts, not prose."""
        lines = [
            f"INSTRUCTION_ID: {instruction_id}",
            f"INTENT: {' '.join(intent.strip().split())}",
            f"MEMORY_HITS ({len(memory_hits)}):",
        ]
        for m in memory_hits[:5]:
            lines.append(f"  - [{m['search_receipt_id']}] {m['fact_text']}")
        lines.append(f"SEARCH_RECEIPTS ({len(envelopes)}):")
        for e in envelopes[:5]:
            lines.append(
                f"  - [{e.search_receipt_id}|T{e.trust_tier}"
                f"|inj={e.injection_detected}] {e.sanitized_excerpt}"
            )
        brief = "\n".join(lines)
        if len(brief) > self.max_brief_chars:
            brief = brief[: self.max_brief_chars] + "\n[TRUNCATED_TO_2K_TOKEN_CAP]"
        return brief

    def _validate_lead_claims(
        self,
        proposal: LeadProposal,
        verified_by_id: dict,
    ) -> Optional[str]:
        """Deterministic pre-check: every external claim must cite live evidence."""
        if not proposal.external_claims:
            return None
        cited_tiers = []
        for claim in proposal.external_claims:
            if (
                not claim.search_receipt_id
                or claim.search_receipt_id not in verified_by_id
            ):
                return f"Uncited or unverified external claim: {claim.claim}"
            env = verified_by_id[claim.search_receipt_id]
            if env.injection_detected:
                return (
                    f"Claim cites injection-quarantined receipt {env.search_receipt_id}"
                )
            cited_tiers.append(env.trust_tier)
        if cited_tiers and all(
            t >= int(TrustTier.TIER_3_QUARANTINED) for t in cited_tiers
        ):
            return (
                "External claims rely solely on Tier-3 quarantined sources "
                "without Tier-1/2 corroboration"
            )
        return None

    @staticmethod
    def _touches_founder_only_path(touched_paths: tuple) -> bool:
        return any(p.startswith(IMMUTABLE_FOUNDER_ONLY_PREFIXES) for p in touched_paths)

    @staticmethod
    def _build_blind_challenger_packet(
        instruction_id: str,
        proposal: LeadProposal,
        envelopes: list,
    ) -> dict:
        """The challenger's view. The lead's model identity is deliberately absent."""
        return {
            "instruction_id": instruction_id,
            "summary": proposal.summary,
            "diff_plan": proposal.diff_plan,
            "touched_paths": list(proposal.touched_paths),
            "invariant_bindings": list(proposal.invariant_bindings),
            "falsification_hooks": list(proposal.falsification_hooks),
            "external_claims": [
                {"claim": c.claim, "search_receipt_id": c.search_receipt_id}
                for c in proposal.external_claims
            ],
            "verified_receipts": [
                {
                    "search_receipt_id": e.search_receipt_id,
                    "trust_tier": e.trust_tier,
                    "sanitized_excerpt": e.sanitized_excerpt,
                }
                for e in envelopes
            ],
        }

    def consult(
        self,
        instruction_id: str,
        intent: str,
        envelopes: list,
        lead_fn: LeadCallable,
        challengers: dict,
        memory_topic: Optional[str] = None,
        lead_transport: str = "stateless_api",
        lead_estimate_uusd: int = 50_000,
        challenger_estimate_uusd: int = 3_000,
        allow_revision: bool = True,
        now_epoch: Optional[int] = None,
    ) -> ConsultOutcome:
        """Run one consultation. Never self-certifies; always returns yield 0."""
        verified_envelopes = [
            e
            for e in envelopes
            if self.search_twin.verify_envelope(e, now_epoch=now_epoch)
        ]
        verified_by_id = {e.search_receipt_id: e for e in verified_envelopes}
        memory_hits = (
            self.search_twin.recall_memory(memory_topic, now_epoch=now_epoch)
            if memory_topic
            else []
        )

        evidence_hashes = [e.content_sha256 for e in verified_envelopes] + [
            m["search_receipt_id"] for m in memory_hits
        ]
        consult_digest = self.ledger.compute_consult_digest(
            INVARIANT_VERSION, intent, evidence_hashes
        )

        # Tier-0 cache: $0, zero model calls, zero upstream fetches.
        cached = self.ledger.get_cached_consult(consult_digest, now_epoch=now_epoch)
        if cached is not None:
            return ConsultOutcome(
                status=cached["status"],
                state=cached["state"],
                operational_yield=0,
                tier_served="TIER_0_CACHE",
                consult_digest=consult_digest,
                total_cost_uusd=0,
                proposal_summary=cached["proposal_summary"],
                discarded_noise_count=cached.get("discarded_noise_count", 0),
                requires_founder_seal=cached["requires_founder_seal"],
                revision_attempted=cached.get("revision_attempted", False),
            )

        compressed_brief = self._compress_brief(
            instruction_id, intent, memory_hits, verified_envelopes
        )

        total_cost = 0
        revision_attempted = False
        objections_for_revision = None

        for attempt in range(2):
            lease_id = self.ledger.reserve(
                instruction_id=instruction_id,
                role="architect",
                estimated_uusd=lead_estimate_uusd,
                transport=lead_transport,
                now_epoch=now_epoch,
            )
            try:
                proposal, actual_uusd = lead_fn(
                    PINNED_INVARIANTS_PREFIX,
                    compressed_brief,
                    verified_envelopes,
                    objections_for_revision,
                )
            except Exception:
                self.ledger.release(lease_id)
                raise
            self.ledger.settle(lease_id, actual_uusd)
            total_cost += actual_uusd

            # Deterministic pre-check, before any challenger is paid.
            claim_err = self._validate_lead_claims(proposal, verified_by_id)
            if claim_err is not None:
                return ConsultOutcome(
                    status="REJECTED_UNCITED_OR_UNTRUSTED_CLAIM",
                    state="REJECTED",
                    operational_yield=0,
                    tier_served="TIER_2_FRONTIER",
                    consult_digest=consult_digest,
                    total_cost_uusd=total_cost,
                    proposal_summary=proposal.summary,
                    substantiated_objections=(
                        {"mandate": "deterministic_precheck", "reason": claim_err},
                    ),
                    revision_attempted=revision_attempted,
                )

            blind_packet = self._build_blind_challenger_packet(
                instruction_id, proposal, verified_envelopes
            )
            substantiated = []
            noise_count = 0
            valid_receipt_ids = set(verified_by_id.keys()) | {
                m["search_receipt_id"] for m in memory_hits
            }

            for mandate in CHALLENGE_MANDATES:
                fn = challengers.get(mandate)
                if fn is None:
                    continue
                c_lease = self.ledger.reserve(
                    instruction_id=instruction_id,
                    role=f"challenger:{mandate}",
                    estimated_uusd=challenger_estimate_uusd,
                    transport="stateless_api",
                    now_epoch=now_epoch,
                )
                try:
                    verdict, c_cost = fn(mandate, blind_packet)
                except Exception:
                    self.ledger.release(c_lease)
                    raise
                self.ledger.settle(c_lease, c_cost)
                total_cost += c_cost

                if verdict.decision == "OBJECT":
                    if is_substantiated_objection(verdict, valid_receipt_ids):
                        substantiated.append(
                            {
                                "challenger_id": verdict.challenger_id,
                                "mandate": verdict.mandate,
                                "invariant_id": verdict.invariant_id,
                                "counterexample": verdict.counterexample,
                                "receipt_id": verdict.receipt_id,
                                "rationale": verdict.rationale,
                            }
                        )
                    else:
                        noise_count += 1

            # Asymmetric falsification: ONE substantiated objection vetoes.
            if substantiated:
                if attempt == 0 and allow_revision:
                    revision_attempted = True
                    objections_for_revision = substantiated
                    continue
                return ConsultOutcome(
                    status="VETOED_FALSIFIED",
                    state="REJECTED",
                    operational_yield=0,
                    tier_served="TIER_2_FRONTIER",
                    consult_digest=consult_digest,
                    total_cost_uusd=total_cost,
                    proposal_summary=proposal.summary,
                    substantiated_objections=tuple(substantiated),
                    discarded_noise_count=noise_count,
                    requires_founder_seal=self._touches_founder_only_path(
                        proposal.touched_paths
                    ),
                    revision_attempted=revision_attempted,
                )

            requires_seal = self._touches_founder_only_path(proposal.touched_paths)
            status = (
                "ESCALATED_FOUNDER_SEAL" if requires_seal else "APPROVED_FOR_GREENLANE"
            )
            state = "BLOCKED_FOUNDER_SEAL" if requires_seal else "FLOW"

            if not requires_seal:
                # The cached payload must reproduce the original outcome field
                # for field. A replay that reported a different noise count
                # would make the same digest return two different answers.
                self.ledger.put_cached_consult(
                    consult_digest,
                    {
                        "status": status,
                        "state": state,
                        "proposal_summary": proposal.summary,
                        "requires_founder_seal": False,
                        "discarded_noise_count": noise_count,
                        "revision_attempted": revision_attempted,
                    },
                    now_epoch=now_epoch,
                )

            return ConsultOutcome(
                status=status,
                state=state,
                operational_yield=0,  # Never self-certified; Lane 3 decides.
                tier_served="TIER_2_FRONTIER",
                consult_digest=consult_digest,
                total_cost_uusd=total_cost,
                proposal_summary=proposal.summary,
                discarded_noise_count=noise_count,
                requires_founder_seal=requires_seal,
                revision_attempted=revision_attempted,
            )

        raise RuntimeError("Unreachable consultation state")
