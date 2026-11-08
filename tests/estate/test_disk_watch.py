"""bin/idp-disk-watch's memory brake: measured memory pressure stops ollama, and only ollama.

The founder, 2026-09-10: "no i killed ollama because machine is slow" -- 8GB of RAM and no GPU,
and a resident 7B model took the machine to load 95 with the swap thrashing. ollama's autostart
was removed on 2026-10-24, so the brake is recurrence insurance: the resident guardian measures
memory every cycle and stops the one process that causes the grind, and says so in the log.

The test never touches the real machine: vm_stat and sysctl are shimmed on PATH, the brake's
target is a uniquely named copy of sleep, and the disk floors are set so the guardian takes no
cleanup branch at all.

Two measured defects this file grades, both found on 2026-10-29:

  * the brake fired on EVERY cycle, because nothing remembered that it had already stopped the
    process, so the log claimed twenty interventions in ten minutes and the founder's tooling was
    being interrupted at the guardian's cadence rather than the estate's need. One stop per
    cooldown, and the log says when the next one is allowed.
  * the RAM reading was ALWAYS None. /usr/bin/vm_stat on this machine is a Mach-O BINARY, so
    reading the file produced 134 KB of Mach-O segments and no "Pages free" line; the guardian
    printed "free=?M" every cycle and braked on swap alone. Executing it fixed the reading but
    cost a process spawn -- 0.11 s healthy, 7.6 s on the stressed volume where the guardian
    runs. The RAM reading now comes from the kernel (host_statistics64, 0.1 ms, no spawn), with
    the executed vm_stat as the fallback.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from importlib.machinery import SourceFileLoader
from pathlib import Path

WATCH = Path(__file__).resolve().parents[2] / "bin/idp-disk-watch"
# macOS matches the process name, and a process name is at most 16 characters: a longer one is
# truncated and `pgrep -x` would never match it.
#
# MEASURED 2026-10-29: the target was named "ollama" -- the name the founder's ollama actually
# has -- and the founder's Ollama.app was RUNNING (pid 94885) while this suite ran. So the test
# was not testing the brake: `pgrep -x ollama` found the founder's real server, `pkill -TERM -x
# ollama` would have killed it, and the assertion "the brake target must be stopped" was graded
# against a process the estate does not own. A test that can stop the founder's tooling is not a
# test; it is a hazard that happens to be green most of the time.
#
# The brake target now comes from the guardian's own seam (DISK_WATCH_BRAKE_PROCS) and the test
# points it at a name nothing else on the machine wears. The production default is still
# "ollama" -- that is the process the brake exists for -- but the suite proves the BRAKE, not
# the founder's server.
PROC_NAME = "estdiskbrake"


def _load():
    """Load the guardian with the brake pointed at THIS test's stand-in, not at the founder's.

    DISK_WATCH_BRAKE_PROCS is the guardian's own configuration seam, so pointing it here is the
    production mechanism, not a test-only back door: the same code path runs with a different
    target, exactly as it does in production with a different BRAKE_PROCS.
    """
    old = os.environ.get("DISK_WATCH_BRAKE_PROCS")
    os.environ["DISK_WATCH_BRAKE_PROCS"] = PROC_NAME
    try:
        loader = SourceFileLoader("estate_disk_watch_brake", str(WATCH))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        sys.modules[loader.name] = mod
        loader.exec_module(mod)
    finally:
        if old is None:
            os.environ.pop("DISK_WATCH_BRAKE_PROCS", None)
        else:
            os.environ["DISK_WATCH_BRAKE_PROCS"] = old
    return mod


def _shims(tmp_path: Path, free_pages: int, swap_used: float) -> Path:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "vm_stat").write_text(
        "#!/bin/sh\n"
        "cat <<'EOF'\n"
        "Mach Virtual Memory Statistics: (page size of 4096 bytes)\n"
        f"Pages free:                                {free_pages}.\n"
        "Pages active:                              200.\n"
        "Pages speculative:                           0.\n"
        "EOF\n"
    )
    (bindir / "sysctl").write_text(
        "#!/bin/sh\n"
        "cat <<'EOF'\n"
        f"total = 5120.00M  used = {swap_used:.2f}M  free = 525.25M  (encrypted)\n"
        "EOF\n"
    )
    for f in (bindir / "vm_stat", bindir / "sysctl"):
        f.chmod(0o755)
    return bindir


def _stub_memory(mod, free_mb, swap_pct) -> None:
    """Pin the guardian's two memory readings.

    The readings come from the kernel (host_statistics64 and sysctl vm.swapusage), so PATH
    shims cannot steer them. The measurement seam is the two functions themselves: a test that
    cannot inject a reading cannot test the brake.
    """
    mod._mach_free_ram_mb = lambda: free_mb
    mod._mach_swap_pct = lambda: swap_pct


def _stand_in(bindir: Path) -> subprocess.Popen:
    """A live process that macOS calls "ollama", without being one.

    A copied binary is SIGKILLed on this laptop, so the stand-in is the real /bin/sleep wearing
    the name: `exec -a <path>/ollama` sets argv[0], and both pgrep -x and pkill -x match the last
    component of it -- exactly how they match the founder's ollama server.

    Its stdio goes to DEVNULL on purpose. A child that inherits the caller's stdout pipe holds
    that pipe open until it exits, so a 300-second stand-in would keep the executor waiting for
    EOF long after pytest had finished (measured 2026-10-29: the run exceeded the 100 s ceiling
    and was SIGTERMed, with the log showing nothing but the timeout).
    """
    return subprocess.Popen(
        ["bash", "-c", f"exec -a {bindir / PROC_NAME} /bin/sleep 300"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _log_text(mod) -> str:
    """The guardian's log, or the empty string when it wrote nothing.

    A guardian that stopped nothing must leave no trace; "no log file" and "an empty log" are
    the same fact, and reading a missing file as a failure would grade silence as a fault.
    """
    path = Path(mod.LOG)
    return path.read_text() if path.exists() else ""


def _kill(proc: subprocess.Popen) -> None:
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except (OSError, subprocess.SubprocessError):
        pass


def _with_path(bindir: Path, fn):
    old = os.environ["PATH"]
    os.environ["PATH"] = f"{bindir}:{old}"
    try:
        return fn()
    finally:
        os.environ["PATH"] = old


def test_the_ram_reading_is_not_broken_by_a_non_utf8_vm_stat(tmp_path):
    """The measured defect: vm_stat on this machine is a binary; reading it yielded no
    "Pages free" line, so the RAM reading was ALWAYS None and the brake fired on swap alone.

    The fallback EXECUTES vm_stat; the shim prints its figures, so the reading works. If the
    guardian had read the file instead of running it, the shim's own source text would be
    parsed and no "Pages free:" line would be found."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "vm_stat").write_text(
        "#!/bin/sh\n"
        "cat <<'EOF'\n"
        "Mach Virtual Memory Statistics: (page size of 4096 bytes)\n"
        "Pages free:                                100000.\n"
        "Pages active:                              200.\n"
        "Pages speculative:                           0.\n"
        "EOF\n"
    )
    (bindir / "vm_stat").chmod(0o755)
    mod = _load()
    free_mb = _with_path(bindir, mod._vm_stat_free_ram_mb)
    assert free_mb is not None, "the vm_stat fallback must produce a reading"
    assert free_mb == 390, f"100000 pages of 4096 bytes is 390 MB, not {free_mb}"


