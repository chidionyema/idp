"""The required checks on main are read by name, not off one page of everything (2026-10-11).

`bin/idp-greenlane status` is what /fleet shows, and its `main.green` answers "is main green?".
It read `commits/main/check-runs?per_page=100&filter=latest` -- one page of every check on
main's tip, keyed by name -- and took whatever that page happened to hold.

The Greenlane's own `tick` reports a check on main's sha every ~80 seconds, so the page fills
with `tick` long before the checks that ran when main landed. Measured on main e47ab313e,
2026-10-11T23:5xZ: 249 check-runs on the sha, 132 of them `tick`, and not one of the eight
required contexts (`bdd`, `ci-success`, `fast-gate / fast-gate`, `guarded-paths`, `test`,
`portal-app`, `executes-gate`, `feature-request-plan`) inside the first hundred. All eight read
`absent`, `main.green` was false and /fleet raised its alarm, while all eight were in fact
`success` or `skipped` on that commit. Read by name (`?check_name=<context>`) each resolves, and
the tick stream cannot bury it.

An alarm that is always on is worse than no alarm: the invariant that *was* true that minute
(`work_lost: 1`) could not be seen through it. So these tests pin both directions -- green when
the required checks are green, and never a silent `absent` when the read itself failed.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
from pathlib import Path
from urllib.parse import quote, unquote

import pytest

ROOT = Path(__file__).resolve().parents[1]
SHA = "e47ab313eab8443962905a2130c6970592368279"


def _mod():
    loader = importlib.machinery.SourceFileLoader(
        "idp_greenlane_status", str(ROOT / "bin/idp-greenlane")
    )
    mod = importlib.util.module_from_spec(
        importlib.util.spec_from_loader("idp_greenlane_status", loader)
    )
    loader.exec_module(mod)
    return mod


@pytest.fixture
def mod(monkeypatch):
    monkeypatch.setenv("GH_REPO", "owner/name")
    monkeypatch.setenv("GH_TOKEN", "x")
    return _mod()


def _run(name: str, conclusion: str, at: str) -> dict:
    return {
        "name": name,
        "status": "completed",
        "conclusion": conclusion,
        "completed_at": at,
    }


class _Gh:
    """Answers `gh api repos/owner/name/<path>` from a script, recording every argv.

    `check_runs` is what a name-filtered read returns. The unfiltered page is deliberately a
    hundred `tick` runs and no required name: that is the page the old read keyed by name, so an
    edit that goes back to reading it fails the green test below instead of passing quietly.
    `unreadable` names answer as GitHub does when it refuses -- rc=1, reason on stderr.
    """

    def __init__(
        self, check_runs: dict[str, list[dict]], unreadable: tuple[str, ...] = ()
    ):
        self.check_runs = dict(check_runs)
        self.unreadable = set(unreadable)
        self.calls: list[list[str]] = []

    def __call__(self, argv, **kw):
        self.calls.append(list(argv))
        path = argv[2].split("repos/owner/name/", 1)[-1] if len(argv) > 2 else ""

        class R:
            pass

        r = R()
        r.stderr = ""
        if path == "commits/main":
            r.returncode, r.stdout = 0, json.dumps({"sha": SHA})
            return r
        if path.startswith("commits/main/check-runs?"):
            query = dict(
                kv.split("=", 1) for kv in path.split("?", 1)[1].split("&") if "=" in kv
            )
            if "check_name" not in query:
                r.returncode, r.stdout = (
                    0,
                    json.dumps(
                        {
                            "check_runs": [
                                _run("tick", "success", "2026-10-11T23:40:00Z")
                            ]
                            * 100
                        }
                    ),
                )
                return r
            name = unquote(query["check_name"])
            if name in self.unreadable:
                r.returncode, r.stdout = 1, ""
                r.stderr = "HTTP 403: API rate limit exceeded"
                return r
            r.returncode, r.stdout = (
                0,
                json.dumps({"check_runs": self.check_runs.get(name, [])}),
            )
            return r
        if path in (
            "pulls?state=open&per_page=100",
            "pulls?state=closed&per_page=100",
            "git/matching-refs/heads/",
        ):
            r.returncode, r.stdout = 0, "[]"
            return r
        r.returncode, r.stdout, r.stderr = 1, "", "HTTP 404: Not Found"
        return r


def _status(mod, monkeypatch, gh: _Gh, capsys) -> dict:
    """`status`'s stdout, which is the interface /fleet parses."""
    monkeypatch.setattr(mod.subprocess, "run", gh)
    assert mod.status() == 0
    return json.loads(capsys.readouterr().out)


def _green(mod, at: str = "2026-10-11T20:41:00Z") -> dict[str, list[dict]]:
    return {c: [_run(c, "success", at)] for c in mod.required_contexts()}


def test_main_is_green_when_the_required_checks_are_green(mod, monkeypatch, capsys):
    """The defect itself: every required check green, so main must read green.

    The unfiltered page holds a hundred `tick` runs and no required name, exactly as main
    e47ab313e did, so going back to that read fails here with eight `absent`s.
    """
    required = mod.required_contexts()
    runs = {
        c: [_run(c, "skipped" if i == 2 else "success", "2026-10-11T20:41:00Z")]
        for i, c in enumerate(required)
    }
    out = _status(mod, monkeypatch, _Gh(runs), capsys)
    assert out["main"]["green"] is True, out["main"]["required"]
    assert set(out["main"]["required"].values()) <= {"success", "skipped"}


def test_the_newest_run_wins_even_when_the_api_lists_it_first(mod, monkeypatch, capsys):
    """Selection is by time, not by page order, and a fresh failure must show through."""
    c = mod.required_contexts()[0]
    runs = _green(mod)
    runs[c] = [
        _run(c, "failure", "2026-10-11T21:00:00Z"),
        _run(c, "success", "2026-10-11T20:00:00Z"),
    ]
    out = _status(mod, monkeypatch, _Gh(runs), capsys)
    assert out["main"]["required"][c] == "failure", out["main"]["required"]
    assert out["main"]["green"] is False


def test_a_required_check_that_never_ran_reads_absent_and_is_not_green(
    mod, monkeypatch, capsys
):
    required = mod.required_contexts()
    runs = {c: [_run(c, "success", "2026-10-11T20:41:00Z")] for c in required[:-1]}
    out = _status(mod, monkeypatch, _Gh(runs), capsys)
    assert out["main"]["required"][required[-1]] == "absent"
    assert out["main"]["green"] is False


def test_a_read_that_failed_is_unreadable_with_its_reason_never_absent(
    mod, monkeypatch, capsys
):
    """The surface's own standard: an unreadable check is reported with its reason, never as a
    silent zero, and it is never green."""
    required = mod.required_contexts()
    missing = required[0]
    out = _status(mod, monkeypatch, _Gh(_green(mod), unreadable=(missing,)), capsys)
    value = out["main"]["required"][missing]
    assert value.startswith("unreadable:") and "403" in value, value
    assert out["main"]["required"][required[1]] != "absent"
    assert out["main"]["green"] is False


def test_every_required_context_is_asked_for_by_name(mod, monkeypatch, capsys):
    required = mod.required_contexts()
    gh = _Gh(_green(mod))
    _status(mod, monkeypatch, gh, capsys)
    asked = {
        c
        for c in required
        if any(f"check_name={quote(c, safe='')}" in a[2] for a in gh.calls)
    }
    assert asked == set(required), (
        f"not asked for by name: {sorted(set(required) - asked)}"
    )
