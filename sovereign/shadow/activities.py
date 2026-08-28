"""Activities behind sovereign/shadow/workflow.py. Every side effect of a
branch run -- git, the budget row, the DAG, the receipt chain -- lives
here, never in the workflow, so replay stays deterministic. All of them
are `async def` and push blocking I/O through asyncio.to_thread, for the
reason sovereign/engine/activities.py records (a blocking call here
stalls every workflow task on the worker).

Each branch runs in its own git worktree under branch.worktree_dir, so
three children committing at once never fight over one index. The
branches themselves are ordinary refs in the repository; the worktrees
are removed after the merge and the refs stay (spec 3.2: losers are
archived, never deleted).
"""
from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Any

from temporalio import activity

from sovereign import config
from sovereign.engine import budget
from sovereign.engine import dag
from sovereign.engine import receipts as receipts_mod
from sovereign.engine import runners
from sovereign.shadow import config_keys as ck


def _git(repo: str | Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=int(ck.get("branch.git_timeout_s")),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def worktree_dir(parent_id: str, branch: str) -> Path:
    base = ck.get("branch.worktree_dir")
    root = Path(base) if base else config.SOVEREIGN_HOME / "branches"
    return root / parent_id / branch


def _fork(inp: dict[str, Any]) -> dict[str, Any]:
    repo = inp.get("repo")
    branches: list[str] = list(inp["branches"])
    fork_commit = ""
    if repo:
        fork_commit = _git(repo, "rev-parse", "HEAD")
        for branch in branches:
            _git(repo, "branch", "-f", branch, fork_commit)
            wt = worktree_dir(inp["parent_id"], branch)
            if wt.exists():
                shutil.rmtree(wt)
            wt.parent.mkdir(parents=True, exist_ok=True)
            _git(repo, "worktree", "add", "-f", str(wt), branch)
    head = dag.read_head(dag.main_head_name())
    parent_hash = str(head["root"]) if head and head.get("root") else dag.GENESIS
    fork_hash, _body = dag.write_node(
        {"fork": inp["parent_id"], "branches": branches, "commit": fork_commit},
        parent=parent_hash,
        timestamp=int(inp["timestamp"]),
        budget_remaining=int(inp.get("budget", 0)),
    )
    return {"fork_commit": fork_commit, "fork_hash": fork_hash, "branches": branches}


@activity.defn
async def branch_fork(inp: dict[str, Any]) -> dict[str, Any]:
    return await asyncio.to_thread(_fork, inp)


def _commit_marker(wt: Path, branch: str, task: str, step: int, output: str) -> str:
    marker = wt / str(ck.get("branch.marker_filename"))
    marker.write_text(f"# {branch}\n\ntask: {task}\nstep: {step}\n\n{output}\n")
    _git(wt, "add", "--", marker.name)
    _git(wt, "commit", "-qm", f"{branch}: step {step}")
    return _git(wt, "rev-parse", "HEAD")


@activity.defn
async def branch_step(inp: dict[str, Any]) -> dict[str, Any]:
    repo = inp.get("repo")
    wt = worktree_dir(inp["parent_id"], inp["branch"]) if repo else None
    result = await runners.run(inp["runner"], inp["task"], str(wt) if wt else None, int(inp["step"]), [])
    result = dict(result)
    result["commit"] = None
    if wt is not None:
        result["commit"] = await asyncio.to_thread(
            _commit_marker, wt, inp["branch"], inp["task"], int(inp["step"]), str(result.get("output", ""))
        )
    return result


@activity.defn
async def branch_budget(inp: dict[str, Any]) -> dict[str, Any]:
    """The child's own row in the budget table (crew#213). Allocation is
    idempotent and spend is compare-and-swap, both in engine/budget.py."""
    op = inp["op"]
    session_id = inp["session_id"]
    tokens = int(inp.get("tokens", 0))
    if op == "allocate":
        result = await asyncio.to_thread(budget.allocate, session_id, tokens)
    elif op == "read":
        result = await asyncio.to_thread(budget.read, session_id)
    else:
        result = await asyncio.to_thread(budget.spend, session_id, tokens)
    return budget.as_dict(result)


@activity.defn
async def branch_receipt(record: dict[str, Any]) -> dict[str, Any]:
    return await asyncio.to_thread(receipts_mod.append, dict(record))


def pick_winner(children: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Deterministic grader (spec 3.2 step 4). The criterion is the one
    the estate can measure today: among the branches that finished, the
    one that spent the fewest tokens, first branch on a tie. A branch that
    halted on its cap, stopped or failed never wins."""
    done = [c for c in children if c.get("status") == "done"]
    if not done:
        return None
    return min(done, key=lambda c: (int(c.get("tokens", 0)), str(c.get("branch", ""))))


def _merge(inp: dict[str, Any]) -> dict[str, Any]:
    repo = inp.get("repo")
    children: list[dict[str, Any]] = list(inp["children"])
    winner = pick_winner(children)
    if winner is None:
        return {"ok": False, "reason": "no branch finished", "winner": None}
    main = str(ck.get("branch.main_branch"))
    merged_commit = str(winner.get("commit") or "")
    if repo:
        for child in children:
            wt = worktree_dir(inp["parent_id"], str(child.get("branch", "")))
            if wt.exists():
                _git(repo, "worktree", "remove", "--force", str(wt))
        _git(repo, "checkout", "-q", main)
        _git(repo, "merge", "--ff-only", str(winner["branch"]))
        merged_commit = _git(repo, "rev-parse", "HEAD")
    losers = [c for c in children if c is not winner]
    savings = max((int(c.get("tokens", 0)) for c in losers), default=0) - int(winner.get("tokens", 0))
    node_hash, _body = dag.write_node(
        {"merge": inp["parent_id"], "winner": winner["branch"], "commit": merged_commit,
         "losers": [c.get("branch") for c in losers]},
        parent=str(inp.get("fork_hash") or dag.GENESIS),
        timestamp=int(inp["timestamp"]),
    )
    dag.write_head(dag.main_head_name(), node_hash)
    short = merged_commit[: int(ck.get("branch.commit_hash_len"))] if merged_commit else node_hash[: int(ck.get("branch.commit_hash_len"))]
    line = str(ck.get("branch.merge_line_format")).format(winner=winner["branch"], hash=short, savings=savings)
    receipt = receipts_mod.append(
        {
            "session_id": inp["parent_id"],
            "kind": str(ck.get("branch.merge_receipt_kind")),
            "by": "engine",
            "text": line,
            "step": 0,
            "status": "done",
            "winner": winner["branch"],
            "commit": merged_commit or None,
            "node": node_hash,
            "parent_hash": inp.get("fork_hash"),
            "losers": [c.get("branch") for c in losers],
            "savings": savings,
        }
    )
    return {"ok": True, "winner": winner["branch"], "commit": merged_commit, "node": node_hash,
            "losers": [c.get("branch") for c in losers], "savings": savings, "receipt": receipt, "text": line}


@activity.defn
async def branch_merge(inp: dict[str, Any]) -> dict[str, Any]:
    return await asyncio.to_thread(_merge, inp)


ACTIVITIES = [branch_fork, branch_step, branch_budget, branch_receipt, branch_merge]
