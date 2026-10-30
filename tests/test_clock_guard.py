"""The clock guard: a wall clock that lies must be detected, refused, and never recorded.

WHY THESE TESTS. On 2026-10-30 this host's clock read 2024-01-01 for about twenty minutes. Six
Pi agent sessions, the Codex desktop profile and the estate's own incident files were created in
that window, and every one of them carries 2024-01-01 -- because the kernel was serving that
time and nothing was watching. The damage was silent: the timestamps were well-formed, and no
gate, no sensor and no human read them as wrong.

So the guard has to do four things, and each one is falsifiable here:

  1. name the failure (backward, forward, blind) instead of rounding it away,
  2. refuse to stamp a regressed clock -- the ledger and the incident ids must carry a trusted
     projection, never the regressed wall clock,
  3. detect it from witnesses the wall clock cannot argue with, including on the very first
     run, before any history exists,
  4. be reachable as a door that returns a nonzero status when the clock is untrustworthy,
     because a check that cannot fail is not a check.

THE WITNESSES. The kernel's boot record plus CLOCK_MONOTONIC is an absolute reference: the boot
record was captured at boot and did not follow the clock back to 2024 (it still read
2026-10-29 22:17:05 during the event), and the monotonic clock cannot be set at all. The
persisted sample is the second witness, relative, and needs a previous reading. The estate's
own incident ledger is the third, coarse and absolute.

The state file is per-test (a temporary ESTATE_HOME), so no test can touch the real estate.
The door tests put a fake `sysctl` on PATH: that is how a host whose kernel boot record is two
years out is reproduced without touching the real clock.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIBEXEC = ROOT / "platform" / "estate" / "libexec"
DOOR = ROOT / "bin" / "estate-incident-loop"

YEAR = 365 * 24 * 3600


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, LIBEXEC / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


guard = _load("clock_guard", "clock-guard.py")


def _reset_cache() -> None:
    guard._CACHE.update({"key": None, "monotonic": None, "verdict": None})


def _state_file(tmp_path: Path) -> Path:
    return tmp_path / "estate" / "state" / "clock-skew.json"


def _write_state(path: Path, wall: float, monotonic: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"wall": wall, "monotonic": monotonic, "at": "2026-10-30T06:00:00Z"})
    )


def _poison_backward(path: Path) -> float:
    """Make the stored sample look like a clock that has just jumped backwards: the stored wall
    clock is in the future, the stored monotonic reading is where it was a minute ago."""
    now_mono = guard.monotonic()
    future_wall = time.time() + 86400
    _write_state(path, future_wall, now_mono - 60)
    return future_wall


# --- the verdict ------------------------------------------------------------


def test_a_clock_that_agrees_with_the_monotonic_clock_is_ok():
    verdict = guard.judge(
        {"wall": 1000.0, "monotonic": 10.0}, {"wall": 1015.0, "monotonic": 25.0}
    )
    assert verdict["state"] == guard.OK
    assert verdict["trusted"] is True
    assert verdict["projected_epoch"] == 1015.0


def test_a_clock_that_went_backwards_is_named_and_measured():
    verdict = guard.judge(
        {"wall": 1000.0, "monotonic": 10.0}, {"wall": 500.0, "monotonic": 15.0}
    )
    assert verdict["state"] == guard.BACKWARD
    assert verdict["trusted"] is False
    # The clock lost 500s of wall time while 5s of real time passed.
    assert verdict["wall_delta_s"] == -500.0
    assert verdict["skew_s"] == -505.0
    # The projection is the last trusted reading plus the monotonic elapsed time.
    assert verdict["projected_epoch"] == 1005.0
    assert "backwards" in verdict["reason"]


def test_a_clock_that_jumped_forward_is_named():
    verdict = guard.judge(
        {"wall": 1000.0, "monotonic": 10.0}, {"wall": 1300.0, "monotonic": 25.0}
    )
    assert verdict["state"] == guard.FORWARD
    assert verdict["trusted"] is False
    assert verdict["projected_epoch"] == 1015.0


def test_the_first_sample_has_no_evidence_either_way():
    verdict = guard.judge(None, {"wall": 1000.0, "monotonic": 10.0})
    assert verdict["state"] == guard.UNKNOWN
    assert "no previous sample" in verdict["reason"]


def test_a_monotonic_clock_that_did_not_advance_is_blind_not_ok():
    verdict = guard.judge(
        {"wall": 1000.0, "monotonic": 10.0}, {"wall": 1000.0, "monotonic": 10.0}
    )
    assert verdict["state"] == guard.BLIND
    assert verdict["trusted"] is False


def test_a_state_file_that_cannot_be_read_is_blind(tmp_path, monkeypatch):
    path = _state_file(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json")
    monkeypatch.setenv("ESTATE_HOME", str(tmp_path / "estate"))
    _reset_cache()
    # No kernel witness: nothing else can be judged against, so the guard fails closed.
    monkeypatch.setattr(guard, "kernel_epoch", lambda: None)
    verdict = guard.observe(path)
    assert verdict["state"] == guard.BLIND
    assert "could not be read" in verdict["reason"]


# --- the kernel witness -----------------------------------------------------


def test_the_kernel_witness_names_a_clock_that_is_two_years_behind():
    """The 2026-10-30 case, with no state file at all: the wall clock says 2024, the kernel's
    boot record plus the monotonic clock says 2026. The guard must see it on the first run."""
    now = time.time()
    verdict = guard.judge(
        None, {"wall": now - 2 * YEAR, "monotonic": 1000.0}, kernel=now
    )
    assert verdict["state"] == guard.BACKWARD
    assert verdict["trusted"] is False
    assert verdict["witness"] == "kernel"
    assert verdict["projected_epoch"] == now
    assert verdict["kernel_deviation_s"] == pytest_approx(-2 * YEAR, abs=1.0)


def test_the_kernel_witness_names_a_clock_that_is_two_years_ahead():
    now = time.time()
    verdict = guard.judge(
        None, {"wall": now + 2 * YEAR, "monotonic": 1000.0}, kernel=now
    )
    assert verdict["state"] == guard.FORWARD
    assert verdict["witness"] == "kernel"
    assert verdict["projected_epoch"] == now


def test_the_kernel_witness_agrees_with_a_healthy_clock():
    now = time.time()
    verdict = guard.judge(None, {"wall": now, "monotonic": 1000.0}, kernel=now + 0.4)
    assert verdict["state"] == guard.OK
    assert verdict["trusted"] is True
    assert verdict["witness"] == "kernel"


def test_the_real_host_kernel_witness_matches_the_real_wall_clock():
    """On this host the kernel's boot record plus CLOCK_MONOTONIC must track the wall clock
    within a couple of seconds, or the guard would cry wolf on a healthy host."""
    kernel = guard.kernel_epoch()
    assert kernel is not None
    assert abs(kernel - time.time()) < 5.0


def test_a_stale_sample_does_not_untrust_a_clock_the_kernel_vouches_for():
    """After the clock is corrected the stored sample is stale. The kernel vouches for the
    clock, so the verdict is ok and the sample is re-baselined -- otherwise the estate would
    stamp a projection forever."""
    now = time.time()
    verdict = guard.judge(
        {"wall": now - 2 * YEAR, "monotonic": 900.0},
        {"wall": now, "monotonic": 1000.0},
        kernel=now,
    )
    assert verdict["state"] == guard.OK
    assert verdict["trusted"] is True


# --- the ledger witness -----------------------------------------------------


def test_the_ledger_witness_names_a_clock_behind_the_estates_own_history():
    now = time.time()
    verdict = guard.judge(
        None, {"wall": now - 2 * YEAR, "monotonic": 1000.0}, ledger=now
    )
    assert verdict["state"] == guard.BACKWARD
    assert verdict["witness"] == "ledger"
    assert verdict["projected_epoch"] == now


def test_the_ledger_witness_is_silent_when_the_clock_is_ahead():
    now = time.time()
    verdict = guard.judge(None, {"wall": now, "monotonic": 1000.0}, ledger=now - 10)
    assert verdict["state"] == guard.UNKNOWN


# --- the stamp --------------------------------------------------------------


def test_a_regressed_clock_never_becomes_the_stamp(tmp_path, monkeypatch):
    path = _state_file(tmp_path)
    monkeypatch.setenv("ESTATE_HOME", str(tmp_path / "estate"))
    _reset_cache()
    # The kernel says the true time is a year ahead of the wall clock: the wall clock is
    # behind, so the stamp must be the kernel's time, not the wall clock's.
    truth = time.time() + 86400
    monkeypatch.setattr(guard, "kernel_epoch", lambda: truth)
    stamp = guard.stamp(path)
    assert stamp != "2024-01-01T00:00:00Z"
    assert guard.trusted_epoch(path) == pytest_approx(truth, abs=1.0)


def test_the_stamp_is_the_wall_clock_while_the_clock_agrees(tmp_path, monkeypatch):
    path = _state_file(tmp_path)
    _write_state(path, time.time() - 5, guard.monotonic() - 5)
    monkeypatch.setenv("ESTATE_HOME", str(tmp_path / "estate"))
    _reset_cache()
    assert abs(guard.trusted_epoch(path) - time.time()) < 5


def test_the_baseline_survives_a_bad_window(tmp_path, monkeypatch):
    """While the clock is untrusted the stored sample must keep the trusted wall reading and
    advance only the monotonic reference. Overwriting it with the regressed reading would
    destroy the baseline exactly when it is needed: the next tick would compare 2024 with 2024
    and call it fine."""
    path = _state_file(tmp_path)
    monkeypatch.setenv("ESTATE_HOME", str(tmp_path / "estate"))
    _reset_cache()
    truth = time.time() + 86400
    monkeypatch.setattr(guard, "kernel_epoch", lambda: truth)
    guard.commit(path)
    stored = json.loads(path.read_text())
    assert stored["wall"] == pytest_approx(truth, abs=1.0)
    assert stored.get("anchored") is True
    # The wall reading is not the naive wall clock: the regressed reading was refused.
    assert stored["wall"] > time.time() + 3600


def test_a_tick_that_detects_a_bad_clock_does_not_then_trust_it(tmp_path, monkeypatch):
    """The 2026-10-30 failure, exactly: the tick commits the sample, and the stamp that the
    same tick writes must still be the projection.

    The pre-2026-10-30 guard detected the fault and then overwrote its own baseline with the
    regressed reading, so the very next stamp trusted the clock it had just called a liar.
    This runs on the sample witness alone, with no kernel to hide behind."""
    path = _state_file(tmp_path)
    monkeypatch.setenv("ESTATE_HOME", str(tmp_path / "estate"))
    _reset_cache()
    monkeypatch.setattr(guard, "kernel_epoch", lambda: None)
    future = _poison_backward(path)
    verdict = guard.commit(path)
    assert verdict["state"] == guard.BACKWARD
    _reset_cache()
    # The stamp taken after the commit is still the projection, not the naive wall clock.
    assert guard.trusted_epoch(path) == pytest_approx(future + 60, abs=5.0)
    assert guard.trusted_epoch(path) > time.time() + 3600


# --- the door ---------------------------------------------------------------


def _fake_sysctl(tmp_path: Path, boot_epoch: float) -> Path:
    """A `sysctl` on PATH that reports a boot record the caller chooses.

    This is how a host whose kernel boot record is two years out is reproduced without
    touching the real clock: the production code has no test seam and needs none."""
    bindir = tmp_path / "fakebin"
    bindir.mkdir(parents=True, exist_ok=True)
    script = bindir / "sysctl"
    script.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "-n" ] && [ "$2" = "kern.boottime" ]; then\n'
        '  echo "{ sec = %d, usec = 0 } fake boot record"\n'
        "  exit 0\n"
        "fi\n"
        'exec /usr/sbin/sysctl "$@"\n' % int(boot_epoch)
    )
    script.chmod(0o755)
    return bindir


def _door(
    tmp_path: Path, *args: str, bindir: Path | None = None
) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "ESTATE_HOME": str(tmp_path / "estate"),
        "HOME": str(tmp_path),
    }
    if bindir is not None:
        env["PATH"] = f"{bindir}:{env['PATH']}"
    return subprocess.run(
        [str(DOOR), *args], capture_output=True, text=True, env=env, timeout=60
    )


def test_the_door_is_happy_when_the_clock_agrees(tmp_path):
    result = _door(tmp_path, "clock")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ok" in result.stdout


def test_the_door_refuses_a_clock_that_is_behind_the_kernel(tmp_path):
    """The kernel's boot record is two years in the future, so the wall clock is behind it."""
    boot = time.time() - guard.monotonic() + 2 * YEAR
    bindir = _fake_sysctl(tmp_path, boot)
    result = _door(tmp_path, "clock", bindir=bindir)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "backward" in result.stdout


