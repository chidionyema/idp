"""Runner registry (LAW 34 / cp6): the only place in the engine where a
vendor CLI or model name appears. workflow.py and client.py never import a
vendor; they call `runners.run(name, ...)` by string.

Each runner is `async def(task, repo, step, steer) -> {"output": str,
"done": bool, "ask": str | None, "tokens": int}`, runs inside an activity,
and must call `activity.heartbeat()` at least once a second while doing
real work so a long step (sleep, a slow agent CLI) can be cancelled
promptly. `tokens` is spent against the session's budget (cp18); a runner
with no real usage estimates len(output) // 4.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, Awaitable, Callable

import httpx
from temporalio import activity

from sovereign import config

RunnerFn = Callable[
    [str, "str | None", int, list, "str | None"], Awaitable[dict[str, Any]]
]


def _estimate_tokens(output: str) -> int:
    return max(len(output) // config.RUNNER_TOKEN_ESTIMATE_DIVISOR, 0)


async def _echo(
    task: str,
    repo: str | None,
    step: int,
    steer: list[str],
    session_id: str | None = None,
) -> dict[str, Any]:
    activity.heartbeat()
    suffix = f" (steer: {'; '.join(steer)})" if steer else ""
    output = task + suffix
    return {
        "output": output,
        "done": True,
        "ask": None,
        "tokens": _estimate_tokens(output),
    }


async def _sleep(
    task: str,
    repo: str | None,
    step: int,
    steer: list[str],
    session_id: str | None = None,
) -> dict[str, Any]:
    m = re.search(r"(\d+)", task)
    seconds = int(m.group(1)) if m else 1
    for _ in range(seconds):
        activity.heartbeat()
        await asyncio.sleep(1)
    output = f"slept {seconds}s"
    return {
        "output": output,
        "done": True,
        "ask": None,
        "tokens": _estimate_tokens(output),
    }


async def _ask(
    task: str,
    repo: str | None,
    step: int,
    steer: list[str],
    session_id: str | None = None,
) -> dict[str, Any]:
    activity.heartbeat()
    if step <= 1:
        prefix = config.RUNNER_ASK_PREFIX + config.RUNNER_ASK_PREFIX_SEP
        needs = (
            task.split(config.RUNNER_ASK_PREFIX_SEP, 1)[1].strip()
            if task.lower().startswith(prefix)
            else task
        )
        output = f"waiting on: {needs}"
        return {
            "output": output,
            "done": False,
            "ask": needs,
            "tokens": _estimate_tokens(output),
        }
    output = "approved, continuing"
    return {
        "output": output,
        "done": True,
        "ask": None,
        "tokens": _estimate_tokens(output),
    }


async def _burn(
    task: str,
    repo: str | None,
    step: int,
    steer: list[str],
    session_id: str | None = None,
) -> dict[str, Any]:
    activity.heartbeat()
    output = f"burn step {step}"
    return {
        "output": output,
        "done": False,
        "ask": None,
        "tokens": config.BURN_TOKENS_PER_STEP,
    }


async def _llm(
    task: str,
    repo: str | None,
    step: int,
    steer: list[str],
    session_id: str | None = None,
) -> dict[str, Any]:
    activity.heartbeat()
    if not config.LITELLM_BASE_URL:
        output = "LITELLM_BASE_URL not configured"
        return {
            "output": output,
            "done": True,
            "ask": None,
            "tokens": _estimate_tokens(output),
        }
    headers = (
        {"Authorization": f"Bearer {config.LITELLM_API_KEY}"}
        if config.LITELLM_API_KEY
        else {}
    )
    body = {"model": config.SB_MODEL, "messages": [{"role": "user", "content": task}]}
    if session_id:
        # Tags the spend row LiteLLM logs for this call so FleetView's spend reader
        # (backstage/plugins/fleetview-backend/src/spend.py) can attribute it back to
        # this session -- the proxy needs no change, it already stores metadata verbatim
        # (docs/tickets/2026-09-12-estate-twin.md, "Phase 3 -- AI emitter").
        body["metadata"] = {"session_id": session_id, "runtime": "sovereign"}
    url = config.LITELLM_BASE_URL + config.LITELLM_CHAT_COMPLETIONS_PATH
    async with httpx.AsyncClient(timeout=config.RUNNER_LLM_TIMEOUT_S) as client:
        resp = await client.post(url, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    choices = data.get("choices") or [{}]
    output = (choices[0].get("message") or {}).get("content", "")
    tokens = (data.get("usage") or {}).get("total_tokens") or _estimate_tokens(output)
    return {"output": output, "done": True, "ask": None, "tokens": int(tokens)}


REGISTRY: dict[str, RunnerFn] = {
    "echo": _echo,
    "sleep": _sleep,
    "ask": _ask,
    "burn": _burn,
    "llm": _llm,
}


async def run(
    runner: str,
    task: str,
    repo: str | None,
    step: int,
    steer: list[str],
    session_id: str | None = None,
) -> dict[str, Any]:
    fn = REGISTRY.get(runner)
    if fn is None:
        output = f"unknown runner: {runner}"
        return {"output": output, "done": True, "ask": None, "tokens": 0}
    return await fn(task, repo, step, steer, session_id)
