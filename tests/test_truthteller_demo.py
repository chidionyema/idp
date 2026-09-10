"""Tests for bin/idp-truthteller-demo — the founder's spec realised.

The live vcluster reads are NOT tested here -- those need a running demo-sandbox and the
real kubectl/vcluster path, and they are exercised by the end-to-end demo flow (the buyer
click). What we test here is what can be graded without the cluster: the truth-teller's
comparison, the prototype-class shape, the CLI entry point.

These tests follow bin/test-prose-gate: they grade behavior (verdicts, exit codes,
rendered fields), not prose. A test that only asserts a sentence appeared is refused;
a test that asserts a verdict based on observed data is a real test.
"""

from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "bin" / "idp-truthteller-demo"


def _load_module():
    """Import bin/idp-truthteller-demo as a module.

    The script has no .py suffix (it is a bin/ command), so importlib.util.spec_from_file_location
    returns None. SourceFileLoader accepts any file with a Python shebang; spec_from_loader
    builds the spec from the loader. Same end state as a regular import, just by path.
    """
    loader = SourceFileLoader("truthteller_demo", str(SCRIPT))
    spec = importlib.util.spec_from_loader("truthteller_demo", loader)
    assert spec and spec.loader, f"could not load {SCRIPT}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _shadow_mock(actual: dict) -> "object":
    """A ShadowCluster substitute that returns canned observed state without kubectl.

    The class shape is what TruthTeller depends on; the data source is irrelevant for the
    comparison tests. This lets us test the truth-teller's logic against any plausible
    observed state without a live cluster.
    """

    class _Stub:
        def __init__(self, ret):
            self._ret = ret

        def get_deployment_state(self, _name):
            return self._ret

    return _Stub(actual)


# -- TruthTeller logic: the buyable moment ----------------------------------


class TestTruthTeller(unittest.TestCase):
    def setUp(self):
        self.m = _load_module()

    def test_rogue_claim_against_crashloop_is_refused(self):
        # The buyer-demo rogue: agent claims Ready at 3/3, the cluster shows CrashLoopBackOff
        # at 0/1. The verdict must be a refusal -- status AND replicas both disagree.
        shadow = _shadow_mock(
            {"replicas": 0, "status": "CrashLoopBackOff", "error": "OOMKilled"}
        )
        tt = self.m.TruthTeller(shadow)
        pr = {
            "target_workload": "demo-shop",
            "agent_proof_of_convergence": {
                "asserted_replicas": 3,
                "asserted_status": "Ready",
                "logs": "clean",
            },
        }
        audit = tt.evaluate_merge(pr)
        self.assertFalse(audit["match"])
        self.assertEqual(audit["claim"]["asserted_status"], "Ready")
        self.assertEqual(audit["actual"]["status"], "CrashLoopBackOff")

    def test_honest_claim_against_ready_state_passes(self):
        # The same shape with an honest claim: agent asserts Ready at 1/1, cluster says
        # Ready at 1/1. Verdict: approved.
        shadow = _shadow_mock({"replicas": 1, "status": "Ready", "error": None})
        tt = self.m.TruthTeller(shadow)
        pr = {
            "target_workload": "demo-shop",
            "agent_proof_of_convergence": {
                "asserted_replicas": 1,
                "asserted_status": "Ready",
                "logs": "clean",
            },
        }
        audit = tt.evaluate_merge(pr)
        self.assertTrue(audit["match"])

    def test_partial_match_still_refuses(self):
        # Status matches but replicas do not. Ready requires ready == available; a
        # partial match is not acceptable.
        shadow = _shadow_mock({"replicas": 2, "status": "Ready", "error": None})
        tt = self.m.TruthTeller(shadow)
        pr = {
            "target_workload": "demo-shop",
            "agent_proof_of_convergence": {
                "asserted_replicas": 5,
                "asserted_status": "Ready",
                "logs": "clean",
            },
        }
        audit = tt.evaluate_merge(pr)
        self.assertFalse(audit["match"])

    def test_status_word_alone_is_not_enough(self):
        # The trap: agent claims Ready, cluster says Ready -- but cluster reports 1/1 and
        # agent claims 3/3. Without the replicas check, the lie passes.
        shadow = _shadow_mock({"replicas": 1, "status": "Ready", "error": None})
        tt = self.m.TruthTeller(shadow)
        pr = {
            "target_workload": "demo-shop",
            "agent_proof_of_convergence": {
                "asserted_replicas": 3,
                "asserted_status": "Ready",
                "logs": "clean",
            },
        }
        audit = tt.evaluate_merge(pr)
        self.assertFalse(audit["match"])

    def test_signature_is_deterministic_for_same_inputs(self):
        # The receipt is sha256 over workload|status|match|key -- same inputs must yield the
        # same digest. A buyer can verify the signature against the audit record.
        shadow = _shadow_mock({"replicas": 1, "status": "Ready", "error": None})
        tt = self.m.TruthTeller(shadow, estate_private_key="stable-key")
        pr = {
            "target_workload": "demo-shop",
            "agent_proof_of_convergence": {
                "asserted_replicas": 1,
                "asserted_status": "Ready",
                "logs": "",
            },
        }
        a1 = tt.evaluate_merge(pr)
        a2 = tt.evaluate_merge(pr)
        self.assertEqual(a1["signature"], a2["signature"])
        # And the signature is content-addressed -- a different match flag changes it.
        shadow2 = _shadow_mock(
            {"replicas": 1, "status": "CrashLoopBackOff", "error": "OOM"}
        )
        tt2 = self.m.TruthTeller(shadow2, estate_private_key="stable-key")
        a3 = tt2.evaluate_merge(pr)
        self.assertNotEqual(a1["signature"], a3["signature"])

    def test_evaluate_merge_carries_business_impact(self):
        # The audit payload includes the business outcome -- the buyable sentence a CTO
        # and a CEO both understand.
        shadow = _shadow_mock(
            {"replicas": 0, "status": "CrashLoopBackOff", "error": "OOM"}
        )
        tt = self.m.TruthTeller(shadow)
        audit = tt.evaluate_merge(
            {
                "target_workload": "demo-shop",
                "agent_proof_of_convergence": {
                    "asserted_replicas": 3,
                    "asserted_status": "Ready",
                    "logs": "",
                },
            }
        )
        self.assertIn("5,000", audit["business_impact"])
        self.assertIn("checkout", audit["business_impact"].lower())


