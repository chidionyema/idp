"""KARMA causal debt and independent-reward invariants."""

import importlib.util
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "platform/estate/karma/contracts.py"
spec = importlib.util.spec_from_file_location("karma_contract", PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
WHEN = "2026-11-12T14:00:00Z"


def event(eid, kind, parents=None, **overrides):
    row = {
        "event_id": eid,
        "kind": kind,
        "recorded_at": WHEN,
        "parent_event_ids": parents or [],
        "instruction_id": "INS-1",
        "agent_urn": "urn:aid:original",
    }
    row.update(overrides)
    return row


def accepted():
    return event(
        "accept",
        "INSTRUCTION_ACCEPTED",
        expected_outcome_digest="a" * 64,
        model_revision="opaque-alias",
        provider="google",
        generation="G1",
    )


def proof(e):
    # Unit-test-only independent oracle; NOT a real QUAD verifier.
    return e.get("test_oracle") is True


class KarmaContractTests(unittest.TestCase):
    def test_acceptance_without_verified_identity_is_not_accepted(self):
        r = mod.project([accepted()])
        self.assertEqual(r["obligations"], {})
        self.assertEqual(r["gaps"][0]["reason"], "UNVERIFIED_EXTERNAL_AUTHORITY")

    def test_real_evidence_oracle_accepts_bounded_debt_not_imaginary_yield(self):
        r = mod.project([{**accepted(), "test_oracle": True}], proof)
        self.assertEqual(r["unresolved"], ["INS-1"])
        self.assertFalse(r["obligations"]["INS-1"]["verified_yield"])

    def test_exact_accepted_instruction_carries_expense_and_unknown_money(self):
        events = [
            {**accepted(), "test_oracle": True},
            event(
                "spend",
                "COST_OBSERVED",
                ["accept"],
                tokens_in=123,
                tokens_out=34,
                test_oracle=True,
            ),
        ]
        r = mod.project(events, proof)["obligations"]["INS-1"]
        self.assertEqual(r["costs"], {"tokens_in": 123, "tokens_out": 34})
        self.assertIsNone(r["money_cost"])
        self.assertEqual(r["state"], "OPEN")

    def test_self_scored_yield_never_settles(self):
        e = [
            {**accepted(), "test_oracle": True},
            event(
                "emit",
                "YIELD_SUBMITTED",
                ["accept"],
                evidence_digest="b" * 64,
                test_oracle=True,
            ),
            event(
                "verify",
                "YIELD_INDEPENDENTLY_VERIFIED",
                ["emit"],
                evidence_digest="b" * 64,
                test_oracle=True,
            ),
        ]
        r = mod.project(e, proof)
        self.assertEqual(
            r["obligations"]["INS-1"]["state"], "AWAITING_INDEPENDENT_YIELD"
        )
        self.assertEqual(r["gaps"][-1]["reason"], "SELF_GRADED_OR_UNLINKED_YIELD")

    def test_separate_verified_oracle_settles_only_matching_yield(self):
        e = [
            {**accepted(), "test_oracle": True},
            event(
                "emit",
                "YIELD_SUBMITTED",
                ["accept"],
                evidence_digest="b" * 64,
                test_oracle=True,
            ),
            event(
                "verify",
                "YIELD_INDEPENDENTLY_VERIFIED",
                ["emit"],
                agent_urn="urn:aid:oracle",
                evidence_digest="b" * 64,
                test_oracle=True,
            ),
        ]
        r = mod.project(e, proof)
        self.assertEqual(r["unresolved"], [])
        self.assertTrue(r["obligations"]["INS-1"]["verified_yield"])

    def test_out_of_order_causality_rejected_not_sorted_by_timestamp(self):
        e = [
            event(
                "cost",
                "COST_OBSERVED",
                ["accept"],
                tokens_in=1,
                tokens_out=1,
                test_oracle=True,
            ),
            {**accepted(), "test_oracle": True},
        ]
        r = mod.project(e, proof)
        self.assertEqual(r["gaps"][0]["reason"], "CAUSAL_PARENT_NOT_YET_OBSERVED")
        self.assertEqual(r["obligations"]["INS-1"]["costs"]["tokens_in"], 0)

    def test_handover_keeps_original_identity_and_correction_debt(self):
        e = [
            {**accepted(), "test_oracle": True},
            event(
                "failure",
                "ANCESTRAL_FAILURE",
                ["accept"],
                ancestor_event_id="external-ancestor",
                failure_class="FALSE_CLAIM",
                test_oracle=True,
            ),
            event(
                "handoff",
                "OWNERSHIP_HANDBACK",
                ["failure"],
                successor_agent_urn="urn:aid:successor",
                test_oracle=True,
            ),
            event(
                "repair",
                "CORRECTION_VERIFIED",
                ["handoff"],
                agent_urn="urn:aid:oracle",
                ancestor_event_id="external-ancestor",
                falsifier_digest="c" * 64,
                test_oracle=True,
            ),
        ]
        r = mod.project(e, proof)
        self.assertEqual(r["obligations"]["INS-1"]["initial_agent"], "urn:aid:original")
        self.assertEqual(
            r["obligations"]["INS-1"]["current_agent"], "urn:aid:successor"
        )
        self.assertEqual(r["outstanding_ancestor_failures"], 0)

    def test_broken_parent_or_duplicate_event_cannot_double_count(self):
        e = [
            {**accepted(), "test_oracle": True},
            event(
                "cost",
                "COST_OBSERVED",
                ["nonexistent"],
                tokens_in=100,
                tokens_out=0,
                test_oracle=True,
            ),
            event(
                "cost",
                "COST_OBSERVED",
                ["accept"],
                tokens_in=100,
                tokens_out=0,
                test_oracle=True,
            ),
        ]
        r = mod.project(e, proof)
        self.assertEqual(r["obligations"]["INS-1"]["costs"]["tokens_in"], 0)
        self.assertEqual(
            [x["reason"] for x in r["gaps"]],
            ["CAUSAL_PARENT_NOT_YET_OBSERVED", "DUPLICATE_EVENT"],
        )

    def test_actor_cannot_withdraw_own_unfulfilled_contract(self):
        e = [
            {**accepted(), "test_oracle": True},
            event(
                "withdraw",
                "OBLIGATION_WITHDRAWN",
                ["accept"],
                reason="done",
                test_oracle=True,
            ),
        ]
        r = mod.project(e, proof)
        self.assertEqual(r["unresolved"], ["INS-1"])
        self.assertEqual(
            r["gaps"][-1]["reason"], "WITHDRAWAL_REQUIRES_SEPARATE_AUTHORITY"
        )

    def test_unverified_ancestor_correction_remains_outstanding(self):
        e = [
            {**accepted(), "test_oracle": True},
            event(
                "failure",
                "ANCESTRAL_FAILURE",
                ["accept"],
                ancestor_event_id="parent-failure",
                failure_class="MISSED_HANDOVER",
                test_oracle=True,
            ),
            event(
                "repair",
                "CORRECTION_VERIFIED",
                ["failure"],
                agent_urn="urn:aid:oracle",
                ancestor_event_id="parent-failure",
                falsifier_digest="x",
            ),
        ]
        r = mod.project(e, proof)
        self.assertEqual(r["outstanding_ancestor_failures"], 1)


if __name__ == "__main__":
    unittest.main()
