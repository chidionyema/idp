"""features/estate-progress/estate-progress.feature, bound to the real report writer.

A feature that cannot run is prose. Every step here runs against bin/estate-progress -- the same
code the scheduled writer runs and every surface reads -- over a synthetic Greenlane state, so
the scenarios prove the report's arithmetic and its honesty about blindness, not a mock of them.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import time
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

_REPO_ROOT = Path(__file__).resolve().parents[1]
_TOOL = _REPO_ROOT / "bin" / "estate-progress"


def _load():
    loader = importlib.machinery.SourceFileLoader("estate_progress_tool", str(_TOOL))
    spec = importlib.util.spec_from_loader("estate_progress_tool", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


TOOL = _load()

scenarios("../features/estate-progress/estate-progress.feature")


def _now_min() -> float:
    return time.time() / 60.0


def _state(lanes=None, landings=None, history=None, landed=None):
    return {
        "batch": 7,
        "candidates": 12,
        "conflicts": 3,
        "history": history or [],
        "landed": landed if landed is not None else 11,
        "landings": landings or [],
        "lanes": lanes or {},
        "queued": 0,
        "retired": {},
        "seq": 99,
        "timed": {},
    }


@pytest.fixture
def chain():
    return {"state": None, "blind": set(), "previous": None, "report": None}


@given("a delivery chain with one lane landed in the window", target_fixture="chain")
def _one_landed(chain: dict) -> dict:
    now = _now_min()
    chain["state"] = _state(
        lanes={
            "lane/one": {
                "arrived": now - 30,
                "status": "pending",
                "reason": "",
                "attempts": 1,
            }
        },
        landings=[{"lane": "lane/one", "queued": now - 40, "landed": now - 10}],
        history=[
            {
                "id": "b1",
                "outcome": "landed",
                "started": now - 45,
                "verdict_at": now - 12,
            }
        ],
    )
    return chain


@given(
    "a delivery chain with a third of its batches ending in conflict",
    target_fixture="chain",
)
def _conflicting(chain: dict) -> dict:
    now = _now_min()
    history = []
    for i in range(3):
        history.append(
            {
                "id": "b%d" % i,
                "outcome": "conflict",
                "action": "rebase",
                "started": now - 60,
                "verdict_at": now - 30,
            }
        )
    chain["state"] = _state(
        lanes={
            "lane/one": {
                "arrived": now - 20,
                "status": "conflict",
                "reason": "main moved",
            }
        },
        history=history,
    )
    return chain


@given(
    "a delivery chain with nothing landed and a lane three hours old",
    target_fixture="chain",
)
def _stuck(chain: dict) -> dict:
    now = _now_min()
    chain["state"] = _state(
        lanes={
            "lane/old": {
                "arrived": now - 180,
                "status": "red",
                "reason": "ci-success failure https://example.invalid/run/1",
            }
        },
        history=[
            {
                "id": "b1",
                "outcome": "landed",
                "started": now - 600,
                "verdict_at": now - 590,
            }
        ],
    )
    return chain


@given("a source that cannot be read")
def _blind_source(chain: dict) -> None:
    chain["blind"] = {"ci_runs"}


@given("a previous report that recorded three lanes landed in the window")
def _previous(chain: dict) -> None:
    chain["previous"] = {
        "generated_at": "2026-10-29T09:00:00Z",
        "signals": {
            "chain": {
                "landed_in_window": 3,
                "lanes_inflight": 1,
                "oldest_lane_age_min": 10.0,
                "queue_to_land_min": {"p50": 30.0},
            }
        },
    }


def _build(chain: dict, hours: int = 24):
    """The report, built the way the writer builds it, with the blind sources injected."""
    sources = TOOL.Sources()
    now = _now_min()
    state = chain["state"]
    signals = {
        "chain": TOOL.lane_signals(state, now, hours * 60.0) if state else None,
        "ci": None,
        "claims": None,
        "decisions": None,
        "live": None,
        "blind": sorted(chain["blind"]),
    }
    for name in chain["blind"]:
        sources.blind(name, "the source could not be read in this scenario")
    report = {
        "schema": TOOL.SCHEMA,
        "generated_at": "2026-10-29T10:00:00Z",
        "window_hours": hours,
        "sources": sources.rows,
        "signals": signals,
    }
    report = TOOL.finalise(report, chain["previous"])
    chain["report"] = report
    return report


@when("the progress report is built")
def _build_report(chain: dict) -> None:
    _build(chain)


@when("the progress report is spoken", target_fixture="spoken")
def _speak(chain: dict) -> str:
    report = _build(chain)
    return TOOL.speak(report)


@when("the progress report is written", target_fixture="written")
def _written(chain: dict, tmp_path: Path) -> dict:
    report = _build(chain)
    out = tmp_path / "progress"
    TOOL.write_report(report, out)
    return {
        "json": json.loads((out / TOOL.REPORT_NAME).read_text()),
        "prom": (out / TOOL.PROM_NAME).read_text(),
        "md": (out / TOOL.MD_NAME).read_text(),
    }


@then("the verdict is PROGRESSING")
def _progressing(chain: dict) -> None:
    assert chain["report"]["verdict"]["state"] == "PROGRESSING"


@then("the verdict is SLIPPING")
def _slipping(chain: dict) -> None:
    assert chain["report"]["verdict"]["state"] == "SLIPPING"


@then("the verdict is STUCK")
def _stuck(chain: dict) -> None:
    assert chain["report"]["verdict"]["state"] == "STUCK"


@then("the verdict is not a clean PROGRESSING")
def _not_clean(chain: dict) -> None:
    assert chain["report"]["verdict"]["state"] != "PROGRESSING"


@then("that source is marked blind with a reason")
def _marked_blind(chain: dict) -> None:
    rows = {r["name"]: r for r in chain["report"]["sources"]}
    for name in chain["blind"]:
        assert rows[name]["read"] == "BLIND"
        assert rows[name]["why"], "a blind source must say why"


@then("the report does not claim zero for the unread source")
def _no_zero(chain: dict) -> None:
    signals = chain["report"]["signals"]
    for name in chain["blind"]:
        assert signals.get(name) is None, "%s must be unknown, not a number" % name


@then("the delta on lanes landed is minus two")
def _delta(chain: dict) -> None:
    delta = chain["report"]["deltas"]
    assert delta["available"] is True
    assert delta["landed_in_window"] == -2


@then("the spoken answer names the verdict")
def _spoken_verdict(spoken: str) -> None:
    assert "progress" in spoken.lower()
    assert (
        "partial" in spoken.lower()
        or "slipping" in spoken.lower()
        or "stuck" in spoken.lower()
    )


@then("the spoken answer names the blind source")
def _spoken_blind(spoken: str) -> None:
    assert "blind" in spoken.lower()


@then(
    "the json report and the prometheus file and the markdown carry the same number of landed lanes"
)
def _same_numbers(written: dict) -> None:
    landed = written["json"]["signals"]["chain"]["landed_in_window"]
    assert "estate_progress_landed_in_window %s" % landed in written["prom"]
    assert "| lanes landed in the window | %s |" % landed in written["md"]


# --- the report's own arithmetic, outside the scenarios --------------------------------------------


def test_a_lapsed_claim_is_not_a_live_claim(monkeypatch, tmp_path):
    """The register's own liveness flag decides, and a claim with no heartbeat for two hours is
    lapsed. A lapsed claim is not counted as work in flight, and it does not collide with a
    live one."""
    register = tmp_path / "focus-register.json"
    register.write_text(
        json.dumps(
            {
                "at": 1.0,
                "rows": [
                    {
                        "agent": "pi-a",
                        "paths": "bin/a",
                        "live": True,
                        "heartbeat_age_s": 60,
                    },
                    {
                        "agent": "pi-b",
                        "paths": "bin/b",
                        "live": True,
                        "heartbeat_age_s": 9000,
                    },
                    {
                        "agent": "pi-c",
                        "paths": "bin/a",
                        "live": False,
                        "heartbeat_age_s": 10,
                    },
                ],
            }
        )
    )
    monkeypatch.setattr(TOOL, "FOCUS_REGISTER", register)
    sources = TOOL.Sources()
    claims = TOOL.claim_signals(sources)
    assert claims["live_claims"] == 1
    assert claims["stale_claims"] == 1
    assert claims["overlapping_paths"] == 0, (
        "a lapsed claim does not collide with a live one"
    )


def test_the_report_serves_its_cache_until_it_is_stale(monkeypatch, tmp_path):
    out = tmp_path / "progress"
    out.mkdir()
    fresh = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "n": 1}
    (out / TOOL.REPORT_NAME).write_text(json.dumps(fresh))
    report, where = TOOL.read_cached(out, 1800, tmp_path)
    assert report["n"] == 1 and where["from"] == "cache"


def test_an_unreadable_report_is_unknown_not_an_empty_one(monkeypatch, tmp_path):
    """A cache that cannot be read and a publication that cannot be fetched give UNKNOWN, never
    a report with no signals in it."""
    monkeypatch.setattr(
        TOOL, "fetch_published", lambda repo: (None, "the bucket said no")
    )
    report, where = TOOL.read_cached(tmp_path / "nothing", 1800, tmp_path)
    assert report is None
    assert "the bucket said no" in where["why"]


def test_the_report_carries_its_own_sentence():
    """The canonical sentence travels inside the report, so a surface that has the report can
    speak the same numbers without the writer being installed on that host."""
    report = {
        "schema": TOOL.SCHEMA,
        "generated_at": "2026-10-29T10:00:00Z",
        "window_hours": 24,
        "sources": [],
        "signals": {
            "chain": {
                "landed_in_window": 5,
                "lanes_inflight": 2,
                "oldest_lane_age_min": 30.0,
            },
            "ci": {},
            "claims": {},
            "decisions": {},
            "live": {},
            "blind": [],
        },
    }
    report = TOOL.finalise(report, None)
    assert report["speak"].startswith("Estate progress:")
    assert "5 lanes landed" in report["speak"]
    assert report["speak"] == TOOL.speak(report)


# --- the door: the intent a surface actually calls ----------------------------------------------

_INTENT = _REPO_ROOT / "platform" / "estate" / "intents" / "estate.progress.yaml"


def _intent_cmd() -> str:
    """The intent's step, as bytes. Read as text, not as YAML, so the test proves the script
    that runs, not a re-serialisation of it."""
    lines = _INTENT.read_text().splitlines()
    out = []
    started = False
    for line in lines:
        if not started:
            if line.strip() == "cmd: |":
                started = True
            continue
        if line.strip() and not line.startswith("      "):
            break
        out.append(line[6:] if line.startswith("      ") else line)
    assert out, "the intent has no cmd block"
    return "\n".join(out)


def _run_intent(tmp_path, report=None, root=""):
    cmd = _intent_cmd()
    cmd = (
        cmd.replace("{{root}}", root)
        .replace("{{hours}}", "24")
        .replace("{{fresh}}", "false")
    )
    env = dict(os.environ, HOME=str(tmp_path))
    env.pop("ESTATE_PROGRESS_REPORT", None)
    if report is not None:
        env["ESTATE_PROGRESS_REPORT"] = str(report)
    return subprocess.run(
        ["bash", "-c", cmd], capture_output=True, text=True, env=env, timeout=90
    )


def test_the_door_speaks_the_report_when_no_writer_is_installed(tmp_path):
    """A host without the writer still speaks the canonical sentence: the report carries it."""
    report = tmp_path / "estate-progress.json"
    report.write_text(
        json.dumps(
            {
                "speak": "Estate progress: progressing. 5 lanes landed in the last 24 hours.",
                "verdict": {"state": "PROGRESSING"},
            }
        )
    )
    proc = _run_intent(tmp_path, report=report)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().endswith(
        "Estate progress: progressing. 5 lanes landed in the last 24 hours."
    )


def test_the_door_says_unknown_when_there_is_no_report(tmp_path):
    """No report is unknown, never a zero and never a healthy green."""
    proc = _run_intent(tmp_path)
    assert proc.returncode == 0, proc.stderr
    said = proc.stdout.strip()
    assert said.startswith("Estate progress: unknown"), said
    assert "no progress report" in said.lower()


def test_the_door_falls_back_to_the_verdict_of_an_older_report(tmp_path):
    """A report written before the sentence existed still speaks its verdict."""
    report = tmp_path / "estate-progress.json"
    report.write_text(json.dumps({"verdict": {"state": "SLIPPING"}}))
    proc = _run_intent(tmp_path, report=report)
    assert proc.stdout.strip() == "Estate progress: slipping."


def test_the_prometheus_exposition_uses_nan_for_an_unread_signal():
    """A blind plane must not scrape as a healthy zero."""
    report = {
        "signals": {
            "chain": {"landed_in_window": 3, "lanes_inflight": None},
            "ci": {},
            "live": {},
            "blind": ["cluster_receipt"],
        }
    }
    text = TOOL.prom(report)
    assert "estate_progress_lanes_inflight NaN" in text
    assert "estate_progress_landed_in_window 3" in text
    assert "estate_progress_blind_sources 1" in text
