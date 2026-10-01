"""Concierge tasks on Fleet and by voice (backstage/plugins/fleetview-backend/src/fleetview_backend/
concierge_tasks.py, voice_intents.py).

A task starts through the committed `concierge-task` intent, detached, and is read back from the
events file the intent appends to while the browser runs. These tests run no browser and no
executor: the executor is a shell script that records its argv, and the events files are written
by hand in the shape bin/concierge-task --events writes them.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "backstage" / "plugins" / "fleetview-backend" / "src" / "fleetview_backend"
INTENT = ROOT / "platform" / "estate" / "intents" / "concierge-task.yaml"


def _member(name: str):
    full = f"fleetview_backend.{name}"
    if full in sys.modules:
        return sys.modules[full]
    pkg = sys.modules.setdefault("fleetview_backend", types.ModuleType("fleetview_backend"))
    if not hasattr(pkg, "__path__"):
        pkg.__path__ = [str(PKG)]
    spec = importlib.util.spec_from_file_location(full, PKG / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "fleetview_backend"
    sys.modules[full] = mod
    spec.loader.exec_module(mod)
    setattr(pkg, name, mod)
    return mod


ct = _member("concierge_tasks")
vi = _member("voice_intents")


@pytest.fixture
def laptop(tmp_path, monkeypatch):
    """A tasks dir and a fake estate-execute that records what it was asked to run."""
    exe = tmp_path / "estate-execute"
    exe.write_text('#!/bin/sh\nprintf \'%s\\n\' "$@" > "$(dirname "$0")/argv.txt"\n')
    exe.chmod(0o755)
    tasks = tmp_path / "tasks"
    monkeypatch.setenv("ESTATE_EXECUTE", str(exe))
    monkeypatch.setenv("FLEETVIEW_CONCIERGE_DIR", str(tasks))
    monkeypatch.setenv("FLEETVIEW_INTENTS_DIR", str(tmp_path / "intents"))
    monkeypatch.setenv("FLEETVIEW_INTENT_LOG", str(tmp_path / "voice.jsonl"))
    (tmp_path / "intents").mkdir()
    vi._PENDING.clear()
    vi._PENDING_TASK.clear()

    class Laptop:
        dir = tasks

        @staticmethod
        def argv() -> list[str]:
            p = tmp_path / "argv.txt"
            for _ in range(250):
                if p.exists() and p.read_text().strip():
                    return p.read_text().splitlines()
                time.sleep(0.02)
            return []

        @staticmethod
        def events(task_id: str, *lines: dict) -> Path:
            tasks.mkdir(parents=True, exist_ok=True)
            p = tasks / f"{task_id}.jsonl"
            p.write_text("".join(json.dumps(d) + "\n" for d in lines))
            return p

    return Laptop


def ev(kind, text, step=1, **kw):
    return {"kind": kind, "text": text, "step": step, "url": "", "at": time.time(), **kw}


# ── the intent is the only road ───────────────────────────────────────────────────────────────


def test_the_intent_writes_the_events_file_the_page_reads():
    import yaml

    doc = yaml.safe_load(INTENT.read_text())
    assert doc["name"] == "concierge-task"
    assert "default" not in doc["args"]["goal"], "goal must be said; it is never a voice-catalog intent"
    assert doc["args"]["task_id"]["default"] == ""
    step = doc["steps"][0]
    assert step["timeout"] >= 600, "a browser task takes minutes; the executor's default 120s cuts it"
    assert "--events" in step["cmd"] and "concierge-tasks/$id.jsonl" in step["cmd"]
    assert "--never-pay" in step["cmd"]


def test_start_runs_the_intent_detached_with_the_goal_and_task_id(laptop):
    out = ct.start("check bytesync.io on namecheap", url="https://www.namecheap.com/", by="founder")
    assert out["state"] == "running" and out["by"] == "founder"
    argv = laptop.argv()
    assert argv[0] == "concierge-task"
    assert argv[1] == "goal=check bytesync.io on namecheap"
    assert argv[2] == f"task_id={out['task_id']}"
    assert argv[3] == "url=https://www.namecheap.com/"
    assert (laptop.dir / f"{out['task_id']}.log").read_text().startswith("started by founder")


def test_an_empty_or_oversized_goal_is_refused_before_anything_runs(laptop):
    body, status = ct.handle_post({"goal": "   "})
    assert status == 400 and "Say what" in body["error"]
    body, status = ct.handle_post({"goal": "x" * (ct.MAX_GOAL_CHARS + 1)})
    assert status == 400 and "shorter" in body["error"]
    body, status = ct.handle_post("nope")
    assert status == 400
    assert laptop.argv() == []


def test_off_the_laptop_the_board_says_so(laptop, monkeypatch):
    monkeypatch.setenv("ESTATE_EXECUTE", str(laptop.dir / "missing"))
    body, status = ct.list_tasks()
    assert status == 503 and body["available"] is False and "laptop" in body["error"]
    body, status = ct.handle_post({"goal": "anything"})
    assert status == 503


# ── the page reads the events as they happen ─────────────────────────────────────────────────


def test_a_running_task_shows_its_goal_findings_and_last_step(laptop):
    laptop.events(
        "1-aa",
        {"kind": "goal", "text": "check three domains", "url": "https://r.test/", "at": time.time()},
        ev("plan", "Noting status for bytesync.com", 1),
        ev("found", "bytesync.com: REGISTERED IN 2005", 1),
        ev("act", "type 17 bytesync.co.uk", 2, url="https://r.test/?d=co.uk"),
    )
    body, status = ct.list_tasks()
    assert status == 200 and body["available"]
    (t,) = body["tasks"]
    assert t["task_id"] == "1-aa" and t["goal"] == "check three domains"
    assert t["state"] == "running" and t["outcome"] == "running"
    assert t["found"] == ["bytesync.com: REGISTERED IN 2005"]
    assert t["last"] == "type 17 bytesync.co.uk" and t["last_kind"] == "act" and t["steps"] == 2
    assert t["url"] == "https://r.test/?d=co.uk"
    assert [e["kind"] for e in t["events"]] == ["plan", "found", "act"]


def test_a_finished_task_carries_its_result_receipt_and_state(laptop):
    laptop.events(
        "2-bb",
        {"kind": "goal", "text": "price of x", "at": 1.0},
        ev("plan", "looking", 1),
        {"kind": "result", "success": True, "outcome": "done", "summary": "£9/yr", "steps": 3,
         "final_url": "https://r.test/x", "receipt_image_path": "/r/task_2.png"},
    )
    laptop.events(
        "3-cc",
        {"kind": "goal", "text": "buy y", "at": 2.0},
        ev("hold", "This is a payment page", 4),
        {"kind": "result", "success": False, "outcome": "held", "summary": "Stopped at the payment page; nothing was paid.", "steps": 4},
    )
    laptop.events(
        "4-dd",
        {"kind": "goal", "text": "broken", "at": 3.0},
        {"kind": "result", "success": False, "outcome": "failed", "summary": "Could not open", "steps": 0},
    )
    body, _ = ct.list_tasks()
    by_id = {t["task_id"]: t for t in body["tasks"]}
    assert by_id["2-bb"]["state"] == "done" and by_id["2-bb"]["summary"] == "£9/yr"
    assert by_id["2-bb"]["receipt"] == "/r/task_2.png" and by_id["2-bb"]["url"] == "https://r.test/x"
    assert by_id["3-cc"]["state"] == "held" and by_id["3-cc"]["outcome"] == "held"
    assert by_id["4-dd"]["state"] == "failed"


def test_a_task_that_went_quiet_is_not_shown_as_running(laptop):
    p = laptop.events("5-ee", {"kind": "goal", "text": "slow", "at": 1.0}, ev("plan", "thinking", 1))
    old = time.time() - ct.STALE_AFTER_S - 5
    os.utime(p, (old, old))
    (t,) = ct.list_tasks()[0]["tasks"]
    assert t["state"] == "failed" and t["outcome"] == "stale"


def test_a_half_written_line_is_skipped_not_fatal(laptop):
    p = laptop.events("6-ff", {"kind": "goal", "text": "g", "at": 1.0}, ev("plan", "ok", 1))
    with p.open("a") as f:
        f.write('{"kind": "act", "text": "half')
    (t,) = ct.list_tasks()[0]["tasks"]
    assert t["state"] == "running" and t["last"] == "ok"


def test_newest_first_and_only_events_files_count(laptop):
    laptop.events("7-aa", {"kind": "goal", "text": "first", "at": 1.0})
    time.sleep(0.02)
    laptop.events("8-bb", {"kind": "goal", "text": "second", "at": 2.0})
    (laptop.dir / "8-bb.log").write_text("started by fleet\n")
    ids = [t["task_id"] for t in ct.list_tasks()[0]["tasks"]]
    assert ids == ["8-bb", "7-aa"]


# ── by voice ──────────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "said,task",
    [
        ("Concierge, buy bytesync.com on Namecheap.", "buy bytesync.com on Namecheap"),
        ("concierge check whether bytesync.io is free", "check whether bytesync.io is free"),
        ("Hey concierge: find the cheapest flight to Lagos", "find the cheapest flight to Lagos"),
        ("OK. Please ask the concierge to renew the domain.", "renew the domain"),
        ("have the concierge fill in the Companies House form", "fill in the Companies House form"),
        ("tell the concierge to check the order", "check the order"),
        ("Concierge.", ""),
        ("what is the concierge doing", None),
        ("is the concierge deployed", None),
        ("give an agent a job: fix the concierge", None),
    ],
)
def test_the_phrase_is_heard_and_the_task_is_what_came_after_it(said, task):
    assert vi.concierge_task(said) == task


def test_a_spoken_task_is_read_back_and_nothing_starts_before_yes(laptop):
    r = vi.handle("Concierge, buy bytesync.com on Namecheap.", "s1")
    assert (r["intent"], r["status"]) == ("concierge-task", "pending_confirmation")
    assert r["text"] == "Ask the concierge to: buy bytesync.com on Namecheap? Say yes to confirm."
    assert laptop.argv() == []


def test_yes_starts_it_through_the_intent_and_points_at_fleet(laptop):
    vi.handle("concierge buy bytesync.com on Namecheap", "s1")
    r = vi.handle("yes", "s1")
    assert (r["intent"], r["status"]) == ("concierge-task", "ok")
    assert r["text"].startswith("The concierge is on it, task ") and "Fleet" in r["text"]
    argv = laptop.argv()
    assert argv[:2] == ["concierge-task", "goal=buy bytesync.com on Namecheap"]
    assert argv[2].startswith("task_id=")


def test_no_cancels_and_nothing_starts(laptop):
    vi.handle("concierge buy bytesync.com", "s1")
    r = vi.handle("no", "s1")
    assert r["status"] == "cancelled"
    assert laptop.argv() == []


def test_the_word_alone_asks_for_the_task(laptop):
    r = vi.handle("Concierge.", "s1")
    assert r["status"] == "error" and "Say the task" in r["text"]
    assert laptop.argv() == []


def test_a_yes_in_another_session_starts_nothing(laptop):
    vi.handle("concierge buy bytesync.com", "phone")
    assert vi.handle("yes", "glasses") is None
    assert laptop.argv() == []


def test_the_agent_job_phrase_still_wins_when_both_words_are_said(laptop):
    r = vi.handle("give an agent a job: fix the concierge", "s1")
    assert r["intent"] == "agent-job"
