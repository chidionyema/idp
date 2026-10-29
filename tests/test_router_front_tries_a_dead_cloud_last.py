"""A cloud in cooldown is tried last, behind even slots that missed probes (2026-10-29).

Under fleet load the laptop slot misses its 3 s probe; the front then put the known-dead cloud
first, and every request stalled on it (24 cloud failures in a row, :4000 timing out at 90 s).
"""

import importlib.util
import pathlib
import time

FRONT = pathlib.Path(__file__).resolve().parents[1] / "platform/llm/front.py"


def load():
    spec = importlib.util.spec_from_file_location("front_under_test", FRONT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.ACTIVE = pathlib.Path("/nonexistent")
    mod.CLOUD = "https://cloud.example"
    return mod


def test_dead_cloud_goes_behind_slow_slots():
    f = load()
    f.DOWN.update({4001, 4002})
    f.CLOUD_DOWN_UNTIL = time.monotonic() + 600
    assert f.route() == [4001, 4002, "https://cloud.example"]


def test_healthy_cloud_is_still_the_default_route():
    f = load()
    f.DOWN.clear()
    f.CLOUD_DOWN_UNTIL = 0.0
    assert f.route()[0] == "https://cloud.example"
