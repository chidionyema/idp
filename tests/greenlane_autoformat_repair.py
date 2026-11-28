"""Optimus measure: greenlane.format_refusal_repaired.

Prints `optimus.greenlane.format_refusal_repaired=1` when the real Greenlane Engine, handed a lane
whose only pre-CI refusal is the pinned-ruff format refusal, asks its backend to repair the lane
(and reports the repaired head) while it still spends no CI on the unformatted head, still refuses
exactly as before when the backend has no fixer, and never invokes the fixer for any other refusal.
Prints 0 on code that leaves a format-only lane red with no repair attempt.

Stdlib only: the Greenlane judge has no pytest. The real-ruff and real-git proof is
tests/test_greenlane_autoformat.py.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


class _Backend:
    def __init__(self, refusal: str, fixer) -> None:
        self.base = "a" * 40
        self.refusal = refusal
        self.pushed: list[str] = []
        if fixer is not None:
            self.format_fix = fixer

    def main(self):
        return self.base

    def now(self):
        return 1.0

    def rebase(self, head, onto, lane=""):
        return head

    def preflight(self, base, candidate):
        return False, self.refusal

    def push_candidate(self, batch_id, tip):
        self.pushed.append(tip)

    def report(self, lane, head, status, reason):
        pass

    def unclaimed(self, head, base):
        return ""

    def lanes(self):
        return {}


def measure() -> int:
    sys.path.insert(0, str(ROOT))
    try:
        from greenlane.engine import RED, Engine, Lane, State
        from greenlane.ferrari import FORMAT_REFUSAL
    except Exception:
        return 0

    def run(refusal, fixer):
        backend = _Backend(refusal, fixer)
        state = State(lanes={"lane/x": Lane("lane/x", "h1", seq=1)})
        Engine(backend, state, batch_size=1)._start_batch()
        return backend, state.lanes["lane/x"]

    try:
        seen: list[tuple] = []

        def fixer(lane, head, base):
            seen.append((lane, head, base))
            return "f" * 40

        backend, lane = run(FORMAT_REFUSAL + ": a.py", fixer)
        repaired = (
            seen == [("lane/x", "h1", "a" * 40)]
            and lane.status == RED
            and "pushed ffffffffffff" in lane.reason
            and backend.pushed == []
        )
        _, plain = run(FORMAT_REFUSAL + ": a.py", None)
        unchanged = plain.status == RED and plain.reason == FORMAT_REFUSAL + ": a.py"
        other: list[tuple] = []
        run(
            "pre-CI language-gate: x",
            lambda *a: other.append(a) or "f" * 40,
        )
        return 1 if repaired and unchanged and not other else 0
    except Exception:
        return 0


if __name__ == "__main__":
    print(f"optimus.greenlane.format_refusal_repaired={measure()}")
