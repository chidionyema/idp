#!/usr/bin/env python3
"""clock-guard -- can the estate trust the host wall clock?

WHY. 2026-10-29. This host's wall clock fell back to 2024-01-01T00:00:00 at power-on and
stayed there for about nineteen minutes, until the time service corrected it forward. Six Pi
agent sessions, the Codex desktop profile and the estate's own incident files were created in
that window, and every one of them carried 2024-01-01, because the kernel was serving that
time. The kernel process start times prove the clock itself moved; Pi and Codex faithfully
recorded what they were given. A clock that lies is not a formatting problem: every timestamp
the estate writes -- session ids, incident ledgers, ticket ages, backoff windows -- becomes
wrong in the same second, silently.

WHAT IT IS. One module, one state file, one verdict. The wall clock is checked against
witnesses that it cannot argue with, in this order:

  A. the anchor  the last trusted reading of both clocks, kept in
     ~/.estate/state/clock-skew.json. It is the only witness that knows what the clock said
     before, so it decides first: relative inside one boot, absolute across a reboot.
  B. the ledger  the last timestamp the estate's own incident ledger recorded while its clock
     was sane (SELECT MAX(last_seen) FROM incidents, read only). Coarse, absolute, and
     independent of the anchor: it catches a clock that was already wrong when the anchor was
     taken.
  C. the kernel  kern.boottime plus CLOCK_MONOTONIC. A rate and consistency check only.

WHY THE KERNEL IS LAST. It is not an absolute witness of the wall clock on this host, and the
measurement says so exactly. On 2026-10-29 the clock was set back to 2024-01-01T00:00:00 at
power-on and the kernel booted 24 s later, with the boot record carrying that 2024 stamp. When
the time service corrected the clock forward by 89,245,001.563908 s, the boot record moved by
the same amount:

  1704067224.000002 + 89245001.563908 = 1793312225.563910

1704067224 is 2024-01-01T00:00:24Z, the stamp in the kernel's own boot record. So on macOS
kern.boottime follows the wall clock through a step, and kern.boottime + CLOCK_MONOTONIC is
almost exactly the wall clock -- which means it cannot witness a step, and a guard that treats
it as absolute is a guard that is blind exactly when it matters. It is kept as a consistency
check: on a host whose boot record does not follow the clock, a gross disagreement is still
evidence, and it is the last witness to be asked. It never vetoes the anchor or the ledger,
and it never supplies a projection while either of them can.

The verdict is one of five things:

  ok       a witness agrees that the wall clock has not moved
  backward the wall clock went backwards (it was set, or the host came up on a stale clock)
  forward  the wall clock jumped forwards faster than real time
  unknown  no witness has anything to say yet
  blind    no witness could be read, so no verdict is possible

The verdict carries the honest consequence: `projected_epoch` is the time the estate is allowed
to stamp with. While the wall clock is untrusted that is the projection from the witness that
detected the fault -- the last trusted reading plus the real time that has passed since it, or
the ledger's last sane timestamp -- never the regressed wall clock. A regressed timestamp is
not a timestamp; it is a lie that sorts badly and ages wrongly.

STATE. One JSON file, ~/.estate/state/clock-skew.json, holding the last trusted reading:

  {"wall": 1760000000.0, "monotonic": 29761.03, "at": "2026-10-30T06:22:19Z"}

While the clock is untrusted the file keeps the trusted wall reading, marks it "anchored" and
advances only the monotonic reference, so the baseline survives the bad window instead of being
overwritten by it. An anchored entry mixes two timelines, so it is compared absolutely and is
excluded from the wall-versus-monotonic skew test.

HOW TO USE IT.

  from clock_guard import stamp, trusted_epoch, observe, commit
  stamp()                 # an ISO stamp that is never a regressed wall clock
  observe()               # the verdict, without writing
  commit()                # the verdict, and the sample becomes the next comparison

EXIT CODES (the door that wraps this, bin/estate-incident-loop clock): 0 the clock is
trustworthy, 1 the wall clock is untrustworthy (backward or forward), 2 no verdict was possible
(blind). A check that cannot fail is not a check.
"""

