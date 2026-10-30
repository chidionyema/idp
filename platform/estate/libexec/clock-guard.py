#!/usr/bin/env python3
"""clock-guard -- can the estate trust the host wall clock?

WHY. 2026-10-30. Six Pi agent sessions and the Codex desktop app were created on this host
between 00:00 and 00:20 real time, and every one of them stamped itself with the wall clock the
kernel was serving at that moment: 2024-01-01. The transcript filenames, the session UUIDv7
timestamps, the Codex Chromium profile files and the estate's own incident files all carry
2024-01-01, because they were all written while the kernel clock read 2024-01-01. The kernel
process start times prove the clock itself moved; Pi and Codex faithfully recorded what they
were given. A clock that lies is not a formatting problem: every timestamp the estate writes --
session ids, incident ledgers, ticket ages, backoff windows -- becomes wrong in the same second,
silently.

WHAT IT IS. One module, one state file, one verdict. The wall clock is checked against
witnesses that it cannot argue with:

  A. the kernel  kern.boottime (the kernel's boot record) plus CLOCK_MONOTONIC. The boot record
     is captured once, at boot, and does not follow a later change of the wall clock; the
     monotonic clock cannot be set at all. Together they are an estimate of the true current
     time, and they exist on the first run, with no history and no state file.
  B. the sample  the previous reading of both clocks, kept in ~/.estate/state/clock-skew.json.
     Relative, and needs a previous reading.
  C. the ledger  the last timestamp the estate's own incident ledger recorded while its clock
     was good. Absolute, coarse, and independent of both of the above.

The verdict is one of five things:

  ok       the wall clock agrees with the witnesses
  backward the wall clock went backwards (the clock was set, or the host woke from a stale RTC)
  forward  the wall clock jumped forwards faster than real time
  unknown  no witness has anything to say yet
  blind    no witness could be read, so no verdict is possible

The verdict carries the honest consequence: `projected_epoch` is the time the estate is allowed
to stamp with. While the wall clock is untrusted that is the projection from the witness that
detected the fault -- the kernel's own estimate, the last trusted reading plus the monotonic
elapsed time, or the ledger's last sane timestamp -- never the regressed wall clock. A
regressed timestamp is not a timestamp; it is a lie that sorts badly and ages wrongly.

STATE. One JSON file, ~/.estate/state/clock-skew.json, holding the last trusted reading:

  {"wall": 1760000000.0, "monotonic": 29761.03, "at": "2026-10-30T06:22:19Z"}

While the clock is untrusted the file keeps the trusted wall reading and advances only the
monotonic reference, so the baseline survives the bad window instead of being overwritten by it.

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
    """The kernel's own estimate of the true current time.

    kern.boottime is the kernel's boot record: captured once, at boot, from the clock as it
    then was. CLOCK_MONOTONIC counts from that boot and cannot be set. Their sum is the time
    the kernel believes it is, and it does not move when the wall clock is moved -- which is
    exactly what a witness has to do. Returns None when the kernel will not say.
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


