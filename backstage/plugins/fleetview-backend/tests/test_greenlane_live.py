"""fleetview_backend.greenlane_live: the Greenlane as it moves -- the batch under test and its
checks, each lane's age and reason, recent outcomes, push-to-land timings, one spoken line -- and
that an unreadable lane is unavailable with its reason, never an empty queue."""

import base64
import json

from fleetview_backend import greenlane_live, routes

NOW_MIN = 1_000_000.0

STATE = {
    "landed": 42,
    "lanes": {
        "lane/face-fix": {
            "status": "testing",
            "arrived": NOW_MIN - 12,
            "attempts": 1,
            "head": "a" * 40,
        },
        "lane/broken": {
            "status": "red",
            "arrived": NOW_MIN - 30,
            "attempts": 2,
            "reason": "ci failed: offline-gate https://github.com/x/y/actions/runs/1",
        },
        "lane/next": {"status": "pending", "arrived": NOW_MIN - 2},
    },
    "batch": {
        "id": 7,
        "tip": "f" * 40,
        "members": [["lane/face-fix", "a" * 40]],
        "started": NOW_MIN - 9,
    },
    "history": [
        {
            "id": 5,
            "members": ["lane/old"],
            "outcome": "green",
            "action": "landed",
            "started": NOW_MIN - 60,
            "verdict_at": NOW_MIN - 40,
        },
        {
            "id": 6,
            "members": ["lane/broken"],
            "outcome": "red",
            "action": "bisect",
            "reason": "offline-gate",
            "started": NOW_MIN - 35,
            "verdict_at": NOW_MIN - 25,
        },
    ],
    "landings": [
        {
            "lane": "lane/old",
            "batch": 5,
            "queued": NOW_MIN - 70,
            "landed": NOW_MIN - 40,
        },
    ],
}


def test_summarise_orders_lanes_and_times_everything():
    v = greenlane_live.summarise(STATE, NOW_MIN)
    assert [lane["name"] for lane in v["lanes"]] == [
        "lane/face-fix",
        "lane/broken",
        "lane/next",
    ]
    assert v["lanes"][0]["age_min"] == 12.0 and v["lanes"][0]["head"] == "a" * 12
    assert v["batch"] == {
        "id": 7,
        "tip": "f" * 40,
        "lanes": ["lane/face-fix"],
        "age_min": 9.0,
    }
    assert [r["id"] for r in v["recent"]] == [6, 5]  # newest first
    assert v["recent"][0]["took_min"] == 10.0 and v["recent"][0]["ago_min"] == 25.0
    assert v["landed"] == [
        {"lane": "lane/old", "batch": 5, "waited_min": 30.0, "ago_min": 40.0}
    ]
    t = v["timings"]
    assert t["queue_to_land_min"] == {"n": 1, "p50": 30.0, "p90": 30.0}
    assert t["batch_cycle_min"]["n"] == 2
    assert t["outcomes"] == {"green/landed": 1, "red/bisect": 1}
    assert v["landed_total"] == 42


def test_sentence_says_what_is_under_test_what_is_red_and_why():
    v = greenlane_live.summarise(STATE, NOW_MIN)
    v["batch"]["checks"] = [
        {"name": "build", "status": "completed", "conclusion": "success"},
        {"name": "offline-gate", "status": "in_progress", "conclusion": None},
    ]
    s = greenlane_live.sentence(v)
    assert s.startswith("Testing face-fix for 9 minutes; waiting on offline-gate.")
    assert "broken is red: ci failed: offline-gate." in s  # the link is not read aloud
    assert s.endswith("Push to land is about 30 minutes.")


def test_a_failed_check_is_named_ahead_of_the_waiting_ones():
    v = greenlane_live.summarise(STATE, NOW_MIN)
    v["batch"]["checks"] = [
        {"name": "build", "status": "completed", "conclusion": "failure"},
        {"name": "offline-gate", "status": "in_progress", "conclusion": None},
    ]
    assert "; build failed." in greenlane_live.sentence(v)


