"""Falsifiers for the Darwin thin-client guard (platform/estate/governance/thin_client.py).

A gate that cannot fail is not a gate (AGENTS.md section 9 P1). Every rule below is proved BOTH
ways: the known-bad input it must refuse, and the known-good input it must accept. The known-good
half is the one that is usually skipped, and it is the half that catches a guard that refuses
correct work (R14: `fs_guard` refused 34 steps across 22 of the estate's own intents).

The guard's own platform test is the pivot: on a host where it does not apply (CI, Linux) every
command is allowed, and a test that only ran the bad half would pass on a guard that did nothing.
"""

import sys
from pathlib import Path

import pytest

_GOV = Path(__file__).resolve().parents[1] / "platform" / "estate" / "governance"
assert _GOV.is_dir(), f"the guard is not where this test expects it: {_GOV}"
sys.path.insert(0, str(_GOV))
import thin_client  # noqa: E402


@pytest.fixture
def darwin(monkeypatch):
    """Make the guard believe it is running on the founder's laptop."""
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("ESTATE_THIN_CLIENT", raising=False)
    monkeypatch.setattr(thin_client.platform, "system", lambda: "Darwin")
    return thin_client


@pytest.fixture
def roomy(monkeypatch):
    monkeypatch.setattr(thin_client, "free_gb", lambda *a: 200.0)
    monkeypatch.setattr(thin_client, "load_average", lambda *a: 1.2)


# ---- rule 1: no worktrees --------------------------------------------------
@pytest.mark.parametrize(
    "cmd",
    [
        "git worktree add /tmp/wt-42 main",
        "cd /Users/x/code/idp && git worktree add ../wt",
        "make thing; git worktree add /tmp/x",
    ],
)
def test_refuses_worktree_add(darwin, roomy, cmd):
    ok, reason, replacement = darwin.verdict(cmd)
    assert ok is False
    assert "THIN CLIENT" in reason
    assert replacement == ""  # a refusal has no substitute command


def test_accepts_a_plain_branch(darwin, roomy):
    """The known-good half: the replacement the refusal tells the agent to use must pass."""
    assert darwin.verdict("git switch -c lane/my-change")[0] is True
    assert darwin.verdict("git worktree list")[0] is True  # reading is never refused


# ---- rule 2: no clone into temp storage -----------------------------------
@pytest.mark.parametrize(
    "cmd",
    [
        "git clone https://github.com/x/y /tmp/y",
        "git clone git@github.com:x/y.git /var/folders/ab/T/x",
        "git clone git@github.com:x/y.git /private/tmp/y",
    ],
)
def test_refuses_clone_into_temp(darwin, roomy, cmd):
    ok, reason, _ = darwin.verdict(cmd)
    assert ok is False
    assert "temp storage" in reason


def test_accepts_a_clone_into_a_real_home(darwin, roomy):
    assert darwin.verdict("git clone git@github.com:x/y ~/Documents/code/y")[0] is True


# ---- rule 3: shunt the local gate when the laptop is out of room or crushed -
def test_shunts_local_ci_when_disk_is_low(darwin, roomy, monkeypatch):
    monkeypatch.setattr(thin_client, "free_gb", lambda *a: 4.0)
    ok, reason, replacement = darwin.verdict("bin/idp-ci")
    assert ok is False
    assert "4.0 GB free" in reason
    assert replacement == "gh workflow run ci.yml"


def test_shunts_local_ci_when_load_is_high(darwin, roomy, monkeypatch):
    monkeypatch.setattr(thin_client, "load_average", lambda *a: 40.0)
    ok, reason, replacement = darwin.verdict("cd /Users/x && bin/idp-ci")
    assert ok is False
    assert "load 40.0" in reason
    assert replacement


def test_runs_local_ci_when_the_laptop_is_healthy(darwin, roomy):
    """The other known-good half: a healthy laptop still runs its own gate."""
    assert darwin.verdict("bin/idp-ci") == (True, "OK", "")


def test_blind_disk_is_not_read_as_plenty_nor_as_low(darwin, roomy, monkeypatch):
    """An unmeasurable disk must not shunt (a guess is not a measurement) and must not crash."""
    monkeypatch.setattr(thin_client, "free_gb", lambda *a: None)
    monkeypatch.setattr(thin_client, "load_average", lambda *a: None)
    assert darwin.verdict("bin/idp-ci")[0] is True


# ---- the platform pivot ---------------------------------------------------
def test_does_nothing_in_ci(darwin, roomy, monkeypatch):
    """In CI the worktree IS the isolation primitive; the guard must be silent there."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    assert darwin.verdict("git worktree add /tmp/wt main")[0] is True


def test_does_nothing_on_linux(darwin, roomy, monkeypatch):
    monkeypatch.setattr(thin_client.platform, "system", lambda: "Linux")
    assert darwin.verdict("git worktree add /tmp/wt main")[0] is True


def test_explicit_opt_out_is_honoured(darwin, roomy, monkeypatch):
    monkeypatch.setenv("ESTATE_THIN_CLIENT", "0")
    assert darwin.verdict("git worktree add /tmp/wt main")[0] is True


def test_probe_reports_what_it_measured(darwin):
    p = darwin.probe()
    assert set(p) == {
        "applies",
        "platform",
        "free_gb",
        "load_1m",
        "min_free_gb",
        "max_load",
    }
    assert p["applies"] is True
    assert p["min_free_gb"] == 10.0 and p["max_load"] == 16.0


def test_thresholds_are_the_stated_ones(darwin):
    """The founder's numbers, pinned: a silent change to either is a change to the policy."""
    assert darwin.MIN_FREE_GB == 10.0
    assert darwin.MAX_LOAD == 16.0