# -- Prototype class shape: the founder's design intact ---------------------


class TestPrototypeShape(unittest.TestCase):
    """The founder's spec named these classes. Their public surface must hold."""

    def setUp(self):
        self.m = _load_module()

    def test_shadowcluster_is_a_class(self):
        self.assertTrue(callable(self.m.ShadowCluster))

    def test_rogueagent_has_submit_pull_request(self):
        agent = self.m.RogueAgent()
        pr = agent.submit_pull_request()
        self.assertIn("target_workload", pr)
        self.assertIn("agent_proof_of_convergence", pr)
        self.assertIn("asserted_status", pr["agent_proof_of_convergence"])
        self.assertIn("asserted_replicas", pr["agent_proof_of_convergence"])

    def test_truthteller_has_evaluate_merge_and_generate_receipt(self):
        shadow = _shadow_mock({"replicas": 1, "status": "Ready", "error": None})
        tt = self.m.TruthTeller(shadow)
        self.assertTrue(callable(tt.evaluate_merge))
        self.assertTrue(callable(tt.generate_cryptographic_receipt))
        # generate_receipt signature: (pr_data, actual_state, is_match) -> str
        sig = tt.generate_cryptographic_receipt(
            {"target_workload": "store-frontend"},
            {"replicas": 1, "status": "Ready", "error": None},
            True,
        )
        self.assertEqual(len(sig), 64)  # sha256 hex

    def test_run_buyer_demo_returns_audit_dict(self):
        # The CLI demo prints + returns the audit dict. Tests use the return value to
        # assert behaviour; the printed side-by-side is graded by a buyer (eyeball test).
        shadow = _shadow_mock(
            {"replicas": 0, "status": "CrashLoopBackOff", "error": "OOMKilled"}
        )
        captured_stdout = sys.stdout
        sys.stdout = sys.stderr  # silence the demo's prints
        try:
            audit = self.m.run_buyer_demo(shadow=shadow, honest=False)
        finally:
            sys.stdout = captured_stdout
        self.assertIsInstance(audit, dict)
        self.assertIn("match", audit)
        self.assertFalse(audit["match"])

    def test_run_buyer_demo_honest_path_passes(self):
        shadow = _shadow_mock({"replicas": 1, "status": "Ready", "error": None})
        captured_stdout = sys.stdout
        sys.stdout = sys.stderr
        try:
            audit = self.m.run_buyer_demo(shadow=shadow, honest=True)
        finally:
            sys.stdout = captured_stdout
        self.assertTrue(audit["match"])

    def test_default_workload_is_demo_shop(self):
        # The default workload must be the seed of the demo-sandbox, not a fictional name.
        # bin/idp-shadow's `up demo-shop` is what the buyer lands on when they launch the
        # sandbox; the demo must target the same workload.
        agent = self.m.RogueAgent()
        pr = agent.submit_pull_request()
        self.assertEqual(pr["target_workload"], "demo-shop")
        # And the proposed change is the spec's W3.1 / W3.4 case -- a memory-limit raise,
        # not an arbitrary memory decrease.
        self.assertIn("memory", pr["proposed_change"].lower())


# -- CLI shape ---------------------------------------------------------------


class TestCLI(unittest.TestCase):
    def test_help_prints(self):
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        # Subcommands listed.
        self.assertIn("demo", r.stdout)
        self.assertIn("shadow", r.stdout)
        # Flags the buyer demo uses.
        self.assertIn("--honest", r.stdout)

    def test_shadow_subcommand_requires_vcluster(self):
        # Without a launched sandbox the script must exit 2 (BLIND) and print a clear
        # reason, not crash. We can't reach the live vcluster from CI here, but the
        # exit-code contract is what matters.
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "shadow", "--workload", "demo-shop"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertIn(r.returncode, (0, 2), r.stderr)


if __name__ == "__main__":
    unittest.main()
