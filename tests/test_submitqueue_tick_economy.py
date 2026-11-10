"""Native event delivery must never regenerate privileged ticks without work."""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path

import pytest

from greenlane.engine import Batch, State

ROOT = Path(__file__).resolve().parents[1]


def module():
    loader = importlib.machinery.SourceFileLoader(
        "greenlane_tick_economy", str(ROOT / "bin/idp-greenlane")
    )
    spec = importlib.util.spec_from_loader("greenlane_tick_economy", loader)
    result = importlib.util.module_from_spec(spec)
    loader.exec_module(result)
    return result


@pytest.mark.parametrize(
    "before,after,expected",
    [
        ("none", "none", 0),
        ("none", "b1", 0),
        ("b1", "b1", 0),
        ("b1", "none", 1),
        ("b1", "b2", 1),
    ],
)
@pytest.mark.parametrize("judge_only", [False, True])
def test_only_real_batch_resolution_wakes_next_formation(
    monkeypatch, before, after, expected, judge_only
):
    mod = module()
    monkeypatch.setenv("GH_REPO", "chidionyema/idp")
    calls = []
    starting = State()
    if before != "none":
        starting.batch = Batch(before, "a" * 40, "b" * 40, [], 0.1)

    class Backend:
        def __init__(self, *args, **kwargs):
            self.refused = {}

        def fetch(self):
            pass

        def load_state_text(self):
            return starting.dumps()

        def save_state_text(self, value):
            calls.append(("save", value))

        def main(self):
            return "a" * 40

    class Engine:
        def __init__(self, backend, state):
            self.s = state
            self.log = []

        def tick(self, judge_only=False):
            if after == "none":
                self.s.batch = None
            else:
                self.s.batch = Batch(after, "a" * 40, "b" * 40, [], 0.1)

    monkeypatch.setattr(mod, "GitHubBackend", Backend)
    monkeypatch.setattr(mod, "Engine", Engine)
    monkeypatch.setattr(mod, "rearm", lambda state: calls.append(("wake", state)))
    assert mod._tick_once(judge_only=judge_only) == 0
    assert sum(1 for call in calls if call[0] == "wake") == expected
    assert sum(1 for call in calls if call[0] == "save") == 1
