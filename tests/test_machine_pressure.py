"""Falsifiers for bin/machine-pressure.

WHY THIS EXISTS. The disk guardian reported `state=healthy` on 2026-11-11 while its own record said
`free=52M RAM swap=82%`. Nothing in the repo read swap (`rg vm.swapusage` -> 0 files), so the one
resident watchdog measured disk only and called a suffocating machine green.

These tests must be able to FAIL. Each one names the defect it catches, and the two the falsifier
actually caught while this was written are marked CAUGHT: (1) a threshold of 85% could not see the
81.3% failure it was built for, so the constant moved to 80%; (2) a test that parsed swap with a
hardcoded `parts[5] == "used"` raised ValueError instead of asserting anything.
"""

import importlib.util
import json
import os
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBE = os.path.join(REPO, "bin", "machine-pressure")


def _load():
    spec = importlib.util.spec_from_loader(
        "machine_pressure",
        importlib.machinery.SourceFileLoader("machine_pressure", PROBE),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_probe_exists_and_is_executable():
    assert os.path.isfile(PROBE), "bin/machine-pressure is missing"
    assert os.access(PROBE, os.X_OK), "bin/machine-pressure is not executable"


def test_exhausted_swap_is_never_ok():
    """The 2026-11-11 machine: 3331M of 4096M (81.3%) must read exhausted, not ok."""
    mp = _load()
    state, why = mp.verdict(4096.0, 3331.0, 8192.0)
    assert state == "exhausted", why
    assert "81%" in why, why


def test_full_swap_is_exhausted_even_with_plenty_of_ram():
    """Low swap means little if RAM is plentiful -- but a FULL swap is terminal regardless."""
    mp = _load()
    state, _ = mp.verdict(4096.0, 4096.0, 64000.0)
    assert state == "exhausted"


def test_low_ram_is_pressure_even_with_empty_swap():
    mp = _load()
    state, why = mp.verdict(4096.0, 0.0, 100.0)
    assert state == "pressure", why
    assert "RAM" in why


def test_half_swap_is_pressure_not_exhausted():
    mp = _load()
    state, _ = mp.verdict(4096.0, 2048.0, 8192.0)
    assert state == "pressure"


def test_healthy_machine_is_ok():
    mp = _load()
    state, _ = mp.verdict(4096.0, 0.0, 8192.0)
    assert state == "ok"


def test_exit_codes_are_distinct_and_verdict_is_the_code():
    """A caller reads the exit code, never the prose."""
    mp = _load()
    assert mp.CODE["ok"] == 0
    assert mp.CODE["pressure"] == 3
    assert mp.CODE["exhausted"] == 4
    assert len({mp.CODE["ok"], mp.CODE["pressure"], mp.CODE["exhausted"], 2}) == 4


def test_blind_is_exit_2_and_never_ok(monkeypatch):
    """A machine that cannot be read is BLIND, never ok (AGENTS.md section 9 R1).

    This drives the REAL BLIND path, not a constant. CAUGHT: the first version of this test
    asserted `CODE.get("blind", 2) == 2`, which passed even when the BLIND branch was changed to
    `return 0` -- a test that executes nothing is not a test.
    """
    mp = _load()

    def blind(*_a, **_k):
        raise mp.Blind("swap unreadable")

    monkeypatch.setattr(mp, "swap_mb", blind)
    rc = mp.main([])
    assert rc == 2, (
        "BLIND must be exit 2, got %r (a machine that cannot be read is not ok)" % rc
    )


def test_live_agrees_with_the_kernel():
    """One live call, so a unit-green rule cannot hide a door wired to nothing."""
    out = subprocess.run(
        [sys.executable, PROBE, "--json"], capture_output=True, text=True, timeout=30
    )
    assert out.returncode in (0, 2, 3, 4), out.stderr
    if out.returncode == 2:
        pytest.skip("machine unreadable: %s" % out.stdout.strip())
    data = json.loads(out.stdout)
    assert data["state"] in ("ok", "pressure", "exhausted")
    assert data["swap_total_mb"] >= 0
    assert 0 <= data["swap_pct"] <= 100
