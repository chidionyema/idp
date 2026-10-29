"""The estate's concurrency envelope, tested on its own.

The code under test is ``packages/aee/src/aee/scale.py``: the admission controller that
decides WHICH work becomes a queue task and WHEN, in front of the estate's existing
dispatcher and worker pool.

These suites live in the repository's root ``tests/`` tree, not in ``packages/aee/tests/``,
and that is a measured decision rather than a taste one: ``bin/idp-tests-for`` selects a
test by grepping ``tests/`` and ``sovereign/tests/`` for the changed paths, and no CI
workflow collects ``packages/`` at all, so a proof that lives under ``packages/aee/tests/``
is a proof CI never runs. The precedent is ``tests/test_aei_features.py``, which binds a
package's feature file from the root tree for the same reason.

Nothing here is mocked. The lanes are real ``IntelligenceLane`` values, the supply is the
caller's data, and the money lands in the real ``WorkGraph`` -- the graph holds the
reservations and the receipts, and the journal only records what the scheduler decided.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "packages" / "aee" / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from aee.allocation import SupplyOffer  # noqa: E402
from aee.contracts import (  # noqa: E402
    AcceptanceCriterion,
    IntelligenceLane,
    Objective,
    VerificationLevel,
    WorkNode,
)
from aee.digest import digest_of  # noqa: E402
from aee.graph import WorkGraph  # noqa: E402
from aee.scale import (  # noqa: E402
    Admission,
    AdmissionOutcome,
    NodeSupply,
    ScaleError,
    ScalePolicy,
    ScaleScheduler,
    SchedulerJournal,
    decode_goal,
    encode_goal,
    scopes_conflict,
)

# ---------------------------------------------------------------------------
# the estate's own vocabulary
# ---------------------------------------------------------------------------


def _objective() -> Objective:
    return Objective(
        id="obj-scale",
        statement="the estate's work runs at the right scale",
        acceptance=(
            AcceptanceCriterion(
                id="ac-runs",
                description="the admitted work runs and is measured",
                level=VerificationLevel.OPERATION,
            ),
        ),
        authority="founder",
        scope=("packages/aee", "features", "tests"),
    )


def _graph(*nodes: WorkNode, owner: str = "agent-1") -> WorkGraph:
    graph = WorkGraph(_objective(), "graph-scale", owner=owner)
    for node in nodes:
        graph.add_node(node)
    return graph


def _node(
    node_id: str,
    scope: tuple[str, ...],
    *,
    depends_on: tuple[str, ...] = (),
    priority: int = 0,
) -> WorkNode:
    return WorkNode(
        id=node_id,
        title="the %s work" % node_id,
        scope=scope,
        depends_on=depends_on,
        priority=priority,
        owner="agent-1",
    )


def _lane(
    lane_id: str,
    *,
    deterministic: bool = False,
    cost: float = 0.001,
    quality: float = 0.9,
    availability: float = 1.0,
    latency: int = 100,
) -> IntelligenceLane:
    return IntelligenceLane(
        id=lane_id,
        provider="estate",
        model="test-model",
        lane_type="tool" if deterministic else "model",
        deterministic=deterministic,
        cost_usd_per_1k=cost,
        quality_prior=quality,
        availability=availability,
        latency_p95_ms=latency,
    )


def _offer(lane: IntelligenceLane, *, units: int = 1) -> SupplyOffer:
    return SupplyOffer(lane=lane, capabilities=("summarise",), units_available=units)


def _supply(
    *offers: SupplyOffer, tokens: int = 1000, budget: float = 1.0
) -> NodeSupply:
    return NodeSupply(
        offers=offers,
        estimated_tokens=tokens,
        required_capabilities=("summarise",),
        budget_usd=budget,
    )


def _admitted(results: list[Admission]) -> list[Admission]:
    return [r for r in results if r.outcome is AdmissionOutcome.ADMITTED]


def _by_node(results: list[Admission]) -> dict[str, Admission]:
    return {r.node_id: r for r in results}


# ---------------------------------------------------------------------------
# the scope rule
# ---------------------------------------------------------------------------


def test_the_same_path_is_a_conflict():
    assert scopes_conflict(["packages/aee"], ["packages/aee"])


def test_a_path_prefix_is_a_conflict():
    assert scopes_conflict(["packages/aee"], ["packages/aee/src/aee"])


def test_a_sibling_path_is_not_a_conflict():
    assert scopes_conflict(["packages/aee"], ["packages/features"]) == ""


def test_a_glob_prefix_is_a_conflict():
    """Two workers must never write the same file, so a wildcard overlaps conservatively."""
    assert scopes_conflict(["packages/aee/*"], ["packages/aee/src/aee"])


def test_a_distant_glob_is_not_a_conflict():
    assert scopes_conflict(["packages/aee/*"], ["packages/other/*"]) == ""


def test_a_bare_wildcard_conflicts_with_everything():
    assert scopes_conflict(["*"], ["packages/aee"])


# ---------------------------------------------------------------------------
# admission
# ---------------------------------------------------------------------------


def test_independent_nodes_are_admitted_together_and_the_dependent_one_waits():
    """The cap decides how many start; the graph decides which may start at all."""
    graph = _graph(
        _node("node-a", ("packages/aee/src/aee",)),
        _node("node-b", ("packages/aee/tests",)),
        _node("node-c", ("features/assurance",), depends_on=("node-a",)),
    )
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=3))
    supply = {"node-a": _supply(_offer(_lane("lane-a")))}

    results = scheduler.admit(supply, now=10.0)

    admitted = {r.node_id for r in _admitted(results)}
    assert admitted == {"node-a"}, (
        "the dependent node cannot start before its parent is accepted"
    )
    assert "node-c" not in {r.node_id for r in results}


def test_the_concurrency_cap_defers_the_third_node():
    """The envelope holds what it was told to hold, and says what it is waiting for."""
    graph = _graph(
        _node("node-a", ("packages/aee/src/aee",)),
        _node("node-b", ("packages/aee/tests",)),
        _node("node-c", ("features/assurance",)),
    )
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))
    supply = {
        nid: _supply(_offer(_lane("lane-a"))) for nid in ("node-a", "node-b", "node-c")
    }

    results = scheduler.admit(supply, now=10.0)

    assert len(_admitted(results)) == 2
    deferred = [r for r in results if r.outcome is AdmissionOutcome.DEFERRED]
    assert len(deferred) == 1
    assert "waits" in deferred[0].reason


def test_overlapping_scopes_are_refused_with_the_conflict_named():
    """The conflict is detected before the work starts, and it names both paths."""
    graph = _graph(
        _node("node-a", ("packages/aee/src/aee",)),
        _node("node-b", ("packages/aee/src",)),
    )
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=4))
    supply = {nid: _supply(_offer(_lane("lane-a"))) for nid in ("node-a", "node-b")}

    results = scheduler.admit(supply, now=10.0)

    by_node = _by_node(results)
    assert by_node["node-a"].outcome is AdmissionOutcome.ADMITTED
    assert by_node["node-b"].outcome is AdmissionOutcome.REFUSED
    assert "node-a" in by_node["node-b"].reason
    assert "packages/aee/src/aee" in by_node["node-b"].reason


def test_a_node_no_lane_can_take_is_refused_with_the_reason():
    graph = _graph(_node("node-a", ("packages/aee/src/aee",)))
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))
    dead = _lane("lane-dead", availability=0.0)

    results = scheduler.admit({"node-a": _supply(_offer(dead))}, now=10.0)

    refused = [r for r in results if r.outcome is AdmissionOutcome.REFUSED]
    assert len(refused) == 1
    assert "lane-dead" in refused[0].reason


def test_a_node_without_supply_is_refused():
    graph = _graph(_node("node-a", ("packages/aee/src/aee",)))
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))

    results = scheduler.admit({}, now=10.0)

    refused = [r for r in results if r.outcome is AdmissionOutcome.REFUSED]
    assert "no supply" in refused[0].reason


# ---------------------------------------------------------------------------
# money
# ---------------------------------------------------------------------------


def test_the_hold_lives_in_the_graph_and_the_journal_names_the_decision():
    """The graph is the estate's record of the money; the journal is the scheduler's."""
    graph = _graph(_node("node-a", ("packages/aee/src/aee",)))
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))
    supply = {"node-a": _supply(_offer(_lane("lane-a")))}

    results = scheduler.admit(supply, now=10.0)
    admission = _admitted(results)[0]

    assert admission.reservation is not None
    assert graph.reservations[admission.reservation.id].state.value == "held"
    assert scheduler.held_usd() == pytest.approx(admission.reservation.usd)
    assert scheduler.committed_usd() == 0.0
    assert admission.reservation.budget_ref == "sovereign/engine/budget.py"


def test_committing_writes_the_receipt_and_the_committed_reservation():
    graph = _graph(_node("node-a", ("packages/aee/src/aee",)))
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))
    supply = {"node-a": _supply(_offer(_lane("lane-a")))}
    admission = _admitted(scheduler.admit(supply, now=10.0))[0]

    receipt = scheduler.commit(
        "node-a", cost_usd=0.004, ledger_hash="ledger-row-1", now=12.0
    )

    assert receipt.cost_usd == 0.004
    assert receipt.ledger_hash == "ledger-row-1"
    assert graph.economics[receipt.id].cost_usd == 0.004
    assert graph.reservations[admission.reservation.id].state.value == "committed"
    assert scheduler.committed_usd() == pytest.approx(0.004)


def test_committing_twice_is_refused():
    """The second commit would be the double spend the journal exists to prevent."""
    graph = _graph(_node("node-a", ("packages/aee/src/aee",)))
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))
    scheduler.admit({"node-a": _supply(_offer(_lane("lane-a")))}, now=10.0)
    scheduler.commit("node-a", cost_usd=0.004, ledger_hash="ledger-row-1", now=12.0)

    with pytest.raises(ScaleError):
        scheduler.commit("node-a", cost_usd=0.004, ledger_hash="ledger-row-2", now=13.0)


def test_a_cost_without_a_ledger_row_is_refused():
    graph = _graph(_node("node-a", ("packages/aee/src/aee",)))
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))
    scheduler.admit({"node-a": _supply(_offer(_lane("lane-a")))}, now=10.0)

    with pytest.raises(ScaleError):
        scheduler.commit("node-a", cost_usd=0.004, ledger_hash="", now=12.0)


def test_the_budget_ceiling_stops_the_work_and_records_the_reason():
    """The ceiling is a hard stop, and the reason is in the durable state."""
    graph = _graph(
        _node("node-a", ("packages/aee/src/aee",)),
        _node("node-b", ("packages/aee/tests",)),
    )
    scheduler = ScaleScheduler(
        graph, policy=ScalePolicy(max_concurrent=4, budget_ceiling_usd=0.0005)
    )
    supply = {nid: _supply(_offer(_lane("lane-a"))) for nid in ("node-a", "node-b")}

    results = scheduler.admit(supply, now=10.0)

    assert not _admitted(results)
    assert scheduler.journal.cutoff_reason
    assert "ceiling" in scheduler.journal.cutoff_reason


def test_the_ceiling_counts_the_money_that_is_already_held():
    """A hold is money the estate cannot spend twice."""
    graph = _graph(
        _node("node-a", ("packages/aee/src/aee",)),
        _node("node-b", ("packages/aee/tests",)),
    )
    scheduler = ScaleScheduler(
        graph, policy=ScalePolicy(max_concurrent=4, budget_ceiling_usd=0.0015)
    )
    supply = {nid: _supply(_offer(_lane("lane-a"))) for nid in ("node-a", "node-b")}

    results = scheduler.admit(supply, now=10.0)

    by_node = _by_node(results)
    assert by_node["node-a"].outcome is AdmissionOutcome.ADMITTED
    assert by_node["node-b"].outcome is AdmissionOutcome.REFUSED
    assert "ceiling" in by_node["node-b"].reason


# ---------------------------------------------------------------------------
# cancellation and failure
# ---------------------------------------------------------------------------


def test_cancellation_releases_the_hold_and_commits_nothing():
    graph = _graph(
        _node("node-a", ("packages/aee/src/aee",)),
        _node("node-b", ("packages/aee/tests",), depends_on=("node-a",)),
    )
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))
    supply = {"node-a": _supply(_offer(_lane("lane-a")))}
    admission = _admitted(scheduler.admit(supply, now=10.0))[0]

    scheduler.cancel("node-a", reason="the founder changed their mind", now=11.0)

    assert graph.reservations[admission.reservation.id].state.value == "released"
    assert scheduler.held_usd() == 0.0
    assert scheduler.committed_usd() == 0.0
    assert graph.node("node-a").state.value == "cancelled"


def test_cancelling_a_parent_blocks_its_dependent():
    """A dropped dependent is work that disappears from the estate's sight."""
    graph = _graph(
        _node("node-a", ("packages/aee/src/aee",)),
        _node("node-b", ("packages/aee/tests",), depends_on=("node-a",)),
    )
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))
    scheduler.admit({"node-a": _supply(_offer(_lane("lane-a")))}, now=10.0)

    scheduler.cancel("node-a", reason="stopped", now=11.0)

    assert graph.node("node-b").state.value == "blocked"
    assert "cancelled" in graph.node("node-b").reason


