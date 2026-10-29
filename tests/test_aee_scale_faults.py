"""The concurrency envelope, measured against the estate's real execution substrate.

A policy that only works in a mock is a policy nobody runs. These tests drive the REAL
``platform/queue/dispatcher.py`` and the REAL ``platform/execution/worker_pool.py``: the
envelope decides what becomes a queue task, the dispatcher claims it and makes the
worktree, and the estate's own workers run it. Nothing about the queue or the pool is
mocked -- only the work itself, which is a few lines that answer the question the test
asks.

``platform/`` has no ``__init__.py`` -- it collides with the stdlib ``platform`` module the
moment anything imports it bare (idp#3564) -- so its modules are loaded by path under their
real dotted names, the same rule ``tests/test_worker_pool.py`` follows.

The faults injected here are the ones the AEE proposal names for G5: a worker that dies,
a lane that runs out of quota, a cancellation, an integration failure, the budget ceiling,
and a restart. Each one is measured, not narrated.

The suites live in the repository's root ``tests/`` tree rather than in ``packages/aee/tests/``
because that is where CI collects them: ``bin/idp-tests-for`` selects a test by grepping
``tests/`` and ``sovereign/tests/`` for the changed paths, and no workflow collects
``packages/``.
"""

from __future__ import annotations

import asyncio
import importlib.util
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = REPO_ROOT / "packages" / "aee" / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def _load(rel: str, dotted: str):
    """Load a module of platform/ by path, under its real dotted name."""
    if dotted in sys.modules:
        return sys.modules[dotted]
    spec = importlib.util.spec_from_file_location(dotted, str(REPO_ROOT / rel))
    module = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = module
    spec.loader.exec_module(module)
    return module


_queue_package = _load("platform/queue/__init__.py", "platform.queue")
dispatcher = _queue_package.load_dispatcher()
worker_pool = _load(
    "platform/execution/worker_pool.py", "platform.execution.worker_pool"
)
WorkerPool = worker_pool.WorkerPool

from aee.allocation import SupplyOffer  # noqa: E402
from aee.contracts import (  # noqa: E402
    AcceptanceCriterion,
    IntelligenceLane,
    Objective,
    VerificationLevel,
    Verdict,
    VerificationReceipt,
    WorkNode,
)
from aee.graph import WorkGraph  # noqa: E402
from aee.scale import (  # noqa: E402
    AdmissionOutcome,
    NodeSupply,
    ScalePolicy,
    ScaleScheduler,
    decode_goal,
    encode_goal,
)


# ---------------------------------------------------------------------------
# the estate's own fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def repo(tmp_path):
    """A real git repository with one commit in it."""
    path = tmp_path / "repo"
    path.mkdir()
    for args in (
        ["init", "--quiet"],
        ["config", "user.email", "agent@estate"],
        ["config", "user.name", "agent"],
    ):
        subprocess.run(["git"] + args, cwd=str(path), check=True, capture_output=True)
    (path / "README.md").write_text("the estate\n")
    subprocess.run(
        ["git", "add", "README.md"], cwd=str(path), check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "--quiet", "-m", "the estate"],
        cwd=str(path),
        check=True,
        capture_output=True,
    )
    return path


@pytest.fixture
def queue(tmp_path, repo, monkeypatch):
    """A queue in a temp directory, with the environment the dispatcher reads."""
    monkeypatch.setenv("QUEUE_DB_PATH", str(tmp_path / "state" / "queue.db"))
    monkeypatch.setenv("WORKTREE_BASE", str(tmp_path / "wt"))
    monkeypatch.setenv("IDP_ROOT", str(repo))
    monkeypatch.setenv("WORKTREE_ARCHIVE_ROOT", str(tmp_path / "quarantine"))
    dispatcher.init_db()
    return dispatcher


# ---------------------------------------------------------------------------
# the envelope in front of the estate's pool
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


def _node(
    node_id: str, scope: tuple[str, ...], depends_on: tuple[str, ...] = ()
) -> WorkNode:
    return WorkNode(
        id=node_id,
        title="the %s work" % node_id,
        scope=scope,
        depends_on=depends_on,
        owner="agent-1",
    )


def _lane(
    lane_id: str, *, deterministic: bool = False, cost: float = 0.001
) -> IntelligenceLane:
    return IntelligenceLane(
        id=lane_id,
        provider="estate",
        model="test-model",
        lane_type="tool" if deterministic else "model",
        deterministic=deterministic,
        cost_usd_per_1k=cost,
        quality_prior=0.9,
        availability=1.0,
        latency_p95_ms=100,
    )


