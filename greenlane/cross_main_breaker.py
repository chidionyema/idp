"""Durable failure-class epochs for the canonical Greenlane State ref.

Never infer an identical root cause from a generic CI red verdict. A repeated
specific cause on an unchanged source across two different main commits is
parked until that source changes. No runner-local database or merge authority.
"""

from __future__ import annotations

LIMIT = 2


def normalize_epochs(value: object) -> dict[str, dict]:
    if not isinstance(value, dict):
        return {}
    result = {}
    for name, epoch in value.items():
        if not isinstance(epoch, dict):
            continue
        raw = epoch.get("bases")
        if not isinstance(raw, list):
            raw = []
        bases = [base for base in raw if isinstance(base, str)]
        result[str(name)] = {
            "head": str(epoch.get("head", "")),
            "cause": str(epoch.get("cause", "")),
            "bases": list(dict.fromkeys(bases))[:LIMIT],
        }
    return result


def record_failure(
    epochs: dict[str, dict], name: str, head: str, base: str, cause: str
) -> int:
    if not cause:
        return 0
    current = epochs.get(name)
    if not current or (current["head"], current["cause"]) != (head, cause):
        current = {"head": head, "cause": cause, "bases": []}
        epochs[name] = current
    bases = current["bases"]
    if base not in bases and len(bases) < LIMIT:
        bases.append(base)
    return len(bases)


def prune_epochs(epochs: dict[str, dict], heads: dict[str, str]) -> None:
    for name, epoch in list(epochs.items()):
        if heads.get(name) != epoch.get("head"):
            del epochs[name]


def measure_operational_cap() -> bool:
    """Independently exercise the real state-machine path using two main revisions."""
    from greenlane.engine import RED, Batch, Engine, Lane, State
    from greenlane.learning import fingerprint

    class World:
        def __init__(self) -> None:
            self.base = "a" * 40

        def main(self) -> str:
            return self.base

        def now(self) -> float:
            return 100.0

        def checks(self, tip: str) -> tuple[str, str]:
            return "red", (
                "fast-gate / fast-gate failure "
                "-- FAIL language-gate: exact unchanged source violates required trailer"
            )

        def main_red(self, sha: str) -> bool:
            return False

        def report(self, *args: object) -> None:
            return None

    backend = World()
    state = State()
    engine = Engine(backend, state)
    lane_name = "lane/optimus-cross-main-falsifier"
    head = "c" * 40
    for index, base in enumerate(("a" * 40, "b" * 40), start=1):
        backend.base = base
        state.lanes[lane_name] = Lane(lane_name, head)
        state.batch = Batch(f"b{index}", base, head, [(lane_name, head, head)], 90.0)
        engine._judge_batch()
    lane = state.lanes[lane_name]
    expected = ["a" * 40, "b" * 40]
    epoch = state.failure_epochs.get(lane_name, {})
    restored = State.loads(state.dumps())
    valid = (
        lane.status == RED
        and lane.judged_on == ""
        and state.history[-1].get("action") == "cross-main-hold"
        and epoch.get("bases") == expected
        and restored.failure_epochs[lane_name]["bases"] == expected
    )
    cause = fingerprint(backend.checks(head)[1])
    reset_head = "d" * 40
    reset_base = "b" * 40
    cap_retained = record_failure(
        state.failure_epochs, lane_name, reset_head, reset_base, cause
    )
    cap_reset = record_failure(
        state.failure_epochs, lane_name, reset_head, reset_base, ""
    )
    return bool(valid and cap_retained == 1 and cap_reset == 0)


if __name__ == "__main__":
    import sys

    if sys.argv[1:] != ["--optimus"]:
        raise SystemExit("usage: python3 -m greenlane.cross_main_breaker --optimus")
    if not measure_operational_cap():
        raise SystemExit("BLIND: cross-main invariant falsifier failed")
    print("optimus.greenlane.cross_main_failure_cap=1")
