"""The incident loop's own tests: the stages the epic's R-14 asks for, proved or not.

Every test here is hermetic: no network, no GitHub, no cluster. The loop's network stages are
proved by running the loop against the real estate (the sealed-failure drill), not by a mock
here - a test that cannot fail is not a test, and a mock of the thing under test proves nothing
about the thing.

WHAT IS PROVED HERE:
  - the priority function of R-14 (severity + blast radius + age + capacity cost) and its caps;
  - one incident per error (the fingerprint), and one ledger row per incident;
  - the dispatch decision: a session when the bus has room and the score is high enough, the
    worker queue otherwise;
  - MTTR from first_seen to verified.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

LIBEXEC = (
    Path(__file__).resolve().parents[1]
    / "platform"
    / "estate"
    / "libexec"
    / "incident-loop.py"
)
POLICY = Path(__file__).resolve().parents[1] / "catalog" / "incident-policy.json"


def _load():
    spec = importlib.util.spec_from_file_location("incident_loop", LIBEXEC)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


incident_loop = _load()


@pytest.fixture()
def policy():
    return incident_loop.load_policy(POLICY)


def test_the_policy_says_what_the_loop_needs(policy):
    for key in (
        "severities",
        "blast_radius",
        "age",
        "capacity_cost",
        "label_thresholds",
        "dispatch",
        "sense",
    ):
        assert key in policy, key
    assert policy["dispatch"]["max_sessions"] >= 1
    assert policy["dispatch"]["runners"], "a dispatch with no runner dispatches nothing"


def test_severity_outranks_every_other_dimension(policy):
    """A critical incident beats a minor one however old the minor one is."""
    critical, _ = incident_loop.score_incident(policy, "critical", "main")
    minor, _ = incident_loop.score_incident(
        policy, "minor", "local", age_hours=10_000, capacity_minutes=10_000
    )
    assert critical > minor


def test_the_score_never_goes_below_the_severitys_base(policy):
    score, _ = incident_loop.score_incident(policy, "minor", "local")
    assert score >= policy["severities"]["minor"]["base"]
    score, _ = incident_loop.score_incident(policy, "critical", "main")
    assert score >= policy["severities"]["critical"]["base"]


def test_the_score_is_capped_so_one_dimension_cannot_run_away(policy):
    """Age and capacity cost add up, but they are capped: severity decides."""
    capped, _ = incident_loop.score_incident(
        policy, "major", "lane", age_hours=10_000, capacity_minutes=10_000
    )
    fresh, _ = incident_loop.score_incident(policy, "major", "lane")
    assert capped - fresh <= policy["age"]["max"] + policy["capacity_cost"]["max"]


def test_the_label_follows_the_score(policy):
    assert incident_loop.label_for(policy, 1000) == "P0"
    assert incident_loop.label_for(policy, 60) == "P1"
    assert incident_loop.label_for(policy, 0) == "P2"
    _, label = incident_loop.score_incident(policy, "critical", "main")
    assert label == "P0"
    _, label = incident_loop.score_incident(policy, "minor", "local")
    assert label == "P2"


def test_the_same_error_is_the_same_incident():
    first = incident_loop.fingerprint("ci", "chidionyema/idp", "42")
    again = incident_loop.fingerprint("ci", "chidionyema/idp", "42")
    other = incident_loop.fingerprint("ci", "chidionyema/idp", "43")
    assert first == again
    assert first != other


def test_one_incident_holds_one_ledger_row(tmp_path, policy):
    conn = incident_loop.open_ledger(tmp_path / "incidents.db")
    incident = {
        "id": incident_loop.fingerprint("ci", "chidionyema/idp", "7"),
        "source": "ci",
        "repo": "chidionyema/idp",
        "severity": "major",
        "blast": "lane",
        "title": "a workflow failed",
        "url": "https://example.invalid/run/7",
        "detail": {"run_id": 7},
    }
    incident_loop.record_incident(conn, incident, policy)
    incident_loop.record_incident(conn, incident, policy)
    rows = incident_loop.list_incidents(conn)
    assert len(rows) == 1
    history = json.loads(rows[0]["history"])
    assert [event["event"] for event in history] == ["opened", "seen"]
    conn.close()


def test_an_incident_keeps_its_first_seen_and_gains_points_with_age(tmp_path, policy):
    conn = incident_loop.open_ledger(tmp_path / "incidents.db")
    incident = {
        "id": incident_loop.fingerprint("ci", "chidionyema/idp", "9"),
        "source": "ci",
        "repo": "chidionyema/idp",
        "severity": "minor",
        "blast": "lane",
        "title": "a workflow failed",
        "detail": {},
    }
    first = incident_loop.record_incident(conn, incident, policy)
    # age the incident by rewriting its first_seen, then re-sense it: the score must rise and
    # the first_seen must not move
    incident_loop.set_field(conn, incident["id"], first_seen="2026-10-28T00:00:00Z")
    second = incident_loop.record_incident(conn, incident, policy)
    assert second["first_seen"] == "2026-10-28T00:00:00Z"
    assert second["score"] > first["score"]
    conn.close()


def test_the_dispatch_leg_is_chosen_by_measured_capacity(policy):
    rules = policy["dispatch"]
    free = {"reachable": True, "running": 0, "router": True}
    busy = {"reachable": True, "running": rules["max_sessions"], "router": True}
    blind = {"reachable": False, "running": 0, "router": True}
    high = rules["session_min_score"] + 10
    low = rules["session_min_score"] - 10
    assert incident_loop.dispatch_decision(policy, high, free) == "session"
    assert incident_loop.dispatch_decision(policy, high, busy) == "worker"
    assert incident_loop.dispatch_decision(policy, high, blind) == "worker"
    assert incident_loop.dispatch_decision(policy, low, free) == "worker"


def test_no_router_means_the_worker_queue_not_a_session_that_cannot_call_a_model(
    policy,
):
    """A bus that accepts a session whose runner has no route is a dispatch that looks
    like it worked and did not: the incident goes nowhere while the ledger says it was
    dispatched. So the route is measured before the leg is chosen."""
    rules = policy["dispatch"]
    high = rules["session_min_score"] + 10
    no_router = {"reachable": True, "running": 0, "router": False}
    assert incident_loop.dispatch_decision(policy, high, no_router) == "worker"


def test_the_router_probe_asks_the_route_that_can_answer(monkeypatch, policy):
    asked = []

    class _Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(url, timeout=None):
        asked.append(url)
        if "mumchimp" in url:
            raise OSError("the cluster is down")
        return _Response()

    monkeypatch.setattr(incident_loop.urllib.request, "urlopen", fake_urlopen)
    ok, base = incident_loop.router_probe(policy)
    assert ok is True
    assert base == "http://127.0.0.1:4000"
    assert asked[0].endswith("/health")


def test_the_router_probe_reports_no_route_when_every_route_is_silent(
    monkeypatch, policy
):
    def fake_urlopen(url, timeout=None):
        raise OSError("no answer")

    monkeypatch.setattr(incident_loop.urllib.request, "urlopen", fake_urlopen)
    ok, base = incident_loop.router_probe(policy)
    assert ok is False
    assert base == ""


def test_mttr_is_measured_from_first_seen_to_verified():
    seconds = incident_loop.mttr_seconds("2026-10-28T10:00:00Z", "2026-10-28T10:12:30Z")
    assert seconds == 750


def test_an_unknown_severity_or_blast_is_refused_not_guessed(policy):
    with pytest.raises(incident_loop.PolicyError):
        incident_loop.score_incident(policy, "catastrophic", "main")
    with pytest.raises(incident_loop.PolicyError):
        incident_loop.score_incident(policy, "major", "the-whole-estate")


def test_a_red_candidate_is_a_major_error_on_a_lane(monkeypatch, policy):
    """A candidate under the Greenlane's own gate blocks the trunk: it is not a minor push."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    runs = [
        {
            "id": 1,
            "name": "ci",
            "head_branch": "queue/b4507",
            "conclusion": "failure",
            "event": "push",
            "created_at": now,
            "html_url": "u",
        },
        {
            "id": 2,
            "name": "ci",
            "head_branch": "some-branch",
            "conclusion": "failure",
            "event": "push",
            "created_at": now,
            "html_url": "u",
        },
    ]
    monkeypatch.setattr(incident_loop, "run_gh", lambda args: (0, json.dumps(runs), ""))
    incidents = incident_loop.sense_ci("chidionyema/idp", policy)
    by_id = {incident["id"]: incident for incident in incidents}
    candidate = by_id[incident_loop.fingerprint("ci", "chidionyema/idp", "1")]
    push = by_id[incident_loop.fingerprint("ci", "chidionyema/idp", "2")]
    assert candidate["severity"] == "major", candidate
    assert candidate["blast"] == "lane", candidate
    assert push["severity"] == "minor", push