def test_the_door_refuses_a_clock_that_is_ahead_of_the_kernel(tmp_path):
    boot = time.time() - guard.monotonic() - 2 * YEAR
    bindir = _fake_sysctl(tmp_path, boot)
    result = _door(tmp_path, "clock", bindir=bindir)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "forward" in result.stdout


def test_the_door_says_so_when_it_cannot_judge(tmp_path):
    path = _state_file(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json")
    bindir = _fake_sysctl(tmp_path, time.time() - guard.monotonic() + 2 * YEAR)
    result = _door(tmp_path, "clock", bindir=bindir)
    # The kernel still vouches for the clock, so a verdict is possible: the corrupt state
    # file is re-baselined, not a blindness.
    assert result.returncode == 1, result.stdout + result.stderr


def test_the_door_says_so_when_it_cannot_judge_at_all(tmp_path):
    """No kernel witness, no readable state: the guard has nothing to judge against and fails
    closed."""
    path = _state_file(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json")
    bindir = tmp_path / "emptybin"
    bindir.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "ESTATE_HOME": str(tmp_path / "estate"),
        "HOME": str(tmp_path),
        "PATH": f"{bindir}:/usr/bin:/bin",
    }
    result = subprocess.run(
        [str(DOOR), "clock"], capture_output=True, text=True, env=env, timeout=60
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "blind" in result.stdout.lower()


def test_the_door_prints_the_verdict_as_json(tmp_path):
    result = _door(tmp_path, "clock", "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    verdict = json.loads(result.stdout)
    assert verdict["state"] in (guard.OK, guard.UNKNOWN)
    assert "wall" in verdict and "monotonic" in verdict


# --- the writers ------------------------------------------------------------


def test_the_incident_ledger_is_not_stamped_with_a_regressed_clock(
    tmp_path, monkeypatch
):
    """The ledger is where the estate's memory of what went wrong lives. If it is stamped with
    a regressed clock, every later age, SLA and ordering computed from it is wrong."""
    loop = _load("incident_loop", "incident-loop.py")
    monkeypatch.setenv("ESTATE_HOME", str(tmp_path / "estate"))
    _reset_cache()
    # The kernel's clock is a day ahead of the wall clock: the wall clock is behind.
    truth = time.time() + 86400
    monkeypatch.setattr(loop.clock_guard, "kernel_epoch", lambda: truth)

    conn = loop.open_ledger(tmp_path / "estate" / "state" / "incidents.db")
    policy = loop.load_policy()
    try:
        row = loop.record_incident(
            conn,
            {
                "id": "clock-test-1",
                "source": "clock",
                "repo": "idp",
                "severity": "major",
                "blast": "main",
                "title": "the clock jumped backwards",
                "url": "",
            },
            policy,
        )
        first_seen = row["first_seen"]
    finally:
        conn.close()

    assert not first_seen.startswith("2024-01-01")
    assert first_seen.endswith("Z")
    # The trusted projection is in the future of the naive wall clock, not the regressed one.
    assert first_seen > time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time()))


def test_critical_watch_incident_ids_carry_a_trusted_stamp(tmp_path, monkeypatch):
    """The critical-watch incident id is a timestamp. On 2026-10-30 it produced
    estate-bus-20240101T000541Z.json: a real incident, filed under a date two years in the past."""
    watch = _load("critical_watch", "critical-watch.py")
    monkeypatch.setenv("ESTATE_HOME", str(tmp_path / "estate"))
    monkeypatch.setenv("ESTATE_STATE_DIR", str(tmp_path / "estate"))
    _reset_cache()
    truth = time.time() + 86400
    monkeypatch.setattr(watch.clock_guard, "kernel_epoch", lambda: truth)
    stamp = watch.now_iso()
    assert not stamp.startswith("2024-01-01")
    assert stamp.endswith("Z")


def pytest_approx(value, rel=None, abs=None):  # noqa: A002 - the local helper mirrors pytest's
    import pytest

    return pytest.approx(value, rel=rel, abs=abs)


if __name__ == "__main__":
    sys.exit(
        subprocess.run([sys.executable, "-m", "pytest", __file__, "-q"]).returncode
    )
