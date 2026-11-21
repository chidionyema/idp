import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))
import zero_repeat_gate as gate


class TestZeroRepeatHeadlessControl(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "zero_repeat.db"
        self.conn = gate.init_db(self.db_path)

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def test_01_strike_one_blocks_retry_and_strike_two_quarantines(self):
        s1 = gate.record_failure(
            self.conn, "bdd-suites", "acceptance-render", "platform/llm", "e4ce3c3"
        )
        self.assertEqual(s1["status"], "IMMUNIZATION_REQUIRED")
        with self.assertRaises(gate.GuardViolation) as ctx1:
            gate.allow_dispatch(
                self.conn, "bdd-suites", "acceptance-render", "platform/llm"
            )
        self.assertEqual(ctx1.exception.code, "ERR_UNIMMUNIZED_RETRY")

        s2 = gate.record_failure(
            self.conn, "bdd-suites", "acceptance-render", "platform/llm", "708fa0a"
        )
        self.assertEqual(s2["status"], "CLASS_QUARANTINE")
        with self.assertRaises(gate.GuardViolation) as ctx2:
            gate.allow_dispatch(
                self.conn, "bdd-suites", "acceptance-render", "platform/llm"
            )
        self.assertEqual(ctx2.exception.code, "ERR_CLASS_QUARANTINE")

        # Reject immunization without failing-before-fix proof
        with self.assertRaises(gate.GuardViolation) as bad_imm:
            gate.record_immunization(
                self.conn,
                "bdd-suites",
                "acceptance-render",
                "platform/llm",
                "cb274aa87aca6c2982b60c400463ff35974fc864",
                "bin/pre-push-wall.py",
                "tests/test_zero_repeat_headless_control.py",
                False,
                True,
            )
        self.assertEqual(bad_imm.exception.code, "ERR_INVALID_IMMUNIZATION_PROOF")

        # Valid immunization clears dispatch
        gate.record_immunization(
            self.conn,
            "bdd-suites",
            "acceptance-render",
            "platform/llm",
            "cb274aa87aca6c2982b60c400463ff35974fc864",
            "bin/pre-push-wall.py",
            "tests/test_zero_repeat_headless_control.py",
            True,
            True,
        )
        gate.allow_dispatch(
            self.conn, "bdd-suites", "acceptance-render", "platform/llm"
        )

    def test_02_bot_auto_merge_loop_quarantines_at_second_red_sync(self):
        self.assertEqual(gate.record_bot_sync(self.conn, "idp#8207", False, False), 1)
        with self.assertRaises(gate.GuardViolation) as ctx:
            gate.record_bot_sync(self.conn, "idp#8207", False, False)
        self.assertEqual(ctx.exception.code, "ERR_BOT_SYNC_LOOP_QUARANTINED")
        # New fix commit resets counter
        self.assertEqual(gate.record_bot_sync(self.conn, "idp#8207", False, True), 0)

    def test_03_headless_handoff_forbids_waiting_for_founder(self):
        with self.assertRaises(gate.GuardViolation) as ctx:
            gate.enforce_headless_handoff(
                self.conn,
                "glm-5.3-pennyd",
                "lane/harness-rust-ci",
                "cb47fac",
                "#8395",
                requested_action="IDLE_WAIT_FOR_FOUNDER",
                next_unblocked_ticket="#8390",
            )
        self.assertEqual(ctx.exception.code, "ERR_FOUNDER_EVENT_LOOP_FORBIDDEN")

        receipt = gate.enforce_headless_handoff(
            self.conn,
            "glm-5.3-pennyd",
            "lane/harness-rust-ci",
            "cb47fac",
            "#8395",
            requested_action="CONTINUE",
            next_unblocked_ticket="#8390",
        )
        self.assertEqual(receipt["next_action"], "PULL_NEXT_TICKET")
        self.assertEqual(receipt["next_target"], "#8390")

    def test_04_superseded_head_watcher_aborts_immediately(self):
        res = gate.evaluate_lane_watcher("7d8741cc1", "pending", "7d575dacc")
        self.assertEqual(res["verdict"], "SUPERSEDED_HEAD")
        self.assertFalse(res["continue"])
        retired = gate.evaluate_lane_watcher("7d575dacc", "pending", None)
        self.assertEqual(retired["verdict"], "LANE_RETIRED")
        self.assertFalse(retired["continue"])

    def test_05_durable_passkey_sink_survives_nonce_change_and_blocks_unconsumed_purge(
        self,
    ):
        for bad in ("LOCAL_TERMINAL_STDOUT", "LOCAL_MAC_POLLER_PID_85399"):
            with self.assertRaises(gate.GuardViolation) as ctx:
                gate.validate_escalation_channel(bad)
            self.assertEqual(ctx.exception.code, "ERR_LOCAL_POLLER_OR_TERMINAL_TRAP")
        gate.validate_escalation_channel("DURABLE_FOUNDER_INBOX")

        rec = gate.put_passkey_registration(
            self.conn, "cred-founder-1", "SPKI_B64_BYTES", 86_400
        )
        self.assertGreaterEqual(rec["ttl_seconds"], 30 * 86_400)
        # Read via completely different nonce succeeds
        found = gate.read_passkey_by_any_nonce(self.conn, "brand-new-nonce-xyz")
        self.assertEqual(found["credential_id"], "cred-founder-1")
        # Purge before commit SHA fails closed
        with self.assertRaises(gate.GuardViolation) as ctx:
            gate.purge_passkey_if_consumed(self.conn)
        self.assertEqual(ctx.exception.code, "ERR_UNCONSUMED_FOUNDER_TAP")
        # After 40-hex commit SHA ack, purge succeeds
        gate.ack_passkey_committed(
            self.conn, "49c76e3190000000000000000000000000000000"
        )
        gate.purge_passkey_if_consumed(self.conn)
        self.assertIsNone(gate.read_passkey_by_any_nonce(self.conn, "any"))

    def test_06_zero_job_workflow_and_legion_admission_preflight(self):
        broken_workflow = "name: incident-loop\non: [push]\njobs:\n  # empty\n"
        with self.assertRaises(gate.GuardViolation) as wf_ctx:
            gate.validate_workflow_yaml_text(
                ".github/workflows/incident-loop.yml", broken_workflow
            )
        self.assertEqual(wf_ctx.exception.code, "ERR_ZERO_JOB_WORKFLOW")

        valid_workflow = "name: incident-loop\non: [push]\njobs:\n  sense:\n    runs-on: ubuntu-latest\n"
        gate.validate_workflow_yaml_text(
            ".github/workflows/incident-loop.yml", valid_workflow
        )

        with self.assertRaises(gate.GuardViolation) as adm_ctx:
            gate.preflight_legion_admission(
                issue_id="#8302",
                requested_paths=["platform/estate/web/door.py"],
                active_claims={
                    "dsh-web-bind-20261119": ["platform/estate/web/door.py"]
                },
                has_acceptance_contract=True,
                required_tools_available={"git"},
                required_tools_needed={"git", "ruff"},
                target_merges_cleanly_on_main=False,
            )
        self.assertEqual(adm_ctx.exception.code, "ERR_ADMISSION_PRECONDITION_FAILED")
        self.assertIn("claim conflict", adm_ctx.exception.message)
        self.assertIn("missing required sandbox tool: ruff", adm_ctx.exception.message)
        self.assertIn("does not merge cleanly", adm_ctx.exception.message)


if __name__ == "__main__":
    unittest.main(verbosity=2)
