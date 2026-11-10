"""Falsifiers for the MACHINE BOUNDARY in platform/estate/governance/thin_client.py.

WHY THIS FILE EXISTS (DBG-022, 2026-11-10). The estate declared its bound in thin_client.py
(MIN_FREE_GB=10, MAX_LOAD=16), named it again in the lawbook (R5: loops have no budgets; R10:
agents retry instead of diagnosing), and enforced it on exactly one command -- `bin/idp-ci`. So
`pytest`, `cargo build`, `docker build` and `npm ci` ran unbounded, and the machine reached load
522 on 4 cores until a three-line python probe could not finish inside 100 s.

A declared bound with no refusal point is documentation. These tests are the refusal point's
falsifiers: they drive the real decision function with a known-over-bound host and a known-quiet
host, so a guard that quietly stops refusing goes RED here.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "platform" / "estate" / "governance"))

import thin_client as tc  # noqa: E402


@pytest.fixture()
def over_bound(monkeypatch):
    """The host exactly as it was measured on 2026-11-10: 5.5 GB free, load 522."""
    monkeypatch.setattr(tc, "applies", lambda: True)
    monkeypatch.setattr(tc, "free_gb", lambda path=None: 5.5)
    monkeypatch.setattr(tc, "load_average", lambda: 522.6)
    monkeypatch.delenv("ESTATE_THIN_CLIENT", raising=False)


@pytest.fixture()
def quiet(monkeypatch):
    monkeypatch.setattr(tc, "applies", lambda: True)
    monkeypatch.setattr(tc, "free_gb", lambda path=None: 90.0)
    monkeypatch.setattr(tc, "load_average", lambda: 2.0)
    monkeypatch.delenv("ESTATE_THIN_CLIENT", raising=False)


# ---------------------------------------------------------------- the boundary refuses
@pytest.mark.parametrize(
    "cmd",
    [
        "pytest tests/test_x.py",
        "python3 -m pytest tests/",
        "cargo build --release",
        "cargo test",
        "docker build -t x .",
        "npm ci",
        "npm run build",
        "pip3 install -e .",
        "tofu apply -auto-approve",
        "helm upgrade --install x",
        "make",
        "bin/idp-ci",
    ],
)
def test_a_heavy_command_is_refused_when_the_host_is_over_its_bound(over_bound, cmd):
    """DBG-022's falsifier: the refusals must cover the whole harm surface, not just idp-ci."""
    ok, why, _ = tc.verdict(cmd)
    assert ok is False, f"{cmd!r} was allowed on a host at load 522 with 5.5 GB free"
    assert "MACHINE BOUNDARY" in why or "THIN CLIENT" in why


@pytest.mark.parametrize(
    "cmd", ["git status", "echo hi", "rg foo bar", "ls -la", "cat x.yaml"]
)
def test_a_cheap_command_is_allowed_even_over_the_bound(over_bound, cmd):
    """The boundary must not tax the estate's own diagnostics (R14): reading state is how you
    find out the host is over its bound in the first place."""
    ok, why, _ = tc.verdict(cmd)
    assert ok is True, f"{cmd!r} was refused; cheap reads must stay open: {why}"


def test_the_same_heavy_command_is_allowed_on_a_quiet_host(quiet):
    """Refusing correct work is an outage (section 12). The bound, not the command, decides."""
    for cmd in ("pytest tests/x.py", "cargo build", "docker build ."):
        ok, why, _ = tc.verdict(cmd)
        assert ok is True, f"{cmd!r} refused on a quiet host: {why}"


def test_the_idp_ci_shunt_is_kept_for_the_gate(over_bound):
    """The gate keeps its specific remedy: not a refusal, a hand-off to CI."""
    ok, why, replacement = tc.verdict("bin/idp-ci")
    assert ok is False
    assert "shunted to GitHub Actions" in why
    assert replacement, "the gate's shunt must carry the replacement command"


def test_an_unreadable_load_does_not_shunt_or_refuse(monkeypatch):
    """R1 in the other direction: 'cannot judge' must not become 'refuse'. BLIND on one axis
    leaves that axis out of the decision rather than inventing a verdict."""
    monkeypatch.setattr(tc, "applies", lambda: True)
    monkeypatch.setattr(tc, "free_gb", lambda path=None: 90.0)
    monkeypatch.setattr(tc, "load_average", lambda: None)
    monkeypatch.delenv("ESTATE_THIN_CLIENT", raising=False)
    ok, why, _ = tc.verdict("pytest tests/x.py")
    assert ok is True, why


def test_the_ci_environment_is_never_gated(monkeypatch):
    """A guard that taxes the estate's own CI is R14. In CI the runner IS the right place."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    ok, why, _ = tc.verdict("pytest tests/")
    assert ok is True, why


# ---------------------------------------------------------------- one definition
def test_the_shunt_and_the_refusal_share_one_overload_definition(over_bound):
    """If these ever disagree, one path refuses where the other allows and the bound is a
    suggestion again."""
    reasons = tc._overloaded()
    assert len(reasons) == 2, reasons
    assert any("GB free" in r for r in reasons)
    assert any("load" in r for r in reasons)


def test_a_commit_message_naming_a_heavy_word_is_not_refused(over_bound):
    """A flagged word inside an argument is not a heavy command; false positives train agents to
    route around the guard, which is worse than the guard being narrow."""
    ok, why, _ = tc.verdict('git commit -m "rerun pytest and cargo build later"')
    assert ok is True, why