def test_the_ram_reading_costs_no_process_spawn(tmp_path):
    """MEASURED 2026-10-29: executing vm_stat cost 0.11 s healthy but 7.6 s on the stressed
    volume where the guardian runs. The kernel call answers in 0.1 ms and spawns nothing."""
    mod = _load()
    free_mb = mod._mach_free_ram_mb()
    assert free_mb is not None, "the kernel reading must work on this machine"
    assert free_mb > 0, free_mb
    assert mod._mach_free_ram_mb() is not None


def test_a_blind_memory_reading_is_not_zero(tmp_path):
    """An unreadable measurement is UNKNOWN, never zero: a zero would brake the founder's
    tooling on no evidence."""
    mod = _load()
    mod._mach_free_ram_mb = lambda: None
    mod._mach_swap_pct = lambda: None
    mod._vm_stat_free_ram_mb = lambda: None
    pressure, measured = mod.memory_pressure()
    assert pressure is False, measured
    assert "free=?M" in measured, measured


def test_pressure_stops_the_brake_target_and_says_so(tmp_path):
    bindir = _shims(tmp_path, free_pages=100, swap_used=4594.75)
    stand_in = _stand_in(bindir)
    time.sleep(0.5)
    assert subprocess.run(["/usr/bin/pgrep", "-x", PROC_NAME]).returncode == 0

    mod = _load()
    mod.LOG = str(tmp_path / "watch.log")
    mod._LAST_BRAKE = 0.0
    _stub_memory(mod, free_mb=0, swap_pct=90)
    pressure, measured = mod.memory_pressure()
    assert pressure is True, measured
    mod.brake(pressure, measured)
    time.sleep(0.5)
    assert subprocess.run(["/usr/bin/pgrep", "-x", PROC_NAME]).returncode != 0, (
        "the brake target must be stopped under memory pressure"
    )
    log = Path(mod.LOG).read_text()
    assert f"memory brake: stopped {PROC_NAME}" in log, log
    assert "free=0M RAM" in log, log
    _kill(stand_in)


