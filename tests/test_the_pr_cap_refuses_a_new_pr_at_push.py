"""The PR cap refuses a push that would open a sixth PR, and refuses when it cannot count.

On 2026-09-27 the repo reached 16 open PRs: .githooks/pre-push never called
bin/idp-max-open-prs-gate, and the gate passed whenever GH_TOKEN was unset. Also, the hook's first
loop read and discarded the first pushed ref, so a one-branch push reached no rung at all.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import shutil
import subprocess  # noqa: S404 -- fixed argv, no shell
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "bin/idp-max-open-prs-gate"
HOOK = REPO / ".githooks/pre-push"
ZERO = "0" * 40
SHA = "1" * 40

_loader = importlib.machinery.SourceFileLoader("max_open_prs_gate", str(GATE))
_spec = importlib.util.spec_from_loader("max_open_prs_gate", _loader)
gate = importlib.util.module_from_spec(_spec)
_loader.exec_module(gate)


def pr(n: int, ref: str, login: str = "chidionyema") -> dict:
    return {
        "number": n,
        "title": f"pr {n}",
        "head": {"ref": ref},
        "user": {"login": login},
    }


FIVE = [pr(i, f"feat/{i}") for i in range(1, 6)]


def test_a_new_branch_is_refused_when_five_are_open() -> None:
    rc, text = gate.decide(FIVE, "feat/new", gate.CAP)
    assert rc == 1
    assert "5 open non-bot PRs (cap 5)" in text


def test_a_new_branch_is_the_fifth_at_most() -> None:
    assert gate.decide(FIVE[:4], "feat/new", gate.CAP)[0] == 0


def test_a_branch_that_already_has_a_pr_always_passes() -> None:
    many = [pr(i, f"feat/{i}") for i in range(1, 17)]
    rc, text = gate.decide(many, "feat/3", gate.CAP)
    assert rc == 0
    assert "already has an open PR" in text


def test_bot_lanes_neither_count_nor_are_refused() -> None:
    bots = FIVE[:4] + [pr(9, "flux/image-updates", "app/github-actions")]
    assert gate.decide(bots, "feat/new", gate.CAP)[0] == 0
    assert gate.decide(FIVE, "flux/image-updates", gate.CAP)[0] == 0
    assert gate.decide(FIVE, "agent-trunk", gate.CAP)[0] == 0


def test_no_token_anywhere_refuses(monkeypatch, capsys) -> None:
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(
        gate.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 1, "", "not logged in"),
    )
    monkeypatch.setattr(gate.sys, "argv", ["gate", "--branch", "feat/new"])
    with pytest.raises(SystemExit) as exit_:
        gate.main()
    assert exit_.value.code == 2
    assert "REFUSED" in capsys.readouterr().err


def test_the_gh_token_is_used_when_the_env_has_none(monkeypatch) -> None:
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(
        gate.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, "tok-from-gh\n", ""),
    )
    assert gate.token() == "tok-from-gh"


def test_the_cap_has_no_env_override(monkeypatch) -> None:
    monkeypatch.setenv("IDP_MAX_OPEN_PRS", "100")
    assert "IDP_MAX_OPEN_PRS" not in GATE.read_text()
    assert gate.CAP == 5


def run_hook(tmp_path: Path, gate_rc: int, stdin: str):
    """The real pre-push in a scratch repo whose gate is a stub that records its argv."""
    repo = tmp_path / "repo"
    (repo / "bin").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)  # noqa: S603,S607
    calls = tmp_path / "calls"
    stub = repo / "bin" / "idp-max-open-prs-gate"
    stub.write_text(
        f'import sys\nopen("{calls}", "a").write(" ".join(sys.argv[1:]) + "\\n")\nsys.exit({gate_rc})\n'
    )
    hook = repo / "pre-push"
    shutil.copyfile(HOOK, hook)
    r = subprocess.run(  # noqa: S603
        ["bash", str(hook), "origin", "git@github.com:x/y.git"],
        cwd=repo,
        input=stdin,
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "GIT_DIR": str(repo / ".git")},
    )
    return r, calls.read_text().splitlines() if calls.exists() else []


def test_the_hook_asks_the_gate_about_a_single_pushed_branch(tmp_path: Path) -> None:
    r, calls = run_hook(
        tmp_path, 0, f"refs/heads/feat/x {SHA} refs/heads/feat/x {ZERO}\n"
    )
    assert calls == ["--branch feat/x"]
    assert r.returncode == 0, r.stderr


def test_the_hook_refuses_when_the_gate_refuses(tmp_path: Path) -> None:
    r, calls = run_hook(
        tmp_path, 1, f"refs/heads/feat/x {SHA} refs/heads/feat/x {ZERO}\n"
    )
    assert r.returncode == 1
    assert "REFUSED: max-open-prs" in r.stderr


def test_the_hook_refuses_when_the_gate_cannot_count(tmp_path: Path) -> None:
    r, _ = run_hook(tmp_path, 2, f"refs/heads/feat/x {SHA} refs/heads/feat/x {ZERO}\n")
    assert r.returncode == 1


def test_deletions_and_tags_do_not_ask(tmp_path: Path) -> None:
    stdin = (
        f"(delete) {ZERO} refs/heads/old {SHA}\n"
        f"refs/tags/v1 {SHA} refs/tags/v1 {ZERO}\n"
    )
    r, calls = run_hook(tmp_path, 1, stdin)
    assert calls == []
    assert r.returncode == 0, r.stderr
