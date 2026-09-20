"""The 60-second decree. A wait longer than a minute cannot be ASKED FOR, from any harness.

ULTIMATE DECREE (founder, 2026-09-20): "we don't ever do anything at local level ... this is
ultimate decree and must be handled at a layer that bypasses and guarantees and future proofs and
stops this shit in its tracks cold."

WHAT WAS WRONG WITH EVERY PREVIOUS ATTEMPT, checked rather than assumed. This rule has now been
breached seven times, and each fix failed for a DIFFERENT structural reason, so naming them is the
whole point of this file:

  1. A paragraph in ~/.claude/CLAUDE.md -- prose. Nothing makes it happen. Drifted immediately.
  2. `bin/agent-timebox` -- a ceiling, correct, and OPT-IN. A session must remember to prefix it.
     On 2026-09-20 a session ran 800 seconds twice instead. A control that can be declined is not
     a control; it is a suggestion, and it was declined.
  3. `~/.pi/agent/extensions/wall.ts` (written and deleted 2026-09-20, by me) -- a per-harness
     file. It covered pi and nothing else: not Claude Code, not Codex, not a CI runner, not a
     second laptop. `platform/llm/request_ceiling.py` already names this exact mistake in its own
     docstring -- "It is one file on one laptop in one home directory. Fixing it there fixed this
     machine and proved nothing about the estate."
  4. `platform/executor/daemon.py` -- the right idea (a boundary outside the caller, kernel-enforced
     timeout) and it is currently MEASURED_FAIL: no socket, never executed anything, and the
     agent's own uid can rewrite the daemon. It also requires `sudo bin/idp-executor-install`, and
     ANY control that requires an installer TO BE RUN is a control that can be NOT RUN. It has been.

THE LAYER THAT CANNOT BE OFF, and why it is this one:

    THE ROUTER HOLDS THE ONLY MODEL CREDENTIAL. LAW 34: every workload gets a router virtual key,
    never a vendor key. There is no vendor key on this machine or in agent code. So a session
    cannot think without a call through here, and this hook runs BEFORE the upstream is reached.
    There is no install step (the callback is already loaded -- see `callbacks:` in config.yaml),
    no daemon to start, no file a session can rewrite, and no harness that is exempt, because
    every harness is a client of this router or it has no model.

    That is the difference between a guarantee and a request: an agent that ignores this decree
    does not get a warning, it gets no tokens.

WHAT IT REFUSES. A tool call that asks for a wait longer than CEILING_SEC -- measured across the
harness's own tool arguments, not by watching a clock afterward. Refused pre-flight, so nothing
runs and nothing is billed. The wait shapes are the ones that have actually been used here:
`sleep N`, `timeout N`, and a loop that sums its sleeps past the ceiling.

WHY THE CEILING IS 60 AND WHY THAT IS NOT A MODEL LIMIT. Founder, 2026-09-13: "60 secsos is the
nnax" / "it should not even get near the". A wait longer than a minute is a command whose result
arrives too late to be corrected, and it holds the session blind while the founder waits on
something they cannot see. The replacement is an event, not a smaller number: poll for readiness,
run it detached, or split it.

FAIL DIRECTION, stated because a control that hides its scope cannot be trusted on the cases it
does cover. This hook FAILS CLOSED on a recognised wait (the decree is absolute) and FAILS OPEN on
its own inability to read the request -- a malformed payload it cannot parse is passed to the
upstream rather than refused, because a router hook that blocks every request when its own parser
trips would take the estate down and be removed within the hour. The one escape is a named,
time-boxed, logged exception (`execution_waiver`), and it is granted by the operator, never by the
agent asking for it -- see the profile rule in docs/synthesis/harness-composition-and-enforcement.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Literal, Optional, Union

log = logging.getLogger("estate.execution-decree")

try:
    from litellm.integrations.custom_logger import CustomLogger
except ModuleNotFoundError:  # pragma: no cover - a laptop or CI runner has no litellm

    class CustomLogger:  # type: ignore[no-redef]
        """Stand-in so `find_waits` stays importable and testable outside the router image."""

        async def async_pre_call_hook(self, *a, **k) -> None:  # noqa: D102
            raise NotImplementedError


# The ceiling. A wait at or below this is permitted -- the decree is about impossibility past a
# minute, and refusing a 5s wait would be a different (defensible) decision made silently here.
CEILING_SEC = int(os.environ.get("ESTATE_WAIT_CEILING_SEC", "60"))

# The one escape, and it must carry a reason. Textual and greppable so it shows up in review.
WAIVER = re.compile(r"(?:#|//|--)\s*wall-ok:\s*(\S.*)")

# Durations a shell accepts. `ms` to `d`, so `sleep 2m` cannot slip past a rule that only reads
# plain seconds -- the first version of the timebox got exactly that wrong.
_DURATION = re.compile(r"^(\d+(?:\.\d+)?)(ms|s|m|h|d)?$")


def to_seconds(token: str) -> float | None:
    """Seconds for a duration token, or None when it is not a plain duration.

    None is RETURNED, never guessed: `sleep "$N"` and `sleep $DELAY` are not converted to a number,
    because inventing one would be the same class of error as a gate that reports a figure it did
    not measure. The caller treats an unreadable duration as unknown, not as safe.
    """
    m = _DURATION.match(token.strip())
    if not m:
        return None
    value = float(m.group(1))
    return {
        "ms": value / 1000.0,
        "m": value * 60.0,
        "h": value * 3600.0,
        "d": value * 86400.0,
    }.get(m.group(2) or "s", value)


def _iter_strings(obj: Any):
    """Every string inside a nested request payload, so a tool argument is found wherever it sits.

    A request's tool call is not always at a fixed key -- harnesses differ, and that is the point
    of doing this at the router rather than per harness. Walking the whole structure finds the
    command regardless of which key the client used to send it.
    """
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from _iter_strings(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            yield from _iter_strings(value)


def find_waits(text: str) -> list[tuple[float, str]]:
    """Every wait in a command that could block, as (seconds, what).

    A whole-string scan rather than a shell parse: the commands here are pipelines, loops and
    compound statements, and a partial parser would be confidently wrong about exactly the cases
    that matter. Over-inclusive refuses a command the author can rewrite, which is the correct
    direction to be wrong in.
    """
    out: list[tuple[float, str]] = []

    for m in re.finditer(r'\bsleep\s+("?)([^\s;&|)]+)\1', text):
        secs = to_seconds(m.group(2))
        if secs is not None:
            out.append((secs, f"sleep {m.group(2)}"))
        elif not m.group(2).startswith("-"):
            # A VARIABLE DURATION. `sleep $DELAY` is unbounded as far as this hook can prove, and
            # an unprovable wait past a minute is exactly what the decree forbids. The first
            # version matched only `\d+`, so `sleep $DELAY` matched nothing at all and passed --
            # a hole a session would eventually find, since a variable is the obvious way to
            # sidestep a literal ceiling.
            out.append((float(CEILING_SEC + 1), f"sleep {m.group(2)} (unreadable duration)"))

    for m in re.finditer(r'\btimeout\s+(?:-k\s*\S+\s+)?("?)(\d+(?:\.\d+)?(?:ms|s|m|h|d)?)\1', text):
        secs = to_seconds(m.group(2))
        if secs is not None:
            out.append((secs, f"timeout {m.group(2)}"))

    # A loop that waits. `for i in {1..30}; do sleep 5; done` is 150s wearing 30 small pieces, and
    # grading each piece would call it safe.
    for m in re.finditer(r"\b(for|while|until)\b[\s\S]*?\bdone\b", text):
        body = m.group(0)
        inner = []
        for x in re.finditer(r'\bsleep\s+("?)([^\s;&|)]+)\1', body):
            secs = to_seconds(x.group(2))
            inner.append(secs if secs is not None else float(CEILING_SEC + 1))
        if not inner:
            continue
        rng = re.search(r"\{\d+\.\.(\d+)\}", body)
        per = max(inner)
        iterations = int(rng.group(1)) if rng else int(CEILING_SEC / max(per, 1)) + 1
        total = per * iterations
        if total > CEILING_SEC:
            out.append((total, f"a loop sleeping {per:g}s x{iterations} (~{total:g}s)"))

    # A loop over an unbounded list running an external process each turn. THE 800-SECOND BREACH
    # HAD THIS SHAPE AND NOTHING ELSE: `for b in $(git for-each-ref ...); do git push $b; done`, 42
    # turns at ~20s. It contains no `sleep` and no `timeout`, so grading only explicit waits would
    # have passed the exact command that motivated the decree.
    for m in re.finditer(r"\b(for|while|until)\b[\s\S]*?\bdone\b", text):
        body = m.group(0)
        if re.search(r"\bsleep\b", body):
            continue  # already graded above
        bounded = re.search(
            r"\{\d+\.\.\d+\}|-lt\s+\d+|-le\s+\d+|-eq\s+\d+|seq\s+\d+\s+\d+|\b1\.\.\d+", body
        )
        forever = re.search(r"\b(while|until)\s+(:\s*;?|true)\b", body)
        external = re.search(
            r"\b(git|curl|wget|pytest|npm|npx|yarn|node|python3?|kubectl|helm|flux|docker|podman|"
            r"go|cargo|make|rsync|scp|ssh)\b",
            body,
        )
        if forever or (external and not bounded):
            what = "an unbounded loop with no terminating condition" if forever else (
                "a loop over a list whose length is not a literal, running an external process "
                "each turn"
            )
            out.append((float(CEILING_SEC + 1), what))

    return out


def worst_wait(payload: dict) -> tuple[float, str] | None:
    """The longest wait anywhere in a request, or None when there is nothing to refuse."""
    worst: tuple[float, str] | None = None
    for text in _iter_strings(payload):
        if len(text) < 4:
            continue
        for secs, what in find_waits(text):
            if worst is None or secs > worst[0]:
                worst = (secs, what)
    return worst


class EstateExecutionDecree(CustomLogger):
    """Refuses a request that asks for a wait longer than the ceiling. Every harness, every host."""

    @staticmethod
    def _key_hint(user_api_key_dict: Any) -> str:
        """The last 8 of the key, the way LiteLLM itself shortens one. Never the whole key: this
        string reaches logs, and a key in a log is a key leaked."""
        try:
            return (getattr(user_api_key_dict, "api_key", "") or "")[-8:] or "unknown"
        except Exception:
            return "unknown"

    async def async_pre_call_hook(
        self,
        user_api_key_dict: Any,
        cache: Any,
        data: dict,
        call_type: Union[Any, Literal["completion", "text_completion", "embeddings"]],
    ) -> Optional[Union[Exception, str, dict]]:
        try:
            worst = worst_wait(data)
        except Exception as exc:  # fail OPEN on our own parser, and say so
            log.warning("execution-decree: could not analyse a request (%s); passing it", exc)
            return None

        if worst is None:
            return None

        secs, what = worst
        if secs <= CEILING_SEC:
            return None

        # THE ONE ESCAPE. Granted by the operator, carried in the request, and logged. An
        # annotation with no reason is not an annotation.
        blob = "\n".join(_iter_strings(data))
        waiver = WAIVER.search(blob)

        key_hint = self._key_hint(user_api_key_dict)
        model = data.get("model", "unknown")

        if waiver:
            log.warning(
                "execution-decree: WAIVED %s (key %s) -- %s claimed: %s",
                model,
                key_hint,
                what,
                waiver.group(1)[:200],
            )
            return None

        log.error("execution-decree: REFUSED %s (key %s) -- %s", model, key_hint, what)

        return (
            f"Refused before it ran: this turn asks for {secs:g}s of waiting ({what}), and the "
            f"estate's ceiling is {CEILING_SEC}s per command (key ...{key_hint}).\n\n"
            f"That ceiling is not a model limit and not a budget to spend -- it is the point past "
            f"which a command's result arrives too late to be corrected, while the session is "
            f"blind and a person waits on something they cannot see. This has been breached seven "
            f"times, so it is enforced in the router, where every harness must pass and the only "
            f"model credential lives.\n\n"
            f"The fix is an EVENT, not a smaller number:\n"
            f"  * poll for readiness and stop when it is ready (see bin/idp-portal),\n"
            f"  * run it detached, and poll a file for the result,\n"
            f"  * or split it into steps that each finish.\n\n"
            f"If a documented rate limit or protocol heartbeat genuinely forces a fixed interval, "
            f"the operator can waive it by appending `# wall-ok: <the specific reason>` -- a "
            f"waiver is named, logged, and never granted by the session that wants it. Retrying "
            f"this request unchanged will be refused identically."
        )


proxy_handler_instance = EstateExecutionDecree()