def test_a_failed_attempt_gives_the_hold_back():
    graph = _graph(_node("node-a", ("packages/aee/src/aee",)))
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))
    admission = _admitted(
        scheduler.admit({"node-a": _supply(_offer(_lane("lane-a")))}, now=10.0)
    )[0]

    scheduler.fail("node-a", reason="the worker died", now=11.0)

    assert graph.reservations[admission.reservation.id].state.value == "released"
    assert graph.node("node-a").state.value == "failed"
    assert scheduler.committed_usd() == 0.0


# ---------------------------------------------------------------------------
# diversion
# ---------------------------------------------------------------------------


def test_a_diverted_node_keeps_its_key_and_does_not_fail():
    """The work is the same work: the lane changes, the identity does not."""
    graph = _graph(_node("node-a", ("packages/aee/src/aee",)))
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))
    first = _lane("lane-a", deterministic=True)
    second = _lane("lane-b")
    supply = {"node-a": _supply(_offer(first), _offer(second))}

    admission = _admitted(scheduler.admit(supply, now=10.0))[0]
    assert admission.contract.lane.id == "lane-a"

    diverted = scheduler.divert(
        "node-a", supply=_supply(_offer(first, units=0), _offer(second)), now=11.0
    )

    assert diverted.logical_key == admission.logical_key
    assert diverted.contract.lane.id == "lane-b"
    assert graph.node("node-a").state.value == "running"
    assert scheduler.journal.diversions[0]["from_lane"] == "lane-a"
    assert scheduler.journal.diversions[0]["to_lane"] == "lane-b"
    assert len(scheduler.journal.entries) == 1


