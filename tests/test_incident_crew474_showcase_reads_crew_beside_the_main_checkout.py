"""Incident test, crew#474 (2026-08-27): the live showcase read "Standards rows: 0 of 0" and
"Science: BLIND (no page at <scratchpad>/crew/docs/science/SHOWCASE.md)" because
bin/estate-showcase located the crew checkout at ROOT.parent, and ROOT was a scratch
worktree. Rule: the sibling checkouts live beside the MAIN checkout, wherever the
worktree that runs the render happens to sit; ESTATE_CODE still overrides.
"""
import importlib.machinery
import importlib.util
import os
import pathlib
import subprocess

_p = pathlib.Path(__file__).resolve().parents[1] / "bin" / "estate-showcase"
_loader = importlib.machinery.SourceFileLoader("estate_showcase", str(_p))
_spec = importlib.util.spec_from_loader("estate_showcase", _loader)
assert _spec is not None
show = importlib.util.module_from_spec(_spec)
_loader.exec_module(show)


def _git(*a, cwd):
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)


def test_incident_crew474_worktree_render_finds_crew_beside_main(tmp_path, monkeypatch):
    monkeypatch.delenv("ESTATE_CODE", raising=False)
    code = tmp_path / "code"
    main = code / "idp"
    main.mkdir(parents=True)
    _git("init", "-q", "-b", "main", cwd=main)
    _git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "x", cwd=main)
    scratch = tmp_path / "scratchpad" / "wt-render"
    _git("worktree", "add", "-q", str(scratch), cwd=main)
    # The failure: a render from the scratch worktree must still find <code>/crew.
    assert show.code_root(scratch).resolve() == code.resolve()
    # The main checkout resolves the same way.
    assert show.code_root(main).resolve() == code.resolve()


def test_incident_crew474_estate_code_still_wins_and_no_git_falls_back(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_CODE", str(tmp_path / "elsewhere"))
    assert show.code_root(tmp_path / "any") == tmp_path / "elsewhere"
    monkeypatch.delenv("ESTATE_CODE")
    plain = tmp_path / "notgit" / "idp"
    plain.mkdir(parents=True)
    assert show.code_root(plain) == plain.parent