def judge(
    previous: dict | None,
    current: dict,
    kernel: float | None = None,
    ledger: float | None = None,
) -> dict:
    """Compare the readings and say what the wall clock did.

    Pure: no clock, no file, no state. The witnesses are passed in, so every branch is
    testable without touching the machine's real time.
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
    }

    # Witness A: the kernel. Absolute, available on the first run, and measured to be
    # independent of the wall clock on this host: during the 2026-10-30 event the boot record
    # still read 2026-10-29 22:17:05 while the clock read 2024-01-01, so it does not follow a
    # later change of the wall clock. When the kernel can be asked, it decides.
    if kernel is not None:
        deviation = current["wall"] - kernel
        verdict["kernel_deviation_s"] = round(deviation, 3)
        if deviation < -SLACK_S:
            verdict["state"] = BACKWARD
            verdict["projected_epoch"] = kernel
            verdict["witness"] = "kernel"
            verdict["reason"] = (
                f"the wall clock is {abs(deviation):.0f}s behind the kernel's own clock "
                "(the boot record plus the monotonic clock): it was set, or the host woke "
                "from a stale clock"
            )
            return verdict
        if deviation > SLACK_S:
            verdict["state"] = FORWARD
            verdict["projected_epoch"] = kernel
            verdict["witness"] = "kernel"
            verdict["reason"] = (
                f"the wall clock is {deviation:.0f}s ahead of the kernel's own clock: it was set"
            )
            return verdict
        # The kernel agrees, so the wall clock is trustworthy now. A previous sample that
        # disagrees is stale -- the clock has been corrected since it was taken -- and it is
        # re-baselined rather than allowed to untrust a clock the kernel vouches for.
        if previous is not None:
            wall_delta = current["wall"] - previous["wall"]
            monotonic_delta = current["monotonic"] - previous["monotonic"]
            verdict["wall_delta_s"] = round(wall_delta, 3)
            verdict["monotonic_delta_s"] = round(monotonic_delta, 3)
            verdict["skew_s"] = round(wall_delta - monotonic_delta, 3)
        verdict["state"] = OK
        verdict["trusted"] = True
        verdict["projected_epoch"] = current["wall"]
        verdict["witness"] = "kernel"
        verdict["reason"] = (
            f"the wall clock agrees with the kernel's own clock within {SLACK_S:.1f}s"
        )
        return verdict

    # Witness B: the previous sample. Relative, and needs a previous reading.
    sample_blind = False
    if previous is not None:
        wall_delta = current["wall"] - previous["wall"]
        monotonic_delta = current["monotonic"] - previous["monotonic"]
        verdict["wall_delta_s"] = round(wall_delta, 3)
        verdict["monotonic_delta_s"] = round(monotonic_delta, 3)
        skew = wall_delta - monotonic_delta
        verdict["skew_s"] = round(skew, 3)
        tol = tolerance(monotonic_delta)
        if monotonic_delta <= 0:
            sample_blind = True
        elif wall_delta < -tol:
            verdict["state"] = BACKWARD
            verdict["projected_epoch"] = previous["wall"] + monotonic_delta
            verdict["witness"] = "sample"
            verdict["reason"] = (
                f"the wall clock went backwards {abs(wall_delta):.0f}s while real time "
                f"advanced {monotonic_delta:.0f}s: it was set, or the host woke from a "
                "stale clock"
            )
            return verdict
        elif skew > tol:
            verdict["state"] = FORWARD
            verdict["projected_epoch"] = previous["wall"] + monotonic_delta
            verdict["witness"] = "sample"
            verdict["reason"] = (
                f"the wall clock jumped forward {skew:.0f}s ahead of real time: it was set"
            )
            return verdict

    # Witness C: the estate's own ledger. Coarse, absolute, and only consulted when the
    # kernel and the sample have nothing to say.
    if kernel is None and ledger is not None and current["wall"] < ledger - SLACK_S:
        verdict["state"] = BACKWARD
        verdict["projected_epoch"] = ledger
        verdict["witness"] = "ledger"
        verdict["wall_delta_s"] = round(current["wall"] - ledger, 3)
        verdict["reason"] = (
            f"the wall clock is {ledger - current['wall']:.0f}s behind the estate's own "
            "incident ledger: the clock was already wrong when it was last sane"
        )
        return verdict

    if sample_blind:
        verdict["state"] = BLIND
        verdict["reason"] = (
            "the monotonic clock did not advance "
            f"({verdict['monotonic_delta_s']}s): no verdict is possible"
        )
        return verdict

    if previous is not None:
        verdict["state"] = OK
        verdict["trusted"] = True
        verdict["projected_epoch"] = current["wall"]
        verdict["reason"] = (
            f"the wall clock and the monotonic clock agree within "
            f"{tolerance(verdict['monotonic_delta_s'] or 0.0):.1f}s"
        )
        return verdict

    verdict["reason"] = "no previous sample: there is no evidence either way"
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
        # The state file exists but cannot be read. The kernel witness does not depend on it,
        # so a verdict is still possible; without the kernel there is nothing to judge against
        # and the guard fails closed.
        if kernel is None:
            verdict = judge(None, current, None, ledger)
            verdict["state"] = BLIND
            verdict["reason"] = (
                f"the state file {target} exists but could not be read and no other witness "
                "could be reached: no verdict is possible"
            )
            return verdict
        verdict = judge(None, current, kernel, ledger)
        verdict["reason"] += (
            f"; the state file {target} could not be read and is re-baselined"
        )
        return verdict
    return judge(previous, current, kernel, ledger)


def commit(path: Path | None = None, sampler=None, kernel=None, ledger=None) -> dict:
    """The verdict for right now, and the state becomes the next comparison.

    While the clock is untrusted the state keeps the trusted wall reading and advances only the
    monotonic reference. Overwriting it with the regressed reading would destroy the baseline
    exactly when it is needed: the next tick would compare 2024 with 2024 and call it fine.
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