def _offer(lane: IntelligenceLane, *, units: int = 1) -> SupplyOffer:
    return SupplyOffer(lane=lane, capabilities=("summarise",), units_available=units)


def _supply(*offers: SupplyOffer) -> NodeSupply:
    return NodeSupply(
        offers=offers,
        estimated_tokens=1000,
        required_capabilities=("summarise",),
        budget_usd=1.0,
    )


class _Estate:
    """The envelope, the queue and the ledger of what actually happened."""

    def __init__(self, graph, scheduler, queue, supply):
        self.graph = graph
        self.scheduler = scheduler
        self.queue = queue
        self.supply = supply
        self.admissions = []
        self.entered = {}
        self.left = {}
        self.errors = {}

    def pump(self, now: float):
        """Admit what may start, and make it a task on the estate's real queue."""
        results = self.scheduler.admit(self.supply, now=now)
        self.admissions.extend(results)
        for admission in results:
            if admission.outcome is AdmissionOutcome.ADMITTED:
                self.queue.push_task(
                    encode_goal(
                        admission.node_id, admission.logical_key, admission.node_id
                    )
                )
        return results

    def admitted(self, node_id: str) -> bool:
        return any(
            r.node_id == node_id and r.outcome is AdmissionOutcome.ADMITTED
            for r in self.admissions
        )

    def finish(
        self, node_id: str, *, now: float, cost: float = 0.004, verdict=Verdict.PASS
    ):
        """The work is done: the spend is committed, the evidence is recorded."""
        if self.graph.node(node_id).state.value == "cancelled":
            return None
        receipt = self.scheduler.commit(
            node_id, cost_usd=cost, ledger_hash="ledger-row-%s" % node_id, now=now
        )
        verification = VerificationReceipt(
            id="ver-%s" % node_id,
            node_id=node_id,
            attempt_id=receipt.attempt_id,
            level=VerificationLevel.OPERATION,
            verdict=verdict,
            evidence="nsvee-report:%s" % node_id,
            verifier="verifier-1",
            at=now,
            contract_id=receipt.contract_id,
        )
        self.graph.record_verification(verification)
        # The acceptance is the graph's own: a failing verdict is refused here, and the
        # refusal is the measurement the integration-failure scenario is about.
        self.graph.complete(node_id, verification_ids=[verification.id])
        return receipt


def _orchestrator(estate: _Estate, body=None):
    """The estate's worker calling the envelope."""

    async def orchestrator(goal, worktree=None):
        decoded = decode_goal(goal)
        assert decoded is not None, (
            "the queue carried a goal the envelope cannot read: %r" % goal
        )
        _, node_id, _ = decoded
        estate.entered[node_id] = time.monotonic()
        try:
            if body is not None:
                await body(node_id)
        finally:
            estate.left[node_id] = time.monotonic()

    return orchestrator


def _run_pool(pool, orchestrator, until, timeout: float = 40.0) -> None:
    """Run the estate's pool until the work is done, or the clock says otherwise."""

    async def scenario():
        pool.boot()
        runner = asyncio.create_task(pool.run_workers(orchestrator_fn=orchestrator))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            await asyncio.sleep(0.1)
            if until():
                break
        pool.shutdown()
        await asyncio.wait_for(runner, timeout=20)

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# the faults
# ---------------------------------------------------------------------------


def test_independent_work_runs_at_the_same_time_and_dependent_work_waits(queue):
    """The envelope's first promise: independent work together, dependent work after."""
    graph = WorkGraph(_objective(), "graph-scale", owner="agent-1")
    graph.add_node(_node("node-a", ("packages/aee/src/aee",)))
    graph.add_node(_node("node-b", ("packages/aee/tests",)))
    graph.add_node(_node("node-c", ("features/assurance",), depends_on=("node-a",)))
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))
    supply = {
        node_id: _supply(_offer(_lane("lane-a")))
        for node_id in ("node-a", "node-b", "node-c")
    }
    estate = _Estate(graph, scheduler, queue, supply)
    estate.pump(10.0)

    events = {"node-a": asyncio.Event(), "node-b": asyncio.Event()}

    async def body(node_id):
        if node_id in events:
            peer = "node-b" if node_id == "node-a" else "node-a"
            events[node_id].set()
            # Both workers must be inside at the same time, or this times out.
            await asyncio.wait_for(events[peer].wait(), timeout=20)
        estate.finish(node_id, now=11.0)
        estate.pump(12.0)

    pool = WorkerPool(n_workers=2)
    _run_pool(pool, _orchestrator(estate, body), lambda: len(estate.left) == 3)

    assert set(estate.left) == {"node-a", "node-b", "node-c"}
    # node-a and node-b overlapped.
    assert estate.entered["node-b"] < estate.left["node-a"]
    assert estate.entered["node-a"] < estate.left["node-b"]
    # node-c waited for its parent.
    assert estate.entered["node-c"] > estate.left["node-a"]
    assert estate.admitted("node-c")


