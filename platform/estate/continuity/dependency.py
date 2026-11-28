"""Dependency-aware continuity: the estate's failure graph and its freeze.

The mission-custody half of this package (leases, checkpoints, external
effects) keeps ONE session alive across a worker's death. This module answers
the other question: when a shared dependency fails, which work is downstream of
it, and what may run while it is broken. They meet at one rule -- a monotonic
epoch fences every action -- which is why the stale-fence refusal here is the
package's own `StaleFenceError` rather than a second exception class.

Six layers, one registered edge set, one acyclicity proof. A failure freezes its
downstream blast radius (PARKED_UPSTREAM) instead of spawning one incident per
symptom; only the root of the freeze is a repair target. Repairs carry a
post-condition that is measured, so a zero-effect repair is a failure, not a
success. Every action carries a monotonic fence epoch, so a repair begun before
a recurrence can never unpark work that the recurrence re-froze.

Deterministic: no wall clock, no network, no filesystem. Every measurement is
handed in, so the same graph and the same facts always give the same answer.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

from .fields import RecordRejected, StaleFenceError

# ---------------------------------------------------------------------------
# Layers. Lower index = deeper. An edge always points from a deeper layer to a
# shallower one or within a layer; a graph that violates this raises, so the
# six-layer shape is a checked property and not a comment.
# ---------------------------------------------------------------------------

LAYERS: Tuple[str, ...] = (
    "compute",  # 0 machine: disk, swap, cpu
    "runtime",  # 1 executor, gates, hooks
    "auth",  # 2 vault, GitHub App, token
    "delivery",  # 3 claim, lane, CI, Greenlane, merge
    "catalog",  # 4 capability registry, dependency preflight
    "evidence",  # 5 YIELD/1, proof, landed
)
LAYER_INDEX: Dict[str, int] = {name: i for i, name in enumerate(LAYERS)}


class GraphError(ValueError):
    pass


@dataclass(frozen=True)
class Component:
    id: str
    layer: str
    requires: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.layer not in LAYER_INDEX:
            raise GraphError("unknown layer %r on %s" % (self.layer, self.id))
        if self.id in self.requires:
            raise GraphError("self edge on %s" % self.id)


# ---------------------------------------------------------------------------
# The estate's registered nodes on 2026-11-28. Every edge below was a measured
# dependency that day, not an aspiration.
# ---------------------------------------------------------------------------

REGISTERED: Tuple[Component, ...] = (
    Component("compute.disk", "compute"),
    Component("compute.swap", "compute", ("compute.disk",)),
    Component("compute.cpu", "compute"),
    Component("runtime.executor", "runtime", ("compute.disk",)),
    Component("runtime.gate", "runtime", ("runtime.executor",)),
    Component("runtime.hooks", "runtime", ("runtime.gate",)),
    Component("auth.vault", "auth", ("compute.disk",)),
    Component("auth.github_app", "auth", ("auth.vault",)),
    Component("auth.token", "auth", ("auth.github_app",)),
    Component("delivery.claim", "delivery", ("auth.token",)),
    Component("delivery.lane_submit", "delivery", ("delivery.claim", "runtime.gate")),
    Component("delivery.ci", "delivery", ("delivery.lane_submit",)),
    Component("delivery.greenlane", "delivery", ("delivery.ci", "runtime.gate")),
    Component("catalog.index", "catalog", ("runtime.executor",)),
    Component("catalog.preflight", "catalog", ("catalog.index", "delivery.ci")),
    # The merge is a catalog-layer action: it is the moment the registry
    # preflight is enforced, and nothing may land without it. Keeping merge in
    # the catalog layer is what makes registry drift park the landing instead
    # of the landing discovering the drift after the fact.
    Component("delivery.merge", "catalog", ("delivery.greenlane", "catalog.preflight")),
    Component("evidence.protocol", "evidence", ("compute.disk", "runtime.gate")),
    Component("evidence.proof", "evidence", ("evidence.protocol",)),
    Component("evidence.landed", "evidence", ("delivery.merge", "evidence.proof")),
)


class ContinuityGraph:
    """An acyclic dependency graph with precomputed closures.

    Construction proves the two properties the DAG claim needs: no cycle, and
    every edge respects the layer order (deeper or equal -> shallower).
    """

    def __init__(self, components: Sequence[Component]) -> None:
        self.components: Dict[str, Component] = {}
        for c in components:
            if c.id in self.components:
                raise GraphError("duplicate component %s" % c.id)
            self.components[c.id] = c
        self.edges: List[Tuple[str, str]] = []
        self.downstream: Dict[str, Set[str]] = {c.id: set() for c in components}
        for c in components:
            for req in c.requires:
                if req not in self.components:
                    raise GraphError("unknown dependency %s -> %s" % (c.id, req))
                if LAYER_INDEX[self.components[req].layer] > LAYER_INDEX[c.layer]:
                    raise GraphError(
                        "layer inversion: %s(%s) requires %s(%s)"
                        % (c.id, c.layer, req, self.components[req].layer)
                    )
                self.edges.append((req, c.id))
                self.downstream[req].add(c.id)
        self.order: Tuple[str, ...] = self._topological_order()
        self.dependents_closure: Dict[str, frozenset] = {}
        for node in self.components:
            self.dependents_closure[node] = frozenset(self._reach(node))

    # -- structure ---------------------------------------------------------
    def _topological_order(self) -> Tuple[str, ...]:
        indegree = {n: len(self.components[n].requires) for n in self.components}
        ready = sorted(n for n, d in indegree.items() if d == 0)
        order: List[str] = []
        while ready:
            node = ready.pop(0)
            order.append(node)
            for child in sorted(self.downstream[node]):
                indegree[child] -= 1
                if indegree[child] == 0:
                    ready.append(child)
                    ready.sort()
        if len(order) != len(self.components):
            remaining = sorted(set(self.components) - set(order))
            raise GraphError("cycle among %s" % ",".join(remaining))
        return tuple(order)

    def _reach(self, node: str) -> Set[str]:
        seen: Set[str] = set()
        stack = list(self.downstream[node])
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            stack.extend(self.downstream[n])
        return seen

    def ancestors(self, node: str) -> Set[str]:
        seen: Set[str] = set()
        stack = list(self.components[node].requires)
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            stack.extend(self.components[n].requires)
        return seen

    def fingerprint(self) -> str:
        body = json.dumps(
            {
                "nodes": sorted(
                    [c.id, c.layer, list(c.requires)] for c in self.components.values()
                ),
                "order": list(self.order),
                "layers": list(LAYERS),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(body.encode()).hexdigest()

    # -- properties the tests assert --------------------------------------
    def assert_acyclic(self) -> Dict[str, object]:
        """Re-derive the order with a distinct algorithm (Kahn on a copy)."""
        indeg = {n: len(c.requires) for n, c in self.components.items()}
        ready = [n for n, d in indeg.items() if d == 0]
        emitted = 0
        while ready:
            n = ready.pop()
            emitted += 1
            for child in self.downstream[n]:
                indeg[child] -= 1
                if indeg[child] == 0:
                    ready.append(child)
        if emitted != len(self.components):
            raise GraphError("cycle detected on re-derivation")
        position = {n: i for i, n in enumerate(self.order)}
        for a, b in self.edges:
            if position[a] >= position[b]:
                raise GraphError("edge %s->%s violates topological order" % (a, b))
        return {
            "nodes": len(self.components),
            "edges": len(self.edges),
            "topological_order": list(self.order),
            "order_fingerprint": self.fingerprint(),
            "acyclic": True,
        }


# ---------------------------------------------------------------------------
# Repair tiers R0..R7
# ---------------------------------------------------------------------------

TIERS = ("R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7")
TIER_MEANING = {
    "R0": "observe only; no action is admitted yet",
    "R1": "retry the same route once (transient, idempotent)",
    "R2": "local repair with a measured post-condition",
    "R3": "switch to the declared alternate route",
    "R4": "widen scope: the fault is not where it was first measured",
    "R5": "contain: quarantine the work, cap the loop",
    "R6": "escalate: hand to the owning subsystem with the evidence",
    "R7": "hand to the founder / human authority",
}


@dataclass(frozen=True)
class Facts:
    reversible: bool = True
    transient: bool = False
    retry_used: int = 0
    postcondition_measurable: bool = False
    alternate_route: bool = False
    cross_layer: bool = False
    quarantine_available: bool = False
    owner_known: bool = True
    attempted_tiers: Tuple[str, ...] = ()

    def attempted(self, tier: str) -> bool:
        return tier in self.attempted_tiers


def select_tier(facts: Facts, last_result: Optional[str] = None) -> Tuple[str, str]:
    """Deterministic ladder. Returns (tier, reason). First match wins.

    The one jump that is not step-by-step is R2 -> R6 after a zero-effect
    repair: repeating a local repair that changed nothing is the measured
    "same mission re-dispatched 7 times" defect, so the engine refuses to
    spend another attempt on it.
    """
    if last_result in ("ZERO_EFFECT", "POSTCONDITION_UNMET"):
        return (
            "R6",
            "last repair held its post-condition false: repeating it burns the machine",
        )
    if not facts.reversible and facts.owner_known:
        return (
            "R7",
            "irreversible and an owner exists: only human authority may proceed",
        )
    if (
        facts.attempted("R2")
        and facts.attempted("R3")
        and facts.attempted("R4")
        and facts.attempted("R5")
        and facts.owner_known
    ):
        return "R6", "the local ladder is spent; the owning subsystem owns it now"
    if facts.transient and facts.retry_used == 0:
        return "R1", "transient and never retried: one bounded retry"
    if facts.postcondition_measurable and facts.reversible:
        return "R2", "measurable post-condition on a reversible action"
    if facts.cross_layer and facts.quarantine_available:
        return "R5", "fault crosses layers and the work can be held"
    if facts.alternate_route:
        return "R3", "a declared alternate route exists"
    if facts.cross_layer:
        return "R4", "fault crosses layers: widen the measurement"
    if facts.owner_known:
        return "R6", "no local action is admissible: escalate with evidence"
    return "R0", "nothing is admitted yet: observe and measure"


# ---------------------------------------------------------------------------
# Post-condition delta enforcement
# ---------------------------------------------------------------------------

EXIT_OK = 0
EXIT_POSTCONDITION = 6
EXIT_STALE_FENCE = 5


@dataclass(frozen=True)
class Postcondition:
    metric: str
    op: str  # ">=", ">", "<=", "<", "=="
    target: float
    min_delta: float = 0.0

    def holds(self, before: float, after: float) -> Tuple[bool, str]:
        delta = after - before
        if self.min_delta and abs(delta) < self.min_delta:
            return False, "delta %.4f below min_delta %.4f" % (delta, self.min_delta)
        ok = {
            ">=": after >= self.target,
            ">": after > self.target,
            "<=": after <= self.target,
            "<": after < self.target,
            "==": after == self.target,
        }.get(self.op)
        if ok is None:
            raise ValueError("unknown op %r" % self.op)
        if not ok:
            return False, "%s %.4f does not satisfy %s %.4f" % (
                self.metric,
                after,
                self.op,
                self.target,
            )
        return True, "delta %+.4f; %s=%.4f %s %.4f" % (
            delta,
            self.metric,
            after,
            self.op,
            self.target,
        )


@dataclass
class RepairResult:
    node: str
    script: str
    tier_before: str
    tier_after: str
    metric: str
    before: float
    after: float
    delta: float
    postcondition_met: bool
    detail: str
    exit_code: int
    fence_epoch: int
    evidence_sha256: str

    @property
    def ok(self) -> bool:
        return self.exit_code == EXIT_OK

    def as_dict(self) -> Dict[str, object]:
        return {
            "node": self.node,
            "script": self.script,
            "tier_before": self.tier_before,
            "tier_after": self.tier_after,
            "metric": self.metric,
            "before": self.before,
            "after": self.after,
            "delta": round(self.delta, 4),
            "postcondition_met": self.postcondition_met,
            "detail": self.detail,
            "exit_code": self.exit_code,
            "fence_epoch": self.fence_epoch,
            "evidence_sha256": self.evidence_sha256,
        }


# ---------------------------------------------------------------------------
# States, incidents, freeze
# ---------------------------------------------------------------------------

HEALTHY = "HEALTHY"
DEGRADED = "DEGRADED"
FAILED = "FAILED"
PARKED = "PARKED_UPSTREAM"
REPAIRING = "REPAIRING"


@dataclass
class Incident:
    id: str
    node: str
    severity: str
    evidence: str
    fence_epoch: int
    parked: Tuple[str, ...]
    tier: str
    tier_reason: str
    closed: bool = False
    antibodies: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class FreezeReceipt:
    incident_id: str
    node: str
    fence_epoch: int
    parked: Tuple[str, ...]
    tier: str
    duration_us: float

    def as_dict(self) -> Dict[str, object]:
        return {
            "incident_id": self.incident_id,
            "root": self.node,
            "fence_epoch": self.fence_epoch,
            "parked": list(self.parked),
            "parked_count": len(self.parked),
            "tier": self.tier,
            "duration_us": round(self.duration_us, 3),
        }


class ContinuityEngine:
    def __init__(self, graph: ContinuityGraph) -> None:
        self.graph = graph
        self.state: Dict[str, str] = {n: HEALTHY for n in graph.components}
        self.fence_epoch = 0
        self.incidents: Dict[str, Incident] = {}
        self._seq = 0
        self.unhealthy: Set[str] = set()

    # -- freeze ------------------------------------------------------------
    def fail(
        self,
        node: str,
        severity: str,
        evidence: str,
        facts: Optional[Facts] = None,
        last_result: Optional[str] = None,
    ) -> FreezeReceipt:
        """Freeze the blast radius. Returns before any repair can begin.

        One incident for the whole radius. The dependents are PARKED_UPSTREAM,
        not FAILED, so the incident machinery is not woken once per symptom.
        """
        if node not in self.graph.components:
            raise KeyError(node)
        t0 = time.perf_counter()
        self.fence_epoch += 1
        self._seq += 1
        incident_id = "inc-%04d" % self._seq
        node_state = FAILED if severity == "failed" else DEGRADED
        self.state[node] = node_state
        self.unhealthy.add(node)
        parked: List[str] = []
        for dep in sorted(self.graph.dependents_closure[node]):
            if self.state[dep] in (HEALTHY, PARKED):
                self.state[dep] = PARKED
                parked.append(dep)
        fact_set = facts or Facts()
        tier, reason = select_tier(fact_set, last_result)
        incident = Incident(
            id=incident_id,
            node=node,
            severity=severity,
            evidence=evidence,
            fence_epoch=self.fence_epoch,
            parked=tuple(parked),
            tier=tier,
            tier_reason=reason,
        )
        self.incidents[incident_id] = incident
        duration_us = (time.perf_counter() - t0) * 1e6
        return FreezeReceipt(
            incident_id, node, self.fence_epoch, tuple(parked), tier, duration_us
        )

    def report_symptom(self, node: str, evidence: str) -> str:
        """Attribute a symptom to the freeze that caused it. Never a second incident.

        This is the anti-amplification rule: a missing GitHub token produced a
        new "incident" every 30 minutes because each downstream failure was
        triaged as its own root. A symptom whose ancestor is already frozen is
        recorded against that root incident and creates nothing.
        """
        if self.state.get(node) not in (FAILED, DEGRADED, PARKED):
            raise LookupError(
                "%s is not in a frozen radius; measure it before filing a symptom"
                % node
            )
        ancestors = self.graph.ancestors(node)
        for incident in sorted(
            self.incidents.values(), key=lambda i: i.fence_epoch, reverse=True
        ):
            if incident.closed:
                continue
            if incident.node == node or incident.node in ancestors:
                return incident.id
        raise LookupError("no open root incident owns %s" % node)

    # -- root node isolation ----------------------------------------------
    def repair_targets(self) -> Tuple[str, ...]:
        """Only roots of active freezes. A PARKED_UPSTREAM node is never a target."""
        return tuple(sorted({i.node for i in self.incidents.values() if not i.closed}))

    def parked(self) -> Tuple[str, ...]:
        return tuple(sorted(n for n, s in self.state.items() if s == PARKED))

    def wake_ready(self) -> Tuple[str, ...]:
        """Parked nodes whose every upstream requirement is HEALTHY."""
        ready = []
        for n, s in self.state.items():
            if s != PARKED:
                continue
            if all(self.state[r] == HEALTHY for r in self.graph.components[n].requires):
                ready.append(n)
        return tuple(sorted(ready))

    # -- fence -------------------------------------------------------------
    def stale(self, epoch: int) -> bool:
        return epoch != self.fence_epoch

    # -- verify + cascade unpark ------------------------------------------
    def verify(
        self, incident_id: str, epoch: int, receipt_sha256: str
    ) -> Tuple[Tuple[str, ...], ...]:
        """Unpark in topological waves after a VERIFIED receipt.

        A receipt from a superseded fence epoch is refused: the recurrence that
        bumped the epoch re-froze the radius, and an older repair cannot claim
        it. Nothing is unparked by a stale receipt.
        """
        incident = self.incidents[incident_id]
        if epoch != self.fence_epoch:
            raise StaleFenceError(
                "receipt fence %d != current %d (incident %s)"
                % (epoch, self.fence_epoch, incident_id)
            )
        if not receipt_sha256 or len(receipt_sha256) != 64:
            raise ValueError("a VERIFIED receipt carries a 64-hex sha256")
        self.state[incident.node] = HEALTHY
        self.unhealthy.discard(incident.node)
        incident.closed = True
        waves: List[Tuple[str, ...]] = []
        while True:
            ready = self.wake_ready()
            if not ready:
                break
            for n in ready:
                self.state[n] = HEALTHY
            waves.append(ready)
        return tuple(waves)

    # -- repair with post-condition ---------------------------------------
    def repair(
        self,
        node: str,
        script: str,
        postcondition: Postcondition,
        measure,
        action,
        tier_before: str = "R2",
        epoch: Optional[int] = None,
    ) -> RepairResult:
        """Run a repair action only if its measured delta satisfies the post-condition.

        The action runs; then `measure()` is called and the delta is judged. A
        repair whose delta is below min_delta, or whose post-condition is false,
        exits non-zero (6) and escalates R2 -> R6. It is recorded as a failure.
        "Exit 0 because the script printed success" is not admissible.
        """
        epoch = self.fence_epoch if epoch is None else epoch
        if epoch != self.fence_epoch:
            raise StaleFenceError(
                "repair fence %d is stale against %d" % (epoch, self.fence_epoch)
            )
        before = measure()
        self.state[node] = REPAIRING
        action()
        after = measure()
        held, detail = postcondition.holds(before, after)
        delta = after - before
        zero_effect = delta == 0
        if zero_effect and held:
            held, detail = False, "zero delta: the repair changed nothing"
        if held:
            exit_code = EXIT_OK
            tier_after = tier_before
        else:
            exit_code = EXIT_POSTCONDITION
            tier_after = "R6"
        body = json.dumps(
            {
                "node": node,
                "script": script,
                "metric": postcondition.metric,
                "before": before,
                "after": after,
                "delta": delta,
                "held": held,
                "exit_code": exit_code,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(body.encode()).hexdigest()
        return RepairResult(
            node=node,
            script=script,
            tier_before=tier_before,
            tier_after=tier_after,
            metric=postcondition.metric,
            before=before,
            after=after,
            delta=delta,
            postcondition_met=held,
            detail=detail,
            exit_code=exit_code,
            fence_epoch=epoch,
            evidence_sha256=digest,
        )

    # -- auto-immunization -------------------------------------------------
    def close_incident(
        self, incident_id: str, antibodies: Sequence["Antibody"]
    ) -> Incident:
        """Refuse to close an incident without a registered, falsified antibody."""
        incident = self.incidents[incident_id]
        covering = [a for a in antibodies if a.covers(incident.node)]
        if not covering:
            raise Unimmunized(
                "%s may not close: no registered antibody covers %s"
                % (incident_id, incident.node)
            )
        for a in covering:
            a.assert_falsifier()
        incident.closed = True
        incident.antibodies = [a.name for a in covering]
        return incident


class Unimmunized(RecordRejected):
    """An incident was closed without a falsified antibody covering its root."""


# ---------------------------------------------------------------------------
# Auto-immunization CA1..CA5
# ---------------------------------------------------------------------------

ANTIBODY_KINDS = {
    "CA1": "prevent at write time (deterministic gate before the action)",
    "CA2": "detect early (a precheck that refuses before cost is spent)",
    "CA3": "contain (budget, breaker, quarantine)",
    "CA4": "recover deterministically with a measured post-condition",
    "CA5": "learn (the class and its falsifier reach the fleet's memory)",
}


@dataclass(frozen=True)
class Antibody:
    name: str
    kind: str
    failure_class: str
    known_bad: object
    known_good: object
    predicate: object  # callable(fixture) -> bool : True = rejected

    def __post_init__(self) -> None:
        if self.kind not in ANTIBODY_KINDS:
            raise ValueError("kind must be one of %s" % sorted(ANTIBODY_KINDS))

    def covers(self, node: str) -> bool:
        return node == self.failure_class or node.startswith(self.failure_class + ".")

    def assert_falsifier(self) -> None:
        """A gate that cannot fail is not a gate: prove both directions now."""
        if not self.predicate(self.known_bad):
            raise Unimmunized("%s: known-bad fixture was accepted" % self.name)
        if self.predicate(self.known_good):
            raise Unimmunized("%s: known-good fixture was rejected" % self.name)