def test_the_sensor_asks_the_api_for_the_window_it_reads(monkeypatch, policy):
    """The window belongs to the query, not to the reader: the newest 50 runs ever is
    minutes of history in a busy hour, and the failure that started the incident is in
    the oldest part of it."""
    seen = {}

    def fake_run_gh(args):
        seen["url"] = " ".join(args)
        return (0, json.dumps([]), "")

    monkeypatch.setattr(incident_loop, "run_gh", fake_run_gh)
    incident_loop.sense_ci("chidionyema/idp", policy)
    assert "created=>" in seen["url"], seen["url"]
    assert "per_page=100" in seen["url"], seen["url"]


def test_the_ledger_holds_exactly_one_record_type(tmp_path):
    conn = incident_loop.open_ledger(tmp_path / "incidents.db")
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    assert tables == {"incidents"}, tables
    conn.close()


def _greenlane_state(outcome, later=None):
    state = {
        "batch": {"id": "b4507", "members": [["lane/incident-loop", "sha", "cand"]]},
        "history": [
            {
                "id": "b4507",
                "members": [["lane/incident-loop", "sha", "cand"]],
                "outcome": outcome,
            }
        ],
    }
    if later:
        state["history"].append(later)
    return state


def _candidate_row(branch="queue/b4507"):
    return {
        "detail": json.dumps(
            {"run_id": 40795323129, "workflow": "ci", "branch": branch, "url": "u"}
        )
    }