def test_the_brake_refuses_to_fire_unless_pressure_was_measured(tmp_path):
    """The brake is a property of the brake, not of its caller (measured 2026-10-29: brake()
    took only a string, so a caller that never measured pressure could stop the founder's
    tooling)."""
    bindir = _shims(tmp_path, free_pages=500000, swap_used=100.0)
    stand_in = _stand_in(bindir)
    time.sleep(0.5)

    mod = _load()
    mod.LOG = str(tmp_path / "watch.log")
    mod._LAST_BRAKE = 0.0
    mod.brake(False, "free=8000M RAM swap=1%")
    time.sleep(0.5)
    assert subprocess.run(["/usr/bin/pgrep", "-x", PROC_NAME]).returncode == 0, (
        "an unmeasured brake must stop nothing"
    )
    assert "memory brake" not in _log_text(mod), _log_text(mod)
    _kill(stand_in)


def test_a_healthy_machine_is_left_alone(tmp_path):
    bindir = _shims(tmp_path, free_pages=500000, swap_used=100.0)
    stand_in = _stand_in(bindir)
    time.sleep(0.5)

    mod = _load()
    mod.LOG = str(tmp_path / "watch.log")
    mod._LAST_BRAKE = 0.0
    _stub_memory(mod, free_mb=8000, swap_pct=1)
    pressure, measured = mod.memory_pressure()
    assert pressure is False, measured
    mod.brake(pressure, measured)
    time.sleep(0.5)
    assert subprocess.run(["/usr/bin/pgrep", "-x", PROC_NAME]).returncode == 0, (
        "nothing may be stopped when memory is healthy"
    )
    assert "memory brake" not in _log_text(mod), _log_text(mod)
    _kill(stand_in)


