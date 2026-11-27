"""20-case adversarial test suite covering all 10 edge cases, fleet compilation, and CI exit 43."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python"))

from context_governor import (
    ContextGovernor,
    ContextPolicy,
    MissionBudgetLedger,
    externalize_and_compact_history,
    filter_authoritative_memories,
    validate_handoff_packet,
)

POLICY_PATH = ROOT / "governance" / "context-policy.v1.json"


def make_policy(phase: str = "ENFORCE") -> ContextPolicy:
    raw = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    raw["rollout_phase"] = phase
    return ContextPolicy(raw)


class TestEstateContextGovernance(unittest.TestCase):
    # 1. Shadow mode never blocks even over hard cap
    def test_01_shadow_mode_never_interrupts_operations(self):
        gov = ContextGovernor(make_policy("SHADOW"), MissionBudgetLedger())
        huge = "x" * 120000
        d = gov.evaluate_ingress(
            {
                "model": "deepseek-flash",
                "reasoning_effort": "high",
                "messages": [{"role": "user", "content": huge}],
            },
            session_id="s1",
            mission_id="m1",
            role="role:ops-dispatch",
        )
        self.assertTrue(d.allowed)
        self.assertEqual(d.http_status, 200)
        self.assertEqual(d.directive, "ALLOW")
        self.assertEqual(d.telemetry["shadow_would_directive"], "CHECKPOINT_AND_ROTATE")

    # 2. Soft-rotate clamps reasoning_effort=high -> low on ops-dispatch without blocking
    def test_02_role_clamps_high_reasoning_on_ops_dispatch(self):
        gov = ContextGovernor(make_policy("SOFT_ROTATE"), MissionBudgetLedger())
        d = gov.evaluate_ingress(
            {
                "model": "nemotron-3.5-super-vl",
                "reasoning_effort": "high",
                "max_tokens": 16000,
                "messages": [{"role": "user", "content": "gh run view 45248612714"}],
            },
            session_id="s2",
            mission_id="m8416",
            role="role:ops-dispatch",
        )
        self.assertTrue(d.allowed)
        self.assertEqual(d.clamped_request["reasoning_effort"], "low")
        self.assertEqual(d.clamped_request["max_tokens"], 2048)

    # 3. Soft threshold issues CHECKPOINT_AND_ROTATE header while allowing atomic turn completion
    def test_03_soft_cap_emits_rotate_directive_before_hard_block(self):
        gov = ContextGovernor(make_policy("ENFORCE"), MissionBudgetLedger())
        body_18k = "a " * 25000  # ~18k tokens (between 16k soft and 24k hard)
        d = gov.evaluate_ingress(
            {"model": "nemotron", "messages": [{"role": "user", "content": body_18k}]},
            session_id="s3",
            mission_id="m3",
            role="role:ops-dispatch",
        )
        self.assertTrue(d.allowed)
        self.assertEqual(
            d.headers["X-Meridian-Context-Directive"], "CHECKPOINT_AND_ROTATE"
        )

    # 4. Hard cap blocks only after exceeding hard cap when no critical-section lease
    def test_04_hard_cap_blocks_in_enforce_mode(self):
        gov = ContextGovernor(make_policy("ENFORCE"), MissionBudgetLedger())
        body_26k = "a " * 40000
        d = gov.evaluate_ingress(
            {"model": "nemotron", "messages": [{"role": "user", "content": body_26k}]},
            session_id="s4",
            mission_id="m4",
            role="role:ops-dispatch",
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.http_status, 429)
        self.assertEqual(d.directive, "HARD_STOP_CONTEXT_CAP_EXCEEDED")

    # 5. Edge Case 2: Critical-Section Lease allows +15% headroom for up to 2 turns
    def test_05_critical_section_lease_protects_atomic_commit_push(self):
        gov = ContextGovernor(make_policy("ENFORCE"), MissionBudgetLedger())
        # ~25.5k tokens: above 24k hard cap, below 27.6k (+15%) critical-section cap
        body_25k = "word " * 13500
        d1 = gov.evaluate_ingress(
            {"model": "nemotron", "messages": [{"role": "user", "content": body_25k}]},
            session_id="s5",
            mission_id="m5",
            role="role:ops-dispatch",
            critical_section_nonce="commit-push-1",
        )
        self.assertTrue(d1.allowed, d1.to_dict())
        self.assertEqual(d1.headers["X-Meridian-Critical-Section-Lease"], "ACTIVE")

    # 6. Edge Case 2b: Critical-Section Lease is strictly non-renewable after 2 turns even with new nonce
    def test_06_critical_section_lease_non_renewable_after_2_turns(self):
        gov = ContextGovernor(make_policy("ENFORCE"), MissionBudgetLedger())
        body_25k = "word " * 13500
        for i in range(2):
            d = gov.evaluate_ingress(
                {
                    "model": "nemotron",
                    "messages": [{"role": "user", "content": body_25k}],
                },
                session_id="s6",
                mission_id="m6",
                role="role:ops-dispatch",
                critical_section_nonce=f"nonce-{i}",
            )
            self.assertTrue(d.allowed)
        # Turn 3 with fresh nonce MUST fail
        d3 = gov.evaluate_ingress(
            {"model": "nemotron", "messages": [{"role": "user", "content": body_25k}]},
            session_id="s6",
            mission_id="m6",
            role="role:ops-dispatch",
            critical_section_nonce="nonce-renew-attempt",
        )
        self.assertFalse(d3.allowed)
        self.assertIn("ERR_CRITICAL_SECTION_LEASE_EXHAUSTED", d3.violations)

    # 7. Edge Case 4: Stable prefix preserves KV-cache; mutating system prompt flags thrash
    def test_07_kv_cache_prefix_immutability_and_thrash_detection(self):
        gov = ContextGovernor(make_policy("SOFT_ROTATE"), MissionBudgetLedger())
        r1 = gov.evaluate_ingress(
            {
                "model": "deepseek",
                "messages": [
                    {"role": "system", "content": "STATIC_CORE"},
                    {"role": "user", "content": "hi"},
                ],
            },
            session_id="s7",
            mission_id="m7",
            role="role:surgical-patch",
        )
        r2 = gov.evaluate_ingress(
            {
                "model": "deepseek",
                "messages": [
                    {"role": "system", "content": "STATIC_CORE"},
                    {"role": "user", "content": "hi"},
                    {"role": "user", "content": "step 2"},
                ],
            },
            session_id="s7",
            mission_id="m7",
            role="role:surgical-patch",
        )
        self.assertEqual(r2.headers["X-Meridian-Prefix-Cache-State"], "PREFIX_STABLE")
        r3 = gov.evaluate_ingress(
            {
                "model": "deepseek",
                "messages": [
                    {"role": "system", "content": "STATIC_CORE ts=19:33:01Z"},
                    {"role": "user", "content": "step 3"},
                ],
            },
            session_id="s7",
            mission_id="m7",
            role="role:surgical-patch",
        )
        self.assertEqual(
            r3.headers["X-Meridian-Prefix-Cache-State"], "PREFIX_MUTATED_THRASH"
        )
        self.assertIn("ERR_KV_PREFIX_THRASH", r3.violations)

    # 8. Edge Case 3: Provider usage calibration adjusts estimator upward on dense tokenizers
    def test_08_tokenizer_calibration_feedback_loop(self):
        ledger = MissionBudgetLedger()
        gov = ContextGovernor(make_policy("SOFT_ROTATE"), ledger)
        d1 = gov.evaluate_ingress(
            {
                "model": "deepseek-v4",
                "messages": [{"role": "user", "content": "abc" * 500}],
            },
            session_id="s8",
            mission_id="m8",
            role="role:surgical-patch",
        )
        est1 = d1.telemetry["used_tokens"]
        ledger.record_provider_usage(
            "s8", estimated_tokens=est1, actual_prompt_tokens=int(est1 * 1.5)
        )
        d2 = gov.evaluate_ingress(
            {
                "model": "deepseek-v4",
                "messages": [{"role": "user", "content": "abc" * 500}],
            },
            session_id="s8",
            mission_id="m8",
            role="role:surgical-patch",
        )
        self.assertGreater(d2.telemetry["used_tokens"], est1)
        self.assertEqual(
            d2.telemetry["token_measurement_method"], "provider_usage_calibrated"
        )

    # 9. Edge Case 5: Multimodal base64 screenshot accounting + historical image stripping
    def test_09_multimodal_base64_accounting_and_externalization(self):
        fake_b64 = "data:image/png;base64," + ("A" * 400000)
        msgs = [
            {"role": "system", "content": "STATIC"},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "old shot"},
                    {"type": "image_url", "image_url": {"url": fake_b64}},
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "new shot"},
                    {"type": "image_url", "image_url": {"url": fake_b64}},
                ],
            },
        ]
        gov = ContextGovernor(make_policy("SOFT_ROTATE"), MissionBudgetLedger())
        d = gov.evaluate_ingress(
            {"model": "nemotron-vl", "messages": msgs},
            session_id="s9",
            mission_id="m9",
            role="role:ops-dispatch",
        )
        self.assertEqual(d.telemetry["image_count"], 2)
        self.assertGreaterEqual(d.telemetry["image_tokens"], 4000)

        with tempfile.TemporaryDirectory() as td:
            compacted, omissions = externalize_and_compact_history(
                msgs, artifact_dir=Path(td), keep_recent_images=1
            )
            self.assertEqual(len(omissions), 1)
            self.assertIn("EXTERNALIZED_IMAGE", compacted[1]["content"][1]["text"])
            self.assertEqual(compacted[2]["content"][1]["type"], "image_url")

    # 10. Edge Case 6: Sub-agent brief cap + hierarchical mission aggregate budget
    def test_10_subagent_brief_and_mission_aggregate_budget(self):
        ledger = MissionBudgetLedger()
        gov = ContextGovernor(make_policy("ENFORCE"), ledger)
        # Child 1 inherits bloated 6k brief -> flagged
        d_child1 = gov.evaluate_ingress(
            {
                "model": "deepseek",
                "messages": [{"role": "user", "content": "data " * 4000}],
            },
            session_id="child-1",
            mission_id="m-swarm",
            role="role:ops-dispatch",
            is_subagent=True,
        )
        self.assertIn("ERR_SUBAGENT_BRIEF_CAP_EXCEEDED", d_child1.violations)

        # Simulate prior sub-agents burning 47,500 of 48,000 mission cap
        ledger.mission_tokens["m-swarm"] = 47500
        d_child2 = gov.evaluate_ingress(
            {
                "model": "deepseek",
                "messages": [{"role": "user", "content": "small task " * 400}],
            },
            session_id="child-2",
            mission_id="m-swarm",
            role="role:ops-dispatch",
            is_subagent=True,
        )
        self.assertFalse(d_child2.allowed)
        self.assertEqual(d_child2.directive, "HARD_STOP_MISSION_BUDGET_EXHAUSTED")

    # 11. Edge Case 8: BudgetLedgerDO storage outage degrades fail-open safely
    def test_11_storage_outage_degrades_fail_open(self):
        gov = ContextGovernor(
            make_policy("ENFORCE"), MissionBudgetLedger(simulate_storage_outage=True)
        )
        d = gov.evaluate_ingress(
            {
                "model": "deepseek",
                "messages": [{"role": "user", "content": "check health"}],
            },
            session_id="s11",
            mission_id="m11",
            role="role:ops-dispatch",
        )
        self.assertTrue(d.allowed)
        self.assertIn("budget_ledger_unavailable_fail_open", d.degradations)
        self.assertFalse(d.telemetry["complete"])

    # 12. Edge Case 9: >4KB tool output externalization preserves failure traces verbatim
    def test_12_externalize_tool_output_pins_failure_trace(self):
        huge_ok = "INFO ok line\n" * 500
        huge_fail = (
            "INFO step\n" * 500
        ) + "ERROR: HTTP 525 SSL handshake failed on llm.meridianlabs.cloud\n"
        msgs = [
            {"role": "system", "content": "STATIC"},
            {"role": "tool", "content": huge_ok},
            {"role": "tool", "content": huge_fail},
            {"role": "user", "content": "t1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "t2"},
            {"role": "assistant", "content": "a2"},
        ]
        with tempfile.TemporaryDirectory() as td:
            compacted, omissions = externalize_and_compact_history(
                msgs, artifact_dir=Path(td), keep_recent_verbatim_turns=4
            )
            self.assertIn("EXTERNALIZED_TOOL_RESULT", compacted[1]["content"])
            self.assertIn("EXTERNALIZED_FAILURE_TRACE", compacted[2]["content"])
            self.assertIn("HTTP 525", compacted[2]["content"])
            self.assertEqual(len(omissions), 2)

    # 13. Edge Case 9b: Handoff validator blocks missing invariants, Zone A, and TIER_2 laundering
    def test_13_handoff_validator_rejects_amnesia_and_zone_a(self):
        bad_ok, bad_errs = validate_handoff_packet(
            {
                "mission_id": "idp#8416",
                "target_repo": "chidionyema/idp",
                "target_sha": "",
                "acceptance_receipt_contract": "GET /health -> 200",
                "next_discriminating_step": "edit ~/.estate/daemon.plist",
                "pinned_failure_receipts": [
                    {"tier": "TIER_2_AGENT_INFERENCE", "used_as_primary_fact": True}
                ],
            }
        )
        self.assertFalse(bad_ok)
        self.assertIn("ERR_HANDOFF_MISSING_TARGET_SHA", bad_errs)
        self.assertIn("ERR_HANDOFF_ZONE_A_REGRESSION:~/.estate", bad_errs)
        self.assertIn("ERR_HANDOFF_EPISTEMIC_LAUNDERING", bad_errs)

        good_ok, good_errs = validate_handoff_packet(
            {
                "mission_id": "idp#8416",
                "target_repo": "chidionyema/idp",
                "target_sha": "4e88bf0",
                "acceptance_receipt_contract": "GET https://llm.meridianlabs.cloud/health -> 200 zone-b-cloudflare-edge",
                "next_discriminating_step": "dispatch bootstrap mode=live once",
                "pinned_failure_receipts": [
                    {"tier": "TIER_0_RAW_MACHINE_RECEIPT", "run_id": "45248612714"}
                ],
            }
        )
        self.assertTrue(good_ok, good_errs)

    # 14. Edge Case 10: Pre-slice memory filter quarantines self-test probes & SUPERSEDED records
    def test_14_memory_filter_quarantines_probes_before_slicing(self):
        policy = make_policy("ENFORCE")
        records = [
            {"id": "p1", "namespace": "self-test-probe", "authority_status": "CURRENT"},
            {"id": "p2", "namespace": "healthcheck", "authority_status": "CURRENT"},
            {"id": "old", "namespace": "estate", "authority_status": "SUPERSEDED"},
            {"id": "real", "namespace": "estate", "authority_status": "CURRENT"},
        ]
        kept, dropped = filter_authoritative_memories(records, policy=policy, limit=1)
        self.assertEqual([r["id"] for r in kept], ["real"])
        self.assertEqual(len(dropped), 3)

    # 15. Always-on MCP tool ceiling >10 flagged
    def test_15_mcp_tool_ceiling_flagged(self):
        gov = ContextGovernor(make_policy("SOFT_ROTATE"), MissionBudgetLedger())
        tools = [
            {"type": "function", "function": {"name": f"t_{i}"}} for i in range(12)
        ]
        d = gov.evaluate_ingress(
            {
                "model": "deepseek",
                "messages": [{"role": "user", "content": "hi"}],
                "tools": tools,
            },
            session_id="s15",
            mission_id="m15",
            role="role:surgical-patch",
        )
        self.assertIn("ERR_MCP_TOOL_CEILING_EXCEEDED", d.violations)

    # 16. Unknown role fails safely to strictest ops-dispatch cap
    def test_16_unknown_role_defaults_to_strictest_ops_cap(self):
        gov = ContextGovernor(make_policy("SOFT_ROTATE"), MissionBudgetLedger())
        d = gov.evaluate_ingress(
            {
                "model": "deepseek",
                "reasoning_effort": "high",
                "messages": [{"role": "user", "content": "hi"}],
            },
            session_id="s16",
            mission_id="m16",
            role="role:unregistered-rogue",
        )
        self.assertEqual(d.clamped_request["reasoning_effort"], "low")
        self.assertEqual(d.telemetry["budget_tokens"], 24000)

    # 17. Fleet compiler emits lean configs passing audit with exit 0
    def test_17_fleet_compiler_passes_audit_exit_0(self):
        cli = ROOT / "bin" / "estate_context_fleet_sync.py"
        with tempfile.TemporaryDirectory() as td:
            p = subprocess.run(
                [
                    sys.executable,
                    str(cli),
                    "--policy",
                    str(POLICY_PATH),
                    "--repo-root",
                    td,
                    "--compile",
                    "--audit",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertTrue(
                (Path(td) / ".clinerules" / "00-meridian-context-core.md").is_file()
            )
            self.assertTrue((Path(td) / "AGENTS.md").is_file())
            self.assertTrue(
                (Path(td) / ".meridian" / "fleet-gateway-profile.json").is_file()
            )

    # 18. Fleet audit fails closed (exit 43) on Turn-1 rule bloat > 1,500 tokens
    def test_18_fleet_audit_blocks_bloated_rules_exit_43(self):
        cli = ROOT / "bin" / "estate_context_fleet_sync.py"
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "AGENTS.md").write_text(
                "verbose rule line " * 1000, encoding="utf-8"
            )
            p = subprocess.run(
                [
                    sys.executable,
                    str(cli),
                    "--policy",
                    str(POLICY_PATH),
                    "--repo-root",
                    td,
                    "--audit",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(p.returncode, 43)
            self.assertIn("FC_TURN1_BLOATED_RULES", p.stdout)

    # 19. Fleet audit fails closed (exit 43) on direct raw upstream provider bypass
    def test_19_fleet_audit_blocks_raw_provider_bypass_exit_43(self):
        cli = ROOT / "bin" / "estate_context_fleet_sync.py"
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / ".mcp.json").write_text(
                json.dumps({"endpoint": "https://api.deepseek.com/v1"}),
                encoding="utf-8",
            )
            p = subprocess.run(
                [
                    sys.executable,
                    str(cli),
                    "--policy",
                    str(POLICY_PATH),
                    "--repo-root",
                    td,
                    "--audit",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(p.returncode, 43)
            self.assertIn("FC_GATEWAY_BYPASS_RAW_PROVIDER", p.stdout)

    # 20. Fleet audit fails closed (exit 43) on >10 always-on MCP tools
    def test_20_fleet_audit_blocks_excessive_mcp_tools_exit_43(self):
        cli = ROOT / "bin" / "estate_context_fleet_sync.py"
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / ".mcp.json").write_text(
                json.dumps({"always_on_tools": [f"tool_{i}" for i in range(15)]}),
                encoding="utf-8",
            )
            p = subprocess.run(
                [
                    sys.executable,
                    str(cli),
                    "--policy",
                    str(POLICY_PATH),
                    "--repo-root",
                    td,
                    "--audit",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(p.returncode, 43)
            self.assertIn("FC_MCP_TOOL_CEILING_EXCEEDED", p.stdout)

    def test_compile_preserves_existing_estate_authority(self):
        cli = ROOT / "bin" / "estate_context_fleet_sync.py"
        with tempfile.TemporaryDirectory() as td:
            authority = Path(td) / "AGENTS.md"
            original = "# Existing authority\nCurrent signed instructions stay authoritative.\n"
            authority.write_text(original, encoding="utf-8")
            p = subprocess.run(
                [
                    sys.executable,
                    str(cli),
                    "--policy",
                    str(POLICY_PATH),
                    "--repo-root",
                    td,
                    "--compile",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(authority.read_text(), original)
            self.assertTrue((Path(td) / ".meridian" / "context-core.md").is_file())


if __name__ == "__main__":
    unittest.main()