from __future__ import annotations

import calendar
import json
import os
import re
import shutil
import sqlite3
import subprocess
import time
from pathlib import Path

OK = "ok"
BACKWARD = "backward"
FORWARD = "forward"
UNKNOWN = "unknown"
BLIND = "blind"

# A wall clock and a witness may legitimately differ by a little: NTP steps, a leap second, the
# scheduler losing the thread. Two seconds of slack absorbs the ordinary case; 5% of the
# interval absorbs a long interval whose measured duration is itself noisy.
SLACK_S = 2.0
SLACK_FRACTION = 0.05

# The kernel witness is a consistency check between two estimates of the same instant, so its
# tolerance is tight: the boot record is parsed to the microsecond and the residual on a
# healthy host is under a millisecond. 10 ppm of uptime absorbs the drift a host accumulates
# while its clock is slewed, and nothing else.
KERNEL_TOLERANCE_S = 2.0
KERNEL_DRIFT_FRACTION = 1e-5

_BOOTTIME = re.compile(r"sec\s*=\s*(\d+)(?:\D+usec\s*=\s*(\d+))?")


def state_root() -> Path:
    """Where the estate keeps its state. ESTATE_HOME wins, then ESTATE_STATE_DIR."""
    for name in ("ESTATE_HOME", "ESTATE_STATE_DIR"):
        value = os.environ.get(name, "").strip()
        if value:
            return Path(value)
    return Path.home() / ".estate"


def state_path() -> Path:
    return state_root() / "state" / "clock-skew.json"


def ledger_path() -> Path:
    """The incident ledger: the estate's own record of when it was last sane."""
    return state_root() / "state" / "incidents.db"


def monotonic() -> float:
    """CLOCK_MONOTONIC, in seconds. time.monotonic() is not used: on this macOS/Python pair
    it returned a near-zero value, and a monotonic reading that restarts is not a monotonic
    reading. clock_gettime is the authoritative call."""
    return time.clock_gettime(time.CLOCK_MONOTONIC)


