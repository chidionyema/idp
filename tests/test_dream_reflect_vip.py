"""The compulsory offline dream gate and the instant Telegram VIP service, proven.

Founder law (2026-11-27) and the DRO order (2026-11-28) are only worth
anything if they FAIL when they should. So every rule below has a test that
shows the refusal: a lane without a dream cannot close, a proposal without a
verified Tier 1/2 receipt is denied, a Tier-3-only claim is denied, an agent
cannot self-apply its own proposal, a below-threshold proposal never pings the
founder, and a burst is coalesced instead of delivered.

The suite is standard library only: `unittest`, no pytest, no third-party
dependency. That is a property of the feature (harness-agnostic, no vendor
SDK), not an accident of the test runner.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from platform.consult_plane.budget_ledger import MicroUsdLedger
from platform.consult_plane.dream_reflect import (
    BenchmarkEvidenceError,
    DreamProposalInput,
    DreamReflectEngine,
    DreamReflectionRequiredError,
    DreamTarget,
    EstateTopologySnapshot,
    SelfMutationForbiddenError,
)
from platform.consult_plane.search_twin import RawSearchHit, TwinSearchMemory
from platform.consult_plane.telegram_vip import (
    TelegramVipConfig,
    TelegramVipService,
    VipDeliveryError,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestDreamReflectVip(unittest.TestCase):
    def setUp(self) -> None:
        self.now = 1_795_852_000
        self.ledger = MicroUsdLedger(db_path=":memory:", monthly_cap_uusd=200_000_000)
        self.search_twin = TwinSearchMemory(
            signing_secret=b"sovereign-vip-test-secret-32byte!",
            db_path=":memory:",
        )
        self.engine = DreamReflectEngine(
            ledger=self.ledger,
            search_twin=self.search_twin,
            db_path=":memory:",
        )
        self.vip_config = TelegramVipConfig(
            bot_token="TEST_TOKEN",
            chat_id="123456789",
            vip_instant_threshold=8.0,
            max_instant_vip_per_hour=2,
        )
        self.vip = TelegramVipService(config=self.vip_config, db_path=":memory:")
        self.topology = EstateTopologySnapshot(
            captured_at_epoch=self.now,
            lane1_edge_status="OK",
            lane2_oci_status="OK",
            lane3_greenlane_status="OK",
            gortex_status="FALLBACK_AST",
            cortex_status="FALLBACK_WAL",
            mac_free_mib=4200,
            mac_load_1m=1.8,
            budget_remaining_uusd=184_200_000,
            budget_cap_uusd=200_000_000,
            tier0_cache_hit_pct=61.0,
            founder_interrupts_24h=0,
            operational_yield_24h=4,
        )
        envs, _ = self.search_twin.search(
            "sleep-time compute offline consolidation",
            lambda q: [
                RawSearchHit(
                    source_url="https://arxiv.org/abs/2611.12068",
                    raw_content="AutoDream offline memory consolidation outside the write path cuts test-time cost 2.5x.",
                )
            ],
            now_epoch=self.now,
        )
        self.valid_benchmark = envs[0]

    def _make_proposal(
        self,
        instruction_id: str = "I-9200",
        title: str = "Pre-warm Tier-0 prefix cache during offline dream window",
        touched_paths: tuple[str, ...] = ("platform/consult_plane/budget_ledger.py",),
        yield_impact: float = 9.5,
        cost_latency_gain: float = 9.5,
        founder_friction_saved: float = 9.0,
        elite_alignment: float = 9.0,
        blast_radius: str = "LOW",
        benchmarks: tuple | None = None,
    ) -> DreamProposalInput:
        return DreamProposalInput(
            agent_id="coder-lane-2",
            session_id="sess_dream_1",
            instruction_id=instruction_id,
            target=DreamTarget.WORKFLOW,
            title=title,
            executive_pitch="Pre-warm Tier-0 prefix cache offline to cut frontier input spend 82%.",
            current_bottleneck="Cold prefix misses force full prompt billing on first consult.",
            proposed_change="Run 1 cheap Tier-1 sleep-time digest pass after lane close.",
            expected_metric_delta="-82% Tier-2 spend | -410ms latency | 0 Mac RAM",
            touched_paths=touched_paths,
            benchmark_envelopes=(self.valid_benchmark,) if benchmarks is None else benchmarks,
            yield_impact=yield_impact,
            cost_latency_gain=cost_latency_gain,
            founder_friction_saved=founder_friction_saved,
            elite_alignment=elite_alignment,
            blast_radius=blast_radius,
            rollback_plan="Flip DREAM_PREWARM=0 on Lane 1 Worker (<10ms rollback).",
        )

    def test_01_compulsory_dream_blocks_lane_close_until_completed(self) -> None:
        with self.assertRaises(DreamReflectionRequiredError):
            self.engine.assert_dream_completed_before_lane_close("I-9201")

        scored = self.engine.submit_offline_dream(
            self._make_proposal(instruction_id="I-9201"),
            self.topology,
            actual_dream_cost_uusd=2_500,
            now_epoch=self.now,
        )
        pid = self.engine.assert_dream_completed_before_lane_close("I-9201")
        self.assertEqual(pid, scored.proposal_id)

    def test_02_dream_budget_metering_preserves_200_dollar_conservation(self) -> None:
        scored = self.engine.submit_offline_dream(
            self._make_proposal(instruction_id="I-9202"),
            self.topology,
            actual_dream_cost_uusd=4_000,
            now_epoch=self.now,
        )
        self.assertEqual(scored.dream_cost_uusd, 4_000)
        snap = self.ledger.assert_conservation()
        self.assertEqual(snap.settled_uusd, 4_000)
        self.assertEqual(snap.total_uusd, 200_000_000)

    def test_03_unverified_or_tier3_only_benchmark_fails_closed(self) -> None:
        # Missing benchmark receipts -> DENY
        with self.assertRaises(BenchmarkEvidenceError):
            self.engine.submit_offline_dream(
                self._make_proposal(instruction_id="I-9203", benchmarks=()),
                self.topology,
                now_epoch=self.now,
            )

        # Tier-3 forum-only benchmark -> DENY
        t3_envs, _ = self.search_twin.search(
            "random hype blog",
            lambda q: [RawSearchHit("https://random-blog.example/ai", "100x agents easily")],
            now_epoch=self.now,
        )
        with self.assertRaises(BenchmarkEvidenceError):
            self.engine.submit_offline_dream(
                self._make_proposal(instruction_id="I-9204", benchmarks=(t3_envs[0],)),
                self.topology,
                now_epoch=self.now,
            )

    def test_04_guarded_path_flags_founder_seal_and_blocks_self_mutation(self) -> None:
        scored = self.engine.submit_offline_dream(
            self._make_proposal(
                instruction_id="I-9205",
                touched_paths=(".githooks/pre-push",),
            ),
            self.topology,
            now_epoch=self.now,
        )
        self.assertTrue(scored.requires_founder_seal)
        self.assertEqual(scored.operational_yield, 0)
        with self.assertRaises(SelfMutationForbiddenError):
            self.engine.apply_self_mutation_attempt(scored.proposal_id, actor_role="agent_self")

    def test_05_deterministic_scoring_assigns_platinum_gold_silver_tiers(self) -> None:
        p_plat = self.engine.submit_offline_dream(
            self._make_proposal(
                instruction_id="I-9206",
                yield_impact=9.5,
                cost_latency_gain=9.5,
                founder_friction_saved=9.0,
                elite_alignment=9.0,
            ),
            self.topology,
            now_epoch=self.now,
        )
        p_gold = self.engine.submit_offline_dream(
            self._make_proposal(
                instruction_id="I-9207",
                yield_impact=8.5,
                cost_latency_gain=8.0,
                founder_friction_saved=8.5,
                elite_alignment=8.0,
            ),
            self.topology,
            now_epoch=self.now + 1,
        )
        p_silver = self.engine.submit_offline_dream(
            self._make_proposal(
                instruction_id="I-9208",
                yield_impact=6.5,
                cost_latency_gain=6.0,
                founder_friction_saved=6.5,
                elite_alignment=7.0,
                blast_radius="MEDIUM",
            ),
            self.topology,
            now_epoch=self.now + 2,
        )
        self.assertEqual(p_plat.vip_tier, "PLATINUM")
        self.assertEqual(p_gold.vip_tier, "GOLD")
        self.assertEqual(p_silver.vip_tier, "SILVER")

    def test_06_instant_telegram_vip_renders_html_expandable_and_inline_buttons(self) -> None:
        sent_calls: list[tuple[str, dict]] = []

        def fake_telegram(method: str, body: dict) -> dict:
            sent_calls.append((method, body))
            return {"ok": True, "result": {"message_id": 9901}}

        scored = self.engine.submit_offline_dream(
            self._make_proposal(instruction_id="I-9209", title="Optimize <script> & cache"),
            self.topology,
            now_epoch=self.now,
        )
        res = self.vip.dispatch(scored, self.topology, transport_fn=fake_telegram, now_epoch=self.now)
        self.assertEqual(res.delivery_mode, "INSTANT_VIP_SENT")
        self.assertEqual(res.telegram_message_id, 9901)
        self.assertEqual(len(sent_calls), 1)
        method, payload = sent_calls[0]
        self.assertEqual(method, "sendMessage")
        self.assertEqual(payload["parse_mode"], "HTML")
        self.assertIn("<blockquote expandable>", payload["text"])
        self.assertIn("&lt;script&gt;", payload["text"])  # HTML-escaped safely
        self.assertEqual(payload["message_effect_id"], self.vip_config.platinum_effect_id)
        buttons = payload["reply_markup"]["inline_keyboard"]
        self.assertEqual(len(buttons), 2)
        self.assertEqual(buttons[0][0]["callback_data"], f"vip:{scored.proposal_id}:approve")

    def test_07_silver_proposal_routes_to_silent_digest_without_pinging_founder(self) -> None:
        called = {"count": 0}
        scored = self.engine.submit_offline_dream(
            self._make_proposal(
                instruction_id="I-9210",
                yield_impact=6.0,
                cost_latency_gain=6.0,
                founder_friction_saved=6.0,
                elite_alignment=6.0,
            ),
            self.topology,
            now_epoch=self.now,
        )
        res = self.vip.dispatch(
            scored,
            self.topology,
            transport_fn=lambda m, b: called.__setitem__("count", called["count"] + 1) or {},
            now_epoch=self.now,
        )
        self.assertEqual(res.delivery_mode, "QUEUED_SILENT_DIGEST")
        self.assertEqual(called["count"], 0)
        self.assertEqual(len(self.vip.pending_silent_digest()), 1)

    def test_08_hourly_vip_anti_spam_cap_coalesces_burst_proposals(self) -> None:
        sent_ids: list[int] = []

        def fake_tg(method: str, body: dict) -> dict:
            mid = 1000 + len(sent_ids)
            sent_ids.append(mid)
            return {"ok": True, "result": {"message_id": mid}}

        # max_instant_vip_per_hour = 2 -> first 2 send instantly, 3rd coalesces silently
        results = []
        for idx in range(3):
            p = self.engine.submit_offline_dream(
                self._make_proposal(instruction_id=f"I-922{idx}", title=f"Elite opt {idx}"),
                self.topology,
                now_epoch=self.now + idx * 10,
            )
            results.append(
                self.vip.dispatch(p, self.topology, transport_fn=fake_tg, now_epoch=self.now + idx * 10)
            )

        self.assertEqual(
            [r.delivery_mode for r in results],
            [
                "INSTANT_VIP_SENT",
                "INSTANT_VIP_SENT",
                "QUEUED_SILENT_DIGEST",
            ],
        )
        self.assertEqual(len(sent_ids), 2)

    def test_09_one_tap_founder_decision_callback_updates_state_and_edits_card_in_place(self) -> None:
        scored = self.engine.submit_offline_dream(
            self._make_proposal(instruction_id="I-9230"),
            self.topology,
            now_epoch=self.now,
        )
        cb = self.vip.handle_callback(
            callback_query_id="cbq_1",
            callback_data=f"vip:{scored.proposal_id}:approve",
            message_id=9901,
            dream_engine=self.engine,
            topology=self.topology,
        )
        self.assertEqual(cb["updated_proposal"].state, "APPROVED_FOR_LANE")
        self.assertIn("APPROVED_FOR_LANE", cb["editMessageText"]["text"])
        self.assertEqual(cb["editMessageText"]["message_id"], 9901)
        self.assertEqual(cb["answerCallbackQuery"]["callback_query_id"], "cbq_1")

    def test_10_one_tap_founder_rating_and_review_aggregates_agent_reputation(self) -> None:
        p1 = self.engine.submit_offline_dream(
            self._make_proposal(instruction_id="I-9240", title="Opt 1"),
            self.topology,
            now_epoch=self.now,
        )
        p2 = self.engine.submit_offline_dream(
            self._make_proposal(instruction_id="I-9241", title="Opt 2"),
            self.topology,
            now_epoch=self.now + 5,
        )
        self.vip.handle_callback(
            "cbq_r1", f"vip:{p1.proposal_id}:rate:5", 9902, self.engine, self.topology,
            review_note="Ship immediately",
        )
        self.vip.handle_callback(
            "cbq_r2", f"vip:{p2.proposal_id}:rate:3", 9903, self.engine, self.topology,
            review_note="Good, keep in shadow",
        )
        self.vip.handle_callback(
            "cbq_a1", f"vip:{p1.proposal_id}:approve", 9902, self.engine, self.topology
        )

        rep = self.engine.agent_reputation_summary("coder-lane-2")
        self.assertEqual(rep["total_proposals"], 2)
        self.assertEqual(rep["avg_founder_rating"], 4.0)
        self.assertEqual(rep["approved_count"], 1)


class TestDreamReflectVipEdges(unittest.TestCase):
    """The refusals and the seams the founder's order names, each with a falsifier."""

    def setUp(self) -> None:
        self.now = 1_795_852_000
        self.ledger = MicroUsdLedger(db_path=":memory:", monthly_cap_uusd=200_000_000)
        self.search_twin = TwinSearchMemory(
            signing_secret=b"sovereign-vip-test-secret-32byte!",
            db_path=":memory:",
        )
        self.engine = DreamReflectEngine(
            ledger=self.ledger, search_twin=self.search_twin, db_path=":memory:"
        )
        self.vip_config = TelegramVipConfig(bot_token="TEST_TOKEN", chat_id="123456789")
        self.vip = TelegramVipService(config=self.vip_config, db_path=":memory:")
        self.topology = EstateTopologySnapshot(
            captured_at_epoch=self.now,
            lane1_edge_status="OK",
            lane2_oci_status="OK",
            lane3_greenlane_status="OK",
            gortex_status="FALLBACK_AST",
            cortex_status="FALLBACK_WAL",
            mac_free_mib=4200,
            mac_load_1m=1.8,
            budget_remaining_uusd=184_200_000,
            budget_cap_uusd=200_000_000,
            tier0_cache_hit_pct=61.0,
            founder_interrupts_24h=0,
            operational_yield_24h=4,
        )
        envs, _ = self.search_twin.search(
            "sleep-time compute offline consolidation",
            lambda q: [
                RawSearchHit(
                    source_url="https://arxiv.org/abs/2611.12068",
                    raw_content="AutoDream offline consolidation outside the write path cuts cost 2.5x.",
                )
            ],
            now_epoch=self.now,
        )
        self.benchmark = envs[0]

    def _proposal(self, **kw) -> DreamProposalInput:
        base = dict(
            agent_id="coder-lane-2",
            session_id="s",
            instruction_id="I-9300",
            target=DreamTarget.WORKFLOW,
            title="T",
            executive_pitch="p",
            current_bottleneck="b",
            proposed_change="c",
            expected_metric_delta="d",
            touched_paths=("platform/consult_plane/dream_reflect.py",),
            benchmark_envelopes=(self.benchmark,),
            yield_impact=9.0,
            cost_latency_gain=9.0,
            founder_friction_saved=9.0,
            elite_alignment=9.0,
            blast_radius="LOW",
            rollback_plan="flip the flag",
        )
        base.update(kw)
        return DreamProposalInput(**base)

    def test_11_a_proposal_without_a_rollback_plan_is_refused(self) -> None:
        with self.assertRaises(Exception):
            self.engine.submit_offline_dream(
                self._proposal(instruction_id="I-9301", rollback_plan="  "),
                self.topology,
                now_epoch=self.now,
            )

    def test_12_a_proposal_over_the_dream_cost_cap_is_refused_and_metered_nothing(self) -> None:
        before = self.ledger.assert_conservation().settled_uusd
        with self.assertRaises(Exception):
            self.engine.submit_offline_dream(
                self._proposal(instruction_id="I-9302"),
                self.topology,
                actual_dream_cost_uusd=999_999,
                now_epoch=self.now,
            )
        self.assertEqual(self.ledger.assert_conservation().settled_uusd, before)

    def test_13_a_delivery_failure_is_raised_and_never_logged_as_sent(self) -> None:
        scored = self.engine.submit_offline_dream(
            self._proposal(instruction_id="I-9303"), self.topology, now_epoch=self.now
        )

        def broken_transport(method: str, body: dict) -> dict:
            raise VipDeliveryError("Telegram sendMessage answered HTTP 400: Bad Request")

        with self.assertRaises(VipDeliveryError):
            self.vip.dispatch(scored, self.topology, transport_fn=broken_transport, now_epoch=self.now)

        # Not logged as sent, and not in the digest either: a card that failed to
        # deliver must not masquerade as one that was seen.
        self.assertEqual(self.vip.pending_silent_digest(), [])

    def test_14_an_unknown_callback_action_is_refused(self) -> None:
        scored = self.engine.submit_offline_dream(
            self._proposal(instruction_id="I-9304"), self.topology, now_epoch=self.now
        )
        with self.assertRaises(ValueError):
            self.vip.handle_callback(
                "cbq_x",
                f"vip:{scored.proposal_id}:self-approve",
                9901,
                self.engine,
                self.topology,
            )

    def test_15_the_gate_is_an_exit_code_any_harness_can_enforce(self) -> None:
        """The same compulsory gate, as a process exit code a hook or CI step can branch on."""
        module = "platform.consult_plane.dream_reflect"
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                module,
                "check-lane-close",
                "--instruction-id",
                "I-9305",
                "--db",
                ":memory:",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("DRO_REQUIRED_BEFORE_LEASE_CLOSE", proc.stdout + proc.stderr)

    def test_16_the_score_is_deterministic_and_reproducible(self) -> None:
        from platform.consult_plane.dream_reflect import compute_elite_score

        p = self._proposal()
        first = compute_elite_score(p)
        second = compute_elite_score(p)
        self.assertEqual(first, second)
        self.assertEqual(first[0], 9.0)
        self.assertEqual(first[1], "PLATINUM")

    def test_17_the_card_carries_no_third_party_dependency_and_is_json_serialisable(self) -> None:
        from platform.consult_plane.telegram_vip import render_vip_telegram_payload

        scored = self.engine.submit_offline_dream(
            self._proposal(instruction_id="I-9306"), self.topology, now_epoch=self.now
        )
        payload = render_vip_telegram_payload(scored, self.topology, self.vip_config)
        json.dumps(payload)  # must not raise
        self.assertIn("reply_parameters", payload)
        self.assertEqual(payload["reply_parameters"]["message_id"], self.vip_config.pinned_control_msg_id)


if __name__ == "__main__":
    unittest.main()