def test_a_quiet_lane_says_what_landed_last():
    st = {k: v for k, v in STATE.items() if k not in ("batch", "lanes")}
    s = greenlane_live.sentence(greenlane_live.summarise(st, NOW_MIN))
    assert s.startswith("Nothing under test. Last landed old, 40 minutes ago.")


def _fake_get(state, checks_status=200):
    calls = []

    def get(path):
        calls.append(path)
        if "/contents/state.json" in path:
            content = base64.b64encode(json.dumps(state).encode()).decode()
            return 200, {"content": content}
        if "/check-runs" in path:
            if checks_status != 200:
                return checks_status, {"message": "nope"}
            return 200, {
                "check_runs": [
                    {
                        "name": "build",
                        "status": "in_progress",
                        "conclusion": None,
                        "html_url": "u",
                    }
                ]
            }
        return 404, {}

    return get, calls


def test_live_reads_state_and_checks_once_inside_the_cache(monkeypatch):
    get, calls = _fake_get(STATE)
    monkeypatch.setattr(greenlane_live, "_get", get)
    monkeypatch.setattr(greenlane_live, "_repo", lambda: "o/r")
    greenlane_live._cache.update(at=0.0, body=None)
    t = NOW_MIN * 60
    v = greenlane_live.live(now=t)
    assert v["available"] is True
    assert v["batch"]["checks"][0]["name"] == "build"
    assert "waiting on build" in v["sentence"]
    assert greenlane_live.live(now=t + 5) is v  # inside CACHE_S: not re-read
    assert len(calls) == 2


def test_a_failed_check_read_is_marked_not_hidden(monkeypatch):
    get, _ = _fake_get(STATE, checks_status=502)
    monkeypatch.setattr(greenlane_live, "_get", get)
    monkeypatch.setattr(greenlane_live, "_repo", lambda: "o/r")
    greenlane_live._cache.update(at=0.0, body=None)
    v = greenlane_live.live(now=NOW_MIN * 60)
    assert v["available"] is True
    assert "checks" not in v["batch"] and "502" in v["batch"]["checks_error"]


def test_an_unreadable_state_is_unavailable_with_its_reason(monkeypatch):
    monkeypatch.setattr(
        greenlane_live, "_get", lambda path: (401, {"message": "bad creds"})
    )
    monkeypatch.setattr(greenlane_live, "_repo", lambda: "o/r")
    greenlane_live._cache.update(at=0.0, body=None)
    body, status = routes.greenlane_live_envelope()
    assert status == 200
    assert body["available"] is False and "401" in body["error"]
    assert "lanes" not in body and "sentence" not in body


def _voice(monkeypatch, view):
    from fleetview_backend import voice_intents

    monkeypatch.setattr(greenlane_live, "live", lambda now=None: view)
    monkeypatch.setattr(voice_intents, "_audit", lambda *a, **k: None)
    monkeypatch.setattr(
        voice_intents, "executor", lambda: object()
    )  # local, not the laptop
    return voice_intents


def test_asking_about_the_greenlane_answers_with_its_sentence(monkeypatch):
    vi = _voice(
        monkeypatch, {"available": True, "sentence": "Testing face-fix for 9 minutes."}
    )
    for said in ("How's the Greenlane?", "what's landing", "green lane status please"):
        r = vi.handle(said, "s1")
        assert r["intent"] == "greenlane-live" and r["status"] == "ok"
        assert r["text"] == "Testing face-fix for 9 minutes."


def test_an_unreadable_greenlane_is_said_as_unreadable(monkeypatch):
    vi = _voice(
        monkeypatch, {"available": False, "error": "the Greenlane state answered 401"}
    )
    r = vi.handle("how is the greenlane", "s2")
    assert (
        r["status"] == "error"
        and "can't read the Greenlane" in r["text"]
        and "401" in r["text"]
    )


def test_an_agent_job_about_the_greenlane_is_still_an_agent_job(monkeypatch):
    vi = _voice(monkeypatch, {"available": True, "sentence": "x"})
    from fleetview_backend import agent_jobs

    monkeypatch.setattr(agent_jobs, "validate", lambda task, who: (task, "h"))
    r = vi.handle("give an agent a job: speed up the greenlane", "s3")
    assert r["intent"] == "agent-job" and r["status"] == "pending_confirmation"
