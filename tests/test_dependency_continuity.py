"""Tests for the dependency-aware continuity engine, run against the estate's
measured 2026-11-28 failure modes.

Every number these tests assert was measured that day on this machine:
disk below the 1500 MB floor, no GitHub token, registry witness drift, the
R5 incident amplification loop, and the same mission re-dispatched seven times.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# platform/ has no __init__.py (it collides with the stdlib `platform`, idp#3564),
# so the package is imported from platform/estate the way its own tests do.
sys.path.insert(0, str(ROOT / "platform" / "estate"))

from continuity.dependency import (  # noqa: E402
    Antibody,
    Component,
    ContinuityEngine,
    ContinuityGraph,
    EXIT_OK,
    EXIT_POSTCONDITION,
    FAILED,
    DEGRADED,
    Facts,
    GraphError,
    HEALTHY,
    PARKED,
    Postcondition,
    REGISTERED,
    StaleFenceError,
    Unimmunized,
    select_tier,
)
from continuity.dependency_gate import (  # noqa: E402
    DISPATCHED,
    PARKED_UPSTREAM,
    Lane,
    UpstreamFreezeGate,
)


def graph():
    return ContinuityGraph(REGISTERED)


def sha(n=1):
    return ("%064x" % n)[-64:]


# ---------------------------------------------------------------------------
# 1. The DAG itself: acyclic, ordered, layer-consistent, and it refuses a cycle.
# ---------------------------------------------------------------------------


class TestGraph(unittest.TestCase):
    def test_registered_graph_is_acyclic_and_ordered(self):
        g = graph()
        facts = g.assert_acyclic()
        self.assertEqual(facts["nodes"], 19)
        self.assertEqual(facts["edges"], 23)
        self.assertTrue(facts["acyclic"])
        self.assertEqual(len(facts["topological_order"]), 19)
        # every edge points forward in the emitted order
        pos = {n: i for i, n in enumerate(facts["topological_order"])}
        for a, b in g.edges:
            self.assertLess(pos[a], pos[b])

    def test_fingerprint_is_stable(self):
        self.assertEqual(graph().fingerprint(), graph().fingerprint())
        self.assertEqual(len(graph().fingerprint()), 64)

    def test_cycle_is_refused(self):
        nodes = (
            Component("compute.a", "compute"),
            Component("runtime.b", "runtime", ("compute.a",)),
            # runtime.c requires compute.a, and the inversion below closes a cycle
            Component("runtime.c", "runtime", ("compute.a",)),
        )
        g = ContinuityGraph(nodes)
        # now a real cycle inside one layer: c <-> b
        with self.assertRaises(GraphError):
            ContinuityGraph(
                (
                    Component("runtime.b", "runtime", ("runtime.c",)),
                    Component("runtime.c", "runtime", ("runtime.b",)),
                )
            )
        self.assertEqual(len(g.order), 3)

    def test_layer_inversion_is_refused(self):
        with self.assertRaises(GraphError):
            ContinuityGraph(
                (
                    Component("compute.x", "compute", ("delivery.y",)),
                    Component("delivery.y", "delivery"),
                )
            )

    def test_unknown_and_duplicate_are_refused(self):
        with self.assertRaises(GraphError):
            ContinuityGraph((Component("compute.x", "compute", ("nope",)),))
        with self.assertRaises(GraphError):
            ContinuityGraph(
                (Component("compute.x", "compute"), Component("compute.x", "compute"))
            )


# ---------------------------------------------------------------------------
# 2. Freeze: blast radius, one incident, root isolation, under 5 ms.
# ---------------------------------------------------------------------------


class TestFreeze(unittest.TestCase):
    def test_missing_token_freezes_exactly_its_blast_radius(self):
        e = ContinuityEngine(graph())
        r = e.fail("auth.token", "failed", "gh auth status: invalid; token unreadable")
        self.assertEqual(
            set(r.parked),
            {
                "delivery.claim",
                "delivery.lane_submit",
                "delivery.ci",
                "delivery.greenlane",
                "catalog.preflight",
                "delivery.merge",
                "evidence.landed",
            },
        )
        self.assertEqual(e.state["auth.token"], FAILED)
        # the freeze is upstream-only: nothing that auth.token does not feed moves
        for untouched in (
            "compute.disk",
            "compute.cpu",
            "runtime.gate",
            "catalog.index",
            "evidence.protocol",
            "evidence.proof",
        ):
            self.assertEqual(e.state[untouched], HEALTHY)

    def test_one_incident_for_the_whole_radius(self):
        e = ContinuityEngine(graph())
        e.fail("auth.token", "failed", "no token")
        # seven downstream failures observed; seven symptoms, ONE incident
        self.assertEqual(len(e.incidents), 1)
        for node in (
            "delivery.claim",
            "delivery.lane_submit",
            "delivery.ci",
            "delivery.greenlane",
            "catalog.preflight",
            "delivery.merge",
            "evidence.landed",
        ):
            self.assertEqual(e.report_symptom(node, "same root"), "inc-0001")
        self.assertEqual(len(e.incidents), 1)

    def test_root_node_isolation(self):
        e = ContinuityEngine(graph())
        e.fail("auth.token", "failed", "no token")
        self.assertEqual(e.repair_targets(), ("auth.token",))
        for parked in e.parked():
            self.assertNotIn(parked, e.repair_targets())

    def test_symptom_without_a_root_is_refused(self):
        e = ContinuityEngine(graph())
        with self.assertRaises(LookupError):
            e.report_symptom("delivery.ci", "nothing frozen")

    def test_disk_is_the_measured_spof(self):
        e = ContinuityEngine(graph())
        r = e.fail("compute.disk", "degraded", "free_mb 1464 < floor 1500")
        self.assertEqual(len(r.parked), 17)
        # 17 of 19 nodes depend on the volume: the floor is a single point of failure
        self.assertEqual(
            sorted(e.parked()),
            sorted(set(graph().components) - {"compute.disk", "compute.cpu"}),
        )

    def test_a_leaf_freeze_parks_only_its_dependents(self):
        e = ContinuityEngine(graph())
        r = e.fail(
            "catalog.preflight", "degraded", "registry witness not committed at HEAD"
        )
        self.assertEqual(set(r.parked), {"delivery.merge", "evidence.landed"})

    def test_freeze_fanout_under_5ms(self):
        g = graph()
        e = ContinuityEngine(g)
        samples = []
        for _ in range(2000):
            # fresh state each iteration, precomputed closures reused
            e.state = {n: HEALTHY for n in g.components}
            e.unhealthy.clear()
            r = e.fail("compute.disk", "degraded", "measured")
            samples.append(r.duration_us)
        samples.sort()
        p50 = samples[len(samples) // 2]
        p95 = samples[int(len(samples) * 0.95)]
        mx = samples[-1]
        self.assertLess(p95, 5000.0, "p95 %.1fus" % p95)
        TestFreeze.latency = {
            "n": len(samples),
            "p50_us": p50,
            "p95_us": p95,
            "max_us": mx,
            "radius": 17,
        }


# ---------------------------------------------------------------------------
# 3. Repair tiers R0..R7 and the post-condition delta.
# ---------------------------------------------------------------------------


class TestTiers(unittest.TestCase):
    def test_every_tier_is_reachable_and_reasoned(self):
        cases = {
            "R0": Facts(owner_known=False),
            "R1": Facts(transient=True, retry_used=0),
            "R2": Facts(postcondition_measurable=True, reversible=True),
            "R3": Facts(alternate_route=True, reversible=True),
            "R4": Facts(cross_layer=True, reversible=True),
            "R5": Facts(cross_layer=True, quarantine_available=True, reversible=True),
            "R6": Facts(reversible=True),
            "R7": Facts(reversible=False, owner_known=True),
        }
        seen = {}
        for want, facts in cases.items():
            got, reason = select_tier(facts)
            self.assertEqual(got, want, "%s -> %s (%s)" % (want, got, reason))
            self.assertTrue(reason)
            seen[got] = reason
        self.assertEqual(sorted(seen), ["R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7"])

    def test_zero_effect_repair_jumps_r2_to_r6(self):
        tier, reason = select_tier(
            Facts(postcondition_measurable=True), last_result="ZERO_EFFECT"
        )
        self.assertEqual(tier, "R6")
        self.assertIn("burns the machine", reason)

    def test_spent_ladder_escalates(self):
        tier, _ = select_tier(
            Facts(reversible=True, attempted_tiers=("R2", "R3", "R4", "R5"))
        )
        self.assertEqual(tier, "R6")


class TestPostcondition(unittest.TestCase):
    def _engine(self):
        return ContinuityEngine(graph())

    def test_a_7mb_success_is_a_failure(self):
        """Measured 2026-11-28: disk-reclaim printed exit 0 having freed 7 MB (1499 -> 1494)."""
        e = self._engine()
        metric = {"free_mb": 1499}
        r = e.repair(
            "compute.disk",
            "estate-execute disk-reclaim",
            Postcondition("free_mb", ">=", 1500, min_delta=1),
            measure=lambda: metric["free_mb"],
            action=lambda: metric.update(free_mb=1494),
        )
        self.assertEqual(r.exit_code, EXIT_POSTCONDITION)
        self.assertFalse(r.postcondition_met)
        self.assertEqual(r.tier_before, "R2")
        self.assertEqual(r.tier_after, "R6")
        self.assertEqual(r.delta, -5)
        self.assertEqual(len(r.evidence_sha256), 64)

    def test_zero_delta_is_refused_even_when_the_predicate_is_true(self):
        e = self._engine()
        metric = {"errors": 0}
        r = e.repair(
            "runtime.gate",
            "gate republished",
            Postcondition("errors", "<=", 0),
            measure=lambda: metric["errors"],
            action=lambda: None,
        )
        self.assertEqual(r.exit_code, EXIT_POSTCONDITION)
        self.assertIn("zero delta", r.detail)
        self.assertEqual(r.tier_after, "R6")

    def test_a_real_repair_passes_and_keeps_its_tier(self):
        e = self._engine()
        metric = {"free_mb": 1464}
        r = e.repair(
            "compute.disk",
            "remove own scratch trees",
            Postcondition("free_mb", ">=", 1500, min_delta=1),
            measure=lambda: metric["free_mb"],
            action=lambda: metric.update(free_mb=2507),
        )
        self.assertEqual(r.exit_code, EXIT_OK)
        self.assertTrue(r.postcondition_met)
        self.assertEqual(r.tier_after, "R2")
        self.assertEqual(r.delta, 1043)


# ---------------------------------------------------------------------------
# 4. Monotonic fencing.
# ---------------------------------------------------------------------------


class TestFence(unittest.TestCase):
    def test_a_recurrence_supersedes_an_in_flight_repair(self):
        e = ContinuityEngine(graph())
        first = e.fail("auth.token", "failed", "no token")
        self.assertEqual(first.fence_epoch, 1)
        second = e.fail("auth.token", "failed", "token rotated mid-repair")
        self.assertEqual(second.fence_epoch, 2)
        with self.assertRaises(StaleFenceError):
            e.verify(first.incident_id, first.fence_epoch, sha(1))
        # nothing was unparked by the stale receipt
        self.assertEqual(e.state["delivery.claim"], PARKED)
        with self.assertRaises(StaleFenceError):
            e.repair(
                "auth.token",
                "mint token",
                Postcondition("tokens", ">=", 1),
                measure=lambda: 0,
                action=lambda: None,
                epoch=first.fence_epoch,
            )

    def test_the_newest_fence_can_verify(self):
        e = ContinuityEngine(graph())
        e.fail("auth.token", "failed", "no token")
        second = e.fail("auth.token", "failed", "recurrence")
        waves = e.verify(second.incident_id, second.fence_epoch, sha(7))
        self.assertTrue(waves)
        self.assertEqual(e.parked(), ())


# ---------------------------------------------------------------------------
# 5. Topological cascade unpark.
# ---------------------------------------------------------------------------


class TestCascade(unittest.TestCase):
    def test_unpark_walks_the_dag_wave_by_wave(self):
        g = graph()
        e = ContinuityEngine(g)
        r = e.fail("auth.token", "failed", "no token")
        frozen = {n: e.state[n] for n in r.parked}
        waves = e.verify(r.incident_id, r.fence_epoch, sha(3))
        self.assertEqual(sum(len(w) for w in waves), len(frozen))
        self.assertEqual(sorted(n for w in waves for n in w), sorted(frozen))
        # no node is unparked before every one of its requirements is healthy
        pos = {n: i for i, n in enumerate(g.order)}
        seen = set(n for n in g.components if n not in frozen)
        for wave in waves:
            for n in wave:
                for req in g.components[n].requires:
                    self.assertIn(req, seen, "%s unparked before %s" % (n, req))
            seen.update(wave)
            # a wave is strictly forward in topological order
            self.assertEqual(list(wave), sorted(wave, key=lambda n: pos[n]))
        self.assertEqual(e.parked(), ())
        self.assertEqual(waves[0], ("delivery.claim",))

    def test_no_wave_leaves_a_node_held(self):
        g = graph()
        e = ContinuityEngine(g)
        r = e.fail("auth.token", "failed", "no token")
        e.verify(r.incident_id, r.fence_epoch, sha(9))
        for state in e.state.values():
            self.assertEqual(state, HEALTHY)


# ---------------------------------------------------------------------------
# 6. Auto-immunization CA1..CA5.
# ---------------------------------------------------------------------------


def rejects_bad_accepts_good(bad, good):
    def predicate(fixture):
        return fixture == bad

    return predicate


class TestImmunization(unittest.TestCase):
    def _incident(self):
        e = ContinuityEngine(graph())
        e.fail("auth.token", "failed", "no token")
        return e, "inc-0001"

    def test_closing_without_an_antibody_is_refused(self):
        e, inc = self._incident()
        with self.assertRaises(Unimmunized):
            e.close_incident(inc, [])

    def test_an_antibody_whose_falsifier_cannot_fail_is_refused(self):
        e, inc = self._incident()
        toothless = Antibody(
            "CA2-token-precheck",
            "CA2",
            "auth.token",
            known_bad="bad",
            known_good="good",
            predicate=lambda fixture: False,
        )  # accepts everything
        with self.assertRaises(Unimmunized) as refused:
            e.close_incident(inc, [toothless])
        self.assertIn("known-bad fixture was accepted", str(refused.exception))

    def test_an_antibody_that_rejects_good_input_is_refused(self):
        e, inc = self._incident()
        paranoid = Antibody(
            "CA2-token-precheck",
            "CA2",
            "auth.token",
            known_bad="bad",
            known_good="good",
            predicate=lambda fixture: True,
        )
        with self.assertRaises(Unimmunized):
            e.close_incident(inc, [paranoid])

    def test_a_falsified_antibody_closes_the_incident(self):
        e, inc = self._incident()
        good = Antibody(
            "CA2-token-precheck",
            "CA2",
            "auth.token",
            known_bad="missing",
            known_good="present",
            predicate=rejects_bad_accepts_good("missing", "present"),
        )
        closed = e.close_incident(inc, [good])
        self.assertTrue(closed.closed)
        self.assertEqual(closed.antibodies, ["CA2-token-precheck"])

    def test_every_kind_is_registrable(self):
        for kind in ("CA1", "CA2", "CA3", "CA4", "CA5"):
            Antibody(
                "a-" + kind,
                kind,
                "compute.disk",
                "bad",
                "good",
                predicate=rejects_bad_accepts_good("bad", "good"),
            )
        with self.assertRaises(ValueError):
            Antibody("a-CA9", "CA9", "compute.disk", "b", "g", lambda f: False)


# ---------------------------------------------------------------------------
# 7. Greenlane dispatch wiring.
# ---------------------------------------------------------------------------


class TestGreenlaneDispatch(unittest.TestCase):
    def test_a_lane_behind_a_missing_token_is_parked_before_dispatch(self):
        e = ContinuityEngine(graph())
        e.fail("auth.token", "failed", "gh auth status: invalid")
        gate = UpstreamFreezeGate(e)
        calls = []
        d = gate.before_dispatch(
            Lane(
                "lane/8725-estate-gate-worker-spawn",
                "72ff467b0",
                ("auth.token", "runtime.gate", "compute.disk"),
            ),
            dispatch=calls.append,
        )
        self.assertEqual(d.verdict, PARKED_UPSTREAM)
        self.assertEqual(d.blocked_by, ("auth.token",))
        self.assertEqual(d.evidence, {"auth.token": FAILED})
        self.assertFalse(d.dispatch_called)
        self.assertEqual(calls, [])

    def test_a_healthy_lane_is_dispatched_once(self):
        e = ContinuityEngine(graph())
        gate = UpstreamFreezeGate(e)
        calls = []
        d = gate.before_dispatch(
            Lane(
                "lane/run-46146985176",
                "623cfc91f",
                ("compute.disk", "runtime.gate", "delivery.claim"),
            ),
            dispatch=calls.append,
        )
        self.assertEqual(d.verdict, DISPATCHED)
        self.assertTrue(d.dispatch_called)
        self.assertEqual(len(calls), 1)

    def test_an_unregistered_requirement_is_not_treated_as_healthy(self):
        e = ContinuityEngine(graph())
        gate = UpstreamFreezeGate(e)
        d = gate.before_dispatch(Lane("lane/x", "abc", ("dependency_edges.registry",)))
        self.assertEqual(d.verdict, PARKED_UPSTREAM)
        self.assertEqual(
            d.evidence["dependency_edges.registry"], "UNREGISTERED_REQUIREMENT"
        )

    def test_parked_lane_is_admitted_after_the_root_recovers(self):
        e = ContinuityEngine(graph())
        r = e.fail("auth.token", "failed", "no token")
        gate = UpstreamFreezeGate(e)
        lane = Lane("lane/8645", "dfa655c1b", ("auth.token",))
        self.assertEqual(gate.before_dispatch(lane).verdict, PARKED_UPSTREAM)
        e.verify(r.incident_id, r.fence_epoch, sha(11))
        self.assertEqual(gate.before_dispatch(lane).verdict, DISPATCHED)

    def test_preexisting_upstream_failure_is_seen_without_a_freeze_call(self):
        """Today's real order: disk fell before any lane was dispatched."""
        e = ContinuityEngine(graph())
        e.state["compute.disk"] = DEGRADED
        gate = UpstreamFreezeGate(e)
        d = gate.before_dispatch(Lane("lane/any", "sha", ("compute.disk",)))
        self.assertEqual(d.verdict, PARKED_UPSTREAM)
        self.assertEqual(d.evidence, {"compute.disk": DEGRADED})

    def test_dispatch_gate_under_5ms(self):
        e = ContinuityEngine(graph())
        e.fail("auth.token", "failed", "no token")
        gate = UpstreamFreezeGate(e)
        lane = Lane("lane/x", "sha", ("auth.token", "runtime.gate", "compute.disk"))
        samples = []
        for _ in range(2000):
            samples.append(gate.before_dispatch(lane).duration_us)
        samples.sort()
        p95 = samples[int(len(samples) * 0.95)]
        self.assertLess(p95, 5000.0, "p95 %.1fus" % p95)
        TestGreenlaneDispatch.latency = {
            "n": len(samples),
            "p50_us": samples[len(samples) // 2],
            "p95_us": p95,
            "max_us": samples[-1],
        }


# ---------------------------------------------------------------------------
# 8. The whole engine on today's four measured failures at once.
# ---------------------------------------------------------------------------


class TestToday(unittest.TestCase):
    def test_four_real_failures_produce_seven_symptoms_and_one_target(self):
        e = ContinuityEngine(graph())
        # 1. the volume is below the 1500 MB floor
        disk = e.fail(
            "compute.disk",
            "degraded",
            "free_mb 1464 < 1500 (measured); disk-reclaim freed -5 MB",
        )
        # 2. no GitHub token with repo+issues write
        e.fail(
            "auth.token",
            "failed",
            "gh auth status: invalid; bin/idp-github-app hangs rc=142",
        )
        # 3. the registry witness is not committed at the lane head
        e.fail(
            "catalog.preflight",
            "degraded",
            "registry-workflow-dependency-preflight: witness not at HEAD",
        )
        # 4. one lane is red with an unidentified rung
        e.fail("delivery.ci", "degraded", "fast-gate failure run 46146985176")
        self.assertEqual(len(e.incidents), 4)
        # every lane waits on the same two roots, and is not its own incident
        gate = UpstreamFreezeGate(e)
        lanes = (
            Lane(
                "lane/consult-plane-founder-firewall",
                "623cfc91f",
                ("compute.disk", "auth.token", "catalog.preflight"),
            ),
            Lane(
                "lane/8725-estate-gate-worker-spawn",
                "72ff467b0",
                ("compute.disk", "auth.token"),
            ),
            Lane(
                "lane/fix-guard-shared-name-installed",
                "dfa655c1b",
                ("compute.disk", "auth.token"),
            ),
        )
        decisions = gate.dispatch_all(lanes)
        self.assertEqual([d.verdict for d in decisions], [PARKED_UPSTREAM] * 3)
        self.assertEqual(
            decisions[0].blocked_by, ("compute.disk", "auth.token", "catalog.preflight")
        )
        self.assertEqual(
            e.repair_targets(),
            ("auth.token", "catalog.preflight", "compute.disk", "delivery.ci"),
        )
        # the four freezes touch 15+ distinct nodes and still wake 4 incidents, not 15
        self.assertLessEqual(len(e.incidents), len(disk.parked))
