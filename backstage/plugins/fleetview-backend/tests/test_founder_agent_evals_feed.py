"""The founder's eval surface: the ledger and the feed it renders, and the absences it names.

Founder, 2026-10-23: "the founder surface must monitor evals across the estate in real time."
Two failure modes are what these tests exist to refuse:

  * a panel rendering "no rounds yet" over a ledger that is *not there* -- a green light for an
    eval nobody ran (the same defect class as a gate that cannot fail), and
  * a live feed that silently stops when its publish fails, so a round in flight looks idle.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from fleetview_backend import founder_agent_evals as fa


def _ledger(tmp_path, **state):
    path = tmp_path / "rounds.json"
    path.write_text(json.dumps(state), encoding="utf-8")
    return path


def _feed(tmp_path, events):
    path = tmp_path / "live.jsonl"
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    return path


def _round(n, green=True, items=()):
    return {
        "round": n,
        "started": "2026-10-23T00:00:00Z",
        "suite_sha": "s",
        "pass_rate": 1.0 if green else 0.5,
        "verdict": {"G1": "pass" if green else "fail", "P": "pass"},
        "perf": "pass" if green else "fail",
        "improvement": "insufficient-data",
        "green": green,
        "performance": {"answered_ms": {"p50": 900.0, "p95": 1400.0}, "cost_usd": 0.02},
        "improvement_items": list(items),
    }


def test_a_missing_ledger_is_named_not_rendered_as_no_rounds(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_FOUNDER_EVAL_LEDGER", str(tmp_path / "absent.json"))
    monkeypatch.setenv("ESTATE_FOUNDER_EVAL_FEED", str(tmp_path / "feed.jsonl"))
    with pytest.raises(fa.EvalsAbsent) as exc:
        fa.snapshot()
    assert "no round ledger at" in str(exc.value)
    assert "run.py --suite" in str(exc.value)


def test_a_half_written_ledger_says_it_could_not_be_read(tmp_path, monkeypatch):
    bad = tmp_path / "rounds.json"
    bad.write_text('{"rounds": [', encoding="utf-8")
    monkeypatch.setenv("ESTATE_FOUNDER_EVAL_LEDGER", str(bad))
    with pytest.raises(fa.EvalsAbsent) as exc:
        fa.snapshot()
    assert "not readable JSON" in str(exc.value)


def test_the_defaults_are_the_paths_the_harness_itself_writes():
    """An earlier default was `reports/rounds.json`, which `run.py` never writes (`ROUNDS` is
    beside the harness at `eval/founder-agent/rounds.json`). A surface whose default path is one
    the writer never touches answers 503 over a ledger that exists -- so pin the two paths to the
    writer's own constants, read from the source rather than restated here."""
    root = fa.DEFAULT_LEDGER.parents[2]
    run_src = (root / "eval" / "founder-agent" / "run.py").read_text(encoding="utf-8")
    live_src = (root / "eval" / "founder-agent" / "gate_live.py").read_text(
        encoding="utf-8"
    )
    assert 'ROUNDS = HERE / "rounds.json"' in run_src
    assert fa.DEFAULT_LEDGER.name == "rounds.json"
    assert fa.DEFAULT_LEDGER.parent.name == "founder-agent"
    assert fa.DEFAULT_FEED.name == "live.jsonl"
    assert "reports" in live_src.split("ESTATE_FOUNDER_EVAL_LIVE")[1][:200]


def test_a_ledger_row_is_reshaped_from_the_g1_and_perf_it_really_carries(
    tmp_path, monkeypatch
):
    """The row `run.py` writes has flat `g1` / `perf` statuses and no `recent_green`; the panel
    wants a gate map and a count. Both are re-shapings of measured values, so the panel cannot
    disagree with the gate about whether the agent is converging."""
    monkeypatch.setenv(
        "ESTATE_FOUNDER_EVAL_LEDGER",
        str(
            _ledger(
                tmp_path,
                rounds=[
                    {"round": 0, "g1": "fail", "green": False, "pass_rate": 0.0},
                    {
                        "round": 1,
                        "g1": "pass",
                        "perf": "pass",
                        "green": True,
                        "pass_rate": 1.0,
                    },
                    {
                        "round": 2,
                        "g1": "pass",
                        "perf": "pass",
                        "green": True,
                        "pass_rate": 1.0,
                    },
                ],
            )
        ),
    )
    monkeypatch.setenv("ESTATE_FOUNDER_EVAL_FEED", str(tmp_path / "none.jsonl"))
    snap = fa.snapshot()
    assert snap["latest"]["verdict"] == {"G1": "pass", "P": "pass"}
    assert snap["recent_green"] == 2
    assert snap["rounds_measured"] == 3


