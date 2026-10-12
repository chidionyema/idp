"""fleetview_backend.claims: the live claims AGENTS.md section 5 promises on /fleet -- who holds
which paths, how old the heartbeat is -- and the two things it must never do: show a claim that
cannot be read as live, and show a read that could not reach GitHub as "nobody holds anything"."""

import time

from fleetview_backend import agent_jobs, claims, routes

NOW = 1_700_000_000.0  # fixed, so an age is a measurement and not a race with the clock
REPO = "chidionyema/idp"


def _comment(issue: int, body: str, at: str = "2026-10-12T00:00:00Z") -> dict:
    return {
        "body": body,
        "issue_url": f"https://api.github.com/repos/{REPO}/issues/{issue}",
        "created_at": at,
    }


def _claim_body(agent: str, paths: str, hb: str) -> str:
    return f"CLAIM agent={agent} paths={paths} heartbeat={hb}"


def _hb(seconds_ago: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - seconds_ago))


def _issue(n: int, title: str = "some work", state: str = "open") -> dict:
    return {"number": n, "title": title, "state": state}


def _wire(monkeypatch, comments, issues=(), fail=False):
    issues = list(issues)

    def gh_get(path: str):
        if fail:
            raise RuntimeError("GitHub is unreachable from Fleet")
        if "/issues/comments?" in path:
            return 200, comments
        if "/search/issues?" in path:
            return 200, {"items": issues}
        raise AssertionError(f"unexpected path {path}")

    monkeypatch.setenv("FLEETVIEW_AGENT_REPO", REPO)
    monkeypatch.setattr(agent_jobs, "gh_get", gh_get)
    claims._cache.update(at=0.0, body=None)


def test_a_live_claim_carries_who_what_paths_and_heartbeat_age(monkeypatch):
    _wire(
        monkeypatch,
        [
            _comment(
                5737, _claim_body("otto", "backstage/x.ts,backstage/y.ts", _hb(600))
            )
        ],
        [_issue(5737, "face+fleet: conversation, push, and presence")],
    )
    body = claims.claims_snapshot(now=NOW)
    assert body["available"] is True and body["claims"], body
    c = body["claims"][0]
    assert c["agent"] == "otto"
    assert c["paths"] == ["backstage/x.ts", "backstage/y.ts"]
    assert c["title"] == "face+fleet: conversation, push, and presence"
    assert c["issue"] == 5737
    assert c["live"] is True and c["reason"] == "live"
    assert 590 <= c["age_s"] <= 610, c["age_s"]
    assert body["counts"] == {"live": 1, "released": 0, "stale": 0, "issues": 1}


def test_a_heartbeat_older_than_two_hours_is_stale_not_live(monkeypatch):
    _wire(
        monkeypatch,
        [_comment(5616, _claim_body("opencode", "bin/idp-shadow", _hb(3 * 3600)))],
        [_issue(5616)],
    )
    body = claims.claims_snapshot(now=NOW)
    assert body["claims"][0]["live"] is False
    assert body["claims"][0]["reason"] == "stale heartbeat"
    assert body["counts"]["stale"] == 1 and body["counts"]["live"] == 0


def test_a_claim_on_a_closed_issue_is_released_not_stale(monkeypatch):
    # AGENTS.md section 5 rule 6: closing the issue releases the claim. A fresh heartbeat on a
    # closed issue is finished work, and reporting it as a live claim would put work that is
    # done back in front of the founder as though someone still held the files.
    _wire(
        monkeypatch,
        [
            _comment(
                5788, _claim_body("chidionyema", "bin/estate-twin-runtime", _hb(60))
            )
        ],
        [_issue(5788, "the twin's bus probe is unbounded", state="closed")],
    )
    body = claims.claims_snapshot(now=NOW)
    c = body["claims"][0]
    assert c["live"] is False and c["reason"] == "issue closed"
    assert c["issue_open"] is False
    assert body["counts"] == {"live": 0, "released": 1, "stale": 0, "issues": 1}


def test_an_issue_the_search_index_has_not_seen_is_unknown_not_closed(monkeypatch):
    # A claim posted seconds ago on a brand-new issue is not in the search index yet. "Not
    # indexed" must not be read as "closed": that would hide the freshest claim on the page.
    _wire(monkeypatch, [_comment(5900, _claim_body("otto", "bin/new", _hb(30)))], [])
    c = claims.claims_snapshot(now=NOW)["claims"][0]
    assert c["issue_open"] is None and c["live"] is True
    assert c["title"] is None


def test_a_heartbeat_that_is_not_a_time_is_not_live(monkeypatch):
    # bin/claim-gate's own refusal ("heartbeat {hb!r} is not a UTC ISO time"): an unreadable
    # stamp must not be graded as the freshest claim on the page by an age of 0.
    _wire(
        monkeypatch,
        [_comment(5605, _claim_body("claude", "docs/x.md", "yesterday"))],
        [_issue(5605)],
    )
    c = claims.claims_snapshot(now=NOW)["claims"][0]
    assert c["live"] is False and c["age_s"] is None
    assert c["reason"] == "unreadable heartbeat"


def test_the_newest_claim_on_an_issue_wins(monkeypatch):
    _wire(
        monkeypatch,
        [
            _comment(5755, _claim_body("claude", "backstage/old", _hb(5000))),
            _comment(5755, _claim_body("claude", "backstage/new", _hb(60))),
        ],
        [_issue(5755)],
    )
    body = claims.claims_snapshot(now=NOW)
    assert len(body["claims"]) == 1
    assert body["claims"][0]["paths"] == ["backstage/new"]


def test_claims_are_sorted_live_first_then_freshest(monkeypatch):
    _wire(
        monkeypatch,
        [
            _comment(1, _claim_body("a", "p1", _hb(9 * 3600))),
            _comment(2, _claim_body("b", "p2", _hb(300))),
            _comment(3, _claim_body("c", "p3", _hb(120))),
        ],
        [_issue(1), _issue(2), _issue(3)],
    )
    body = claims.claims_snapshot(now=NOW)
    assert [c["issue"] for c in body["claims"]] == [3, 2, 1]


def test_a_read_that_cannot_reach_github_is_unavailable_not_empty(monkeypatch):
    _wire(monkeypatch, [], fail=True)
    body = claims.claims_snapshot(now=NOW)
    assert body["available"] is False
    assert body["claims"] == []
    assert "unreachable" in body["error"]
    # And the route still answers 200 with that reason, the way greenlane.py reports a lane it
    # could not read: the page shows "unreadable", never a confident zero.
    env, status = routes.claims_envelope()
    assert status == 200 and env["available"] is False


def test_the_window_is_reported_so_a_claim_it_did_not_read_is_not_a_zero(monkeypatch):
    _wire(monkeypatch, [_comment(9, _claim_body("a", "p", "not-a-time"))], [_issue(9)])
    body = claims.claims_snapshot(now=NOW)
    assert body["window_h"] == claims.WINDOW_H
    assert body["source"] == f"{REPO} issue comments"
    assert body["truncated"] is False


def test_a_full_page_is_flagged_truncated(monkeypatch):
    # A page that fills means there may be more comments than were read; the payload says so
    # instead of presenting a capped read as the whole truth.
    full = [
        _comment(100 + i, _claim_body(f"a{i}", "p", _hb(60)))
        for i in range(claims.PAGE)
    ]
    _wire(monkeypatch, full, [_issue(100 + i) for i in range(claims.PAGE)])
    body = claims.claims_snapshot(now=NOW)
    assert body["truncated"] is True