def test_a_worker_that_dies_gives_the_hold_back(queue):
    """A dead worker must not leave the estate's money held for nothing."""
    graph = WorkGraph(_objective(), "graph-scale", owner="agent-1")
    graph.add_node(_node("node-a", ("packages/aee/src/aee",)))
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))
    estate = _Estate(
        graph, scheduler, queue, {"node-a": _supply(_offer(_lane("lane-a")))}
    )
    estate.pump(10.0)
    admission = [
        r for r in estate.admissions if r.outcome is AdmissionOutcome.ADMITTED
    ][0]

    async def body(node_id):
        try:
            raise RuntimeError("the worker died")
        except RuntimeError as err:
            scheduler.fail(node_id, reason=str(err), now=11.0)
            raise

    pool = WorkerPool(n_workers=1)
    _run_pool(pool, _orchestrator(estate, body), lambda: bool(estate.left))

    row = queue.get_task_list()[0]
    assert row[2] == "failed", "the estate's queue did not record the death"
    assert graph.node("node-a").state.value == "failed"
    assert graph.reservations[admission.reservation.id].state.value == "released"
    assert scheduler.committed_usd() == 0.0


def test_quota_exhaustion_diverts_to_the_next_lane_without_failing_the_node(queue):
    """The lane ran out mid-run: the work moves, the node does not fail."""
    graph = WorkGraph(_objective(), "graph-scale", owner="agent-1")
    graph.add_node(_node("node-a", ("packages/aee/src/aee",)))
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))
    first = _lane("lane-a", deterministic=True)
    second = _lane("lane-b")
    both = _supply(_offer(first), _offer(second))
    estate = _Estate(graph, scheduler, queue, {"node-a": both})
    estate.pump(10.0)
    admission = [
        r for r in estate.admissions if r.outcome is AdmissionOutcome.ADMITTED
    ][0]
    assert admission.contract.lane.id == "lane-a"

    async def body(node_id):
        diverted = scheduler.divert(
            node_id,
            supply=_supply(_offer(first, units=0), _offer(second)),
            now=11.0,
        )
        assert diverted.logical_key == admission.logical_key
        estate.finish(node_id, now=12.0)

    pool = WorkerPool(n_workers=1)
    _run_pool(pool, _orchestrator(estate, body), lambda: bool(estate.left))

    assert graph.node("node-a").state.value != "failed"
    assert graph.node("node-a").state.value == "accepted"
    assert len(scheduler.journal.entries) == 1
    assert scheduler.journal.diversions[0]["from_lane"] == "lane-a"
    assert scheduler.journal.diversions[0]["to_lane"] == "lane-b"
    receipt = list(graph.economics.values())[0]
    assert receipt.contract_id == graph.node("node-a").contract_id


def test_cancelling_the_work_releases_the_hold_and_stops_the_spend(queue):
    """A cancellation gives the hold back and spends nothing more."""
    graph = WorkGraph(_objective(), "graph-scale", owner="agent-1")
    graph.add_node(_node("node-a", ("packages/aee/src/aee",)))
    graph.add_node(_node("node-b", ("packages/aee/tests",)))
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))
    supply = {
        node_id: _supply(_offer(_lane("lane-a"))) for node_id in ("node-a", "node-b")
    }
    estate = _Estate(graph, scheduler, queue, supply)
    estate.pump(10.0)
    holds = {
        r.node_id: r.reservation
        for r in estate.admissions
        if r.outcome is AdmissionOutcome.ADMITTED
    }

    async def body(node_id):
        if node_id == "node-a":
            scheduler.cancel(
                "node-b", reason="the founder changed their mind", now=11.0
            )
            await asyncio.sleep(0.2)
            estate.finish(node_id, now=12.0)
        else:
            await asyncio.sleep(0.4)

    pool = WorkerPool(n_workers=2)
    _run_pool(pool, _orchestrator(estate, body), lambda: len(estate.left) == 2)

    assert graph.node("node-b").state.value == "cancelled"
    assert graph.reservations[holds["node-b"].id].state.value == "released"
    assert scheduler.committed_usd() == pytest.approx(0.004), (
        "only the work that was not cancelled may be committed"
    )