def test_the_snapshot_carries_the_newest_round_and_the_round_counter(
    tmp_path, monkeypatch
):
    monkeypatch.setenv(
        "ESTATE_FOUNDER_EVAL_LEDGER",
        str(_ledger(tmp_path, rounds=[_round(0), _round(1, green=False)])),
    )
    monkeypatch.setenv("ESTATE_FOUNDER_EVAL_FEED", str(tmp_path / "none.jsonl"))
    snap = fa.snapshot()
    assert snap["latest"]["round"] == 1
    assert snap["latest"]["performance"]["answered_ms"]["p95"] == 1400.0
    # Counted from the rows, not read from the file: `run.py` returns the counter and does not
    # persist it, so a `recent_green:` key in the ledger is not a thing the harness writes.
    assert snap["recent_green"] == 1
    assert snap["running"] is None
    assert snap["live"] == []


def test_a_round_whose_start_has_no_end_reads_as_running(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_FOUNDER_EVAL_LEDGER", str(_ledger(tmp_path, rounds=[])))
    monkeypatch.setenv(
        "ESTATE_FOUNDER_EVAL_FEED",
        str(
            _feed(
                tmp_path,
                [
                    {
                        "kind": "round.start",
                        "session_id": "r7",
                        "agent": "door",
                        "tasks": 12,
                        "runs": 3,
                        "at": "2026-10-23T00:00:00Z",
                    },
                    {
                        "kind": "run.end",
                        "session_id": "r7",
                        "task": "table-booking",
                        "ok": True,
                        "at": "2026-10-23T00:00:05Z",
                    },
                ],
            )
        ),
    )
    snap = fa.snapshot()
    assert snap["running"]["round"] == "r7"
    assert snap["running"]["turns_done"] == 1
    assert snap["running"]["tasks"] == 12


def test_a_round_that_ended_is_not_still_running(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_FOUNDER_EVAL_LEDGER", str(_ledger(tmp_path, rounds=[])))
    monkeypatch.setenv(
        "ESTATE_FOUNDER_EVAL_FEED",
        str(
            _feed(
                tmp_path,
                [
                    {
                        "kind": "round.start",
                        "session_id": "r7",
                        "at": "2026-10-23T00:00:00Z",
                    },
                    {
                        "kind": "round.end",
                        "session_id": "r7",
                        "at": "2026-10-23T00:04:00Z",
                    },
                ],
            )
        ),
    )
    assert fa.snapshot()["running"] is None


def test_the_feed_reports_a_publish_it_could_not_make(tmp_path, monkeypatch):
    """The harness records `feed.not_published` rather than going quiet, and the surface shows it:
    a live feed that stops on a dead bus is indistinguishable from an idle estate."""
    monkeypatch.setenv("ESTATE_FOUNDER_EVAL_LEDGER", str(_ledger(tmp_path, rounds=[])))
    monkeypatch.setenv(
        "ESTATE_FOUNDER_EVAL_FEED",
        str(
            _feed(
                tmp_path,
                [
                    {
                        "kind": "feed.not_published",
                        "session_id": "r7",
                        "why": "no bus configured (ESTATE_FOUNDER_EVAL_NATS unset)",
                        "at": "2026-10-23T00:00:00Z",
                    }
                ],
            )
        ),
    )
    live = fa.snapshot()["live"]
    assert live[0]["kind"] == "feed.not_published"
    assert "no bus configured" in live[0]["why"]
    assert isinstance(live[0]["age_s"], float)


def test_the_stream_emits_a_frame_and_then_only_on_change(tmp_path, monkeypatch):
    ledger = _ledger(tmp_path, rounds=[_round(0)])
    monkeypatch.setenv("ESTATE_FOUNDER_EVAL_LEDGER", str(ledger))
    monkeypatch.setenv("ESTATE_FOUNDER_EVAL_FEED", str(tmp_path / "none.jsonl"))

    async def _collect():
        out: list[str] = []
        frames = fa.stream(interval_s=0.02)

        async def _pull():
            async for frame in frames:
                out.append(frame)

        task = asyncio.create_task(_pull())
        await asyncio.sleep(0.1)  # nothing has changed: exactly one frame should exist
        quiet = list(out)
        ledger.write_text(
            json.dumps({"rounds": [_round(0), _round(1)]}), encoding="utf-8"
        )
        await asyncio.sleep(0.2)
        task.cancel()
        return quiet, out

    quiet, all_frames = asyncio.run(_collect())
    assert len(quiet) == 1, f"a quiet ledger produced {len(quiet)} frames"
    assert len(all_frames) == 2, f"a change produced {len(all_frames)} frames in total"
    assert json.loads(quiet[0][len("data: ") :])["latest"]["round"] == 0
    assert json.loads(all_frames[1][len("data: ") :])["latest"]["round"] == 1


def test_the_stream_says_absent_instead_of_going_quiet(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_FOUNDER_EVAL_LEDGER", str(tmp_path / "absent.json"))
    monkeypatch.setenv("ESTATE_FOUNDER_EVAL_FEED", str(tmp_path / "none.jsonl"))

    async def _one_frame():
        frames = fa.stream(interval_s=0.01)
        frame = await frames.__anext__()
        await frames.aclose()
        return frame

    body = json.loads(asyncio.run(_one_frame())[len("data: ") :])
    assert "no round ledger at" in body["absent"]
