#!/usr/bin/env python3
"""Executable proof for the Founder Protection Firewall and the PoE gate.

Twelve deterministic proofs, standard library only, no network, no model call:

  01 Gortex offline falls back to the deterministic Git/AST index
  02 a repeated error digest freezes the lane and refuses the retry
  03 zero-progress churn and a gate refusal each freeze the lane
  04 missing discovery is rejected at zero frontier spend, with a strike
  05 a raw terminal dump over the cap is rejected at the door
  06 three strikes reap the session through the IoC
  07 cooldown and instruction quota demote the session to Tier-1 only
  08 a spam repeat is served from the Tier-0 cache at $0 and adds a strike
  09 the firewall denies unexhausted and non-whitelisted pings
  10 a guarded-path consult queues a bounded coalesced card, no defect
  11 a non-guarded policy escalation logs a founder-intervention defect
  12 a critical service outage fails closed and emits an immediate alert

The founder's attention is a defect surface: every assertion here is about
what does NOT reach the founder.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

_IDP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _seed_consult_plane() -> None:
    """Load the consult plane by file path and seed sys.modules.

    `platform/` has no __init__.py on purpose (idp#3564): a package named
    `platform` collides with the stdlib module `platform` the moment anything
    imports it bare. Seeding sys.modules under the real dotted names means the
    `from platform.consult_plane...` imports below hit the sys.modules fast
    path instead of re-resolving through the poisoned bare `platform` name.

    Same technique as tests/judge/test_drift.py.
    """
    for dotted, rel in (
        ("platform.consult_plane", "platform/consult_plane/__init__.py"),
        (
            "platform.consult_plane.budget_ledger",
            "platform/consult_plane/budget_ledger.py",
        ),
        (
            "platform.consult_plane.search_twin",
            "platform/consult_plane/search_twin.py",
        ),
        (
            "platform.consult_plane.dialectical_consult",
            "platform/consult_plane/dialectical_consult.py",
        ),
        (
            "platform.consult_plane.discovery_poe",
            "platform/consult_plane/discovery_poe.py",
        ),
        (
            "platform.consult_plane.stuck_router",
            "platform/consult_plane/stuck_router.py",
        ),
        (
            "platform.consult_plane.founder_firewall",
            "platform/consult_plane/founder_firewall.py",
        ),
        ("platform.consult_plane.service", "platform/consult_plane/service.py"),
    ):
        if dotted in sys.modules:
            continue
        path = os.path.join(_IDP_ROOT, rel)
        spec = importlib.util.spec_from_file_location(dotted, path)
        module = importlib.util.module_from_spec(spec)
        if rel.endswith("__init__.py"):
            module.__path__ = [os.path.dirname(path)]
        sys.modules[dotted] = module
        spec.loader.exec_module(module)


_seed_consult_plane()

from platform.consult_plane.budget_ledger import MicroUsdLedger  # noqa: E402
from platform.consult_plane.dialectical_consult import (  # noqa: E402
    ChallengerVerdict,
    ExternalClaim,
    LeadProposal,
)
from platform.consult_plane.discovery_poe import (  # noqa: E402
    AntiAbuseRatchet,
    AntiAbuseReapedError,
    CompositeCodeDiscovery,
    DeterministicGitAstFallback,
    GortexHttpProvider,
    ProofOfEffortBundle,
    ProofOfEffortIncompleteError,
    SqliteMemoryDiscoveryAdapter,
    TierDemotedError,
)
from platform.consult_plane.founder_firewall import (  # noqa: E402
    AdmissionClass,
    DecisionMemoCard,
    DecisionModeFirewall,
    DecisionOption,
    FounderFirewallDenyError,
)
from platform.consult_plane.search_twin import RawSearchHit, TwinSearchMemory  # noqa: E402
from platform.consult_plane.service import (  # noqa: E402
    CriticalConsultService,
    CriticalServiceAlertError,
)
from platform.consult_plane.stuck_router import (  # noqa: E402
    LaneFrozenForConsultError,
    StuckStateRouter,
    normalize_error_digest,
)


class TestFounderFirewallAndPoE(unittest.TestCase):
    def setUp(self) -> None:
        self.now = 1_795_850_000
        self.tmpdir = tempfile.TemporaryDirectory()
        sample_file = Path(self.tmpdir.name) / "router.py"
        sample_file.write_text(
            "class SovereignRouter:\n    def route_role(self):\n        return 'ok'\n",
            encoding="utf-8",
        )

        self.ledger = MicroUsdLedger(db_path=":memory:", monthly_cap_uusd=200_000_000)
        self.search_twin = TwinSearchMemory(
            signing_secret=b"sovereign-key-32-bytes-minimum!!", db_path=":memory:"
        )
        self.stuck_router = StuckStateRouter(db_path=":memory:")
        self.ratchet = AntiAbuseRatchet(
            db_path=":memory:", cooldown_seconds=30, max_consults_per_instruction=2
        )
        self.firewall = DecisionModeFirewall(db_path=":memory:")
        self.service = CriticalConsultService(
            ledger=self.ledger,
            search_twin=self.search_twin,
            stuck_router=self.stuck_router,
            ratchet=self.ratchet,
            firewall=self.firewall,
        )
        self.code_discovery = CompositeCodeDiscovery(
            # Offline Gortex proves the deterministic fallback.
            gortex=GortexHttpProvider("http://127.0.0.1:1", timeout_seconds=0.1),
            fallback=DeterministicGitAstFallback(self.tmpdir.name),
        )
        self.mem_discovery = SqliteMemoryDiscoveryAdapter(
            search_twin=self.search_twin,
            issue_classes={"router_timeout": "CA-0042"},
        )

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def _approving_challengers(self) -> dict:
        return {
            "invariant_security": lambda m, p: (
                ChallengerVerdict("glm-5.3", m, "APPROVE", "ok"),
                1_000,
            ),
            "freshness_evidence": lambda m, p: (
                ChallengerVerdict("deepseek-v3", m, "APPROVE", "ok"),
                1_000,
            ),
            "complexity_asset": lambda m, p: (
                ChallengerVerdict("minimax-m3", m, "APPROVE", "ok"),
                1_000,
            ),
        }

    def _valid_bundle(
        self,
        instruction_id: str = "I-9100",
        session_id: str = "sess_1",
        touches_external: bool = False,
        error_text: str = "AssertionError: router timeout on role architect",
    ) -> ProofOfEffortBundle:
        code_r = self.code_discovery.discover("route_role", now_epoch=self.now)
        mem_r = self.mem_discovery.discover("router_timeout", now_epoch=self.now)
        envs = ()
        if touches_external:
            found, _ = self.search_twin.search(
                "cloudflare workers timeout",
                lambda q: [
                    RawSearchHit(
                        "https://developers.cloudflare.com/workers/",
                        "Workers CPU timeout limit docs.",
                    )
                ],
                now_epoch=self.now,
            )
            envs = tuple(found)
        return ProofOfEffortBundle(
            instruction_id=instruction_id,
            session_id=session_id,
            base_sha="461cb4d5e",
            error_digest=normalize_error_digest(error_text),
            failure_excerpt=error_text,
            touches_external_dependency=touches_external,
            code_receipt=code_r,
            memory_receipt=mem_r,
            search_envelopes=envs,
        )

    def test_01_gortex_offline_falls_back_to_deterministic_git_ast(self) -> None:
        receipt = self.code_discovery.discover("route_role", now_epoch=self.now)
        self.assertEqual(receipt.backend, "git_ast_fallback")
        self.assertTrue(any("route_role" in s for s in receipt.matched_symbols))

    def test_02_compulsory_stuck_trigger_repeat_error_freezes_lane(self) -> None:
        v1 = self.stuck_router.record_attempt(
            "I-9101", "ERR: disk full ENOSPC", failing_assertions=2, now_epoch=self.now
        )
        self.assertFalse(v1.is_stuck)
        v2 = self.stuck_router.record_attempt(
            "I-9101",
            "ERR: disk full ENOSPC",
            failing_assertions=2,
            now_epoch=self.now + 5,
        )
        self.assertTrue(v2.is_stuck)
        self.assertEqual(v2.trigger, "REPEAT_ERROR_HASH")
        self.assertTrue(v2.frozen)

        # An unconsulted retry MUST be refused mechanically.
        with self.assertRaises(LaneFrozenForConsultError):
            self.stuck_router.record_attempt(
                "I-9101",
                "ERR: another try",
                failing_assertions=2,
                now_epoch=self.now + 10,
            )

    def test_03_compulsory_stuck_trigger_zero_progress_and_gate_refusal(self) -> None:
        # 3 attempts with non-decreasing failing_assertions (3 -> 3 -> 4)
        self.assertFalse(
            self.stuck_router.record_attempt(
                "I-9102", "err A", 3, now_epoch=self.now
            ).is_stuck
        )
        self.assertFalse(
            self.stuck_router.record_attempt(
                "I-9102", "err B", 3, now_epoch=self.now + 1
            ).is_stuck
        )
        v3 = self.stuck_router.record_attempt(
            "I-9102", "err C", 4, now_epoch=self.now + 2
        )
        self.assertTrue(v3.is_stuck)
        self.assertEqual(v3.trigger, "ZERO_PROGRESS_CHURN")

        # A gate refusal freezes immediately on attempt 1.
        vg = self.stuck_router.record_attempt(
            "I-9103",
            "denied",
            1,
            gate_refused=True,
            gate_name="bin/idp-ci-guarded-paths",
        )
        self.assertTrue(vg.is_stuck)
        self.assertEqual(vg.trigger, "GATE_REFUSAL")

    def test_04_missing_poe_discovery_rejected_at_zero_frontier_spend(self) -> None:
        lead_called = {"count": 0}
        lazy_bundle = ProofOfEffortBundle(
            instruction_id="I-9104",
            session_id="sess_lazy",
            base_sha="461cb4d5e",
            error_digest="abc123",
            failure_excerpt="help I am stuck",
            touches_external_dependency=True,
            code_receipt=None,
            memory_receipt=None,
            search_envelopes=(),
        )
        with self.assertRaises(ProofOfEffortIncompleteError) as ctx:
            self.service.consult_when_stuck(
                bundle=lazy_bundle,
                intent="Fix my bug",
                lead_fn=lambda *a: (lead_called.__setitem__("count", 1), 0),
                challengers=self._approving_challengers(),
                now_epoch=self.now,
            )
        self.assertEqual(lead_called["count"], 0)
        self.assertEqual(self.ledger.snapshot().settled_uusd, 0)
        self.assertEqual(ctx.exception.strike_count, 1)
        self.assertGreaterEqual(len(ctx.exception.missing_reasons), 3)

    def test_05_raw_terminal_dump_exceeding_2k_token_cap_rejected(self) -> None:
        bundle = self._valid_bundle(instruction_id="I-9105", session_id="sess_dump")
        bloated = ProofOfEffortBundle(
            **{**bundle.__dict__, "failure_excerpt": "X" * 9000}
        )
        with self.assertRaises(ProofOfEffortIncompleteError) as ctx:
            self.service.consult_when_stuck(
                bundle=bloated,
                intent="Analyze raw dump",
                lead_fn=lambda *a: self.fail(
                    "Lead must not be invoked on a bloated dump"
                ),
                challengers=self._approving_challengers(),
                now_epoch=self.now,
            )
        self.assertTrue(any("2K-token cap" in r for r in ctx.exception.missing_reasons))

    def test_06_three_abuse_strikes_reap_session_via_ioc(self) -> None:
        lazy = ProofOfEffortBundle(
            instruction_id="I-9106",
            session_id="sess_abuser",
            base_sha="461cb4d5e",
            error_digest="err1",
            failure_excerpt="stuck",
            touches_external_dependency=False,
        )
        for expected_strike in (1, 2):
            with self.assertRaises(ProofOfEffortIncompleteError) as ctx:
                self.service.consult_when_stuck(
                    lazy,
                    "help",
                    lambda *a: None,
                    {},
                    now_epoch=self.now + expected_strike,
                )
            self.assertEqual(ctx.exception.strike_count, expected_strike)

        # Strike 3 MUST reap the session permanently.
        with self.assertRaises(AntiAbuseReapedError):
            self.service.consult_when_stuck(
                lazy, "help", lambda *a: None, {}, now_epoch=self.now + 3
            )

        state = self.ratchet.get_session_state("sess_abuser")
        self.assertEqual(state["status"], "REAPED_IOC")
        self.assertEqual(len(self.ratchet.defect_log()), 3)

    def test_07_cooldown_and_instruction_quota_demote_to_tier1_only(self) -> None:
        def lead_fn(prefix, brief, envs, obj):
            return (
                LeadProposal(
                    "Fix A",
                    "diff",
                    ("platform/a.py",),
                    ("I1",),
                    ("test_a",),
                    (),
                    "frontier-x",
                ),
                15_000,
            )

        b1 = self._valid_bundle("I-9107", "sess_burst", error_text="error alpha")
        self.service.consult_when_stuck(
            b1,
            "Resolve alpha timeout",
            lead_fn,
            self._approving_challengers(),
            now_epoch=self.now,
        )

        # A second call inside the cooldown with a distinct error MUST demote to Tier-1 only.
        b2 = self._valid_bundle(
            "I-9108", "sess_burst", error_text="error beta completely different"
        )
        with self.assertRaises(TierDemotedError):
            self.service.consult_when_stuck(
                b2,
                "Resolve beta cache miss",
                lead_fn,
                self._approving_challengers(),
                now_epoch=self.now + 5,
            )

        self.assertEqual(
            self.ratchet.get_session_state("sess_burst")["status"], "DEMOTED_TIER1"
        )

    def test_08_spam_duplicate_serves_tier0_cache_at_zero_spend_and_adds_strike(
        self,
    ) -> None:
        lead_calls = {"count": 0}

        def lead_fn(prefix, brief, envs, obj):
            lead_calls["count"] += 1
            return (
                LeadProposal(
                    "Fix cache",
                    "diff",
                    ("platform/c.py",),
                    ("I1",),
                    ("test_c",),
                    (),
                    "frontier-x",
                ),
                15_000,
            )

        b1 = self._valid_bundle("I-9109", "sess_spam", error_text="exact same error")
        r1 = self.service.consult_when_stuck(
            b1,
            "Fix cache timeout issue",
            lead_fn,
            self._approving_challengers(),
            now_epoch=self.now,
        )
        self.assertEqual(r1.outcome.tier_served, "TIER_2_FRONTIER")
        self.assertEqual(lead_calls["count"], 1)

        # A spam repeat hits the Tier-0 cache at $0 AND increments the strike count.
        r2 = self.service.consult_when_stuck(
            b1,
            "Fix cache timeout issue",
            lead_fn,
            self._approving_challengers(),
            now_epoch=self.now + 60,
        )
        self.assertEqual(r2.outcome.tier_served, "TIER_0_CACHE")
        self.assertEqual(r2.outcome.total_cost_uusd, 0)
        self.assertEqual(lead_calls["count"], 1)
        self.assertEqual(self.ratchet.get_session_state("sess_spam")["strikes"], 1)

    def test_09_founder_firewall_blocks_direct_unexhausted_and_non_whitelist_pings(
        self,
    ) -> None:
        # Case A: missing Proof-of-Exhaustion -> DENY
        unexhausted_card = DecisionMemoCard(
            instruction_id="I-9110",
            base_sha="461cb4d5e",
            admission_class=AdmissionClass.IRREVERSIBLE_POLICY_TRADEOFF,
            deadlock_summary="Need policy call on retention window.",
            autonomy_stop_reason="No law in laws.yaml specifies retention.",
            options=(
                DecisionOption("A", "30 days", "Low"),
                DecisionOption("B", "90 days", "Medium"),
            ),
            recommended_option_id="A",
            poe_receipt_id="poe_forged",
            consult_digest="digest_forged",
        )
        with self.assertRaises(FounderFirewallDenyError):
            self.firewall.submit(unexhausted_card, now_epoch=self.now)

        # Case B: a non-whitelisted chatter class -> DENY
        with self.assertRaises(FounderFirewallDenyError):
            self.firewall.submit(
                unexhausted_card,
                raw_class_override="DEBUGGING_QUESTION",
                now_epoch=self.now,
            )

    def test_10_guarded_path_consult_auto_queues_coalesced_5_field_card_without_defect(
        self,
    ) -> None:
        def lead_fn(prefix, brief, envs, obj):
            return (
                LeadProposal(
                    "Update pre-push thin-client shunt",
                    "Edit .githooks/pre-push",
                    (".githooks/pre-push",),
                    ("I5",),
                    ("tests/falsify_guarded_paths.sh",),
                    (),
                    "frontier-x",
                ),
                15_000,
            )

        b = self._valid_bundle("I-9111", "sess_guard")
        res = self.service.consult_when_stuck(
            b,
            "Update hook shunt",
            lead_fn,
            self._approving_challengers(),
            now_epoch=self.now,
        )
        self.assertEqual(res.outcome.status, "ESCALATED_FOUNDER_SEAL")
        self.assertIsNotNone(res.founder_decision)
        self.assertEqual(res.founder_decision.delivery_mode, "COALESCED_DIGEST")
        self.assertFalse(res.founder_decision.defect_logged)
        self.assertIn("APPROVE_A", res.founder_decision.one_tap_tokens)
        self.assertIn("REJECT_PARK", res.founder_decision.one_tap_tokens)

        digest = self.firewall.flush_coalesced_digest()
        self.assertEqual(len(digest), 1)
        self.assertEqual(self.firewall.flush_coalesced_digest(), [])

    def test_11_non_guarded_policy_escalation_logs_founder_intervention_defect_ratchet(
        self,
    ) -> None:
        self.firewall.register_exhaustion(
            "I-9112", "poe_valid1234", "dig_valid1234", now_epoch=self.now
        )
        card = DecisionMemoCard(
            instruction_id="I-9112",
            base_sha="461cb4d5e",
            admission_class=AdmissionClass.IRREVERSIBLE_POLICY_TRADEOFF,
            deadlock_summary="Pricing tier split between Ring 1 SDK and Ring 2 SaaS.",
            autonomy_stop_reason="Commercial pricing policy absent from laws.yaml.",
            options=(
                DecisionOption(
                    "A", "Separate Ring 1 license", "Clean commercial isolation"
                ),
                DecisionOption("B", "Bundle with Mumchimp", "Couples rings"),
            ),
            recommended_option_id="A",
            poe_receipt_id="poe_valid1234",
            consult_digest="dig_valid1234",
        )
        admitted = self.firewall.submit(card, now_epoch=self.now)
        self.assertTrue(admitted.defect_logged)
        self.assertEqual(admitted.delivery_mode, "COALESCED_DIGEST")
        self.assertEqual(len(self.firewall.defect_ratchet_entries()), 1)

    def test_13_firewall_enforces_the_contract_itself_not_just_the_whitelist(
        self,
    ) -> None:
        """Every clause of the five-field contract must be able to refuse a card.

        The whitelist alone is not the firewall: a card can be in the right class
        and still be unusable, and an unusable card must not reach the founder.
        """
        self.firewall.register_exhaustion(
            "I-9114", "poe_valid1234", "dig_valid1234", now_epoch=self.now
        )
        base = dict(
            instruction_id="I-9114",
            base_sha="461cb4d5e",
            admission_class=AdmissionClass.IRREVERSIBLE_POLICY_TRADEOFF,
            deadlock_summary="One line of deadlock.",
            autonomy_stop_reason="No governing law exists.",
            recommended_option_id="A",
            poe_receipt_id="poe_valid1234",
            consult_digest="dig_valid1234",
        )
        good_options = (
            DecisionOption("A", "First", "Low"),
            DecisionOption("B", "Second", "Medium"),
        )

        # A class value that is not an AdmissionClass at all -> DENY.
        with self.assertRaises(FounderFirewallDenyError):
            self.firewall.submit(
                DecisionMemoCard(
                    **{
                        **base,
                        "admission_class": "IRREVERSIBLE_POLICY_TRADEOFF",
                        "options": good_options,
                    }
                ),
                now_epoch=self.now,
            )

        # A multi-line deadlock summary -> DENY (one line only).
        with self.assertRaises(FounderFirewallDenyError):
            self.firewall.submit(
                DecisionMemoCard(
                    **{
                        **base,
                        "deadlock_summary": "line one\nline two",
                        "options": good_options,
                    }
                ),
                now_epoch=self.now,
            )

        # An over-long deadlock summary -> DENY.
        with self.assertRaises(FounderFirewallDenyError):
            self.firewall.submit(
                DecisionMemoCard(
                    **{**base, "deadlock_summary": "x" * 161, "options": good_options}
                ),
                now_epoch=self.now,
            )

        # One option is not a decision -> DENY.
        with self.assertRaises(FounderFirewallDenyError):
            self.firewall.submit(
                DecisionMemoCard(
                    **{
                        **base,
                        "options": (DecisionOption("A", "Only", "Low"),),
                    }
                ),
                now_epoch=self.now,
            )

        # Four options is a survey, not a decision -> DENY.
        with self.assertRaises(FounderFirewallDenyError):
            self.firewall.submit(
                DecisionMemoCard(
                    **{
                        **base,
                        "options": (
                            DecisionOption("A", "a", "Low"),
                            DecisionOption("B", "b", "Low"),
                            DecisionOption("C", "c", "Low"),
                            DecisionOption("D", "d", "Low"),
                        ),
                    }
                ),
                now_epoch=self.now,
            )

        # A recommendation that is not one of the options -> DENY.
        with self.assertRaises(FounderFirewallDenyError):
            self.firewall.submit(
                DecisionMemoCard(
                    **{**base, "recommended_option_id": "Z", "options": good_options}
                ),
                now_epoch=self.now,
            )

        # Duplicate option ids -> DENY.
        with self.assertRaises(FounderFirewallDenyError):
            self.firewall.submit(
                DecisionMemoCard(
                    **{
                        **base,
                        "options": (
                            DecisionOption("A", "First", "Low"),
                            DecisionOption("A", "Duplicate", "Low"),
                        ),
                    }
                ),
                now_epoch=self.now,
            )

        # And the well-formed card IS admitted, so the checks are not simply refusing all.
        admitted = self.firewall.submit(
            DecisionMemoCard(**{**base, "options": good_options}), now_epoch=self.now
        )
        self.assertTrue(admitted.card_id.startswith("dec_"))

    def test_14_outage_always_alerts_immediately_and_never_coalesces(self) -> None:
        """A critical outage interrupts the founder NOW, and is never batched.

        test_12 shows the outage path raises. This proves the delivery mode of
        the card it queues, and that a second outage card does not get swept
        into the coalesced digest either.
        """
        self.service.set_health_for_test(False)
        b = self._valid_bundle("I-9115", "sess_outage2")
        for _ in range(2):
            with self.assertRaises(CriticalServiceAlertError):
                self.service.consult_when_stuck(
                    b, "Need consult", lambda *a: None, {}, now_epoch=self.now
                )
        # Nothing is waiting in the coalesced digest.
        self.assertEqual(self.firewall.flush_coalesced_digest(), [])
        # Both outage cards logged a defect.
        entries = self.firewall.defect_ratchet_entries()
        self.assertEqual(len(entries), 2)
        for entry in entries:
            self.assertEqual(entry["admission_class"], "CRITICAL_SERVICE_OUTAGE")

    def test_15_paraphrased_spam_is_detected_not_only_identical_digests(self) -> None:
        """A reworded intent is the same request and must be caught as spam.

        Identical error digests are the easy case. An agent that changes the
        wording but asks the same thing must still hit the spam path.
        """
        calls = {"count": 0}

        def lead_fn(prefix, brief, envs, obj):
            calls["count"] += 1
            return (
                LeadProposal(
                    "Fix the timeout in the router",
                    "diff",
                    ("platform/router.py",),
                    ("I1",),
                    ("test_router",),
                    (),
                    "frontier-x",
                ),
                15_000,
            )

        b1 = self._valid_bundle("I-9116", "sess_para", error_text="alpha failure text")
        self.service.consult_when_stuck(
            b1,
            "Resolve the router timeout that keeps failing in the queue consumer",
            lead_fn,
            self._approving_challengers(),
            now_epoch=self.now,
        )
        # A reworded intent with a DIFFERENT error digest, same session.
        b2 = self._valid_bundle(
            "I-9117", "sess_para", error_text="totally other failure"
        )
        self.service.consult_when_stuck(
            b2,
            "Resolve the router timeout that keeps failing in the queue consumer",
            lead_fn,
            self._approving_challengers(),
            now_epoch=self.now + 60,
        )
        self.assertGreaterEqual(
            self.ratchet.get_session_state("sess_para")["strikes"], 1
        )

    def test_16_identical_error_digest_is_spam_even_when_the_intent_differs(
        self,
    ) -> None:
        """The error digest alone is a spam signal, independent of the wording.

        test_08 catches a repeat because the intent repeats too, and test_15
        catches a repeat because the wording repeats. An agent can also repeat
        the SAME failure while rewording the request, and the shared error
        digest must catch that on its own -- and serve the answer at $0 rather
        than paying for the same question twice.
        """
        calls = {"count": 0}

        def lead(prefix, brief, envs, obj):
            calls["count"] += 1
            return (
                LeadProposal(
                    "Clear the build cache",
                    "diff",
                    ("platform/cache.py",),
                    ("I1",),
                    ("t",),
                    (),
                    "x",
                ),
                15_000,
            )

        r1 = self.service.consult_when_stuck(
            self._valid_bundle(
                "I-9118", "sess_digest", error_text="ENOSPC no space left"
            ),
            "Diagnose the disk exhaustion in the build cache directory",
            lead,
            self._approving_challengers(),
            now_epoch=self.now,
        )
        self.assertEqual(r1.outcome.tier_served, "TIER_2_FRONTIER")
        self.assertEqual(calls["count"], 1)

        # Same failure digest, deliberately different wording with no token overlap.
        r2 = self.service.consult_when_stuck(
            self._valid_bundle(
                "I-9119", "sess_digest", error_text="ENOSPC no space left"
            ),
            "Diagnose the ENOSPC condition",
            lead,
            self._approving_challengers(),
            now_epoch=self.now + 60,
        )
        # The repeat is served from the cache at $0: no second frontier call.
        self.assertEqual(r2.outcome.tier_served, "TIER_0_CACHE")
        self.assertEqual(r2.outcome.total_cost_uusd, 0)
        self.assertEqual(calls["count"], 1)
        # And the session is struck for asking again.
        self.assertGreaterEqual(
            self.ratchet.get_session_state("sess_digest")["strikes"], 1
        )

    def test_12_critical_service_outage_fails_closed_and_emits_immediate_alert(
        self,
    ) -> None:
        self.service.set_health_for_test(False)
        b = self._valid_bundle("I-9113", "sess_outage")
        with self.assertRaises(CriticalServiceAlertError) as ctx:
            self.service.consult_when_stuck(
                b, "Need consult", lambda *a: None, {}, now_epoch=self.now
            )
        self.assertTrue(ctx.exception.probe_receipt.startswith("outage_"))
        # An outage does not wait in the coalesced digest.
        self.assertEqual(self.firewall.flush_coalesced_digest(), [])
        self.assertEqual(len(self.firewall.defect_ratchet_entries()), 1)
        self.assertEqual(
            self.firewall.defect_ratchet_entries()[0]["admission_class"],
            "CRITICAL_SERVICE_OUTAGE",
        )


if __name__ == "__main__":
    unittest.main()
