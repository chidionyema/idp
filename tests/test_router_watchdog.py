"""The laptop router's watchdog restarts a dead router, never a slow one.

WHAT THIS GRADES. `platform/llm/watchdog.py` claims: only a refused port (curl exit 7) counts
toward a restart; a timeout or an HTTP error from a listening process is logged and never
counted; three refusals in a row restart once; no second restart inside the cooldown.

WHY. On 2026-10-02 the watchdog kickstarted the router 12 times, each after 3 s curl timeouts
while the laptop's load average was 50-90. Every kickstart cut every live agent session. The
first test below fails on that version: three slow probes produced a kickstart.

CALLED THE WAY LAUNCHD CALLS IT: `main()` once per 15 s tick, state carried in the JSON file.
"""

import importlib.util
import pathlib
import subprocess

import pytest

MODULE = (
    pathlib.Path(__file__).resolve().parents[1] / "platform" / "llm" / "watchdog.py"
)


class FakeRun:
    """Stands in for subprocess.run: curl answers from a script, launchctl is recorded."""

    def __init__(self, curl_answers):
        self.curl_answers = list(curl_answers)
        self.kickstarts = 0
        self.labels = []
        self.urls = []

    def __call__(self, argv, **_):
        if argv[0] == "launchctl":
            self.kickstarts += 1
            self.labels.append(argv[-1].rsplit("/", 1)[-1])
            return subprocess.CompletedProcess(argv, 0, "", "")
        self.urls.append(argv[-1])
        code, out = self.curl_answers.pop(0)
        return subprocess.CompletedProcess(argv, code, out, "")


@pytest.fixture
def wd(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("router_watchdog", MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "STATE", tmp_path / "watchdog.json")
    monkeypatch.setattr(mod, "LOG", tmp_path / "watchdog.log")
    monkeypatch.setattr(
        mod, "ACTIVE", tmp_path / "active"
    )  # no slots: the single router
    return mod


def ticks(wd, monkeypatch, answers, start=1_000_000.0, step=15.0, probes_per_tick=1):
    fake = FakeRun(answers)
    monkeypatch.setattr(wd.subprocess, "run", fake)
    for i in range(len(answers) // probes_per_tick):
        monkeypatch.setattr(wd.time, "time", lambda t=start + i * step: t)
        wd.main()
    return fake


TIMEOUT = (
    28,
    "000",
)  # curl: operation timed out -- the process is listening, just slow
REFUSED = (7, "000")  # curl: could not connect -- nothing is listening
HTTP_500 = (0, "500")
OK = (0, "200")


def test_slow_router_is_never_restarted(wd, monkeypatch):
    fake = ticks(wd, monkeypatch, [TIMEOUT] * 10 + [HTTP_500] * 5)
    assert fake.kickstarts == 0
    assert "not restarted" in (wd.LOG).read_text()


def test_three_refusals_restart_once(wd, monkeypatch):
    fake = ticks(wd, monkeypatch, [REFUSED] * 3)
    assert fake.kickstarts == 1


def test_slow_probe_does_not_add_to_refusal_count(wd, monkeypatch):
    fake = ticks(wd, monkeypatch, [REFUSED, REFUSED, TIMEOUT, OK, REFUSED, REFUSED])
    assert fake.kickstarts == 0


def test_a_router_still_starting_is_not_killed_inside_the_cooldown(wd, monkeypatch):
    # restart at tick 3, then refused for the ~100 s a loaded laptop takes to start it
    fake = ticks(wd, monkeypatch, [REFUSED] * 3 + [REFUSED] * 8)
    assert fake.kickstarts == 1


# --- slots: front on :4000, router in slot 4001 or 4002 (platform/llm/front.py) ---------------


def test_without_slots_the_single_router_on_4000_is_guarded(wd, monkeypatch):
    fake = ticks(wd, monkeypatch, [REFUSED] * 3)
    assert fake.urls == ["http://127.0.0.1:4000/health/liveliness"] * 3
    assert fake.labels == ["com.estate.litellm-local"]


def test_the_active_slot_is_probed_on_its_own_port_and_its_agent_restarted(
    wd, monkeypatch
):
    # Through the front a dead router is an empty reply (curl 52), which counts as slow; only
    # the slot's own port can say "refused". Each tick probes the front, then the slot.
    wd.ACTIVE.write_text("4002\n")
    fake = ticks(wd, monkeypatch, [OK, REFUSED] * 3, probes_per_tick=2)
    assert fake.urls[1] == "http://127.0.0.1:4002/health/liveliness"
    assert fake.labels == ["com.estate.litellm-local-4002"]


def test_a_refused_front_is_restarted_at_once(wd, monkeypatch):
    wd.ACTIVE.write_text("4001")
    fake = ticks(wd, monkeypatch, [REFUSED, OK], probes_per_tick=2)
    assert fake.labels == ["com.estate.litellm-front"]