def test_a_candidate_is_resolved_when_the_greenlane_landed_its_lane(monkeypatch):
    """The estate's own record of the lane is the verdict, not an unrelated green run."""
    monkeypatch.setattr(
        incident_loop, "greenlane_state", lambda repo: _greenlane_state("landed")
    )
    monkeypatch.setattr(
        incident_loop,
        "run_gh",
        lambda args: (
            0,
            json.dumps(
                [
                    {
                        "id": 40795323130,
                        "name": "ci",
                        "conclusion": "success",
                        "head_branch": "some/other/branch",
                    }
                ]
            ),
            "",
        ),
    )
    resolved, evidence = incident_loop.ci_resolved("chidionyema/idp", _candidate_row())
    assert resolved, "the lane landed, so the red candidate is resolved"
    assert "lane/incident-loop" in evidence


def test_a_candidate_is_not_resolved_by_a_green_run_on_another_branch(monkeypatch):
    """A red candidate stays open on an unrelated green run: the loop must not close early."""
    monkeypatch.setattr(
        incident_loop, "greenlane_state", lambda repo: _greenlane_state("red")
    )
    monkeypatch.setattr(
        incident_loop,
        "run_gh",
        lambda args: (
            0,
            json.dumps(
                [
                    {
                        "id": 40795323130,
                        "name": "ci",
                        "conclusion": "success",
                        "head_branch": "some/other/branch",
                    }
                ]
            ),
            "",
        ),
    )
    resolved, _ = incident_loop.ci_resolved("chidionyema/idp", _candidate_row())
    assert not resolved, "an unrelated green run must not close a red candidate"


def test_a_candidate_is_resolved_when_a_later_batch_landed_the_same_lane(monkeypatch):
    later = {
        "id": "b4508",
        "members": [["lane/incident-loop", "sha2", "cand2"]],
        "outcome": "landed",
    }
    monkeypatch.setattr(
        incident_loop,
        "greenlane_state",
        lambda repo: _greenlane_state("red", later=later),
    )
    resolved, evidence = incident_loop.ci_resolved("chidionyema/idp", _candidate_row())
    assert resolved, "the lane landed in a later batch"
    assert "b4508" in evidence
