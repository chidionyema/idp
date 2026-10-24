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

    #: What the feed and the report call this agent. Present on every agent so a round can name
    #: the thing it measured without a getattr dance in main().
    kind: str = "stub"

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
    kind: str = "command"

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
    """Sends a turn to the estate's real door and reads the transcript it publishes.

    Two shapes, because the door answers two kinds of surface and the difference is the agent's,
    not the harness's:

    * **push** (`pull=False`, Telegram): POST the update, read the transcript a door-written file
      holds. Used where the door has an address to push an answer to.
    * **pull** (`pull=True`, HTTP): POST the turn and get a `202` with a task id -- a plain HTTP
      caller has no chat id, so the door records the answer and the caller reads it back at
      `GET /turns/{task_id}` with the same credential (hermes-v2 `otto/ingress`, PR #111). This is
      the surface the founder-agent gate grades on: no synthetic Telegram update on the founder's
      phone, and no call into the router that skips the door.

    The pull read-back carries what Otto *said*, plus the lane, model, attempts and the verified
    flag; it does not carry the tool transcript. `run.artifacts["evidence"]` says `door.answer` so
    a verifier that needs tool evidence fails the task with that reason rather than reading an
    answer-only run as proof of a tool call.
    """

    door: str
    channel: str = "telegram"
    transcript_path: str | None = (
        None  # where a door-written transcript can be read afterwards
    )
    timeout_s: float = 120.0
    surface: str = "telegram"
    allow_door: bool = False
    secret_env: str = "OTTO_CHANNEL_SECRET"  # noqa: S105 - the NAME of an env var, not a key
    pull: bool = False
    api_secret_env: str = "OTTO_HTTP_SECRET"  # noqa: S105 - the NAME of an env var, not a key
    poll_interval_s: float = 1.0
    deadline_s: float = 300.0
    kind: str = "door"

    def url(self) -> str:
        return f"{self.door.rstrip('/')}/webhook/{self.channel}"

    def turn_url(self, task_id: str) -> str:
        return f"{self.door.rstrip('/')}/turns/{task_id}"

    def turn(self, task_id: str, prompt: str, run_index: int = 0) -> Run:
        session = _fresh_session(task_id, run_index)
        run = Run(task_id=task_id, surface=self.surface, session=session)
        if not self.allow_door:
            run.add(
                "error",
                text="door adapter disabled: pass --allow-door to send a real turn",
            )
            return run.end("refused")
        if self.pull:
            return self._pull(
                turn_task=task_id, prompt=prompt, session=session, run=run
            )
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

    # -- the pull surface (HTTP): a 202, then the answer read back by task id ----------------
    def _pull(self, *, turn_task: str, prompt: str, session: str, run: Run) -> Run:
        secret = os.environ.get(self.api_secret_env, "")
        if not secret:
            run.add(
                "error",
                text=(
                    f"{self.api_secret_env} is not set, so this turn has no credential and the "
                    "door cannot answer it: an unasked task is a failure, never a skip"
                ),
            )
            return run.end("refused")

        body = json.dumps(
            {
                "content": prompt,
                "caller_id": session,
                "received_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "harness": {"session": session, "task": turn_task},
            }
        ).encode()
        run.add("user", text=prompt, channel=self.channel, session=session)

        t0 = time.time()
        try:
            req = urllib.request.Request(self.url(), data=body, method="POST")  # noqa: S310
            req.add_header("content-type", "application/json")
            req.add_header("authorization", f"Bearer {secret}")
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

        accepted_ms = round((time.time() - t0) * 1000.0, 1)
        try:
            first = json.loads(raw)
        except json.JSONDecodeError:
            first = {}
        run.add(
            "step",
            name="door",
            text=f"HTTP {code}",
            body=raw[:2000],
            accepted_ms=accepted_ms,
        )
        run.metrics["accepted_ms"] = accepted_ms
        if code != 202:
            # 503 (a dead bus, now honest) is a refusal to accept the turn; 401 is a credential
            # the door does not know. Either way the turn was never asked, and that is a failure.
            run.add(
                "error",
                text=f"the door did not accept the turn: HTTP {code} {first.get('reason', '')}".strip(),
            )
            return run.end("refused")
        answer_task = first.get("task_id")
        if not answer_task:
            run.add("error", text="the door answered 202 with no task id to read back")
            return run.end("ungradable")
        run.artifacts["evidence"] = "door.answer"
        run.artifacts["task_id_at_door"] = answer_task

        deadline = t0 + self.deadline_s
        polls = 0
        last = None
        while time.time() < deadline:
            polls += 1
            try:
                req = urllib.request.Request(self.turn_url(answer_task), method="GET")  # noqa: S310
                req.add_header("authorization", f"Bearer {secret}")
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:  # noqa: S310
                    payload = json.loads(resp.read(500_000).decode(errors="replace"))
            except urllib.error.HTTPError as exc:
                last = f"HTTP {exc.code}"
                if exc.code == 404:
                    # Legitimately not answered yet: a caller that just got a 202 polls this and
                    # the first reads miss. Wait and ask again.
                    time.sleep(self.poll_interval_s)
                    continue
                if exc.code == 503:
                    run.add(
                        "error",
                        text=(
                            "the door could not read its conversation store, so the answer to "
                            f"{answer_task} cannot be established (HTTP 503)"
                        ),
                    )
                    return run.end("error")
                run.add("error", text=f"read-back refused: HTTP {exc.code}")
                return run.end("refused")
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last = f"unreachable: {exc}"
                time.sleep(self.poll_interval_s)
                continue
            except json.JSONDecodeError as exc:
                run.add("error", text=f"the read-back was not JSON: {exc}")
                return run.end("ungradable")

            answered_ms = round((time.time() - t0) * 1000.0, 1)
            run.metrics.update(
                {
                    "answered_ms": answered_ms,
                    "polls": polls,
                    "cost_usd": payload.get("cost_usd"),
                    "model": payload.get("model"),
                    "lane": payload.get("lane"),
                    "attempts": payload.get("attempts"),
                    "verified": payload.get("verified"),
                    "outcome_state": payload.get("outcome_state"),
                }
            )
            run.cost_usd = float(payload.get("cost_usd") or 0.0)
            run.artifacts["answer"] = payload
            answer_text = payload.get("answered")
            if answer_text is None:
                run.add(
                    "error",
                    text=(
                        f"the turn {answer_task} is recorded with no answer "
                        f"(outcome_state={payload.get('outcome_state')!r})"
                    ),
                )
                return run.end("error")
            run.add(
                "assistant",
                text=answer_text,
                lane=payload.get("lane"),
                model=payload.get("model"),
                answered_ms=answered_ms,
            )
            return run.end("ok")

        run.metrics["polls"] = polls
        run.add(
            "error",
            text=(
                f"no answer read back within {self.deadline_s:.0f}s "
                f"({polls} polls, last: {last or 'not found'})"
            ),
        )
        return run.end("timeout")


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
            pull=kw.get("pull", False),
            api_secret_env=kw.get("api_secret_env", "OTTO_HTTP_SECRET"),
            poll_interval_s=kw.get("poll_interval_s", 1.0),
            deadline_s=kw.get("deadline_s", 300.0),
        )
    raise AgentError(f"unknown agent {kind!r}")
