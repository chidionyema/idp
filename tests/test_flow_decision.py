"""Falsifiers for the existing FLOW machine-first decision seam."""
import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "flow_decision", ROOT / "platform/estate/governance/flow_decision.py"
)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
NOW = datetime(2026, 11, 8, 23, 0, tzinfo=timezone.utc)


def iso(seconds=0):
    return (NOW - timedelta(seconds=seconds)).isoformat()


def evidence(seconds=5):
    return {"observer": "independent-runner", "source_sha": "a" * 40,
            "ref": "https://github.com/chidionyema/idp/actions/runs/1000",
            "observed_at": iso(seconds)}


def node(key, *, severity="minor", blast="lane", **changes):
    n = {"id": key, "state": "READY", "kind": "build", "severity": severity, "blast": blast,
         "owner": "test-agent", "placement": "github_actions",
         "incremental_monthly_gbp": 0, "requires_founder_device": False,
         "attempts": 0, "depends_on": [], "resources": [],
         "last_progress_at": iso(5), "evidence": evidence(),
         "issue": f"https://github.com/chidionyema/idp/issues/{key}"}
    n.update(changes)
    return n


def plan(*nodes, slots=3, capacity_proof=None, observed=5):
    snapshot = {"schema": module.SCHEMA, "observed_at": iso(observed),
                "capacity": {"remote_slots": slots, "evidence": capacity_proof or evidence()},
                "nodes": list(nodes)}
    return module.select(snapshot, now=NOW)


class FlowMachineDecisionTests(unittest.TestCase):
    def test_priority_not_issue_order(self):
        r = plan(node("first"), node("critical", severity="critical", blast="main"))
        self.assertEqual([x["id"] for x in r["wake"]], ["critical", "first"])
        self.assertFalse(r["release_authority"])

    def test_dependency_priority_inheritance(self):
        r = plan(node("critical", severity="critical", depends_on=["prereq"]),
                 node("unrelated", severity="major", blast="service"), node("prereq"))
        self.assertEqual([x["id"] for x in r["wake"]], ["prereq", "unrelated"])
        self.assertEqual(next(x for x in r["waiting"] if x["id"] == "critical")["state"], "WAIT_DEPENDENCY")

    def test_parallel_when_independent(self):
        r = plan(node("a", resources=["db"]), node("b", resources=["api"]))
        self.assertEqual(len(r["wake"]), 2)
        self.assertEqual(r["parallel_width"], 2)

    def test_serial_if_common_resource(self):
        r = plan(node("a", resources=["db"]), node("b", resources=["db"]))
        self.assertEqual(len(r["wake"]), 1)
        self.assertEqual(r["waiting"][0]["state"], "SERIAL_RESOURCE_WAIT")

    def test_running_resources_excluded(self):
        r = plan(node("a", state="RUNNING", resources=["db"]),
                 node("b", resources=["db"]))
        self.assertEqual(r["wake"], [])
        self.assertEqual(r["waiting"][0]["state"], "SERIAL_RESOURCE_WAIT")

    def test_recovers_stagnant_and_not_heartbeat_only(self):
        r = plan(node("a", state="RUNNING", last_progress_at=iso(600)))
        self.assertEqual(r["recovery"][0]["protocol"], "FENCED_CHECKPOINT_AND_PEER_TAKEOVER")

    def test_599_not_stagnant(self):
        self.assertEqual(plan(node("a", state="RUNNING", last_progress_at=iso(599)))["recovery"], [])

    def test_retry_limit_changes_hypothesis(self):
        r = plan(node("a", attempts=2))
        self.assertEqual(r["wake"], [])
        self.assertEqual(r["waiting"][0]["state"], "FAILURE_CLASS_ESCALATION")

    def test_stale_evidence_never_authorizes_wake(self):
        r = plan(node("a", evidence=evidence(1000)))
        self.assertEqual(r["wake"], [])
        self.assertEqual(r["waiting"][0]["state"], "OBSERVE")

    def test_stale_supervisor_blind(self):
        r = plan(node("a"), observed=901)
        self.assertEqual(r["state"], "BLIND")
        self.assertEqual(r["wake"], [])

    def test_zero_capacity_no_local_fallback(self):
        r = plan(node("a"), slots=0)
        self.assertEqual(r["wake"], [])
        self.assertEqual(r["waiting"][0]["state"], "WAIT_CAPACITY")

    def test_bad_capacity_proof_blind(self):
        r = plan(node("a"), capacity_proof=evidence(1000))
        self.assertEqual(r["state"], "BLIND")

    def test_reject_local_and_paid(self):
        for change in ({"placement": "oke"}, {"placement": "local"},
                       {"requires_founder_device": True}, {"incremental_monthly_gbp": 1}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                plan(node("a", **change))

    def test_graph_bad_edges_and_cycles_refused(self):
        with self.assertRaises(ValueError):
            plan(node("a", depends_on=["missing"]))
        with self.assertRaises(ValueError):
            plan(node("a", depends_on=["b"]), node("b", depends_on=["a"]))

    def test_critical_requests_fenced_preemption_not_blind_kill(self):
        r = plan(node("routine", state="RUNNING", severity="minor",
                      preemptible=True, checkpoint_evidence=evidence(),
                      resources=["worker-1"]),
                 node("p0", severity="critical", blast="main"), slots=0)
        self.assertEqual(r["wake"], [])
        self.assertEqual(r["preempt_requests"][0]["victim"], "routine")
        self.assertEqual(r["preempt_requests"][0]["for"], "p0")
        self.assertFalse(r["preempt_requests"][0]["release_authority"])
        self.assertEqual(next(x for x in r["waiting"] if x["id"] == "p0")["state"],
                         "WAIT_FENCED_PREEMPTION")

    def test_no_preemption_without_remote_checkpoint(self):
        r = plan(node("routine", state="RUNNING", preemptible=True,
                      checkpoint_evidence=evidence(1000)),
                 node("p0", severity="critical", blast="main"), slots=0)
        self.assertEqual(r["preempt_requests"], [])
        self.assertEqual(next(x for x in r["waiting"] if x["id"] == "p0")["state"],
                         "WAIT_CAPACITY")

    def test_p0_must_not_preempt_another_p0(self):
        r = plan(node("current", state="RUNNING", severity="critical", blast="main",
                      preemptible=True, checkpoint_evidence=evidence()),
                 node("next", severity="critical", blast="main"), slots=0)
        self.assertEqual(r["preempt_requests"], [])

    def test_machine_cannot_self_mint_authority(self):
        r = plan(node("a", severity="critical", blast="main"))
        self.assertFalse(r["release_authority"])
        self.assertEqual(r["wake"][0]["admission"], "EXISTING_TRUSTED_GATE_MUST_RECHECK")
        self.assertEqual(r["wake"][0]["action"], "WAKE_EXISTING_HOSTED_AGENT_SANDBOX")


if __name__ == "__main__":
    unittest.main()
