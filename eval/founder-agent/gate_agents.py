"""Who the harness runs: today's Otto, through the door it actually has, or a replay.

The rule the spec keeps (G2 edge case): *a probe that bypasses the door is rejected*. So every
adapter here either speaks to the door the founder speaks to, or replays a transcript the door
produced. Nothing here calls the model directly, and nothing here decides that a task passed  -
that is the verifier's job.

Three adapters:

* `StubAgent`    -  replays a recorded `Run`. Used by `--self-test` and `--dry-run`; cannot invent
  a turn.
* `CommandAgent` -  runs a local command per turn and reads one JSON `Run` from its stdout. This is
  how a loop running on the laptop (tests, a rebuilt Otto) is graded without a cluster.
* `DoorAgent`    -  POSTs a turn to `OTTO_DOOR/webhook/<channel>` and reads the transcript the door
  returns. Today's door answers a webhook with an empty 200: for it, `turn()` returns
  `status="ungradable"` with the POST result as the only event, and every task fails with that
  reason instead of a fabricated pass (measured 2026-10-23: POST /webhook/probe -> 000 from the
  estate network; see round-0 report `door` section).
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from gate_schema import Run


class AgentError(RuntimeError):
    pass


def _fresh_session(task_id: str, run_index: int) -> str:
    """A session id nothing else shares: 'fresh session per run' is a spec requirement, so the
    session must not be derivable from a previous run's."""
    return f"gate-{task_id}-r{run_index}-{int(time.time() * 1000)}"


@dataclass
class StubAgent:
    """Replays a fixture. `fixture` is a path to a recorded run.json."""

    fixture: str
    surface: str = "telegram"

    def turn(self, task_id: str, prompt: str, run_index: int = 0) -> Run:
        run = Run.load(self.fixture)
        run.session = _fresh_session(task_id, run_index)
        return run


@dataclass
class CommandAgent:
    """`command` gets the prompt on stdin as JSON and must print one JSON Run on stdout."""

    command: str
    timeout_s: float = 300.0
    surface: str = "telegram"

    def turn(self, task_id: str, prompt: str, run_index: int = 0) -> Run:
        session = _fresh_session(task_id, run_index)
        run = Run(task_id=task_id, surface=self.surface, session=session)
        payload = json.dumps({"task_id": task_id, "prompt": prompt, "session": session})
        try:
            # S603: the command is the operator's own --command string, given to this adapter on
            # purpose (it is how a loop under test is plugged in), never model output.
            proc = subprocess.run(  # noqa: S603
                shlex.split(self.command),
                input=payload,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
            )
        except subprocess.TimeoutExpired:
            run.add("error", text=f"agent command exceeded {self.timeout_s}s")
            return run.end("timeout")
        run.add(
            "step",
            name="agent",
            text=f"exit {proc.returncode}",
            stdout=proc.stdout[-4000:],
            stderr=proc.stderr[-2000:],
        )
        if proc.returncode != 0:
            return run.end("crashed")
        try:
            out = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            run.add("error", text=f"agent printed no JSON run: {exc}")
            return run.end("ungradable")
        # The command is the authority on its own transcript: its events replace the placeholder.
        from gate_schema import Event

        run.events = [Event(**e) for e in out.get("events", [])] or run.events
        run.artifacts = out.get("artifacts", {})
        run.cost_usd = float(out.get("cost_usd", 0.0))
        run.fleet = out.get("fleet", [])
        return run.end(out.get("status", "ok"))


@dataclass
class DoorAgent:
    """Sends a turn to the estate's real door and reads the transcript it publishes."""

    door: str
    channel: str = "telegram"
    transcript_path: str | None = (
        None  # where a door-written transcript can be read afterwards
    )
    timeout_s: float = 120.0
    surface: str = "telegram"
    allow_door: bool = False
    secret_env: str = "OTTO_CHANNEL_SECRET"  # noqa: S105 - the NAME of an env var, not a key

    def url(self) -> str:
        return f"{self.door.rstrip('/')}/webhook/{self.channel}"

    def turn(self, task_id: str, prompt: str, run_index: int = 0) -> Run:
        session = _fresh_session(task_id, run_index)
        run = Run(task_id=task_id, surface=self.surface, session=session)
        if not self.allow_door:
            run.add(
                "error",
                text="door adapter disabled: pass --allow-door to send a real turn",
            )
            return run.end("refused")
        body = json.dumps(
            {
                "update_id": int(time.time() * 1000),
                "message": {
                    "message_id": int(time.time() * 1000),
                    "chat": {"id": 0},
                    "text": prompt,
                    "harness": {"session": session, "task": task_id},
                },
            }
        ).encode()
        req = urllib.request.Request(self.url(), data=body, method="POST")  # noqa: S310 - https, fixed host
        req.add_header("content-type", "application/json")
        secret = os.environ.get(self.secret_env, "")
        if secret:
            req.add_header("X-Telegram-Bot-Api-Secret-Token", secret)
        run.add("user", text=prompt, channel=self.channel, session=session)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:  # noqa: S310
                code = resp.status
                raw = resp.read(200_000).decode(errors="replace")
        except urllib.error.HTTPError as exc:
            run.add(
                "error",
                text=f"door refused the turn: HTTP {exc.code}",
                body=exc.read(2000).decode(errors="replace"),
            )
            return run.end("refused")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            run.add("error", text=f"door unreachable: {exc}")
            return run.end("refused")
        run.add("step", name="door", text=f"HTTP {code}", body=raw[:8000])
        if self.transcript_path and os.path.exists(self.transcript_path):
            recorded = Run.load(self.transcript_path)
            recorded.task_id, recorded.session = task_id, session
            return recorded
        run.add(
            "error",
            text=(
                "the door accepted the turn but publishes no transcript, so this task cannot be "
                "graded: an ungradable task is a failure, never a skip"
            ),
        )
        return run.end("ungradable")


def build(kind: str, **kw: Any):
    if kind == "stub":
        return StubAgent(fixture=kw["fixture"])
    if kind == "command":
        return CommandAgent(command=kw["command"], timeout_s=kw.get("timeout_s", 300.0))
    if kind == "door":
        return DoorAgent(
            door=kw["door"],
            channel=kw.get("channel", "telegram"),
            transcript_path=kw.get("transcript_path"),
            allow_door=kw.get("allow_door", False),
        )
    raise AgentError(f"unknown agent {kind!r}")
