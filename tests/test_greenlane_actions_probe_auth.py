"""GitHub Actions acceptance proofs require trusted, host-bound API reads."""

import urllib.request

import greenlane.github as G

ACTIONS = (
    "https://api.github.com/repos/chidionyema/idp/actions/workflows/"
    "agent-sandbox.yml/runs?status=success&per_page=5"
)


def test_actions_read_uses_same_repository_authenticated_gh(monkeypatch):
    calls = []

    def fake_run(*args):
        calls.append(args)
        return '{"workflow_runs":[{"name":"agent (auto)"}]}'

    monkeypatch.setenv("GH_TOKEN", "token-never-in-uri")
    monkeypatch.setattr(G, "_run", fake_run)
    status, body = G._http_get(ACTIONS)
    assert status == 200 and "agent (auto)" in body
    assert calls == [
        (
            "gh",
            "api",
            "repos/chidionyema/idp/actions/workflows/"
            "agent-sandbox.yml/runs?status=success&per_page=5",
        )
    ]
    assert all("token-never-in-uri" not in str(args) for args in calls)


def test_no_token_is_blind_not_an_anonymous_403(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)

    def refuse(*args):
        raise AssertionError("must not call the API without trusted authority")

    monkeypatch.setattr(G, "_run", refuse)
    status, evidence = G._http_get(ACTIONS)
    assert status == 0 and "BLIND" in evidence


def test_refused_authenticated_read_never_becomes_success(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "test")

    def refuse(*args):
        raise RuntimeError("HTTP 403")

    monkeypatch.setattr(G, "_run", refuse)
    status, evidence = G._http_get(ACTIONS)
    assert status == 0 and "BLIND" in evidence


def test_other_hosts_are_anonymous_even_with_a_token(monkeypatch):
    calls = []

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit):
            return b"public"

    def get(req, timeout):
        calls.append(req)
        return Response()

    def gh(*args):
        raise AssertionError("no privileged API call for an external host")

    monkeypatch.setenv("GH_TOKEN", "secret")
    monkeypatch.setattr(G, "_run", gh)
    monkeypatch.setattr(urllib.request, "urlopen", get)
    for url in (
        "https://another.example/health",
        "https://api.github.com.evil.example/repos/chidionyema/idp/actions/runs",
        "https://api.github.com/repos/another/repo/actions/runs",
    ):
        status, body = G._http_get(url)
        assert status == 200 and body == "public"
    assert len(calls) == 3
    assert all(req.get_header("Authorization") is None for req in calls)