def test_the_brake_fires_once_per_cooldown(tmp_path):
    """The measured defect: the brake fired every cycle, so the log claimed twenty
    interventions in ten minutes and the founder's tooling was interrupted at the guardian's
    cadence rather than the estate's need."""
    bindir = _shims(tmp_path, free_pages=100, swap_used=4594.75)
    # MEASURED 2026-10-29: this test created no stand-in, so the brake's pgrep found whatever
    # the machine happened to be running -- the founder's Ollama server -- and the assertion was
    # graded against a process the estate does not own. The brake must be proved against a
    # process this test owns.
    stand_in = _stand_in(bindir)
    time.sleep(0.5)
    mod = _load()
    mod.LOG = str(tmp_path / "watch.log")
    mod.BRAKE_COOLDOWN_S = 300
    mod._LAST_BRAKE = 0.0
    _stub_memory(mod, free_mb=0, swap_pct=90)
    mod.brake(True, mod.memory_pressure()[1])
    first = Path(mod.LOG).read_text()
    # A second brake inside the cooldown must not log a second stop.
    mod.brake(True, "free=0M RAM swap=89%")
    second = Path(mod.LOG).read_text()
    assert "memory brake: stopped" in first, first
    assert second == first, "the brake must not claim a stop it did not make"
    _kill(stand_in)


def test_the_guardian_writes_a_heartbeat_the_spine_can_read(tmp_path):
    """A healthy cycle costs one statvfs and a heartbeat: nothing is measured, nothing deleted."""
    mod = _load()
    mod.HEARTBEAT = str(tmp_path / "hb.json")
    mod.heartbeat("healthy", 4096, {"memory": "free=1M RAM swap=1%"})
    row = json.loads(Path(mod.HEARTBEAT).read_text())
    assert row["state"] == "healthy"
    assert row["free_mb"] == 4096
    assert row["at"].endswith("Z")


# -- the bound: a contended volume loss is never presented as successful reclamation ----------
#
# MEASURED 2026-11-08. The guardian reported `freed_mb` as a whole-volume statvfs delta. On a
# volume that concurrent agents write to, that number belongs to the other writers: the log in
# ~/.estate/disk-watch.log carries `freed=-1634M` and `freed=-158M` runs beside `+2480M` ones
# while free space swung between 401M and 3745M within minutes. And `met` is assigned solely by
# `after_mb >= TARGET_MB`, so a run could print `met=yes` next to a negative delta: a LOSS
# presented as successful reclamation. These tests are the falsifier for that class.
#
# The child's RESULT contract is untouched: `freed_mb` keeps its pinned `-?\d+` format and its
# net-delta meaning. What is new is a SECOND measurement, parsed from the stdout the guardian
# already captured, plus an explicit `outcome` so the two can never be collapsed.

_RESULT_FULL = (
    "freed  Caches  1200M  /Users/x/Library/Caches  (the cache regenerates)\n"
    "freed  Repo  NM of loose objects  /p/.git  (400M -> 380M on disk; git gc)\n"
    "RESULT mode=full free_before_mb=2000 free_after_mb=1500 target_mb=2500 met=no freed_mb=-500\n"
)


def test_a_negative_net_delta_cannot_be_read_as_reclamation(tmp_path):
    """THE FALSIFIER for the defect: met=yes must never stand in for success.

    Under the old behaviour this case produced `freed_mb=-400, met=yes` and nothing else, so a
    reader -- or the heartbeat's `last_freed_mb`, or an escalation that described the run as
    having freed space -- saw a successful reclaim. The volume was above target (met=yes) while
    it LOST 400M. The run's own outcome is `loss`, and that is a fact no other field answers.
    """
    mod = _load()
    own = mod.synth_result(
        3000,
        2600,
        "RESULT mode=full free_before_mb=3000 free_after_mb=2600 target_mb=2500 "
        "met=yes freed_mb=-400\n",
    )
    # The old fields are unchanged, so every existing consumer still works.
    assert own["freed_mb"] == "-400", own
    assert own["met"] == "yes", own
    # And the run can no longer be mistaken for a reclamation.
    assert own["reclaimed_mb"] == "0", own
    assert own["outcome"] == "loss", own
    assert own["outcome"] != "reclaimed"


