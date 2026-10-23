"""The research engine researches the objectives the founder wrote, wherever he wrote them.

Founder, 2026-10-23: "mumchimp is a commercial website, ive given you objectives". They sit in
crew and prospector issues (crew#239, #774), not in idp, and the adapter read only idp, so none
was ever researched. These tests pin the intake across repositories and the failures that cost
money: an unbounded founder objective, a lost Park tick, a report posted on the wrong repository,
one unreadable repository blinding the rest.
"""

from __future__ import annotations

import importlib.util
import re
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "objective_adapter", ROOT / "platform" / "research-engine" / "objective-adapter.py"
)
adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adapter)

IDP, CREW, PROSPECTOR = "o/idp", "o/crew", "o/prospector"


@pytest.fixture(autouse=True)
def repos(monkeypatch):
    monkeypatch.setattr(adapter, "REPO", IDP)
    monkeypatch.setattr(adapter, "REPOS", [IDP, CREW, PROSPECTOR])
    monkeypatch.setattr(adapter.time, "sleep", lambda s: None)


def founder_issue(number: int, title: str = "Reimagine mumchimp") -> dict:
    return {
        "number": number,
        "title": title,
        "body": "Founder verbatim: make it a media company.",
    }


def mined_issue(number: int, rank: float = 48.0) -> dict:
    return {
        "number": number,
        "title": f"objective: thing {number}",
        "body": f"rank {rank} min per USD\n**cap:** $5\n**Research subject:** s{number}",
    }


class FakeGitHub:
    """issues[repo] -> list of issues; comments[(repo, n)] -> list; broken[repo] -> HTTP code."""

    def __init__(self, issues, comments=None, broken=None):
        self.issues, self.comments, self.broken = issues, comments or {}, broken or {}
        self.posted = []

    def __call__(self, method, path, token, data=None):
        parts = path.split("?")[0].split("/")  # '', repos, owner, repo, issues, ...
        repo = f"{parts[2]}/{parts[3]}"
        if repo in self.broken:
            raise urllib.error.HTTPError(path, self.broken[repo], "x", {}, None)
        m = re.search(r"[?&]page=([0-9]+)", path)
        page = int(m.group(1)) if m else 1
        if method == "POST":
            self.posted.append((repo, int(parts[5]), data["body"]))
            return {"html_url": f"https://github.com/{repo}/issues/{parts[5]}#c"}
        if parts[-1] == "comments":
            rows = self.comments.get((repo, int(parts[5])), [])
        elif len(parts) == 6:
            return next(i for i in self.issues[repo] if i["number"] == int(parts[5]))
        else:
            rows = self.issues.get(repo, [])
        return rows[(page - 1) * 100 : page * 100]


def use(monkeypatch, gh):
    monkeypatch.setattr(adapter, "_call", gh)
    return gh


def test_a_founder_objective_in_crew_is_picked_ahead_of_a_mined_one(monkeypatch):
    use(
        monkeypatch,
        FakeGitHub({IDP: [mined_issue(6634, 900.0)], CREW: [founder_issue(239)]}),
    )
    chosen = adapter.pick("t")
    assert adapter.ref(chosen) == f"{CREW}#239"
    assert adapter.subject(chosen) == "Reimagine mumchimp"


def test_prospector_objectives_are_read_too(monkeypatch):
    use(monkeypatch, FakeGitHub({PROSPECTOR: [founder_issue(7, "prospector store")]}))
    assert adapter.ref(adapter.pick("t")) == f"{PROSPECTOR}#7"


def test_same_issue_number_in_two_repositories_stays_distinct(monkeypatch):
    done = {
        "body": "<!-- research-report request=r cost=0.1000 -->\n- [ ] Continue researching"
    }
    use(
        monkeypatch,
        FakeGitHub(
            {IDP: [mined_issue(5)], CREW: [founder_issue(5)]},
            comments={(CREW, 5): [done]},
        ),
    )
    # crew#5 was reported and is waiting; idp#5 is new and must not inherit that state.
    assert adapter.ref(adapter.pick("t")) == f"{IDP}#5"


def test_a_hand_written_objective_is_bounded_by_the_default_cap():
    i = founder_issue(239)
    assert adapter.cap_usd(i["body"]) == adapter.DEFAULT_CAP_USD
    assert adapter.cap_usd("**cap:** $0") == adapter.DEFAULT_CAP_USD
    spent = {
        "body": "<!-- research-report request=r cost=5.5000 -->\n- [x] Continue researching"
    }
    assert adapter.decision(i, [spent])[0] == "cap"


def test_park_and_waiting_apply_to_founder_objectives(monkeypatch):
    park = {
        "body": "<!-- research-report request=r cost=0.5000 -->\n- [x] Park this research"
    }
    use(
        monkeypatch,
        FakeGitHub({CREW: [founder_issue(239)]}, comments={(CREW, 239): [park]}),
    )
    assert adapter.pick("t") is None


