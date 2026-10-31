# ruff: noqa
# fmt: off
"""The enforcement runtime.

A Run is the only way to produce user-visible output. It advances one stage at a
time, in the protocol's order, and only when the stage's validator passes.
"""
from __future__ import annotations

import hashlib
import json

from . import gates
from .model import Stage
from .registry import Protocol


class ProtocolViolation(Exception):
    def __init__(self, stage: Stage, violations: list[str]):
        self.stage, self.violations = stage, violations
        super().__init__(f"{stage.value}: " + "; ".join(violations))


class RunAborted(Exception):
    pass


class Run:
    def __init__(self, protocol: Protocol, *, ctx: gates.Ctx | None = None, max_attempts: int = 3):
        self.protocol = protocol
        self.ctx = ctx or gates.Ctx()
        self.max_attempts = max_attempts
        self._i = 0
        self._attempts = 0
        self.aborted = False
        self.log: list[dict] = []  # hash-chained audit trail

    # -- state -----------------------------------------------------------
    @property
    def expected(self) -> Stage | None:
        return None if self.finished else self.protocol.stages[self._i]

    @property
    def finished(self) -> bool:
        return self._i >= len(self.protocol.stages)

    # -- advance ---------------------------------------------------------
    def submit(self, stage: Stage, output) -> None:
        if self.aborted:
            raise RunAborted("run aborted after repeated violations")
        if self.finished:
            raise ProtocolViolation(stage, ["run already finished"])
        want = self.protocol.stages[self._i]
        violations: list[str] = []
        if stage != want:
            violations.append(f"out of order: expected {want.value}, got {stage.value}")
        else:
            violations = self.protocol.validators[stage](output, self.ctx)
        self._record(stage, violations)
        if violations:
            self._attempts += 1
            if self._attempts >= self.max_attempts:
                self.aborted = True
            raise ProtocolViolation(stage, violations)
        self.ctx.outputs[stage] = output
        if stage == Stage.COMMIT:
            self.ctx.committed_keys.add(output.idempotency_key)
        self._i += 1
        self._attempts = 0

    # -- egress ----------------------------------------------------------
    def egress(self) -> str:
        """The only path to user-visible text. Refuses unless every stage passed."""
        if not self.finished:
            raise ProtocolViolation(
                Stage.RESPONSE, [f"cannot respond: run stopped before {self.expected.value}"]
            )
        return gates.render(self.ctx.outputs[Stage.RESPONSE], self.ctx, self.protocol.proofset_stage)

    # -- audit -----------------------------------------------------------
    def _record(self, stage: Stage, violations: list[str]) -> None:
        prev = self.log[-1]["hash"] if self.log else ""
        entry = {"stage": stage.value, "ok": not violations, "violations": violations, "prev": prev}
        entry["hash"] = hashlib.sha256(json.dumps(entry, sort_keys=True).encode()).hexdigest()
        self.log.append(entry)

    def verify_log(self) -> bool:
        prev = ""
        for e in self.log:
            body = {k: e[k] for k in ("stage", "ok", "violations", "prev")}
            if e["prev"] != prev or e["hash"] != hashlib.sha256(
                json.dumps(body, sort_keys=True).encode()
            ).hexdigest():
                return False
            prev = e["hash"]
        return True