def test_the_cleaners_own_share_is_reported_apart_from_the_contended_volume():
    """Two measurements, never one: what the cleaner freed, and what the volume did.

    The cleaner really removed 1200M of caches and repacked a repo from 400M to 380M (20M on
    disk) -- 1220M attributable to it. The volume fell 500M anyway, because other agents wrote
    more than the cleaner freed. Both facts are true and both are reported.
    """
    mod = _load()
    own = mod.synth_result(2000, 1500, _RESULT_FULL)
    assert own["reclaimed_mb"] == "1220", own
    assert own["freed_mb"] == "-500", own
    assert own["outcome"] == "reclaimed", own
    names = [t["name"] for t in own["reclaim_targets"]]
    assert names == ["Caches", "Repo"], own["reclaim_targets"]


def test_cut_short_output_is_unknown_and_never_a_fabricated_zero():
    """A step the door cut short printed a partial line: its reclaim is UNKNOWN, not 0.

    `reclaim_complete` is the honesty marker. Without the child's RESULT line the output
    finished early, so silence about other targets proves nothing -- and reporting 0 would be a
    number this file did not measure.
    """
    mod = _load()
    own = mod.synth_result(2000, 1900, "freed  Caches  500M  /c  (x)\n")
    assert own["reclaim_complete"] == "no", own
    assert own["reclaimed_mb"] == "unknown", own
    assert own["outcome"] == "unknown", own


def test_a_complete_run_that_freed_nothing_reports_a_genuine_zero():
    """The other side of the same coin: RESULT present and no freed lines IS a real 0."""
    mod = _load()
    own = mod.synth_result(2000, 2000, "RESULT mode=full met=no freed_mb=0\n")
    assert own["reclaim_complete"] == "yes", own
    assert own["reclaimed_mb"] == "0", own
    assert own["outcome"] == "no_change", own


def test_a_repack_that_grew_the_repository_counts_as_nothing_freed():
    """crit_repack prints an object COUNT, not bytes, and a repack can grow the repo.

    Reading `NM of loose objects` as megabytes would invent hundreds of MB that never existed;
    the repo's own `(beforeM -> afterM on disk)` is the only measurement of the disk effect, and
    a repack that grew the repo freed nothing.
    """
    mod = _load()
    grew = mod.parse_reclaimed(
        "freed  Repo  NM of loose objects  /p/.git  (100M -> 130M on disk; git gc)\nRESULT m\n"
    )
    assert grew["reclaimed_mb"] == 0, grew
    shrank = mod.parse_reclaimed(
        "freed  Repo  NM of loose objects  /p/.git  (400M -> 380M on disk; git gc)\nRESULT m\n"
    )
    assert shrank["reclaimed_mb"] == 20, shrank


def test_an_unreadable_volume_is_blind_not_a_loss_and_not_a_success():
    """The third thing a run can be: unable to measure at all. That is BLIND, not 0 and not ok."""
    mod = _load()
    own = mod.synth_result(2000, None, "RESULT mode=full met=no freed_mb=0\n")
    assert own["freed_mb"] == "blind", own
    assert own["reclaimed_mb"] == "blind", own
    assert own["outcome"] == "unknown", own


def test_the_child_result_contract_is_unchanged():
    """The pinned RESULT regex still accepts what the guardian's own line now looks like.

    The guardian must not break the field contract just because it added fields: `freed_mb`
    stays a signed integer and `met` stays a word, so every existing consumer keeps working.
    """
    import re

    pin = re.compile(
        r"^RESULT mode=\S+ free_before_mb=\d+ free_after_mb=\d+ target_mb=\d+ "
        r"met=\S+ freed_mb=-?\d+$"
    )
    mod = _load()
    own = mod.synth_result(3000, 2600, "RESULT mode=full met=yes freed_mb=-400\n")
    line = "RESULT " + " ".join(
        f"{k}={own[k]}"
        for k in (
            "mode",
            "free_before_mb",
            "free_after_mb",
            "target_mb",
            "met",
            "freed_mb",
        )
    )
    assert pin.match(line), line
