"""Self-termination (R32, spec v1.0 section 5).

Four conditions, each with a threshold that was already a config key or is
one now. Before this module `blind.halt_after_min` sat in config.py and
nothing read it: the estate had a configured tolerance for blind execution
and no code that could act on it.

  confidence     < terminate.min_confidence for
                   terminate.low_confidence_steps consecutive steps -> soft halt
  latency        > terminate.latency_max_s (baseline terminate.latency_baseline_s)
                   -> retry once via the fallback chain, then halt
  blind          Langfuse unreachable for more than blind.halt_after_min
                   minutes -> halt non-critical work
  alert volume   > alerts.digest_over_per_hour -> compress into a signed
                   digest and escalate, rather than emit the flood

`evaluate()` is a pure function of the signals handed to it and the config.
It takes no clock of its own beyond `now`, opens no socket and writes
nothing, so it can be tested as a property over many inputs instead of by
standing up Langfuse and waiting five minutes.

ACTIONS is ordered by severity, and `evaluate` returns the most severe
action any condition asks for -- not the first one it happens to check.
Two conditions firing at once must never produce the milder answer.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from sovereign import config
from sovereign.engine import config_keys as ck

# Least to most severe.
ACTIONS = ("continue", "digest", "retry_fallback", "soft_halt", "halt")

REASON_CONFIDENCE = "confidence"
REASON_LATENCY = "latency"
REASON_BLIND = "blind"
REASON_ALERTS = "alert_volume"

SECONDS_PER_MINUTE = int(ck.get("time.seconds_per_minute"))
SECONDS_PER_HOUR = SECONDS_PER_MINUTE * int(ck.get("time.minutes_per_hour"))


@dataclass(frozen=True)
class Signals:
    """What the caller observed. Every field has a default that means "no
    evidence of a problem", so a caller that can only measure one of the
    four is not forced to fabricate the other three."""

    low_confidence_streak: int = 0
    last_latency_s: float = 0.0
    latency_retries_used: int = 0
    langfuse_blind_s: float = 0.0
    alerts_last_hour: int = 0


def _severity(action: str) -> int:
    return ACTIONS.index(action)


def evaluate(signals: Signals) -> dict[str, Any]:
    """Returns {"action", "reasons", "thresholds"}. `action` is the most
    severe of everything that fired; `reasons` lists every condition that
    fired, each with the observed value and the threshold it crossed, so a
    receipt records why and not just what."""
    min_confidence_steps = int(ck.get("terminate.low_confidence_steps"))
    latency_max_s = float(ck.get("terminate.latency_max_s"))
    latency_retries = int(ck.get("terminate.latency_retries"))
    blind_halt_s = float(config.get("blind.halt_after_min").value) * SECONDS_PER_MINUTE
    alerts_max = int(config.get("alerts.digest_over_per_hour").value)

    reasons: list[dict[str, Any]] = []
    action = ACTIONS[0]

    def fire(candidate: str, reason: str, observed: Any, threshold: Any) -> None:
        nonlocal action
        reasons.append({"reason": reason, "observed": observed, "threshold": threshold})
        if _severity(candidate) > _severity(action):
            action = candidate

    if signals.low_confidence_streak >= min_confidence_steps:
        fire("soft_halt", REASON_CONFIDENCE, signals.low_confidence_streak, min_confidence_steps)

    if signals.last_latency_s > latency_max_s:
        # Retry once via the fallback chain, then halt -- the retry is
        # spent before the halt, never instead of it.
        candidate = "retry_fallback" if signals.latency_retries_used < latency_retries else "halt"
        fire(candidate, REASON_LATENCY, signals.last_latency_s, latency_max_s)

    if signals.langfuse_blind_s > blind_halt_s:
        fire("halt", REASON_BLIND, signals.langfuse_blind_s, blind_halt_s)

    if signals.alerts_last_hour > alerts_max:
        fire("digest", REASON_ALERTS, signals.alerts_last_hour, alerts_max)

    return {
        "action": action,
        "reasons": reasons,
        "thresholds": {
            "min_confidence": float(ck.get("terminate.min_confidence")),
            "low_confidence_steps": min_confidence_steps,
            "latency_baseline_s": float(ck.get("terminate.latency_baseline_s")),
            "latency_max_s": latency_max_s,
            "latency_retries": latency_retries,
            "blind_halt_s": blind_halt_s,
            "alerts_per_hour": alerts_max,
        },
    }


def is_low_confidence(confidence: float) -> bool:
    return float(confidence) < float(ck.get("terminate.min_confidence"))


def langfuse_blind_seconds(now: float | None = None) -> float:
    """How long Langfuse has been unreachable, from the marker
    sovereign/engine/tracing.py writes on every successful flush. No
    marker at all means nothing has ever succeeded, which is not the same
    as "fine" -- it returns 0.0 only when tracing was never configured,
    since halting every agent on a laptop with no Langfuse would be a
    guard refusing correct work (LAW 38)."""
    from sovereign.engine import tracing

    if not tracing.configured():
        return 0.0
    marker = tracing.last_ok_path()
    if not marker.exists():
        return 0.0
    try:
        data = json.loads(marker.read_text())
    except (OSError, json.JSONDecodeError):
        return 0.0
    last_ok = float(data.get("ts") or 0)
    if not last_ok:
        return 0.0
    return max(0.0, (now if now is not None else time.time()) - last_ok)


def alerts_in_last_hour(now: float | None = None) -> int:
    """Count of alert-inbox lines within the last hour."""
    path = config.ESTATE_ALERT_INBOX
    if not path.exists():
        return 0
    cutoff = (now if now is not None else time.time()) - SECONDS_PER_HOUR
    count = 0
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if float(row.get("ts") or 0) >= cutoff:
            count += 1
    return count


STOPPING_ACTIONS = ("soft_halt", "halt")


def enforce(verdict: dict[str, Any], *, by: str = "kernel") -> dict[str, Any]:
    """Act on evaluate()'s verdict (spec section 5, crew#284 CP6).

    halt / soft_halt: signal `stop` to every non-critical session whose status
    is running, asking or waiting. A session started with `--critical` is
    skipped and listed under "kept" so the receipt says what survived.
    digest: build the signed digest and post it once instead of the flood.
    continue / retry_fallback: nothing to do here; the runner retries.
    Returns what was done so the receipt records the action, not just the
    verdict."""
    import asyncio

    action = verdict["action"]
    reason = ",".join(r["reason"] for r in verdict.get("reasons", []))
    if action in STOPPING_ACTIONS:
        from sovereign.engine import client as engine_client

        async def _stop_all() -> list[str]:
            stopped: list[str] = []
            kept: list[str] = []
            for row in await engine_client.list_sessions():
                if row.get("status") not in ("running", "asking", "waiting"):
                    continue
                if row.get("critical"):
                    kept.append(row["session_id"])
                    continue
                await engine_client.signal(row["session_id"], "stop", by, f"self-termination:{reason}")
                stopped.append(row["session_id"])
            return stopped, kept

        stopped, kept = asyncio.run(_stop_all())
        return {"action": action, "stopped": stopped, "kept": kept}
    if action == "digest":
        from sovereign.presence import chat, digest as digest_mod

        d = digest_mod.build()
        chat.send(chat.TelegramSink(), d)
        return {"action": action, "digest_lines": len(d.lines)}
    return {"action": action}