def test_an_integration_failure_leaves_the_dependent_work_waiting(queue):
    """The parent did not pass verification, so the child never starts."""
    graph = WorkGraph(_objective(), "graph-scale", owner="agent-1")
    graph.add_node(_node("node-a", ("packages/aee/src/aee",)))
    graph.add_node(_node("node-b", ("features/assurance",), depends_on=("node-a",)))
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))
    supply = {
        node_id: _supply(_offer(_lane("lane-a"))) for node_id in ("node-a", "node-b")
    }
    estate = _Estate(graph, scheduler, queue, supply)
    estate.pump(10.0)

    async def body(node_id):
        try:
            estate.finish(node_id, now=11.0, verdict=Verdict.FAIL)
        except Exception as err:  # noqa: BLE001 -- the refusal is the measurement
            estate.errors[node_id] = err

    pool = WorkerPool(n_workers=2)
    _run_pool(pool, _orchestrator(estate, body), lambda: bool(estate.left))

    assert isinstance(estate.errors.get("node-a"), Exception)
    assert graph.node("node-a").state.value != "accepted"
    assert not estate.admitted("node-b"), "the child started without an accepted parent"
    assert "node-b" not in estate.entered


def test_the_budget_ceiling_stops_the_work_with_the_reason_recorded(queue):
    """The ceiling is a hard stop, and the reason is in the durable state."""
    graph = WorkGraph(_objective(), "graph-scale", owner="agent-1")
    graph.add_node(_node("node-a", ("packages/aee/src/aee",)))
    graph.add_node(_node("node-b", ("packages/aee/tests",)))
    scheduler = ScaleScheduler(
        graph, policy=ScalePolicy(max_concurrent=4, budget_ceiling_usd=0.0015)
    )
    supply = {
        node_id: _supply(_offer(_lane("lane-a"))) for node_id in ("node-a", "node-b")
    }
    estate = _Estate(graph, scheduler, queue, supply)
    estate.pump(10.0)

    async def body(node_id):
        estate.finish(node_id, now=11.0)

    pool = WorkerPool(n_workers=2)
    _run_pool(pool, _orchestrator(estate, body), lambda: bool(estate.left))

    assert "ceiling" in scheduler.journal.cutoff_reason
    assert estate.admitted("node-a")
    assert not estate.admitted("node-b")
    assert "node-b" not in estate.entered


def test_a_restart_resumes_the_work_without_spending_it_twice(queue):
    """The work is done; a restart must not do it again and must not pay for it again."""
    graph = WorkGraph(_objective(), "graph-scale", owner="agent-1")
    graph.add_node(_node("node-a", ("packages/aee/src/aee",)))
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))
    supply = {"node-a": _supply(_offer(_lane("lane-a")))}
    estate = _Estate(graph, scheduler, queue, supply)
    estate.pump(10.0)
    runs = []

    async def body(node_id):
        runs.append(node_id)
        estate.finish(node_id, now=11.0)

    pool = WorkerPool(n_workers=1)
    _run_pool(pool, _orchestrator(estate, body), lambda: bool(estate.left))

    assert len(runs) == 1
    spent = scheduler.committed_usd()

    # The plan is rebuilt from durable state; the journal is what survives.
    rebuilt = WorkGraph(_objective(), "graph-scale", owner="agent-1")
    rebuilt.add_node(_node("node-a", ("packages/aee/src/aee",)))
    restarted = ScaleScheduler(
        rebuilt, policy=ScalePolicy(max_concurrent=2), journal=scheduler.journal
    )
    results = restarted.admit(supply, now=20.0)

    assert not [r for r in results if r.outcome is AdmissionOutcome.ADMITTED]
    assert restarted.committed_usd() == spent
    assert len(runs) == 1, "the work was executed twice"