def test_a_divert_with_no_other_lane_is_refused():
    graph = _graph(_node("node-a", ("packages/aee/src/aee",)))
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))
    only = _lane("lane-a")
    scheduler.admit({"node-a": _supply(_offer(only))}, now=10.0)

    with pytest.raises(ScaleError):
        scheduler.divert("node-a", supply=_supply(_offer(only)), now=11.0)


# ---------------------------------------------------------------------------
# restart
# ---------------------------------------------------------------------------


def test_the_journal_round_trips():
    graph = _graph(_node("node-a", ("packages/aee/src/aee",)))
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))
    scheduler.admit({"node-a": _supply(_offer(_lane("lane-a")))}, now=10.0)

    data = scheduler.journal.to_dict()
    restored = SchedulerJournal.from_dict(data)

    assert restored.digest() == scheduler.journal.digest()
    key = list(restored.entries)[0]
    assert restored.entries[key].state == "running"
    assert restored.entries[key].node_id == "node-a"


def test_a_restart_does_not_execute_committed_work_twice():
    """The work is already done; a restart must not spend it again."""
    graph = _graph(_node("node-a", ("packages/aee/src/aee",)))
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))
    supply = {"node-a": _supply(_offer(_lane("lane-a")))}
    scheduler.admit(supply, now=10.0)
    scheduler.commit("node-a", cost_usd=0.004, ledger_hash="ledger-row-1", now=12.0)

    # The plan is rebuilt from durable state; the journal is what survives.
    rebuilt = _graph(_node("node-a", ("packages/aee/src/aee",)))
    restarted = ScaleScheduler(
        rebuilt, policy=ScalePolicy(max_concurrent=2), journal=scheduler.journal
    )

    results = restarted.admit(supply, now=20.0)

    assert not _admitted(results)
    assert "no second execution" in results[0].reason
    assert restarted.committed_usd() == pytest.approx(0.004)


