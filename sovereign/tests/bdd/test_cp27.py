"""cp27 acceptance: Temporal branching -- fork silently, merge the winner, keep the losers

Owner: W5 (sovereign/shadow/workflow.py, activities.py, branching.py).

The workflows run for real on a Temporal dev server started by the
Temporal SDK's own test environment (`WorkflowEnvironment.start_local`)
from the `temporal` CLI already on this machine, with a real worker, a
real git repository, the real budget row and the real receipt chain.
The one substitution is the runner: "claude" is a vendor CLI and a true
external boundary, so the branches run the engine's `echo` runner (or
`sleep`, for the stop scenario), which is the same activity path minus
the subprocess.

Steps are synchronous; the Temporal environment lives on a background
event loop for the length of one scenario so "Given running / When stop /
Then stopped" can each submit work to the same server.
"""
from __future__ import annotations

import asyncio
import importlib
import re
import shlex
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Coroutine, Iterator, TypeVar

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from temporalio.client import WorkflowHandle
from temporalio.service import RPCError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from sovereign import config
from sovereign.engine import receipts as receipts_mod
from sovereign.shadow import activities as shadow_activities
from sovereign.shadow import branching
from sovereign.shadow import config_keys as ck
from sovereign.shadow.workflow import BranchChildWorkflow, BranchParentWorkflow

scenarios("features/sovereign-bus/cp27_temporal_branching.feature")

T = TypeVar("T")

# The runner the feature names is a vendor CLI; see the module docstring.
_RUNNER_STAND_IN = {"claude": "echo"}


class TemporalLab:
    """A dev server + worker on a background loop, driven from sync steps."""

    def __init__(self, task_queue: str) -> None:
        self.task_queue = task_queue
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()
        self.env: WorkflowEnvironment | None = None
        self.worker: Worker | None = None
        self._worker_task: asyncio.Task[None] | None = None

    def run(self, coro: Coroutine[Any, Any, T], timeout: float = 120) -> T:
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout)

    async def _start(self) -> None:
        cli = shutil.which(str(ck.get("temporal.cli_binary")))
        assert cli, "temporal CLI not on PATH"
        self.env = await WorkflowEnvironment.start_local(dev_server_existing_path=cli)
        self.worker = Worker(
            self.env.client,
            task_queue=self.task_queue,
            workflows=[BranchParentWorkflow, BranchChildWorkflow],
            activities=shadow_activities.ACTIVITIES,
        )
        self._worker_task = asyncio.ensure_future(self.worker.run())

    async def _stop(self) -> None:
        if self.worker is not None:
            await self.worker.shutdown()
        if self._worker_task is not None:
            await self._worker_task
        if self.env is not None:
            await self.env.shutdown()

    def start(self) -> None:
        self.run(self._start())

    def stop(self) -> None:
        try:
            self.run(self._stop(), timeout=60)
        finally:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join(timeout=10)

    @property
    def client(self) -> Any:
        assert self.env is not None
        return self.env.client

    def child_state(self, child_id: str) -> dict[str, Any]:
        handle: WorkflowHandle[Any, Any] = self.client.get_workflow_handle(child_id)
        return self.run(handle.query(BranchChildWorkflow.state))

    def history_activity_types(self, workflow_id: str) -> list[str]:
        async def _fetch() -> list[str]:
            handle: WorkflowHandle[Any, Any] = self.client.get_workflow_handle(workflow_id)
            history = await handle.fetch_history()
            out: list[str] = []
            for event in history.events:
                attrs = getattr(event, "activity_task_scheduled_event_attributes", None)
                if attrs is not None and attrs.activity_type.name:
                    out.append(attrs.activity_type.name)
            return out

        return self.run(_fetch())


@pytest.fixture
def lab(estate_home: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TemporalLab]:
    monkeypatch.setenv("SB_TRUST_BACKEND", "software_key")
    lab = TemporalLab(config.TEMPORAL_TASK_QUEUE)
    lab.start()
    try:
        yield lab
    finally:
        lab.stop()


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def _fork(lab: TemporalLab, repo: Path, task: str, runner: str, budget: int, count: int, context: dict[str, Any]) -> None:
    p = branching.params(task, runner=_RUNNER_STAND_IN.get(runner, runner), repo=str(repo), budget=budget, count=count)
    started = lab.run(branching.start(lab.client, p, task_queue=lab.task_queue))
    context.update({"params": p, "parent_id": p["parent_id"], "children": started["children"], "repo": repo,
                    "handle": lab.client.get_workflow_handle(p["parent_id"])})


def _finish(lab: TemporalLab, context: dict[str, Any], timeout: float = 120) -> dict[str, Any]:
    if "result" not in context:
        context["result"] = lab.run(context["handle"].result(), timeout=timeout)
    return context["result"]


# ---- scenario 1: fork, merge, keep the losers ---------------------------------


@when(parsers.parse('I run "bin/sb start --runner {runner} --repo <repo> --task {task} --branches {count:d} --json"'))
def _start_branches(lab: TemporalLab, scratch_repo: Path, runner: str, task: str, count: int, context: dict[str, Any]) -> None:
    _fork(lab, scratch_repo, shlex.split(task)[0], runner, 10_000, count, context)


@then("three child sessions run in Ghost mode")
def _three_children_ghost(lab: TemporalLab, context: dict[str, Any]) -> None:
    result = _finish(lab, context)
    assert len(context["children"]) == 3
    assert [c["status"] for c in result["children"]] == ["done", "done", "done"], result["children"]
    for child_id in context["children"]:
        types = lab.history_activity_types(child_id)
        assert types, f"{child_id} scheduled no activity"
        assert not any("notify" in t.lower() for t in types), f"{child_id} scheduled a notification: {types}"
    assert not any("notify" in t.lower() for t in lab.history_activity_types(context["parent_id"]))


