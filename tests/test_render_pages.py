"""Renderer tests: inlined data is byte-stable, no leftover placeholders,
the three pages all render, and BLIND envelopes degrade to a labelled state."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RECORDER = ROOT / "bin" / "estate-deploy-recorder"
RIVER = ROOT / "bin" / "estate-river-data"
SCRUB = ROOT / "bin" / "estate-time-scrub"
PLANES = ROOT / "bin" / "estate-planes-snapshot"
RENDERER = ROOT / "bin" / "estate-render-pages"


def _load(p, name):
    loader = importlib.machinery.SourceFileLoader(name, str(p))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    loader.exec_module(m)
    return m


rec = _load(RECORDER, "estate_deploy_recorder")
ren = _load(RENDERER, "estate_render_pages")


PR_OK = {
    "number": 3906,
    "title": "ok",
    "headRefName": "feat/ok",
    "headRefOid": "a" * 40,
    "createdAt": "2026-09-23T08:00:00Z",
    "mergedAt": "2026-09-23T08:07:00Z",
    "state": "MERGED",
    "baseRefName": "main",
}
PR_FAIL = {
    "number": 3907,
    "title": "fail",
    "headRefName": "feat/fail",
    "headRefOid": "b" * 40,
    "createdAt": "2026-09-23T08:30:00Z",
    "mergedAt": None,
    "state": "OPEN",
    "baseRefName": "main",
}


def _stub(args):
    if args[:2] == ["pr", "list"]:
        return [PR_OK, PR_FAIL]
    if args[0] == "api" and "check-runs" in args[1]:
        if "feat/ok" in args[1]:
            return {
                "check_runs": [
                    {
                        "name": "g",
                        "conclusion": "success",
                        "completedAt": "2026-09-23T08:01:00Z",
                        "htmlUrl": "x",
                    }
                ]
            }
        return {
            "check_runs": [
                {
                    "name": "g",
                    "conclusion": "failure",
                    "completedAt": "2026-09-23T08:35:00Z",
                    "htmlUrl": "y",
                }
            ]
        }
    raise rec.BlindError(args)


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "estate.db"))
    monkeypatch.delenv("FLUX_EVENTS_PATH", raising=False)
    con = rec._connect()
    for j in rec.run(None, 25, runner=_stub):
        rec.write_journey(con, j)
    con.commit()
    con.close()
    return tmp_path / "estate.db"


# ----------------------------------------------------------- river page


def test_river_page_has_no_leftover_placeholders(db, tmp_path):
    out = tmp_path / "web"
    ren._render_river_page(out / "deploy-river.html")
    html = (out / "deploy-river.html").read_text()
    leftovers = re.findall(r"\{\{[A-Z_]+\}\}", html)
    assert leftovers == []


def test_river_page_inlines_one_comet_per_open_pr(db, tmp_path):
    out = tmp_path / "web"
    ren._render_river_page(out / "deploy-river.html")
    html = (out / "deploy-river.html").read_text()
    assert html.count('<circle r="6" class="comet-body"/>') == 1


def test_river_page_inlines_recent_history(db, tmp_path):
    out = tmp_path / "web"
    ren._render_river_page(out / "deploy-river.html")
    html = (out / "deploy-river.html").read_text()
    # PR_OK merged -> appears in the recent trail
    assert "aaaaaaa" in html


def test_river_page_ambient_drives_color(db, tmp_path):
    out = tmp_path / "web"
    ren._render_river_page(out / "deploy-river.html")
    html = (out / "deploy-river.html").read_text()
    # PR_FAIL is open with a failed check -> ambient = red
    assert "#d05656" in html


def test_river_page_blind_when_ledger_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "never.db"))
    out = tmp_path / "web"
    ren._render_river_page(out / "deploy-river.html")
    html = (out / "deploy-river.html").read_text()
    assert "BLIND" in html


# ----------------------------------------------------------- scrub page


def test_scrub_page_inlines_journey_data(db, tmp_path):
    out = tmp_path / "web"
    ren._render_scrub_page(out / "deploy-time-scrub.html", "2026-09-23")
    html = (out / "deploy-time-scrub.html").read_text()
    m = re.search(r"const INLINED = (\{.*?\});", html, re.DOTALL)
    assert m, "scrub page missing INLINED JSON"
    data = json.loads(m.group(1))
    assert data["available"] is True
    assert len(data["journeys"]) == 2
    shas = {j["sha"] for j in data["journeys"]}
    assert shas == {"a" * 40, "b" * 40}


def test_scrub_page_handles_empty_day(db, tmp_path):
    out = tmp_path / "web"
    ren._render_scrub_page(out / "deploy-time-scrub.html", "2025-01-01")
    html = (out / "deploy-time-scrub.html").read_text()
    m = re.search(r"const INLINED = (\{.*?\});", html, re.DOTALL)
    data = json.loads(m.group(1))
    assert data["journeys"] == []
    assert "no journeys" in data["error"]


# ----------------------------------------------------------- observatory


def test_observatory_inlines_rings(db, tmp_path):
    out = tmp_path / "web"
    con = sqlite3.connect(str(db))
    # The fixture only seeds deploy_journeys schema; observatory needs assets.
    con.execute(
        "CREATE TABLE IF NOT EXISTS assets (declared_in TEXT, id TEXT,"
        " name TEXT, plane TEXT, type TEXT, verdict TEXT, why TEXT,"
        " licence_file TEXT)"
    )
    con.execute(
        "INSERT INTO assets VALUES (?,?,?,?,?,?,?,?)",
        (
            "judges.yaml",
            "redteam:1",
            "red-team #1",
            "adversarial",
            "redteam",
            "pass",
            "no payload triggered",
            "LICENSE",
        ),
    )
    con.execute(
        "INSERT INTO assets VALUES (?,?,?,?,?,?,?,?)",
        (
            "seals.yaml",
            "seal:1",
            "aevum seal #1",
            "physics",
            "seal",
            "pass",
            "Ed25519 verified",
            "LICENSE",
        ),
    )
    con.commit()
    con.close()
    ren._render_observatory_page(out / "deploy-observatory.html")
    html = (out / "deploy-observatory.html").read_text()
    assert html.count('class="star') >= 2


def test_observatory_shows_empty_label_when_no_ring_data(db, tmp_path):
    out = tmp_path / "web"
    ren._render_observatory_page(out / "deploy-observatory.html")
    html = (out / "deploy-observatory.html").read_text()
    assert "no ring data yet" in html


# ----------------------------------------------------------- CLI entry


def test_cli_renders_three_pages(db, tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_DB", str(db))
    target = tmp_path / "out"
    r = subprocess.run(
        [sys.executable, str(RENDERER), "2026-09-23", "--out", str(target)],
        capture_output=True,
        text=True,
        env={
            **__import__("os").environ,
            "ESTATE_DB": str(db),
        },
    )
    assert r.returncode == 0, r.stderr
    for name in (
        "deploy-river.html",
        "deploy-time-scrub.html",
        "deploy-observatory.html",
    ):
        assert (target / name).exists(), f"missing {name}"
        html = (target / name).read_text()
        leftovers = re.findall(r"\{\{[A-Z_]+\}\}", html)
        assert leftovers == [], f"{name} has leftover placeholders: {leftovers}"


def test_renderer_never_imports_llm():
    """The renderer must not import any LLM client -- it is a pure data
    inliner; the language model lives in the voice pipeline, not here."""
    src = RENDERER.read_text()
    forbidden = ("litellm", "openai", "anthropic", "langchain")
    for name in forbidden:
        assert name not in src
