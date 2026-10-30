"""The clock guard: a wall clock that lies must be detected, refused, and never recorded.

WHY THESE TESTS. On 2026-10-29 this host's wall clock fell back to 2024-01-01T00:00:00 at
power-on and stayed there for about nineteen minutes, until the time service corrected it.
Six Pi agent sessions, the Codex desktop profile and the estate's own incident files were
created in that window, and every one of them carried 2024-01-01 -- because the kernel was
serving that time and nothing was watching. The damage was silent: the timestamps were
well-formed, and no gate, no sensor and no human read them as wrong.

So the guard has to do four things, and each one is falsifiable here:

  1. name the failure (backward, forward, blind) instead of rounding it away,
  2. refuse to stamp a regressed clock -- the ledger and the incident ids must carry a trusted
     projection, never the regressed wall clock,
  3. decide from a witness that cannot be fooled by the clock itself,
  4. be reachable as a door that returns a nonzero status when the clock is untrustworthy,
     because a check that cannot fail is not a check.

THE WITNESSES, IN THE ORDER THEY ARE ASKED.

  A. the anchor -- the last trusted reading of both clocks, in the estate's state directory.
     It is the only witness that knows what the clock said before, so it decides first:
     relative inside one boot, absolute across a reboot.
  B. the ledger -- the last timestamp the estate's own incident ledger recorded while its
     clock was sane. Coarse, absolute, and independent of the anchor.
  C. the kernel -- kern.boottime plus CLOCK_MONOTONIC. A consistency check only, and the last
     witness asked.

WHY THE KERNEL IS NOT FIRST. The first version of this guard made the kernel absolute, on the
belief that the kernel's boot record does not follow the wall clock. The measurement says the
opposite, and exactly: when the time service corrected the clock forward by 89,245,001.563908 s
on 2026-10-29, the boot record moved by the same amount, so kern.boottime + CLOCK_MONOTONIC
tracks the wall clock almost exactly and cannot witness a step. A guard that trusts the kernel
first is blind to the one failure it was built for, which is why the kernel is now checked last
and can never overrule the anchor or the ledger.

THE STATE FILE is per-test (a temporary ESTATE_HOME), so no test can touch the real estate.
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

import pytest

ROOT = Path(__file__).resolve().parents[1]
LIBEXEC = ROOT / "platform" / "estate" / "libexec"
DOOR = ROOT / "bin" / "estate-incident-loop"

YEAR = 365 * 24 * 3600

# --- the measured evidence of 2026-10-29, kept here so the arithmetic is asserted ---------
#
# The kernel's boot record, as read on 2026-10-30:
#   kern.boottime raw: { sec = 1793312225, usec = 563910 } Thu Oct 29 22:17:05 2026
# The kernel's own boot record in the unified log, stamped with the wall clock as it then was:
#   2024-01-01 00:00:24.000000+0000  Timesync  === system boot
# The correction, from the time service:
#   2026-10-29 22:36:00.293794+0000  dasd: Time change: Clock shifted by 89245001.563908 secs
BOOTTIME_SEC = 1793312225
BOOTTIME_USEC = 563910
CLOCK_STEP_S = 89245001.563908
TIMESYNC_BOOT_EPOCH = 1704067224.000000

# The wall clock at power-on: exactly 2024-01-01T00:00:00Z.
FALLBACK_WALL = 1704067200.0
# The wall clock at the moment the kernel booted, from the trusted 2026 timeline.
TRUSTED_WALL = 1793312225.563910


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


def _write_state(
    path: Path, wall: float, monotonic: float, anchored: bool = False
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"wall": wall, "monotonic": monotonic, "at": "2026-10-29T22:17:05Z"}
    if anchored:
        payload["anchored"] = True
    path.write_text(json.dumps(payload))


# --- the measured kernel behaviour ---------------------------------------------------


def test_the_kernel_boot_record_followed_the_wall_clock_step():
    """The measurement that demotes the kernel witness, asserted as arithmetic.

    The kernel booted 24 s after the clock was set back to 2024-01-01T00:00:00, so its boot
    record carried the 2024 stamp 1704067224. When the time service corrected the clock
    forward by 89,245,001.563908 s, the boot record moved by exactly the same amount. So
    kern.boottime + CLOCK_MONOTONIC tracks the wall clock through a step, and it cannot
    witness one."""
    boot_epoch = BOOTTIME_SEC + BOOTTIME_USEC / 1_000_000
    assert boot_epoch == pytest.approx(TRUSTED_WALL, abs=1e-6)
    stepped_back = boot_epoch - CLOCK_STEP_S
    # 1704067224 is 2024-01-01T00:00:24Z: the stamp in the kernel's own boot record.
    assert stepped_back == pytest.approx(TIMESYNC_BOOT_EPOCH, abs=2e-6)
    assert (
        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(TIMESYNC_BOOT_EPOCH))
        == "2024-01-01T00:00:24Z"
    )


def test_the_real_host_kernel_witness_tracks_the_real_wall_clock():
    """On this host the kernel's boot record plus CLOCK_MONOTONIC must track the wall clock
    within a couple of seconds. If it ever stops tracking it, the kernel witness has become a
    real witness and the guard should say so rather than assume."""
    kernel = guard.kernel_epoch()
    assert kernel is not None
    assert abs(kernel - time.time()) < 5.0


# --- witness A: the anchor ------------------------------------------------------------


def test_a_power_on_fallback_is_caught_by_the_trusted_anchor_across_a_reboot():
    """The 2026-10-29 case, exactly: the trusted anchor is a 2026 reading, the host rebooted
    (the monotonic clock restarted) and the wall clock came up on 2024. The anchor must name
    it, and the trusted wall reading must survive."""
    previous = {"wall": TRUSTED_WALL, "monotonic": 33752.88}
    current = {"wall": FALLBACK_WALL, "monotonic": 24.0}
    verdict = guard.judge(previous, current)
    assert verdict["state"] == guard.BACKWARD
    assert verdict["trusted"] is False
    assert verdict["witness"] == "anchor"
    assert verdict["reboot"] is True
    # The projection is the trusted anchor advanced by the time this boot has been up.
    assert verdict["projected_epoch"] == pytest.approx(TRUSTED_WALL + 24.0, abs=1e-6)


def test_the_kernel_witness_cannot_mask_the_anchor():
    """The kernel agrees with the regressed wall clock -- on this host it always does, because
    it follows the wall clock -- and the anchor still decides. If the kernel could overrule
    the anchor the guard would be blind to the very failure it exists for."""
    previous = {"wall": TRUSTED_WALL, "monotonic": 33752.88}
    current = {"wall": FALLBACK_WALL, "monotonic": 24.0}
    verdict = guard.judge(previous, current, kernel=FALLBACK_WALL)
    assert verdict["state"] == guard.BACKWARD
    assert verdict["witness"] == "anchor"
    assert verdict["kernel_deviation_s"] == pytest.approx(0.0, abs=1e-6)


def test_the_ledger_cannot_be_masked_by_the_kernel_either():
    """Same shape with no anchor at all: the ledger knows the estate was sane at 22:17 on
    2026-10-29, the kernel agrees with the regressed clock, and the ledger still decides."""
    current = {"wall": FALLBACK_WALL, "monotonic": 24.0}
    verdict = guard.judge(None, current, kernel=FALLBACK_WALL, ledger=TRUSTED_WALL)
    assert verdict["state"] == guard.BACKWARD
    assert verdict["witness"] == "ledger"
    assert verdict["projected_epoch"] == pytest.approx(TRUSTED_WALL, abs=1e-6)


def test_a_long_power_off_with_a_forward_wall_is_not_a_fault():
    """The host was off for ten days and the clock caught up on the way back. A reboot moves
    the wall clock forward by any amount, so this must not be called a forward jump."""
    previous = {"wall": TRUSTED_WALL, "monotonic": 33752.88}
    current = {"wall": TRUSTED_WALL + 10 * 86400, "monotonic": 30.0}
    verdict = guard.judge(previous, current)
    assert verdict["state"] == guard.OK
    assert verdict["trusted"] is True
    assert verdict["witness"] == "anchor"
    assert verdict["reboot"] is True
    assert "not a clock fault" in verdict["reason"]


def test_a_healthy_host_is_ok():
    now = time.time()
    verdict = guard.judge(
        {"wall": now - 5.0, "monotonic": 100.0}, {"wall": now, "monotonic": 105.0}
    )
    assert verdict["state"] == guard.OK
    assert verdict["trusted"] is True
    assert verdict["witness"] == "anchor"
    assert verdict["projected_epoch"] == pytest.approx(now, abs=1e-6)


def test_a_clock_that_went_backwards_inside_one_boot_is_named_and_measured():
    verdict = guard.judge(
        {"wall": 1000.0, "monotonic": 10.0}, {"wall": 500.0, "monotonic": 15.0}
    )
    assert verdict["state"] == guard.BACKWARD
    assert verdict["trusted"] is False
    assert verdict["witness"] == "anchor"
    assert verdict["wall_delta_s"] == -500.0
    assert verdict["skew_s"] == -505.0
    assert verdict["projected_epoch"] == pytest.approx(1005.0, abs=1e-6)
    assert "backwards" in verdict["reason"]


def test_a_clock_that_jumped_forward_inside_one_boot_is_named():
    verdict = guard.judge(
        {"wall": 1000.0, "monotonic": 10.0}, {"wall": 1300.0, "monotonic": 25.0}
    )
    assert verdict["state"] == guard.FORWARD
    assert verdict["trusted"] is False
    assert verdict["witness"] == "anchor"
    assert verdict["projected_epoch"] == pytest.approx(1015.0, abs=1e-6)


def test_an_anchored_entry_is_compared_absolutely_not_by_skew():
    """An anchored entry mixes two timelines: its wall is a projection and its monotonic is
    the reading at the moment of the fault. Comparing the two against each other would be
    meaningless, so the comparison is absolute."""
    previous = {"wall": TRUSTED_WALL, "monotonic": 33752.88, "anchored": True}
    current = {"wall": TRUSTED_WALL + 10.0, "monotonic": 33762.88}
    verdict = guard.judge(previous, current)
    assert verdict["state"] == guard.OK
    assert verdict["anchored"] is True
    assert verdict["skew_s"] is None


def test_an_anchored_entry_still_names_a_clock_that_is_still_regressed():
    previous = {"wall": TRUSTED_WALL, "monotonic": 33752.88, "anchored": True}
    current = {"wall": FALLBACK_WALL, "monotonic": 33762.88}
    verdict = guard.judge(previous, current)
    assert verdict["state"] == guard.BACKWARD
    assert verdict["witness"] == "anchor"
    assert "still regressed" in verdict["reason"]


# --- witness B: the ledger ------------------------------------------------------------


def test_the_ledger_witness_names_a_clock_behind_the_estates_own_history():
    now = time.time()
    verdict = guard.judge(
        None, {"wall": now - 2 * YEAR, "monotonic": 1000.0}, ledger=now
    )
    assert verdict["state"] == guard.BACKWARD
    assert verdict["witness"] == "ledger"
    assert verdict["projected_epoch"] == pytest.approx(now, abs=1e-6)


def test_the_ledger_witness_is_silent_when_the_clock_is_ahead():
    now = time.time()
    verdict = guard.judge(None, {"wall": now, "monotonic": 1000.0}, ledger=now - 10)
    assert verdict["state"] == guard.OK
    assert verdict["witness"] == "ledger"


def test_a_host_with_no_anchor_and_no_ledger_has_no_evidence_either_way():
    verdict = guard.judge(None, {"wall": 1000.0, "monotonic": 10.0})
    assert verdict["state"] == guard.UNKNOWN
    assert verdict["trusted"] is False
    assert "no evidence either way" in verdict["reason"]


def test_the_kernel_witness_alone_is_not_evidence_of_the_wall_clock():
    """The kernel agrees with the wall clock -- it follows it through a step -- so on a host
    with no anchor and no ledger the kernel's agreement proves nothing. The verdict says so
    instead of pretending the clock is vouched for."""
    now = time.time()
    verdict = guard.judge(None, {"wall": now, "monotonic": 1000.0}, kernel=now + 0.4)
    assert verdict["state"] == guard.UNKNOWN
    assert verdict["trusted"] is False
    assert "not evidence of the wall clock's truth" in verdict["reason"]


def test_the_kernel_witness_fires_when_the_host_does_not_track_the_clock():
    """On a host whose boot record does not follow the wall clock, a gross disagreement is
    real evidence -- and it is asked only when the anchor and the ledger are silent."""
    now = time.time()
    verdict = guard.judge(
        None, {"wall": now - 2 * YEAR, "monotonic": 1000.0}, kernel=now
    )
    assert verdict["state"] == guard.BACKWARD
    assert verdict["witness"] == "kernel"
    assert verdict["projected_epoch"] == pytest.approx(now, abs=1e-6)


def test_the_kernel_witness_never_overrules_a_ledger_that_objects():
    now = time.time()
    verdict = guard.judge(
        None,
        {"wall": now - 2 * YEAR, "monotonic": 1000.0},
        kernel=now - 2 * YEAR,
        ledger=now,
    )
    assert verdict["state"] == guard.BACKWARD
    assert verdict["witness"] == "ledger"


# --- the state file -------------------------------------------------------------------


def test_a_state_file_that_cannot_be_read_is_blind_with_no_witness(
    tmp_path, monkeypatch
):
    path = _state_file(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json")
    monkeypatch.setenv("ESTATE_HOME", str(tmp_path / "estate"))
    _reset_cache()
    monkeypatch.setattr(guard, "kernel_epoch", lambda: None)
    monkeypatch.setattr(guard, "ledger_epoch", lambda: None)
    verdict = guard.observe(path)
    assert verdict["state"] == guard.BLIND
    assert "could not be read" in verdict["reason"]


def test_a_corrupt_state_file_is_repaired_by_the_ledger(tmp_path, monkeypatch):
    """The ledger is independent of the state file, so a corrupt state file does not blind the
    guard when the ledger can still be asked."""
    path = _state_file(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json")
    monkeypatch.setenv("ESTATE_HOME", str(tmp_path / "estate"))
    _reset_cache()
    now = time.time()
    monkeypatch.setattr(guard, "kernel_epoch", lambda: None)
    monkeypatch.setattr(guard, "ledger_epoch", lambda: now)
    verdict = guard.observe(path)
    assert verdict["state"] == guard.OK
    assert verdict["witness"] == "ledger"
    assert "re-baselined" in verdict["reason"]


def test_the_baseline_survives_a_bad_window(tmp_path, monkeypatch):
    """While the clock is untrusted the stored sample must keep the trusted wall reading and
    advance only the monotonic reference. Overwriting it with the regressed reading would
    destroy the baseline exactly when it is needed: the next tick would compare 2024 with 2024
    and call it fine."""
    path = _state_file(tmp_path)
    monkeypatch.setenv("ESTATE_HOME", str(tmp_path / "estate"))
    _reset_cache()
    truth = time.time() + 86400
    _write_state(path, truth, guard.monotonic() - 60)
    verdict = guard.commit(path)
    assert verdict["state"] == guard.BACKWARD
    stored = json.loads(path.read_text())
    # The stored wall is the trusted reading advanced by the real time that has passed since
    # it was taken -- not the regressed reading, and not the stale anchor either.
    assert stored["wall"] == pytest.approx(truth + 60, abs=2.0)
    assert stored.get("anchored") is True
    # The wall reading is not the naive wall clock: the regressed reading was refused.
    assert stored["wall"] > time.time() + 3600


def test_a_tick_that_detects_a_bad_clock_does_not_then_trust_it(tmp_path, monkeypatch):
    """The pre-2026-10-30 guard detected the fault and then overwrote its own baseline with
    the regressed reading, so the very next stamp trusted the clock it had just called a
    liar. This runs on the anchor alone, with no kernel and no ledger to hide behind."""
    path = _state_file(tmp_path)
    monkeypatch.setenv("ESTATE_HOME", str(tmp_path / "estate"))
    _reset_cache()
    monkeypatch.setattr(guard, "kernel_epoch", lambda: None)
    monkeypatch.setattr(guard, "ledger_epoch", lambda: None)
    future = time.time() + 86400
    _write_state(path, future, guard.monotonic() - 60)
    verdict = guard.commit(path)
    assert verdict["state"] == guard.BACKWARD
    _reset_cache()
    # The stamp taken after the commit is still the projection, not the naive wall clock.
    assert guard.trusted_epoch(path) == pytest.approx(future + 60, abs=5.0)
    assert guard.trusted_epoch(path) > time.time() + 3600


def test_a_healthy_tick_writes_a_fresh_sample(tmp_path, monkeypatch):
    path = _state_file(tmp_path)
    monkeypatch.setenv("ESTATE_HOME", str(tmp_path / "estate"))
    _reset_cache()
    monkeypatch.setattr(guard, "kernel_epoch", lambda: None)
    monkeypatch.setattr(guard, "ledger_epoch", lambda: None)
    now = time.time()
    _write_state(path, now - 5, guard.monotonic() - 5)
    verdict = guard.commit(path)
    assert verdict["state"] == guard.OK
    stored = json.loads(path.read_text())
    assert stored.get("anchored") is None
    assert stored["wall"] == pytest.approx(now, abs=5.0)


# --- the door -------------------------------------------------------------------------


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
    assert result.stdout.strip()


def test_the_door_refuses_a_clock_that_is_behind_the_kernel(tmp_path):
    """The kernel's boot record is two years in the future, so the wall clock is behind it.
    This is a host whose boot record does not follow the wall clock: the kernel is the only
    witness, and it decides."""
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


def test_the_door_refuses_a_clock_that_is_behind_the_trusted_anchor_after_a_reboot(
    tmp_path,
):
    """Through the real door: a trusted anchor a day ahead of the wall clock, a host that
    rebooted, and a kernel boot record that agrees with the wall clock. The anchor must
    decide, and the kernel's agreement must not overrule it."""
    state = tmp_path / "estate" / "state" / "clock-skew.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    _write_state(state, time.time() + 86400, guard.monotonic() + 5)
    bindir = _fake_sysctl(tmp_path, time.time() - guard.monotonic())
    result = _door(tmp_path, "clock", bindir=bindir)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "backward" in result.stdout
    assert "rebooted" in result.stdout


