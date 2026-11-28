"""The critical-service facade: one entrypoint for the whole consultation path.

`CriticalConsultService` is the Ring-1-clean entrypoint that composes the
consultation plane into one flow:

  1. HEALTH. Fail closed. An unhealthy consult-plane halts the lane and emits a
     CRITICAL_SERVICE_OUTAGE escalation. There is no local Chrome fallback, no
     shadow account, no infinite retry, and no raw trace dumped to Telegram.
  2. PROOF OF EFFORT. Tier-0 discovery receipts are verified before any
     Tier-2 frontier token may be spent.
  3. ANTI-ABUSE. Spam, quota and cooldown are checked against the session.
  4. CONSULTATION. Tier-0 cache, or the Tier-2 frontier lead plus blind fleet.
  5. EXHAUSTION. The PoE receipt and consult digest are registered with the
     Founder firewall, so only a genuinely exhausted lane can escalate.
  6. DECISION CARD. A guarded-path result is compiled into the bounded
     five-field card. Nothing else escalates automatically.
  7. UNFREEZE. A lane is released only when the consultation produced actionable
     certified guidance.

This module does NOT deliver anything to the founder and does NOT mutate any
founder-only path. It decides and packages; the estate's existing doors
deliver.

Standard library only.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Optional

from .budget_ledger import MicroUsdLedger
from .dialectical_consult import (
    INVARIANT_VERSION,
    ChallengerCallable,
    ConsultOutcome,
    DialecticalConsultEngine,
    LeadCallable,
)
from .discovery_poe import (
    AntiAbuseRatchet,
    ProofOfEffortBundle,
    ProofOfEffortGate,
    TierDemotedError,
)
from .founder_firewall import (
    AdmissionClass,
    AdmittedDecision,
    DecisionMemoCard,
    DecisionModeFirewall,
    DecisionOption,
)
from .search_twin import TwinSearchMemory
from .stuck_router import StuckStateRouter


class CriticalServiceAlertError(RuntimeError):
    """Fail-closed outage: agents MUST halt. No Chrome, no manual fallback."""

    def __init__(self, probe_receipt: str, reason: str) -> None:
        self.probe_receipt = probe_receipt
        super().__init__(f"CRITICAL_SERVICE_ALERT [{probe_receipt}]: {reason}")


@dataclass(frozen=True)
class CriticalConsultResult:
    poe_receipt_id: str
    outcome: ConsultOutcome
    founder_decision: Optional[AdmittedDecision]
    unfroze_lane: bool


class CriticalConsultService:
    """First-class critical estate service: discovery, budget, consult, protect."""

    def __init__(
        self,
        ledger: MicroUsdLedger,
        search_twin: TwinSearchMemory,
        stuck_router: StuckStateRouter,
        ratchet: AntiAbuseRatchet,
        firewall: DecisionModeFirewall,
        max_brief_chars: int = 8000,
    ) -> None:
        self.ledger = ledger
        self.search_twin = search_twin
        self.stuck_router = stuck_router
        self.ratchet = ratchet
        self.firewall = firewall
        self.poe_gate = ProofOfEffortGate(search_twin=search_twin, ratchet=ratchet)
        self.engine = DialecticalConsultEngine(
            ledger=ledger,
            search_twin=search_twin,
            max_brief_chars=max_brief_chars,
        )
        self._healthy_override: bool = True

    def set_health_for_test(self, healthy: bool) -> None:
        """Test hook. Production health comes from the real probe, never a flag."""
        self._healthy_override = healthy

    def health_check(self, now_epoch: Optional[int] = None):
        ts = now_epoch if now_epoch is not None else int(time.time())
        if not self._healthy_override:
            receipt = (
                "outage_"
                + hashlib.sha256(f"manual_unhealthy|{ts}".encode("utf-8")).hexdigest()[
                    :12
                ]
            )
            return False, receipt
        try:
            self.ledger.assert_conservation()
            return True, f"ok_{ts}"
        except Exception as exc:
            receipt = (
                "outage_"
                + hashlib.sha256(f"ledger_err|{exc}|{ts}".encode("utf-8")).hexdigest()[
                    :12
                ]
            )
            return False, receipt

    def consult_when_stuck(
        self,
        bundle: ProofOfEffortBundle,
        intent: str,
        lead_fn: LeadCallable,
        challengers: dict,
        memory_topic: Optional[str] = None,
        lead_transport: str = "stateless_api",
        now_epoch: Optional[int] = None,
    ) -> CriticalConsultResult:
        ts = now_epoch if now_epoch is not None else int(time.time())

        # 1. Fail-closed criticality.
        healthy, probe_receipt = self.health_check(now_epoch=ts)
        if not healthy:
            self.firewall.submit(
                DecisionMemoCard(
                    instruction_id=bundle.instruction_id,
                    base_sha=bundle.base_sha,
                    admission_class=AdmissionClass.CRITICAL_SERVICE_OUTAGE,
                    deadlock_summary=(
                        "consult-plane failed health probe; active lanes halted fail-closed."
                    ),
                    autonomy_stop_reason=f"Health probe failed with receipt {probe_receipt}",
                    options=(
                        DecisionOption(
                            "A",
                            "Restart Lane 1/2 consult-plane worker",
                            "Low -- stateless restart",
                        ),
                        DecisionOption(
                            "B",
                            "Park non-critical lanes until DB audit",
                            "Zero write risk",
                        ),
                    ),
                    recommended_option_id="A",
                    outage_probe_receipt=probe_receipt,
                ),
                now_epoch=ts,
            )
            raise CriticalServiceAlertError(
                probe_receipt,
                "consult-plane unhealthy; halt active branch cleanly "
                "(zero Chrome/manual fallback)",
            )

        # 2. Proof of Effort, before any frontier spend.
        poe_receipt_id = self.poe_gate.verify(bundle, now_epoch=ts)

        # 3. Anti-abuse.
        abuse_check = self.ratchet.check_pre_consult(
            session_id=bundle.session_id,
            instruction_id=bundle.instruction_id,
            error_digest=bundle.error_digest,
            intent_text=intent,
            invariant_version=INVARIANT_VERSION,
            now_epoch=ts,
        )

        # 4. The consultation itself.
        if abuse_check.get("spam_detected"):
            # A repeat of a question already answered in this session is served
            # from the Tier-0 cache at $0. Paying for the same answer twice is
            # exactly what the ratchet exists to prevent.
            prior_digest = abuse_check.get("prior_consult_digest") or ""
            cached = (
                self.ledger.get_cached_consult(prior_digest, now_epoch=ts)
                if prior_digest
                else None
            )
            if cached is None:
                # Nothing cached to serve: refuse rather than pay again.
                raise TierDemotedError(
                    "TIER_1_ONLY: duplicate or paraphrased request with no cached answer to serve"
                )
            outcome = ConsultOutcome(
                status=cached["status"],
                state=cached["state"],
                operational_yield=0,
                tier_served="TIER_0_CACHE",
                consult_digest=prior_digest,
                total_cost_uusd=0,
                proposal_summary=cached["proposal_summary"],
                discarded_noise_count=cached.get("discarded_noise_count", 0),
                requires_founder_seal=cached["requires_founder_seal"],
                revision_attempted=cached.get("revision_attempted", False),
            )
        else:
            outcome = self.engine.consult(
                instruction_id=bundle.instruction_id,
                intent=intent,
                envelopes=list(bundle.search_envelopes),
                lead_fn=lead_fn,
                challengers=challengers,
                memory_topic=memory_topic,
                lead_transport=lead_transport,
                now_epoch=ts,
            )

        if not abuse_check["spam_detected"]:
            self.ratchet.record_consult(
                session_id=bundle.session_id,
                instruction_id=bundle.instruction_id,
                error_digest=bundle.error_digest,
                intent_text=intent,
                invariant_version=INVARIANT_VERSION,
                now_epoch=ts,
                consult_digest=outcome.consult_digest,
            )

        # 5. Register the exhaustion chain.
        self.firewall.register_exhaustion(
            instruction_id=bundle.instruction_id,
            poe_receipt_id=poe_receipt_id,
            consult_digest=outcome.consult_digest,
            now_epoch=ts,
        )

        # 6. A guarded-path result is the ONLY automatic escalation.
        founder_decision: Optional[AdmittedDecision] = None
        if outcome.status == "ESCALATED_FOUNDER_SEAL":
            founder_decision = self.firewall.submit(
                DecisionMemoCard(
                    instruction_id=bundle.instruction_id,
                    base_sha=bundle.base_sha,
                    admission_class=AdmissionClass.GUARDED_PATH_SEAL,
                    deadlock_summary=(
                        f"Guarded path change on {bundle.instruction_id} "
                        "requires Founder ES256 seal."
                    ),
                    autonomy_stop_reason=(
                        "Touches immutable founder-only path; blind fleet approved proposal."
                    ),
                    options=(
                        DecisionOption(
                            "A",
                            "Sign ES256 Founder seal and promote to Greenlane",
                            "Control-plane update",
                        ),
                        DecisionOption(
                            "B",
                            "Reject and keep current guarded primitive frozen",
                            "Zero state change",
                        ),
                    ),
                    recommended_option_id="A",
                    poe_receipt_id=poe_receipt_id,
                    consult_digest=outcome.consult_digest,
                ),
                now_epoch=ts,
            )

        # 7. Release the lane only on actionable certified guidance.
        unfroze = False
        if outcome.status == "APPROVED_FOR_GREENLANE" and self.stuck_router.is_frozen(
            bundle.instruction_id
        ):
            self.stuck_router.unfreeze_after_consult(
                bundle.instruction_id, outcome.consult_digest
            )
            unfroze = True

        return CriticalConsultResult(
            poe_receipt_id=poe_receipt_id,
            outcome=outcome,
            founder_decision=founder_decision,
            unfroze_lane=unfroze,
        )
