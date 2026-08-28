"""Fan one prompt out to three models through the LiteLLM proxy, and count
the votes (cp30, spec v1.0 4.2).

Three models, not three vendors' SDKs. `llm/config.yaml` already routes
minimax / deepseek / gemini / openrouter / ollama behind one OpenAI-shaped
endpoint with its own fallback chains, spend tracking and a $5/day cap, and
sovereign/engine/runners.py already speaks to it. LAW 43: the rejected
alternative was three provider clients here, which would have duplicated
the routing, lost the shared budget wall, and made "swap a model" a code
change instead of a config line.

Two rules do the work, and they are separate on purpose:

  quorum   -- 2 of 3 must propose the SAME normalized tool call.
  deadline -- a vote that arrives after consensus.timeout_s is discarded
              before quorum is counted, not after. Late votes therefore
              cannot rescue a failing quorum, which is the whole point:
              spec 4.2 says partial quorum on a destructive op is a hard
              fail, never a retry.

Normalization is what makes two votes comparable. Models wrap commands in
code fences, prefix a shell prompt, and pad whitespace; none of that
changes the command. Nothing else is touched -- case is significant in a
shell, so it is left alone.
"""
from __future__ import annotations

import asyncio
import re
import time
from typing import Any

import httpx

from sovereign import config
from sovereign.consensus import config_keys as ck

_FENCE_RE = re.compile(r"^```[a-zA-Z0-9_-]*\s*|\s*```$")
_PROMPT_RE = re.compile(r"^[$#>]\s+")
_WS_RE = re.compile(r"\s+")
_SPACE = " "
_EMPTY = ""


def normalize_tool_call(raw: str | None) -> str:
    """The canonical form two votes are compared in."""
    if not raw:
        return _EMPTY
    text = raw.strip()
    for line in text.splitlines():
        line = _FENCE_RE.sub(_EMPTY, line).strip()
        if not line:
            continue
        line = _PROMPT_RE.sub(_EMPTY, line).strip()
        if line:
            return _WS_RE.sub(_SPACE, line)
    return _EMPTY


def is_destructive(op: str) -> bool:
    """Classify an op when the caller did not. Over-classifies by design --
    see the help text on consensus.destructive_markers."""
    lowered = (op or _EMPTY).lower()
    markers = [m.strip().lower() for m in str(ck.get("consensus.destructive_markers")).split(",") if m.strip()]
    return any(marker in lowered for marker in markers)


def _models(destructive: bool) -> list[str]:
    if not destructive:
        # spec 4.2: "For non-destructive ops: single model (cheapest
        # available via LiteLLM fallback chain)."
        return [str(ck.get("consensus.cheap_model"))]
    return list(config.SB_MODEL_CONSENSUS)


async def _one_vote(client: httpx.AsyncClient, model: str, op: str, index: int) -> dict[str, Any]:
    """One model's proposal. Never raises: a model that errors is a vote
    that did not arrive, which is exactly how a timeout is treated, and a
    quorum that cannot be reached must fail on the quorum rule rather than
    on an exception escaping from one provider."""
    started = time.monotonic()
    headers = {"Authorization": f"Bearer {config.LITELLM_API_KEY}"} if config.LITELLM_API_KEY else {}
    body = {
        "model": model,
        "temperature": float(ck.get("consensus.temperature")),
        "max_tokens": int(ck.get("consensus.max_tokens")),
        "messages": [
            {"role": "system", "content": str(ck.get("consensus.system_prompt"))},
            {"role": "user", "content": op},
        ],
    }
    url = str(config.LITELLM_BASE_URL) + config.LITELLM_CHAT_COMPLETIONS_PATH
    vote: dict[str, Any] = {"model": model, "index": index, "proposal": _EMPTY, "error": None}
    try:
        resp = await client.post(url, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices") or [{}]
        vote["proposal"] = normalize_tool_call((choices[0].get("message") or {}).get("content"))
    except Exception as exc:
        vote["error"] = str(exc)
    vote["elapsed_s"] = time.monotonic() - started
    return vote


async def collect(op: str, destructive: bool, deadline_s: float | None = None) -> list[dict[str, Any]]:
    """Every vote, each tagged `stale` if it arrived past the deadline.

    The deadline is enforced here rather than left to httpx's own timeout,
    because "the proxy answered in 29.9s and the fan-out started 5s ago"
    and "the proxy answered in 31s" have to be told apart -- one is a
    counted vote and the other is discarded."""
    deadline_s = deadline_s if deadline_s is not None else float(config.get("consensus.timeout_s").value)
    models = _models(destructive)
    if not config.LITELLM_BASE_URL:
        return [
            {"model": m, "index": i, "proposal": _EMPTY, "stale": False,
             "error": "LITELLM_BASE_URL not configured", "elapsed_s": 0.0}
            for i, m in enumerate(models)
        ]
    started = time.monotonic()
    timeout = float(ck.get("consensus.request_timeout_s"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        tasks = [asyncio.create_task(_one_vote(client, m, op, i)) for i, m in enumerate(models)]
        done, pending = await asyncio.wait(tasks, timeout=deadline_s)
        for task in pending:
            task.cancel()
        votes = [t.result() for t in tasks if t in done]
        for task, model, index in zip(tasks, models, range(len(models))):
            if task in pending:
                votes.append({
                    "model": model, "index": index, "proposal": _EMPTY, "stale": True,
                    "error": "no answer before the consensus deadline",
                    "elapsed_s": time.monotonic() - started,
                })
    for vote in votes:
        vote.setdefault("stale", float(vote.get("elapsed_s", 0)) > deadline_s)
    return sorted(votes, key=lambda v: int(v["index"]))


def tally(votes: list[dict[str, Any]], quorum: str | None = None) -> dict[str, Any]:
    """Count the fresh, non-erroring votes and apply the quorum rule.

    Returns {"agreed", "proposal", "count", "needed", "of", "fresh",
    "stale"}. A stale or errored vote is not counted for anything -- it is
    not evidence of agreement and it is not evidence of disagreement."""
    quorum = quorum or str(config.get("consensus.quorum").value)
    needed_s, _, of_s = quorum.partition(str(ck.get("consensus.quorum_separator")))
    needed, of = int(needed_s), int(of_s)
    fresh = [v for v in votes if not v.get("stale") and not v.get("error") and v.get("proposal")]
    counts: dict[str, int] = {}
    for vote in fresh:
        proposal = str(vote["proposal"])
        counts[proposal] = counts.get(proposal, 0) + 1
    best_proposal, best_count = _EMPTY, 0
    for proposal, count in sorted(counts.items()):
        if count > best_count:
            best_proposal, best_count = proposal, count
    return {
        "agreed": best_count >= needed,
        "proposal": best_proposal if best_count >= needed else _EMPTY,
        "count": best_count,
        "needed": needed,
        "of": of,
        "fresh": len(fresh),
        "stale": sum(1 for v in votes if v.get("stale")),
    }
