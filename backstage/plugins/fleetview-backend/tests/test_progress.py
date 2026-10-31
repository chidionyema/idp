"""fleetview_backend.progress: what /fleet shows of the estate's progress report, and that a
report nobody could read is unavailable with its reason, never an empty board."""

import json

from fleetview_backend import progress, routes


def _report(verdict="PROGRESSING", landed=52):
    return {
        "schema": "estate.progress.v1",
        "verdict": {"state": verdict, "why": ["52 lanes landed in the window"]},
        "signals": {
            "chain": {"landed_in_window": landed, "lanes_inflight": 17},
            "blind": [],
        },
    }


def test_the_report_is_served_from_the_writer_s_file(monkeypatch, tmp_path):
    path = tmp_path / "estate-progress.json"
    path.write_text(json.dumps(_report()))
    monkeypatch.setenv("ESTATE_PROGRESS_REPORT", str(path))
    progress._cache.update(at=0.0, body=None)
    body = progress.progress_snapshot(now=1000.0)
    assert body["available"] is True
    assert body["report"]["verdict"]["state"] == "PROGRESSING"
    assert body["report"]["signals"]["chain"]["landed_in_window"] == 52


def test_the_route_serves_the_same_report(monkeypatch, tmp_path):
    path = tmp_path / "estate-progress.json"
    path.write_text(json.dumps(_report(verdict="SLIPPING")))
    monkeypatch.setenv("ESTATE_PROGRESS_REPORT", str(path))
    progress._cache.update(at=0.0, body=None)
    env, status = routes.progress_envelope()
    assert status == 200 and json.dumps(env)
    assert env["available"] is True
    assert env["report"]["verdict"]["state"] == "SLIPPING"


def test_no_report_is_unavailable_with_its_reason_not_an_empty_board(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("ESTATE_PROGRESS_REPORT", str(tmp_path / "nothing.json"))
    monkeypatch.setenv(
        "ESTATE_IDP_ROOT", str(tmp_path)
    )  # no bin/estate-progress either
    progress._cache.update(at=0.0, body=None)
    body = progress.progress_snapshot(now=5.0)
    assert body["available"] is False
    assert "nothing.json" in body["error"]


def test_nowait_never_waits_on_a_measurement(monkeypatch, tmp_path):
    import threading
    import time

    release = threading.Event()
    calls = []

    def slow(now=None):
        calls.append(1)
        release.wait(5)
        return {"available": True}

    monkeypatch.setattr(progress, "progress_snapshot", slow)
    progress._cache.update(at=0.0, body=None)
    t0 = time.time()
    first = progress.progress_snapshot_nowait(now=1000.0)
    assert time.time() - t0 < 1.0  # the reader runs off the request path
    assert first["available"] is False and "in flight" in first["error"]
    progress._cache.update(at=1000.0, body={"available": True, "stale": True})
    stale = progress.progress_snapshot_nowait(now=1100.0)  # past CACHE_S
    assert stale["stale"] is True  # last body served while the refresh runs
    release.set()
    for _ in range(50):
        if not progress._refresh_lock.locked():
            break
        time.sleep(0.05)
    assert len(calls) == 1  # one refresh at a time, not one per poll
