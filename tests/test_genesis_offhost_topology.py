"""ADR 0052: falsifiers for source-only off-host topology decisions.

The source-preflight CANNOT mint runtime/provider/identity authority.
Tests use deterministic fixture time; no real cloud credentials required.
"""
import importlib.machinery
import importlib.util
import json
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "bin/idp-topology-policy"
loader = importlib.machinery.SourceFileLoader("idp_topology_policy", str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
topology = importlib.util.module_from_spec(spec)
loader.exec_module(topology)

NOW = datetime(2026, 11, 8, 22, 40, tzinfo=timezone.utc)


class TopologyDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy, cls.digest = topology.load_policy()

    def plan(self, **updates):
        plan = {
            "placement": "github_actions",
            "role": "batch",
            "incremental_monthly_gbp": 0,
            "requires_founder_device": False,
            "requires_local_infrastructure": False,
            "remote_recovery_custody": True,
            "quota_bound": True,
            "source_only": False,
            "always_on": False,
            "commercial_sla_promised": False,
            "endpoint": "https://github.com",
            "capacity_observation": {
                "observer": "distinct-trusted-remote-observer",
                "receipt": "https://github.com/chidionyema/idp/actions/runs/100",
                "observed_at": "2026-11-08T22:39:00Z",
            },
        }
        plan.update(updates)
        return plan

    def state(self, plan):
        return topology.evaluate(plan, self.policy, self.digest, NOW)["state"]

    def test_policy_is_single_machine_readable_adr(self):
        self.assertEqual(self.policy["version"], "genesis.offhost.v1")
        self.assertEqual(self.policy["incremental_monthly_gbp_ceiling"], 0)
        self.assertTrue({"oke", "local", "laptop"}.issubset(self.policy["retired"]))

    def test_ordinary_remote_batch_never_mints_release_authority(self):
        result = topology.evaluate(self.plan(), self.policy, self.digest, NOW)
        self.assertEqual(result["state"], topology.SOURCE_ONLY)
        self.assertFalse(result["release_authority"])

    def test_oke_and_local_and_paid_placements_are_refused(self):
        for placement in ("oke", "local", "laptop", "homelab", "localhost", "paid"):
            with self.subTest(placement=placement):
                self.assertEqual(self.state(self.plan(placement=placement)), "REFUSED")

    def test_founder_machine_dependency_is_refused_even_for_cloud(self):
        self.assertEqual(self.state(self.plan(requires_founder_device=True)), "REFUSED")
        self.assertEqual(self.state(self.plan(requires_local_infrastructure=True)), "REFUSED")

    def test_localhost_endpoint_is_refused(self):
        self.assertEqual(self.state(self.plan(endpoint="http://localhost:4222")), "REFUSED")
        self.assertEqual(self.state(self.plan(endpoint="http://127.0.0.1:4222")), "REFUSED")
        self.assertEqual(self.state(self.plan(endpoint="file:///Users/founder/.estate")), "REFUSED")

    def test_unapproved_paid_or_unbounded_resource_is_refused(self):
        for cost in (0.01, -0.01, float("nan"), "0", True, None):
            with self.subTest(cost=repr(cost)):
                self.assertEqual(self.state(self.plan(incremental_monthly_gbp=cost)), "REFUSED")

    def test_incompatible_role_refused(self):
        for placement, role in (
            ("github_actions", "stateful_core"),
            ("cloudflare_free", "stateful_core"),
            ("oci_e2_existing", "stateful_core"),
            ("oci_a1_existing", "stateless_edge"),
        ):
            with self.subTest(placement=placement, role=role):
                self.assertEqual(self.state(self.plan(placement=placement, role=role)), "REFUSED")

    def test_source_only_unallocated_infrastructure_is_refused(self):
        self.assertEqual(self.state(self.plan(placement="oci_a1_existing",
                                             role="stateful_core", source_only=True)), "REFUSED")

    def test_ephemeral_runner_or_edge_not_always_on(self):
        for placement in ("github_actions", "cloudflare_free"):
            role = "batch" if placement == "github_actions" else "stateless_edge"
            self.assertEqual(self.state(self.plan(placement=placement, role=role,
                                                  always_on=True)), "REFUSED")

    def test_unproven_commercial_sla_is_refused(self):
        self.assertEqual(self.state(self.plan(commercial_sla_promised=True)), "REFUSED")

    def test_missing_quota_custody_and_capacity_is_blind(self):
        self.assertEqual(self.state(self.plan(quota_bound=False)), "BLIND")
        self.assertEqual(self.state(self.plan(remote_recovery_custody=False)), "BLIND")
        self.assertEqual(self.state(self.plan(capacity_observation={})), "BLIND")

    def test_stale_future_or_unattributed_proof_is_blind(self):
        obs = self.plan()["capacity_observation"]
        for bad in (
            {**obs, "observed_at": "2026-11-08T21:39:00Z"},
            {**obs, "observed_at": "2026-11-08T23:39:00Z"},
            {**obs, "observer": ""},
            {**obs, "receipt": ""},
            {**obs, "observed_at": "not-a-date"},
        ):
            with self.subTest(proof=bad):
                self.assertEqual(self.state(self.plan(capacity_observation=bad)), "BLIND")

    def test_unknown_fields_refused_not_silently_ignored(self):
        self.assertEqual(self.state(self.plan(authorized_override=True)), "REFUSED")

    def test_untrusted_proposal_cannot_impersonate_an_admission_receipt(self):
        forged = self.plan()
        forged["capacity_observation"]["observer"] = "self-asserted-founder"
        result = topology.evaluate(forged, self.policy, self.digest, NOW)
        self.assertNotEqual(result["state"], "OPERATIONAL")
        self.assertFalse(result["release_authority"])

    def test_source_only_brief_is_explicitly_not_live(self):
        p = subprocess.run([sys.executable, str(SOURCE), "--brief"],
                           capture_output=True, text=True, check=True)
        data = json.loads(p.stdout)
        self.assertEqual(data["runtime"], "UNKNOWN")
        self.assertFalse(data["release_authority"])


if __name__ == "__main__":
    unittest.main()
