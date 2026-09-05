"""crew#607 CP2/CP3: a green PR merges itself (`gh pr merge --auto --merge`), a PR over the bound gets one
`PR AGE:` comment naming the reason and is not nagged again while the reason stands. Hourly in
.github/workflows/pr-age.yml."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import pathlib
import subprocess

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load():
    loader = importlib.machinery.SourceFileLoader("idp_pr_age", str(ROOT / "bin/idp-pr-age"))
    spec = importlib.util.spec_from_loader("idp_pr_age", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class _Gh:
    def __init__(self, last_comment=""):
        self.calls, self.last_comment = [], last_comment

    def __call__(self, argv, **kw):
        self.calls.append(argv[1:])
        out = self.last_comment if argv[1:3] == ["pr", "view"] else ""
        return subprocess.CompletedProcess(argv, 0, stdout=out, stderr="")


def _wire(monkeypatch, last_comment=""):
    mod = _load()
    rec = _Gh(last_comment)
    monkeypatch.setattr(mod.subprocess, "run", rec)
    return mod, rec


def test_a_green_row_is_put_on_auto_merge(monkeypatch):
    mod, rec = _wire(monkeypatch)
    assert mod.act("idp", 647, 1.0, "green", 4) == "auto-merge"
    assert rec.calls == [["pr", "merge", "647", "-R", "chidionyema/idp", "--auto", "--merge"]]


def test_a_row_over_the_bound_is_told_why_once(monkeypatch):
    mod, rec = _wire(monkeypatch)
    assert mod.act("crew", 605, 6.2, "red:review-gate", 4) == "commented"
    body = rec.calls[-1][-1]
    assert rec.calls[-1][:3] == ["pr", "comment", "605"]
    assert body.startswith("PR AGE: 6.2h open, reason: red:review-gate")
    mod, rec = _wire(monkeypatch, last_comment=body)
    assert mod.act("crew", 605, 7.2, "red:review-gate", 4) == "quiet"
    assert not any(c[:2] == ["pr", "comment"] for c in rec.calls), "nagged again for the same reason"
    mod, rec = _wire(monkeypatch, last_comment=body)
    assert mod.act("crew", 605, 7.2, "conflict", 4) == "commented", "a new reason is a new line"


def test_the_red_clock_drafts_at_the_bound_and_closes_at_six(monkeypatch):
    mod, rec = _wire(monkeypatch)
    assert mod.act("crew", 605, 6.2, "red:review-gate", 4) == "commented"
    assert ["pr", "ready", "605", "-R", "chidionyema/crew", "--undo"] in rec.calls, "drafted at the bound"
    mod, rec = _wire(monkeypatch)
    assert mod.act("idp", 623, 25.0, "conflict", 4) == "closed"
    assert rec.calls[0][:3] == ["pr", "close", "623"] and "Reopen when it is green" in rec.calls[0][-1]
    mod, rec = _wire(monkeypatch)
    assert mod.act("idp", 641, 25.0, "blocked-by-policy", 4) == "commented", "only red rows are on the clock"
    assert not any(c[1] in ("close", "ready") for c in rec.calls)


def test_a_young_red_row_is_left_alone(monkeypatch):
    mod, rec = _wire(monkeypatch)
    assert mod.act("idp", 648, 1.0, "pending:hydrate", 4) == "-"
    assert rec.calls == []


def test_the_sweep_is_hourly_and_acts():
    wf = yaml.safe_load((ROOT / ".github/workflows/pr-age.yml").read_text())
    assert wf[True]["schedule"][0]["cron"].split()[1] == "*", "hourly"
    steps = wf["jobs"]["sweep"]["steps"]
    assert any("bin/idp-pr-age --act" in (s.get("run") or "") for s in steps)
    assert wf["permissions"]["pull-requests"] == "write"
