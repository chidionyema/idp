"""Voice: ask the fleet, in words, and get an answer worth speaking.

WHY THIS EXISTS. `bin/idp-voice` proved the loop but lives in a terminal, and the browser half
(`FleetVoice.tsx`) could only pattern-match commands and read back canned sentences -- `speak()`
was called with hardcoded strings and there was NO model call anywhere in the component. So the
estate had a brain with no body and a body with no brain.

This is the join. The browser sends what it heard; this asks the estate's router with the FLEET'S
LIVE STATE in the prompt and returns one or two sentences to speak.

THE ENGINE IS THE ESTATE'S ROUTER (LAW 34): one router key per identity, no vendor key on this
machine. Local inference was tried first and measured 530ms per token on a 2-physical-core Mac
under load, which made a 22-second answer; the same question through the router is 1.4s. The
router is both faster and the mandated door.

THE FLEET STATE IS READ FROM THE SAME SOURCE THE BOARD READS. Not a second query, not a cache:
`sessions.list_all_sessions()` is what `/sessions` serves, so the answer cannot describe a fleet
the reader is not looking at.

WHAT THE PROMPT FORBIDS, because a voice that overclaims is worse than a voice that is silent:
  * it may not say it has done anything it has not -- the tool list is READ-ONLY and it is told so;
  * it may not invent a session, a state or a number;
  * it must answer in speech, which means one or two sentences and no markdown.

CONFIG (LAW 46):
  LITELLM_HOST        default https://llm.mumchimp.com
  LITELLM_API_KEY     required; no key means BLIND, never a silent fallback to a local model
  VOICE_ROUTER_MODEL  default deepseek
  VOICE_TIMEOUT_S     default 20
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

# The whole instruction. Short on purpose: every token here is latency, and the rules that matter
# are the four sentences at the end. Anything longer competes with the fleet summary for the
# model's attention, which is the thing it actually needs to read.
SYSTEM = (
    "You are the estate's fleet operator. You answer questions about running agents: what each is "
    "doing, whether it is stuck, and what it has cost.\n"
    "\n"
    "You are speaking aloud. Answer in ONE or TWO short sentences, plain words, no markdown, no "
    "lists, no code. Say the number when a number matters.\n"
    "\n"
    "You have NO ability to act. You cannot stop, steer or change anything, and you must never "
    "say that you have. If asked to act, say what you would do and that it needs confirmation.\n"
    "\n"
    "Use ONLY the fleet summary below. Never invent a session, a state or a number. If the summary "
    "does not answer the question, say so plainly."
)


def router_host() -> str:
    return os.environ.get("LITELLM_HOST", "https://llm.mumchimp.com").rstrip("/")


def router_key() -> str:
    return os.environ.get("LITELLM_API_KEY", "").strip()


def router_model() -> str:
    return os.environ.get("VOICE_ROUTER_MODEL", "deepseek")


def _timeout() -> float:
    return float(os.environ.get("VOICE_TIMEOUT_S", "20"))


def fleet_summary(sessions: list[dict[str, Any]], limit: int = 24) -> str:
    """The fleet, in the fewest words that still let an answer be true.

    Counts by activity first, because "how many are stuck" is the question a person actually asks
    and it must be answerable without counting rows. Then the sessions themselves, capped: a
    prompt that grows with the fleet would grow the latency with it, and 200 lines of session
    detail makes the model slower and less accurate at the same time.

    A session with no task is described by what it IS (runtime, state, events), never by a
    fabricated task name.
    """
    counts: dict[str, int] = {}
    for s in sessions:
        a = s.get("activity") or "unknown"
        counts[a] = counts.get(a, 0) + 1

    stuck = counts.get("stuck", 0)
    lines = [
        f"{len(sessions)} agents total. "
        + ", ".join(f"{n} {k}" for k, n in sorted(counts.items(), key=lambda kv: -kv[1]))
        + ".",
    ]
    if stuck:
        # Leading with the thing that needs a person, because that is what the board leads with.
        lines.append(f"{stuck} need attention.")

    # The ones worth naming: stuck first, then everything else, most events first.
    ordered = sorted(
        sessions,
        key=lambda s: (s.get("activity") != "stuck", -(s.get("event_count") or 0)),
    )
    for s in ordered[:limit]:
        task = (s.get("task") or "").strip().replace("\n", " ")[:90]
        bits = [
            s.get("runtime") or "?",
            f"#{str(s.get('session_id') or '')[-6:]}",
            s.get("activity") or "unknown",
        ]
        if s.get("state") and s.get("state") != s.get("activity"):
            bits.append(f"process {s['state']}")
        if s.get("event_count") is not None:
            bits.append(f"{s['event_count']} events")
        if isinstance(s.get("spend_usd"), (int, float)):
            bits.append(f"${s['spend_usd']:.2f}")
        if s.get("repo"):
            bits.append(f"repo {s['repo']}")
        line = " ".join(bits)
        if task:
            line += f" — {task}"
        lines.append(line)
    return "\n".join(lines)


def ask(question: str, sessions: list[dict[str, Any]]) -> tuple[dict[str, Any], int]:
    """Ask the fleet. Returns (body, status).

    A missing key is 503 with the reason, not a fallback: silently answering from a local model
    would give a different, worse answer than the one this deployment is configured to give, and
    the reader would have no way to know which they got.
    """
    question = (question or "").strip()
    if not question:
        return {"error": "question is required"}, 400
    if not router_key():
        return {
            "error": "no LITELLM_API_KEY on this deployment, so voice has no model",
            "fix": "source the estate vault (estate-secrets/scripts/secret-load), or set it in the pod",
        }, 503

    payload = {
        "model": router_model(),
        "messages": [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": f"FLEET SUMMARY\n{fleet_summary(sessions)}\n\nQUESTION\n{question}",
            },
        ],
        "max_tokens": 220,
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        f"{router_host()}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {router_key()}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_timeout()) as resp:
            doc = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        # The router reports a depleted vendor plan as an error envelope with a 4xx; pass its
        # words through rather than saying "upstream error", which sends a reader to the wrong
        # place.
        detail = ""
        try:
            detail = (json.loads(exc.read().decode()).get("error") or {}).get("message", "")
        except Exception:  # noqa: BLE001
            detail = ""
        return {"error": f"the router refused the call ({exc.code})", "detail": detail[:300]}, 502
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"error": f"cannot reach the router: {exc}"}, 503
    except (ValueError, UnicodeDecodeError) as exc:
        return {"error": f"the router returned something unreadable: {exc}"}, 502

    choices = doc.get("choices") or []
    if not choices:
        err = doc.get("error")
        return {
            "error": "the router returned no answer",
            "detail": (err.get("message") if isinstance(err, dict) else str(err or ""))[:300],
        }, 502
    answer = ((choices[0].get("message") or {}).get("content") or "").strip()
    if not answer:
        return {"error": "the router returned an empty answer"}, 502
    return {"answer": answer, "model": router_model()}, 200
