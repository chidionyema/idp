"""The contract between the harness and a task's verifier (idp#6921, spec G1).

A verifier never reads prose and never reads the agent's own claim of success: it reads a `Run`,
which is the transcript the gateway wrote (tool calls, messages, notices, fleet lines), and answers
`Verdict(ok, reason)`. Everything here is plain data so a `known-good` and a `known-bad` transcript
can be committed beside a task and replayed by `--self-test` without an agent.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

# The kinds a transcript may carry. `notice` is a message the agent sends the founder; `step` is a
# progress line; `error` is a failure the agent itself raised. Anything else is a tool event.
KINDS = {
    "user",
    "assistant",
    "tool_call",
    "tool_result",
    "error",
    "step",
    "notice",
    "artifact",
}


@dataclass
class Event:
    t: float  # epoch seconds, UTC
    kind: str
    name: str = ""  # tool name, surface, or channel
    text: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(
                f"unknown event kind {self.kind!r}; add it to KINDS deliberately"
            )


@dataclass
class Run:
    """One execution of one task, in one fresh session, on one surface."""

    task_id: str
    surface: str
    session: str
    started: float = field(default_factory=time.time)
    ended: float = 0.0
    status: str = "running"  # ok | error | timeout | refused | crashed | stuck
    events: list[Event] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    cost_usd: float = 0.0
    fleet: list[dict[str, Any]] = field(default_factory=list)
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    # -- writing ---------------------------------------------------------
    def add(self, kind: str, text: str = "", name: str = "", **data: Any) -> Event:
        ev = Event(t=time.time(), kind=kind, name=name, text=text, data=data)
        self.events.append(ev)
        return ev

    def end(self, status: str) -> "Run":
        self.status = status
        self.ended = time.time()
        return self

    # -- reading (what verifiers use) ------------------------------------
    def of(self, kind: str, name: str | None = None) -> list[Event]:
        return [
            e
            for e in self.events
            if e.kind == kind and (name is None or e.name == name)
        ]

    def text_of(self, *kinds: str) -> str:
        return "\n".join(e.text for e in self.events if e.kind in kinds)

    def tool_calls(self) -> list[Event]:
        return self.of("tool_call")

    def tool_log(self) -> list[str]:
        """What the gateway recorded the agent doing, flattened for a canary scan (G5)."""
        out: list[str] = []
        for e in self.events:
            if e.kind in {"tool_call", "tool_result", "artifact"}:
                out.append(json.dumps({"name": e.name, "text": e.text, "data": e.data}))
        return out

    def messages_to_founder(self) -> list[Event]:
        return [e for e in self.events if e.kind in {"notice", "assistant"}]

    def first_response_after(self, t0: float) -> float | None:
        for e in self.events:
            if e.kind in {"notice", "assistant", "step"} and e.t >= t0:
                return e.t - t0
        return None

    def duration(self) -> float:
        return (self.ended or time.time()) - self.started

    # -- persistence -----------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Run":
        d = dict(d)
        d["events"] = [Event(**e) for e in d.get("events", [])]
        return cls(**d)

    def save(self, path) -> None:
        import pathlib

        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n")

    @classmethod
    def load(cls, path) -> "Run":
        import pathlib

        return cls.from_dict(json.loads(pathlib.Path(path).read_text()))


@dataclass
class Verdict:
    ok: bool
    reason: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "reason": self.reason, "data": self.data}


def verdict(ok: bool, reason: str = "", **data: Any) -> Verdict:
    return Verdict(ok=ok, reason=reason, data=data)