def test_the_door_says_so_when_it_cannot_judge(tmp_path):
    path = _state_file(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json")
    bindir = _fake_sysctl(tmp_path, time.time() - guard.monotonic() + 2 * YEAR)
    result = _door(tmp_path, "clock", bindir=bindir)
    # The kernel still disagrees with the wall clock, so a verdict is possible: the corrupt
    # state file is re-baselined, not a blindness.
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


# --- the writers ----------------------------------------------------------------------


def test_the_incident_ledger_is_not_stamped_with_a_regressed_clock(
    tmp_path, monkeypatch
):
    """The ledger is where the estate's memory of what went wrong lives. If it is stamped with
    a regressed clock, every later age, SLA and ordering computed from it is wrong."""
    loop = _load("incident_loop", "incident-loop.py")
    monkeypatch.setenv("ESTATE_HOME", str(tmp_path / "estate"))
    _reset_cache()
    # The trusted anchor says the clock is a day ahead of the wall clock: the wall clock is
    # behind, so the stamp must be the anchor's projection, not the wall clock's.
    truth = time.time() + 86400
    _write_state(
        tmp_path / "estate" / "state" / "clock-skew.json", truth, guard.monotonic() - 60
    )
    _reset_cache()

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
    """The critical-watch incident id is a timestamp. On 2026-10-29 it produced
    estate-bus-20240101T000541Z.json: a real incident, filed under a date two years in the
    past."""
    watch = _load("critical_watch", "critical-watch.py")
    monkeypatch.setenv("ESTATE_HOME", str(tmp_path / "estate"))
    monkeypatch.setenv("ESTATE_STATE_DIR", str(tmp_path / "estate"))
    _reset_cache()
    truth = time.time() + 86400
    _write_state(
        tmp_path / "estate" / "state" / "clock-skew.json", truth, guard.monotonic() - 60
    )
    _reset_cache()
    stamp = watch.now_iso()
    assert not stamp.startswith("2024-01-01")
    assert stamp.endswith("Z")
    assert stamp > time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time()))


if __name__ == "__main__":
    sys.exit(
        subprocess.run([sys.executable, "-m", "pytest", __file__, "-q"]).returncode
    )