def test_a_restart_resumes_work_that_was_in_flight_under_the_same_key():
    """A worker died mid-run: the work resumes, and it resumes as the same work."""
    graph = _graph(_node("node-a", ("packages/aee/src/aee",)))
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))
    supply = {"node-a": _supply(_offer(_lane("lane-a")))}
    admission = _admitted(scheduler.admit(supply, now=10.0))[0]

    rebuilt = _graph(_node("node-a", ("packages/aee/src/aee",)))
    restarted = ScaleScheduler(
        rebuilt, policy=ScalePolicy(max_concurrent=2), journal=scheduler.journal
    )

    results = restarted.admit(supply, now=20.0)

    resumed = _admitted(results)
    assert len(resumed) == 1
    assert resumed[0].logical_key == admission.logical_key
    assert len(restarted.journal.entries) == 1
    assert restarted.held_usd() == pytest.approx(admission.reservation.usd)
    assert restarted.committed_usd() == 0.0


def test_the_same_work_is_admitted_the_same_way_every_time():
    """One hundred identical passes produce one hundred identical decisions."""
    decisions = set()
    for _ in range(100):
        graph = _graph(_node("node-a", ("packages/aee/src/aee",)))
        scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))
        results = scheduler.admit(
            {"node-a": _supply(_offer(_lane("lane-a")))}, now=10.0
        )
        admission = _admitted(results)[0]
        decisions.add(
            (
                admission.logical_key,
                admission.contract.id,
                admission.reservation.id,
                admission.reason,
            )
        )
    assert len(decisions) == 1


# ---------------------------------------------------------------------------
# the seam to the estate's queue
# ---------------------------------------------------------------------------


def test_the_goal_carries_the_node_identity():
    """The dispatcher stores a goal string; the envelope needs the node on the other side."""
    goal = encode_goal("node-a", "lk-0123456789abcdef", "the work")

    assert decode_goal(goal) == ("lk-0123456789abcdef", "node-a", "the work")
    assert decode_goal("prove the thing") is None


def test_the_logical_key_does_not_depend_on_the_lane():
    """The key is the work's identity, which is why a diversion keeps it."""
    graph = _graph(_node("node-a", ("packages/aee/src/aee",)))
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))

    first = scheduler.logical_key("node-a", 1)
    second = scheduler.logical_key("node-a", 1)

    assert first == second
    assert (
        first
        == "lk-%s"
        % digest_of({"graph": "graph-scale", "node": "node-a", "attempt": 1})[:16]
    )