@then("zero messages are sent during their run")
def _zero_messages(messages: Any) -> None:
    messages.assert_silent()


@then(parsers.parse('when all finish, exactly one receipt "{line}" is emitted'))
def _one_receipt(lab: TemporalLab, context: dict[str, Any], line: str) -> None:
    result = _finish(lab, context)
    rows = receipts_mod.read_all()
    assert len(rows) == 1, f"expected exactly one receipt, got {[r.get('kind') for r in rows]}"
    row = rows[0]
    assert row["kind"] == str(ck.get("branch.merge_receipt_kind"))
    winner = result["winner"]
    sha = _git(context["repo"], "rev-parse", str(ck.get("branch.main_branch")))
    short = sha[: int(ck.get("branch.commit_hash_len"))]
    expected_prefix = line.split("<winner>")[0]
    assert row["text"].startswith(expected_prefix), row["text"]
    assert f"main←{winner}" in row["text"]
    assert f"hash:{short}" in row["text"], (row["text"], sha)
    assert row["commit"] == sha
    assert row["parent_hash"] == result["fork_hash"] and row["parent_hash"]


@then("the two losing git branches still exist")
def _losers_exist(context: dict[str, Any]) -> None:
    result = context["result"]
    losers = result["merge"]["losers"]
    assert len(losers) == 2
    existing = set(re.sub(r"^[* ]+", "", b).strip() for b in _git(context["repo"], "branch", "--list").splitlines())
    for loser in losers:
        assert loser in existing, f"losing branch {loser} was deleted; have {existing}"
    assert result["winner"] in existing


# ---- scenario 2: stop freezes all branches ------------------------------------


@given("three branches are running")
def _branches_running(lab: TemporalLab, scratch_repo: Path, context: dict[str, Any]) -> None:
    _fork(lab, scratch_repo, "sleep 60", "sleep", 10_000, 3, context)
    deadline = time.monotonic() + 30
    states: list[dict[str, Any]] = []
    while time.monotonic() < deadline:
        try:
            states = [lab.child_state(c) for c in context["children"]]
        except RPCError:  # the parent has not forked that child yet
            states = []
        if states and all(s["status"] == "running" and s["step"] >= 1 for s in states):
            break
        time.sleep(0.2)
    else:
        pytest.fail(f"children never reached running: {states}")


@when(parsers.parse('I run "bin/sb stop <parent_id> --by {by}"'))
def _stop_parent(lab: TemporalLab, context: dict[str, Any], by: str) -> None:
    context["stop_at"] = time.monotonic()
    lab.run(context["handle"].signal(BranchParentWorkflow.stop, args=[by, "founder stop"]))


@then(parsers.parse('all three child sessions are "{status}" within {seconds:d} seconds'))
def _children_stopped(lab: TemporalLab, context: dict[str, Any], status: str, seconds: int) -> None:
    result = _finish(lab, context, timeout=seconds)
    elapsed = time.monotonic() - context["stop_at"]
    assert elapsed <= seconds, f"stop took {elapsed:.1f}s"
    assert result["status"] == "stopped"
    for child_id in context["children"]:
        assert lab.child_state(child_id)["status"] == status, child_id


@then("the receipt records the parent hash")
def _receipt_parent_hash(context: dict[str, Any]) -> None:
    result = context["result"]
    rows = [r for r in receipts_mod.read_all() if r.get("kind") == "stop"]
    assert len(rows) == 1, f"expected one stop receipt, got {len(rows)}"
    assert rows[0]["parent_hash"] == result["fork_hash"] and result["fork_hash"]
    assert rows[0]["by"] == "founder"


# ---- scenario 3 (crew#213): the 10% budget cap ---------------------------------


@given(parsers.parse("a parent session with budget {budget:d} tokens and branches costing {cost:d} tokens per step"))
def _capped_parent(lab: TemporalLab, scratch_repo: Path, monkeypatch: pytest.MonkeyPatch, budget: int, cost: int, context: dict[str, Any]) -> None:
    # burn.tokens_per_step is a module constant of sovereign.config, so the
    # env override needs the module re-resolved; the estate_home fixture
    # reloads it again on teardown.
    monkeypatch.setenv("SB_BURN_TOKENS", str(cost))
    importlib.reload(config)
    assert config.BURN_TOKENS_PER_STEP == cost
    context["parent_budget"] = budget
    _fork(lab, scratch_repo, "burn", "burn", budget, 3, context)


@when("the three branches run")
def _branches_run(lab: TemporalLab, context: dict[str, Any]) -> None:
    _finish(lab, context)


@then(parsers.parse("each child budget is {pct:d} percent of the parent budget"))
def _child_budget(context: dict[str, Any], pct: int) -> None:
    result = context["result"]
    assert int(config.get("branch.budget_pct").value) == pct
    expected = context["parent_budget"] * pct // 100
    for child in result["children"]:
        assert child["budget"] == expected, child


@then(parsers.parse('each child halts with a receipt reason "{reason}"'))
def _children_halt(context: dict[str, Any], reason: str) -> None:
    result = context["result"]
    assert [c["status"] for c in result["children"]] == ["halted"] * 3, result["children"]
    rows = [r for r in receipts_mod.read_all() if r.get("kind") == str(ck.get("branch.halt_receipt_kind"))]
    assert len(rows) == 3
    assert all(r["text"] == reason and r["budget_remaining"] == 0 for r in rows), rows
    assert set(r["session_id"] for r in rows) == set(context["children"])
    assert result["winner"] is None