def test_comments_beyond_the_first_page_are_read_so_a_park_tick_is_not_lost(
    monkeypatch,
):
    filler = [{"body": "chatter"}] * 100
    park = {
        "body": "<!-- research-report request=r cost=0.5000 -->\n- [x] Park this research"
    }
    use(
        monkeypatch,
        FakeGitHub(
            {CREW: [founder_issue(239)]}, comments={(CREW, 239): filler + [park]}
        ),
    )
    assert adapter.pick("t") is None


def test_more_than_a_hundred_objectives_are_all_seen(monkeypatch):
    many = [mined_issue(n, 1.0) for n in range(1, 131)]
    many.append(mined_issue(500, 99.0))
    use(monkeypatch, FakeGitHub({IDP: many}))
    assert adapter.ref(adapter.pick("t")) == f"{IDP}#500"


def test_pull_requests_are_not_objectives(monkeypatch):
    pr = {**founder_issue(3), "pull_request": {"url": "x"}}
    use(monkeypatch, FakeGitHub({CREW: [pr]}))
    assert adapter.pick("t") is None


def test_one_unreadable_repository_does_not_blind_the_others(monkeypatch, capsys):
    use(
        monkeypatch,
        FakeGitHub({CREW: [founder_issue(239)]}, broken={PROSPECTOR: 403, IDP: 404}),
    )
    assert adapter.ref(adapter.pick("t")) == f"{CREW}#239"
    assert "cannot read objectives in o/prospector" in capsys.readouterr().err


def test_no_readable_repository_is_a_failure_not_an_idle_hour(monkeypatch):
    use(monkeypatch, FakeGitHub({}, broken={IDP: 403, CREW: 403, PROSPECTOR: 403}))
    with pytest.raises(RuntimeError, match="no objective repository could be read"):
        adapter.pick("t")


def test_an_issue_whose_comments_cannot_be_read_is_skipped_not_respent(
    monkeypatch, capsys
):
    class Flaky(FakeGitHub):
        def __call__(self, method, path, token, data=None):
            if path.startswith(f"/repos/{CREW}/issues/239/comments"):
                raise urllib.error.URLError("reset")
            return super().__call__(method, path, token, data)

    use(monkeypatch, Flaky({CREW: [founder_issue(239)], IDP: [mined_issue(1)]}))
    assert adapter.ref(adapter.pick("t")) == f"{IDP}#1"
    assert "skipping o/crew#239" in capsys.readouterr().err


def test_empty_or_missing_body_does_not_crash():
    i = {"number": 9, "title": "objective: x", "body": None}
    assert adapter.rank(i["body"]) == adapter.FOUNDER_RANK
    assert adapter.subject(i) == "x"


def test_reference_parsing_accepts_only_known_repositories():
    assert adapter.parse_ref(f"{CREW}#239") == (CREW, 239)
    assert adapter.parse_ref("12") == (IDP, 12)
    for bad in ("evil/repo#1", "o/crew#", "o/crew#1; rm", "", "o/crew#1#2"):
        with pytest.raises(ValueError):
            adapter.parse_ref(bad)


def test_the_report_is_posted_on_the_issues_own_repository(monkeypatch):
    gh = use(monkeypatch, FakeGitHub({CREW: [founder_issue(239)]}))
    monkeypatch.setattr(adapter, "claims_for", lambda dsn, rid: ([], {}))
    run = {
        "request_id": "r",
        "delivery": {"status": "delivered"},
        "worker": {"cost_usd": 0.3},
    }
    url = adapter.report("t", f"{CREW}#239", run, "dsn")
    assert url == "https://github.com/o/crew/issues/239#c"
    assert [(r, n) for r, n, _ in gh.posted] == [(CREW, 239)]
    assert "of the $5 cap" in gh.posted[0][2]


def test_a_transient_server_error_does_not_lose_the_paid_report(monkeypatch):
    calls = []

    def flaky(method, path, token, data=None):
        calls.append(1)
        if len(calls) < 3:
            raise urllib.error.HTTPError(path, 502, "bad gateway", {}, None)
        return {"html_url": "ok"}

    monkeypatch.setattr(adapter, "_call", flaky)
    assert adapter._call_retry("POST", "/x", "t", {}) == {"html_url": "ok"}
    assert len(calls) == 3


def test_a_client_error_is_not_retried(monkeypatch):
    calls = []

    def refused(method, path, token, data=None):
        calls.append(1)
        raise urllib.error.HTTPError(path, 403, "forbidden", {}, None)

    monkeypatch.setattr(adapter, "_call", refused)
    with pytest.raises(urllib.error.HTTPError):
        adapter._call_retry("POST", "/x", "t", {})
    assert len(calls) == 1


def test_an_unpostable_report_is_kept_in_the_log(monkeypatch, capsys):
    use(monkeypatch, FakeGitHub({CREW: [founder_issue(239)]}))
    monkeypatch.setattr(adapter, "claims_for", lambda dsn, rid: ([], {}))

    def dead(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setattr(adapter, "_call_retry", dead)
    run = {
        "request_id": "r",
        "delivery": {"status": "delivered"},
        "worker": {"cost_usd": 0.3},
    }
    with pytest.raises(RuntimeError):
        adapter.report("t", f"{CREW}#239", run, "dsn")
    assert "research-report request=r" in capsys.readouterr().err