def kernel_epoch() -> float | None:
    """The kernel's own estimate of the current time, for a consistency check.

    kern.boottime is the kernel's boot record and CLOCK_MONOTONIC counts from that boot, so
    their sum is the time the kernel believes it is. On this host it is NOT an absolute witness
    of the wall clock: macOS moves the boot record with the wall clock when the clock is
    stepped, so the sum tracks the wall clock almost exactly and cannot see a step. It is used
    only to check that the wall clock and the kernel's own clock are telling the same story,
    and it is the last witness asked. Returns None when the kernel will not say.
    """
    try:
        binary = shutil.which("sysctl")
        if binary is None:
            return None
        result = subprocess.run(  # noqa: S603 -- sysctl resolved from PATH, argv constant
            [binary, "-n", "kern.boottime"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    match = _BOOTTIME.search(result.stdout or "")
    if not match:
        return None
    boot = float(match.group(1))
    if match.group(2):
        boot += float(match.group(2)) / 1_000_000.0
    return boot + monotonic()


def ledger_epoch() -> float | None:
    """The last time the estate's own ledger says it was sane.

    A coarse, independent witness: the ledger rows written while the clock was good. The
    greatest last_seen wins, so rows written during a bad window (which are small) cannot drag
    it back. Returns None when there is no ledger or no readable row.
    """
    target = ledger_path()
    if not target.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{target}?mode=ro", uri=True, timeout=5)
        try:
            row = conn.execute("SELECT MAX(last_seen) AS ts FROM incidents").fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    if not row or not row[0]:
        return None
    try:
        return float(calendar.timegm(time.strptime(str(row[0]), "%Y-%m-%dT%H:%M:%SZ")))
    except (ValueError, OverflowError):
        return None


def sample() -> dict:
    """One reading of both clocks."""
    return {"wall": time.time(), "monotonic": monotonic()}


def _iso(epoch: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def load(path: Path | None = None) -> dict | None:
    """The previous sample, or None when there is none. Raises nothing: an unreadable state
    file is blindness, and blindness is a verdict, not an exception."""
    target = Path(path) if path else state_path()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if "wall" not in data or "monotonic" not in data:
        return None
    try:
        data["wall"] = float(data["wall"])
        data["monotonic"] = float(data["monotonic"])
    except (TypeError, ValueError):
        return None
    return data


def save(current: dict, path: Path | None = None) -> None:
    target = Path(path) if path else state_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(current)
    payload["at"] = _iso(current["wall"])
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(target)


def tolerance(monotonic_delta: float) -> float:
    return max(SLACK_S, SLACK_FRACTION * abs(monotonic_delta))


def kernel_tolerance(uptime: float) -> float:
    """How far the kernel's own estimate may differ from the wall clock before it is evidence."""
    return max(KERNEL_TOLERANCE_S, KERNEL_DRIFT_FRACTION * abs(uptime))


def _advance(previous: dict, current: dict) -> float:
    """Real seconds elapsed since the anchor was taken.

    Inside one boot this is the monotonic delta, which nothing can set. Across a reboot the
    monotonic clock restarts, so the only real time that can be proven here is the uptime of
    the current boot: a lower bound, because the power-off time is not knowable from here.
    """
    delta = current["monotonic"] - previous["monotonic"]
    if delta <= 0:
        delta = max(0.0, current["monotonic"])
    return delta


def judge(
    previous: dict | None,
    current: dict,
    kernel: float | None = None,
    ledger: float | None = None,
) -> dict:
    """Compare the readings and say what the wall clock did.

    Pure: no clock, no file, no state. The witnesses are passed in, so every branch is
    testable without touching the machine's real time.

    The order is the point: the anchor (what the clock said before) decides first, the ledger
    (what the estate itself recorded) second, and the kernel (a consistency check that
    follows the wall clock through a step on this host) last. A witness that cannot see the
    fault must never be able to overrule one that can.
    """
    verdict = {
        "state": UNKNOWN,
        "trusted": False,
        "wall": current["wall"],
        "monotonic": current["monotonic"],
        "wall_delta_s": None,
        "monotonic_delta_s": None,
        "skew_s": None,
        "projected_epoch": current["wall"],
        "reason": "",
        "witness": "none",
        "kernel_epoch": kernel,
        "kernel_deviation_s": None,
        "ledger_epoch": ledger,
        "reboot": False,
        "anchored": False,
    }

    # The kernel's deviation is recorded whenever the kernel can be reached, even when the
    # anchor or the ledger decides: a witness that was not asked still has something to say
    # about the diagnosis.
    if kernel is not None:
        verdict["kernel_deviation_s"] = round(current["wall"] - kernel, 3)

    # --- Witness A: the anchor. What the clock said the last time we looked. --------------
    if previous is not None:
        wall_delta = current["wall"] - previous["wall"]
        monotonic_delta = current["monotonic"] - previous["monotonic"]
        anchored = bool(previous.get("anchored"))
        reboot = monotonic_delta <= 0
        verdict["wall_delta_s"] = round(wall_delta, 3)
        verdict["monotonic_delta_s"] = round(monotonic_delta, 3)
        verdict["reboot"] = reboot
        verdict["anchored"] = anchored

        if anchored:
            # An anchored entry mixes two timelines: its wall is a projection and its
            # monotonic is the reading at the moment of the fault. Only an absolute
            # comparison against the projection is meaningful.
            if wall_delta < -SLACK_S:
                verdict["state"] = BACKWARD
                verdict["projected_epoch"] = previous["wall"] + _advance(
                    previous, current
                )
                verdict["witness"] = "anchor"
                verdict["reason"] = (
                    f"the wall clock is {abs(wall_delta):.0f}s behind the trusted anchor: "
                    "the clock is still regressed"
                )
                return verdict
        elif reboot:
            # The monotonic clock restarted: the host rebooted. The wall clock is then
            # compared with the anchor absolutely, because a power-off can legitimately
            # move it forward by any amount.
            if wall_delta < -SLACK_S:
                verdict["state"] = BACKWARD
                verdict["projected_epoch"] = previous["wall"] + _advance(
                    previous, current
                )
                verdict["witness"] = "anchor"
                verdict["reason"] = (
                    "the host rebooted (the monotonic clock restarted) and the wall clock "
                    f"is {abs(wall_delta):.0f}s behind the trusted anchor: the clock came "
                    "up on a stale time"
                )
                return verdict
        else:
            skew = wall_delta - monotonic_delta
            verdict["skew_s"] = round(skew, 3)
            tol = tolerance(monotonic_delta)
            if wall_delta < -tol:
                verdict["state"] = BACKWARD
                verdict["projected_epoch"] = previous["wall"] + _advance(
                    previous, current
                )
                verdict["witness"] = "anchor"
                verdict["reason"] = (
                    f"the wall clock went backwards {abs(wall_delta):.0f}s while real time "
                    f"advanced {monotonic_delta:.0f}s: it was set"
                )
                return verdict
            if skew > tol:
                verdict["state"] = FORWARD
                verdict["projected_epoch"] = previous["wall"] + _advance(
                    previous, current
                )
                verdict["witness"] = "anchor"
                verdict["reason"] = (
                    f"the wall clock jumped forward {skew:.0f}s ahead of real time: it was set"
                )
                return verdict

    # --- Witness B: the estate's own ledger. Coarse, absolute, independent of the anchor. ---
    if ledger is not None:
        behind = ledger - current["wall"]
        if behind > SLACK_S:
            verdict["state"] = BACKWARD
            verdict["projected_epoch"] = ledger
            verdict["witness"] = "ledger"
            verdict["reason"] = (
                f"the wall clock is {behind:.0f}s behind the estate's own incident ledger: "
                "the clock was already wrong when it was last sane"
            )
            return verdict

    # --- Witness C: the kernel. A consistency check, asked last, and never a veto. --------
    if kernel is not None:
        deviation = verdict["kernel_deviation_s"]
        tol = kernel_tolerance(current["monotonic"])
        if abs(deviation) > tol:
            verdict["state"] = BACKWARD if deviation < 0 else FORWARD
            verdict["witness"] = "kernel"
            if previous is not None:
                verdict["projected_epoch"] = previous["wall"] + _advance(
                    previous, current
                )
            else:
                # No anchor and no ledger: the kernel's own estimate is the only time
                # anybody can offer, and the disagreement is what proves it does not
                # follow the wall clock on this host.
                verdict["projected_epoch"] = kernel
            verdict["reason"] = (
                f"the wall clock is {abs(deviation):.0f}s "
                f"{'behind' if deviation < 0 else 'ahead of'} the kernel's own clock "
                "(the boot record plus the monotonic clock)"
            )
            return verdict

    # --- Nothing objected. ---------------------------------------------------------------
    if previous is not None:
        verdict["state"] = OK
        verdict["trusted"] = True
        verdict["projected_epoch"] = current["wall"]
        verdict["witness"] = "anchor"
        if verdict["reboot"]:
            verdict["reason"] = (
                "the host rebooted (the monotonic clock restarted) and the wall clock is "
                "not behind the trusted anchor: the reboot is not a clock fault"
            )
        else:
            verdict["reason"] = (
                "the wall clock and the monotonic clock agree within "
                f"{tolerance(verdict['monotonic_delta_s'] or 0.0):.1f}s"
            )
        return verdict

    if ledger is not None:
        verdict["state"] = OK
        verdict["trusted"] = True
        verdict["projected_epoch"] = current["wall"]
        verdict["witness"] = "ledger"
        verdict["reason"] = (
            "the wall clock is not behind the estate's own incident ledger"
        )
        return verdict

    verdict["reason"] = (
        "no previous sample and no ledger: there is no evidence either way"
    )
    if kernel is not None:
        verdict["reason"] += (
            "; the kernel's boot record agrees with the wall clock, but it follows the wall "
            "clock through a step, so it is not evidence of the wall clock's truth"
        )
    return verdict


def observe(path: Path | None = None, sampler=None, kernel=None, ledger=None) -> dict:
    """The verdict for right now, judged against the witnesses. Writes nothing."""
    target = Path(path) if path else state_path()
    current = (sampler or sample)()
    if kernel is None:
        kernel = kernel_epoch()
    if ledger is None:
        ledger = ledger_epoch()
    previous = load(target)
    if previous is None and target.exists():
        # The state file exists but cannot be read, so the anchor is gone. The ledger and
        # the kernel can still be asked: whatever they say, the state is re-baselined. Only
        # when no witness can be reached at all does the guard fail closed.
        verdict = judge(None, current, kernel, ledger)
        if verdict["state"] == UNKNOWN and kernel is None and ledger is None:
            verdict["state"] = BLIND
            verdict["trusted"] = False
            verdict["reason"] = (
                f"the state file {target} exists but could not be read and no other witness "
                "could be reached: no verdict is possible"
            )
            return verdict
        verdict["reason"] += (
            f"; the state file {target} could not be read and is re-baselined"
        )
        return verdict
    return judge(previous, current, kernel, ledger)


def commit(path: Path | None = None, sampler=None, kernel=None, ledger=None) -> dict:
    """The verdict for right now, and the state becomes the next comparison.

    While the clock is untrusted the state keeps the trusted wall reading, marks it anchored
    and advances only the monotonic reference. Overwriting it with the regressed reading would
    destroy the baseline exactly when it is needed: the next tick would compare 2024 with 2024
    and call it fine.
    """
    target = Path(path) if path else state_path()
    current = (sampler or sample)()
    verdict = observe(target, sampler=lambda: current, kernel=kernel, ledger=ledger)
    try:
        if verdict["state"] in (BACKWARD, FORWARD):
            save(
                {
                    "wall": float(verdict["projected_epoch"]),
                    "monotonic": current["monotonic"],
                    "anchored": True,
                },
                target,
            )
        else:
            save(current, target)
    except OSError as exc:
        verdict["state"] = BLIND
        verdict["reason"] = f"the state file {target} could not be written: {exc}"
    return verdict


def _cache_key(path: Path | None) -> str:
    return str(Path(path) if path else state_path())


_CACHE: dict = {"key": None, "monotonic": None, "verdict": None}


def _cached_verdict(path: Path | None = None) -> dict:
    """The verdict, reused for half a second.

    The kernel witness costs a sysctl call. Stamping a ledger row asks for the time several
    times in the same pass, and half a second is far below the resolution of anything the
    estate cares about, while a clock that moved inside that window would be moving by less
    than a second anyway."""
    key = _cache_key(path)
    now = monotonic()
    cached = _CACHE.get("verdict")
    if (
        cached is not None
        and _CACHE.get("key") == key
        and _CACHE.get("monotonic") is not None
    ):
        if now - _CACHE["monotonic"] < 0.5:
            return cached
    verdict = observe(path)
    _CACHE["key"] = key
    _CACHE["monotonic"] = now
    _CACHE["verdict"] = verdict
    return verdict


def trusted_epoch(path: Path | None = None) -> float:
    """The epoch the estate is allowed to stamp with.

    While the wall clock is untrusted this is the projection from the witness that detected the
    fault, so a regressed clock cannot write 2024 into a transcript, a ledger row or a ticket
    age."""
    verdict = _cached_verdict(path)
    if verdict["state"] in (BACKWARD, FORWARD):
        return float(verdict["projected_epoch"])
    return float(verdict["wall"])


def stamp(path: Path | None = None) -> str:
    """An ISO stamp that is never a regressed wall clock."""
    return _iso(trusted_epoch(path))


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="clock-guard", description=__doc__.split("\n")[0]
    )
    parser.add_argument("--json", action="store_true", help="print the verdict as JSON")
    parser.add_argument(
        "--no-write", action="store_true", help="judge without storing the sample"
    )
    args = parser.parse_args(argv)

    verdict = observe() if args.no_write else commit()
    if args.json:
        print(json.dumps(verdict, indent=2))
    else:
        print(f"{verdict['state']:<8} {verdict['reason']}")
        print(f"wall {verdict['wall']:.0f}  trusted {verdict['trusted']}")
    if verdict["state"] == BLIND:
        return 2
    if verdict["state"] in (BACKWARD, FORWARD):
        return 1
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
