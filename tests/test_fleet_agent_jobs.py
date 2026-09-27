"""Fleet's agent-jobs panel: every way a job can be asked for, refused, run, and end.

Founder, 2026-09-27: "i need to know how i am going to use this seamlessly from fleet page",
"add proper test", "this is my work surface so all edge cases". The module under test
(backstage/plugins/fleetview-backend/src/fleetview_backend/agent_jobs.py) talks to GitHub over
real HTTP here: a local http.server plays GitHub's REST API with GitHub's own status codes and
headers, so the request the module builds and the answer it parses are both exercised. Nothing
is mocked inside the module.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import socket
import sys
import threading
import time
import types
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "backstage" / "plugins" / "fleetview-backend" / "src" / "fleetview_backend"
WORKFLOW = ROOT / ".github" / "workflows" / "agent-sandbox.yml"
TOKEN = "fleet-test-credential-0001"  # noqa: S105 -- a fixture, not a secret
REPO = "chidionyema/idp"


def _member(name: str):
    """Load one file of the plugin package without its __init__ (which pulls NATS, models)."""
    full = f"fleetview_backend.{name}"
    if full in sys.modules:
        return sys.modules[full]
    pkg = sys.modules.setdefault(
        "fleetview_backend", types.ModuleType("fleetview_backend")
    )
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


_member("redact")
aj = _member("agent_jobs")


def _iso(seconds_ago: float = 0) -> str:
    t = datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


class FakeGitHub:
    """GitHub's REST API, the parts agent_jobs uses, with GitHub's status codes."""

    def __init__(self):
        self.runs: list[dict] = []
        self.jobs: dict[int, list[dict]] = {}
        self.pulls: dict[str, list[dict]] = {}
        self.annotations: dict[int, list[dict]] = {}
        self.dispatch = "200"  # "200" | "204" | "204-late"
        self.fail: dict[
            str, tuple[int, dict, dict]
        ] = {}  # path regex -> (code, body, headers)
        self.delay: dict[str, float] = {}
        self.requests: list[dict] = []
        self.next_id = 9000
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code, body=None, headers=None):
                raw = b"" if body is None else json.dumps(body).encode()
                self.send_response(code)
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def _handle(self, method):
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n)) if n else None
                fake.requests.append(
                    {
                        "method": method,
                        "path": self.path,
                        "auth": self.headers.get("Authorization"),
                        "body": body,
                    }
                )
                for pat, secs in fake.delay.items():
                    if re.search(pat, self.path):
                        time.sleep(secs)
                for pat, (code, b, h) in fake.fail.items():
                    if re.search(pat, f"{method} {self.path}"):
                        return self._send(code, b, h)
                u = urlparse(self.path)
                p, q = u.path, parse_qs(u.query)
                wf = f"/repos/{REPO}/actions/workflows/agent-sandbox.yml"
                if method == "POST" and p == wf + "/dispatches":
                    return fake._dispatch(self, body)
                if method == "GET" and p == wf + "/runs":
                    per = int(q.get("per_page", ["30"])[0])
                    runs = sorted(fake.runs, key=lambda r: r["id"], reverse=True)[:per]
                    return self._send(
                        200, {"total_count": len(runs), "workflow_runs": runs}
                    )
                m = re.fullmatch(rf"/repos/{REPO}/actions/runs/(\d+)/jobs", p)
                if method == "GET" and m:
                    return self._send(200, {"jobs": fake.jobs.get(int(m.group(1)), [])})
                m = re.fullmatch(rf"/repos/{REPO}/check-runs/(\d+)/annotations", p)
                if method == "GET" and m:
                    return self._send(200, fake.annotations.get(int(m.group(1)), []))
                if method == "GET" and p == f"/repos/{REPO}/pulls":
                    return self._send(200, fake.pulls.get(q["head"][0], []))
                return self._send(404, {"message": "Not Found"})

            def do_GET(self):
                self._handle("GET")

            def do_POST(self):
                self._handle("POST")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def add_run(
        self, title, status="in_progress", conclusion=None, age=30, actor="chidionyema"
    ):
        self.next_id += 1
        run = {
            "id": self.next_id,
            "display_title": title,
            "status": status,
            "conclusion": conclusion,
            "created_at": _iso(age),
            "html_url": f"https://github.com/{REPO}/actions/runs/{self.next_id}",
            "triggering_actor": {"login": actor},
        }
        self.runs.append(run)
        return run

    def _dispatch(self, h, body):
        title = f"agent ({body['inputs']['harness']}): {body['inputs']['task']}"
        if self.dispatch == "204-late":
            return h._send(204)
        run = self.add_run(title, status="queued", age=0, actor="estate-agents[bot]")
        if self.dispatch == "204":
            return h._send(204)
        return h._send(
            200,
            {
                "workflow_run_id": run["id"],
                "run_url": f"https://api.github.com/repos/{REPO}/actions/runs/{run['id']}",
                "html_url": run["html_url"],
            },
        )

    def calls(self, method, pattern):
        return [
            r
            for r in self.requests
            if r["method"] == method and re.search(pattern, r["path"])
        ]


@pytest.fixture
def gh(tmp_path, monkeypatch):
    fake = FakeGitHub()
    tok = tmp_path / "GITHUB_TOKEN"
    tok.write_text(TOKEN + "\n")
    monkeypatch.setenv("FLEETVIEW_GITHUB_API", fake.url)
    monkeypatch.setenv("FLEETVIEW_GITHUB_TOKEN_FILE", str(tok))
    monkeypatch.setenv("FLEETVIEW_AGENT_REPO", REPO)
    monkeypatch.setenv(
        "PATH", str(tmp_path / "no-gh")
    )  # no `gh` fallback unless a test adds one
    aj.reset_for_tests()
    fake.token_file = tok
    yield fake
    fake.server.shutdown()


def _no_token_in(obj):
    assert TOKEN not in json.dumps(obj)


# ── submitting ────────────────────────────────────────────────────────────────────────────


def test_a_task_is_dispatched_to_the_sandbox_on_main_and_comes_back_as_a_job(gh):
    job, status = aj.submit("fix the typo in README", "pi", by="founder")
    assert status == 201
    (post,) = gh.calls("POST", r"/dispatches$")
    assert post["body"] == {
        "ref": "main",
        "inputs": {"harness": "pi", "task": "fix the typo in README"},
    }
    assert post["auth"] == f"Bearer {TOKEN}"
    assert job["run_id"] == gh.runs[-1]["id"]
    assert job["run_url"] == gh.runs[-1]["html_url"]
    assert (job["stage"], job["state"], job["by"], job["harness"]) == (
        "queued",
        "running",
        "founder",
        "pi",
    )
    _no_token_in(job)


def test_the_task_is_trimmed_and_the_harness_defaults_to_pi(gh):
    job, _ = aj.submit("   tidy the docs index   \n")
    (post,) = gh.calls("POST", r"/dispatches$")
    assert post["body"]["inputs"] == {"harness": "pi", "task": "tidy the docs index"}
    assert job["task"] == "tidy the docs index"


def test_an_api_that_answers_204_still_names_the_run_it_started(gh):
    gh.dispatch = "204"
    job, status = aj.submit("add a test for idp-shadow", "claude-code")
    assert status == 201
    assert job["run_id"] == gh.runs[-1]["id"]


def test_a_run_github_has_not_listed_yet_is_accepted_and_says_so(gh):
    gh.dispatch = "204-late"
    job, status = aj.submit("add a test for idp-shadow", "pi")
    assert status == 202
    assert job["run_id"] is None
    assert "not listed the run yet" in job["reason"]


@pytest.mark.parametrize("task", ["", "   ", "\n\t", None, 42, ["a"]])
def test_an_empty_or_non_text_task_is_refused_before_anything_leaves(gh, task):
    with pytest.raises(aj.JobRefused) as e:
        aj.submit(task, "pi")
    assert e.value.status == 400
    assert "empty" in str(e.value)
    assert gh.requests == []


def test_an_oversized_task_is_refused_and_says_the_limit(gh):
    with pytest.raises(aj.JobRefused) as e:
        aj.submit("x" * (aj.MAX_TASK_CHARS + 1), "pi")
    assert (e.value.status, str(aj.MAX_TASK_CHARS) in str(e.value)) == (400, True)
    assert gh.requests == []


def test_a_task_at_exactly_the_limit_is_sent(gh):
    _job, status = aj.submit("y" * aj.MAX_TASK_CHARS, "pi")
    assert status == 201


@pytest.mark.parametrize("harness", ["", "claude", "PI", None, "pi; rm -rf /"])
def test_an_unknown_harness_is_refused(gh, harness):
    with pytest.raises(aj.JobRefused) as e:
        aj.submit("do a thing", harness)
    assert e.value.status == 400
    assert gh.requests == []


@pytest.mark.parametrize(
    "task",
    [
        "use GITHUB_TOKEN=ghp_abcdefghijklmnopqrstuvwxyz0123456789 to push",
        "the key is sk-ant-api03-abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGH",
        "set MINIMAX_API_KEY: abc123def456ghi789 in the workflow",
    ],
)
def test_a_task_that_holds_a_secret_is_refused_and_the_secret_is_not_echoed(gh, task):
    with pytest.raises(aj.JobRefused) as e:
        aj.submit(task, "pi")
    assert e.value.status == 400
    assert "published" in str(e.value)
    for word in re.findall(r"\S{16,}", task):
        assert word not in str(e.value)
    assert gh.requests == []


def test_a_double_tap_is_one_job(gh):
    first, s1 = aj.submit("rename the fleet pill", "pi")
    second, s2 = aj.submit("rename the fleet pill", "pi")
    assert (s1, s2) == (201, 200)
    assert second["duplicate"] is True
    assert second["run_id"] == first["run_id"]
    assert len(gh.calls("POST", r"/dispatches$")) == 1


def test_two_taps_at_the_same_instant_are_still_one_job(gh):
    out = []
    barrier = threading.Barrier(2)

    def tap():
        barrier.wait()
        out.append(aj.submit("same instant", "pi")[1])

    threads = [threading.Thread(target=tap) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(out) == [200, 201]
    assert len(gh.calls("POST", r"/dispatches$")) == 1


def test_the_same_task_after_the_first_finished_is_a_new_job(gh):
    gh.add_run(
        "agent (pi): same again", status="completed", conclusion="success", age=10
    )
    _job, status = aj.submit("same again", "pi")
    assert status == 201


def test_the_same_task_on_another_harness_is_a_new_job(gh):
    aj.submit("compare harnesses", "pi")
    _job, status = aj.submit("compare harnesses", "claude-code")
    assert status == 201
    assert len(gh.calls("POST", r"/dispatches$")) == 2


def test_the_same_task_long_after_is_a_new_job_even_if_the_old_run_hangs(gh):
    gh.add_run(
        "agent (pi): stuck one", status="in_progress", age=aj.DUPLICATE_WINDOW_S + 60
    )
    _job, status = aj.submit("stuck one", "pi")
    assert status == 201


def test_the_spawn_budget_refuses_a_fourth_running_job(gh):
    for i in range(aj.MAX_ACTIVE):
        gh.add_run(f"agent (pi): job {i}", status="in_progress", age=600)
    gh.add_run("agent (pi): old", status="completed", conclusion="success", age=900)
    with pytest.raises(aj.JobRefused) as e:
        aj.submit("one more", "pi")
    assert e.value.status == 429
    assert "already running" in str(e.value)
    assert gh.calls("POST", r"/dispatches$") == []


def test_queued_runs_count_against_the_budget_too(gh):
    for i in range(aj.MAX_ACTIVE):
        gh.add_run(f"agent (pi): waiting {i}", status="queued", age=600)
    with pytest.raises(aj.JobRefused) as e:
        aj.submit("one more", "pi")
    assert e.value.status == 429


# ── the credential ────────────────────────────────────────────────────────────────────────


def test_no_credential_is_a_503_that_says_so_and_nothing_is_sent(gh, monkeypatch):
    monkeypatch.delenv("FLEETVIEW_GITHUB_TOKEN_FILE")
    with pytest.raises(aj.JobRefused) as e:
        aj.submit("anything", "pi")
    assert e.value.status == 503
    assert "no GitHub credential" in str(e.value)
    assert gh.requests == []


def test_an_empty_or_missing_token_file_is_no_credential(gh, tmp_path, monkeypatch):
    gh.token_file.write_text("  \n")
    with pytest.raises(aj.JobRefused) as e:
        aj.submit("anything", "pi")
    assert e.value.status == 503
    monkeypatch.setenv("FLEETVIEW_GITHUB_TOKEN_FILE", str(tmp_path / "absent"))
    with pytest.raises(aj.JobRefused):
        aj.submit("anything", "pi")
    assert gh.requests == []


def test_the_laptop_falls_back_to_gh_auth_token(gh, tmp_path, monkeypatch):
    monkeypatch.delenv("FLEETVIEW_GITHUB_TOKEN_FILE")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "gh"
    fake.write_text(f'#!/bin/sh\n[ "$1 $2" = "auth token" ] && echo {TOKEN}-gh\n')
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}/bin{os.pathsep}/usr/bin")
    aj.submit("via gh", "pi")
    assert {r["auth"] for r in gh.requests} == {f"Bearer {TOKEN}-gh"}


def test_a_rotated_token_is_used_on_the_very_next_call(gh):
    aj.submit("before rotation", "pi")
    gh.token_file.write_text("fleet-test-credential-0002\n")
    aj.submit("after rotation", "pi")
    assert gh.requests[-1]["auth"] == "Bearer fleet-test-credential-0002"


# ── GitHub saying no ──────────────────────────────────────────────────────────────────────


def _refusal(gh, code, body=None, headers=None, pattern=r"POST .*/dispatches$"):
    gh.fail[pattern] = (code, body or {"message": "nope"}, headers or {})
    with pytest.raises(aj.JobRefused) as e:
        aj.submit("will be refused", "pi")
    _no_token_in(str(e.value))
    return e.value


def test_a_rejected_credential_says_401(gh):
    e = _refusal(gh, 401, {"message": "Bad credentials"})
    assert (e.status, "401" in str(e)) == (502, True)


def test_a_spent_rate_limit_says_when_it_resets(gh):
    reset = int(datetime(2026, 9, 27, 14, 5, tzinfo=timezone.utc).timestamp())
    e = _refusal(
        gh,
        403,
        {"message": "API rate limit exceeded"},
        {"x-ratelimit-remaining": "0", "x-ratelimit-reset": str(reset)},
    )
    assert e.status == 503
    assert "14:05Z" in str(e)


def test_a_credential_without_the_actions_permission_says_403(gh):
    e = _refusal(gh, 403, {"message": "Resource not accessible by integration"})
    assert (e.status, "may not dispatch" in str(e)) == (502, True)


def test_a_missing_workflow_is_named(gh):
    e = _refusal(gh, 404, {"message": "Not Found"})
    assert "agent-sandbox.yml" in str(e)


def test_githubs_own_422_reason_is_shown(gh):
    e = _refusal(gh, 422, {"message": 'Unexpected inputs provided: ["by"]'})
    assert e.status == 400
    assert "Unexpected inputs provided" in str(e)


def test_a_github_outage_is_a_502_with_the_status(gh):
    e = _refusal(gh, 503, {"message": "Service Unavailable"})
    assert (e.status, "503" in str(e)) == (502, True)


def test_a_github_answer_that_is_not_json_is_still_a_sentence(gh):
    gh.fail[r"POST .*/dispatches$"] = (500, None, {})
    with pytest.raises(aj.JobRefused) as e:
        aj.submit("x", "pi")
    assert "500" in str(e.value)


def test_no_network_is_named_as_unreachable(gh, monkeypatch):
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()  # nothing listens here now
    monkeypatch.setenv("FLEETVIEW_GITHUB_API", f"http://127.0.0.1:{port}")
    with pytest.raises(aj.JobRefused) as e:
        aj.submit("x", "pi")
    assert (e.value.status, "unreachable" in str(e.value)) == (502, True)


def test_a_github_that_hangs_times_out_instead_of_hanging_the_page(gh, monkeypatch):
    monkeypatch.setattr(aj, "HTTP_TIMEOUT_S", 0.3)
    gh.delay[r"/runs\?"] = 1.5
    t0 = time.monotonic()
    with pytest.raises(aj.JobRefused) as e:
        aj.submit("x", "pi")
    assert time.monotonic() - t0 < 1.4
    assert "unreachable" in str(e.value)


# ── watching a job ────────────────────────────────────────────────────────────────────────


def _job(name, status="completed", conclusion="success", job_id=None, steps=None):
    return {
        "id": job_id or abs(hash(name)) % 10**6,
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "steps": steps or [],
    }


def _one(gh):
    body, status = aj.list_jobs()
    assert status == 200 and body["available"] is True
    _no_token_in(body)
    return body["jobs"][0]


def test_a_run_no_runner_has_picked_up_is_queued(gh):
    gh.add_run("agent (pi): waiting", status="queued")
    j = _one(gh)
    assert (j["stage"], j["state"], j["harness"], j["task"]) == (
        "queued",
        "running",
        "pi",
        "waiting",
    )


@pytest.mark.parametrize(
    "jobs,stage",
    [
        ([("agent", "in_progress", None)], "agent"),
        ([("agent", "queued", None)], "agent"),
        ([("agent", "completed", "success")], "firewall"),
        (
            [("agent", "completed", "success"), ("firewall", "in_progress", None)],
            "firewall",
        ),
        (
            [("agent", "completed", "success"), ("firewall", "completed", "success")],
            "open-pr",
        ),
        (
            [
                ("agent", "completed", "success"),
                ("firewall", "completed", "success"),
                ("open-pr", "in_progress", None),
            ],
            "open-pr",
        ),
    ],
)
def test_a_running_job_shows_the_stage_it_is_in(gh, jobs, stage):
    run = gh.add_run("agent (pi): working")
    gh.jobs[run["id"]] = [_job(n, s, c) for n, s, c in jobs]
    assert _one(gh)["stage"] == stage


def test_a_passed_run_with_an_open_pr_links_the_pr(gh):
    run = gh.add_run("agent (pi): ship it", status="completed", conclusion="success")
    gh.pulls[f"chidionyema:agent/pi-{run['id']}"] = [
        {
            "number": 4600,
            "html_url": "https://github.com/x/pull/4600",
            "state": "open",
            "merged_at": None,
        }
    ]
    j = _one(gh)
    assert (j["stage"], j["state"]) == ("pr", "running")
    assert j["pr"] == {
        "number": 4600,
        "url": "https://github.com/x/pull/4600",
        "state": "open",
    }


def test_a_merged_pr_is_done_and_is_never_asked_about_again(gh):
    run = gh.add_run("agent (pi): ship it", status="completed", conclusion="success")
    gh.pulls[f"chidionyema:agent/pi-{run['id']}"] = [
        {"number": 4601, "html_url": "u", "state": "closed", "merged_at": _iso(5)}
    ]
    j = _one(gh)
    assert (j["stage"], j["state"], j["pr"]["state"]) == ("merged", "done", "merged")
    aj._LIST_CACHE["at"] = 0.0
    before = len(gh.calls("GET", r"/pulls"))
    assert _one(gh)["stage"] == "merged"
    assert len(gh.calls("GET", r"/pulls")) == before


def test_a_pr_closed_without_merging_is_a_failure_that_says_so(gh):
    run = gh.add_run(
        "agent (claude-code): try", status="completed", conclusion="success"
    )
    gh.pulls[f"chidionyema:agent/claude-code-{run['id']}"] = [
        {"number": 4602, "html_url": "u", "state": "closed", "merged_at": None}
    ]
    j = _one(gh)
    assert (j["stage"], j["state"]) == ("closed", "failed")
    assert "without merging" in j["reason"]


def test_a_passed_run_with_no_pr_is_not_shown_as_success(gh):
    gh.add_run("agent (pi): vanished", status="completed", conclusion="success")
    j = _one(gh)
    assert j["state"] == "failed"
    assert "no PR" in j["reason"]


def test_an_open_pr_is_asked_about_again_until_it_ends(gh):
    run = gh.add_run("agent (pi): pending", status="completed", conclusion="success")
    head = f"chidionyema:agent/pi-{run['id']}"
    gh.pulls[head] = [
        {"number": 1, "html_url": "u", "state": "open", "merged_at": None}
    ]
    assert _one(gh)["stage"] == "pr"
    gh.pulls[head] = [
        {"number": 1, "html_url": "u", "state": "closed", "merged_at": _iso()}
    ]
    aj._LIST_CACHE["at"] = 0.0
    assert _one(gh)["stage"] == "merged"


def test_waiting_on_a_pr_costs_one_github_call_per_poll_not_two(gh):
    # The portal token's hourly budget is shared; a passed run needs its PR, never its jobs.
    gh.add_run("agent (pi): cheap", status="completed", conclusion="success")
    _one(gh)
    assert gh.calls("GET", r"/jobs$") == []
    assert len(gh.calls("GET", r"/pulls")) == 1


def test_a_credential_that_may_not_read_prs_says_so_instead_of_failing(gh):
    gh.add_run("agent (pi): hidden", status="completed", conclusion="success")
    gh.fail[r"GET .*/pulls"] = (
        403,
        {"message": "Resource not accessible by integration"},
        {},
    )
    j = _one(gh)
    assert (j["stage"], j["state"]) == ("pr", "running")
    assert "may not read pull requests" in j["reason"]


def test_an_agent_failure_shows_the_workflows_own_error_line(gh):
    run = gh.add_run("agent (pi): broken", status="completed", conclusion="failure")
    gh.jobs[run["id"]] = [_job("agent", conclusion="failure", job_id=77)]
    gh.annotations[77] = [
        {
            "annotation_level": "failure",
            "message": "Process completed with exit code 1.",
        },
        {
            "annotation_level": "failure",
            "message": "the harness failed (exit 1); provider said: 401 authentication_error",
        },
    ]
    j = _one(gh)
    assert (j["stage"], j["state"]) == ("agent", "failed")
    assert (
        j["reason"]
        == "the harness failed (exit 1); provider said: 401 authentication_error"
    )


def test_a_firewall_refusal_is_the_firewall_stage(gh):
    run = gh.add_run(
        "agent (pi): overclaimed", status="completed", conclusion="failure"
    )
    gh.jobs[run["id"]] = [
        _job("agent"),
        _job("firewall", conclusion="failure", job_id=78),
    ]
    gh.annotations[78] = [
        {"annotation_level": "failure", "message": "refused claims: 2"}
    ]
    j = _one(gh)
    assert (j["stage"], j["reason"]) == ("firewall", "refused claims: 2")


def test_an_error_line_that_quotes_a_secret_is_redacted(gh):
    run = gh.add_run("agent (pi): leaky", status="completed", conclusion="failure")
    gh.jobs[run["id"]] = [_job("agent", conclusion="failure", job_id=79)]
    gh.annotations[79] = [
        {
            "annotation_level": "failure",
            "message": "bad key MINIMAX_API_KEY=abcdef0123456789abcdef",
        }
    ]
    j = _one(gh)
    assert "abcdef0123456789abcdef" not in j["reason"]
    assert "MINIMAX_API_KEY" in j["reason"]


def test_without_annotations_the_failed_step_is_named(gh):
    run = gh.add_run("agent (pi): quiet", status="completed", conclusion="failure")
    gh.jobs[run["id"]] = [
        _job("agent"),
        _job("firewall"),
        _job(
            "open-pr",
            conclusion="failure",
            job_id=80,
            steps=[
                {"name": "Decode the App key", "conclusion": "success"},
                {
                    "name": "Apply the patch to main, refusing what an agent may not change",
                    "conclusion": "failure",
                },
            ],
        ),
    ]
    gh.fail[r"GET .*/annotations"] = (
        403,
        {"message": "Resource not accessible by integration"},
        {},
    )
    j = _one(gh)
    assert j["stage"] == "open-pr"
    assert (
        j["reason"]
        == "failed at: Apply the patch to main, refusing what an agent may not change"
    )


def test_a_cancelled_run_says_cancelled(gh):
    gh.add_run("agent (pi): stopped", status="completed", conclusion="cancelled")
    j = _one(gh)
    assert (j["stage"], j["state"]) == ("cancelled", "failed")


def test_a_failed_run_with_no_failed_job_still_says_how_it_ended(gh):
    gh.add_run("agent (pi): odd", status="completed", conclusion="timed_out")
    assert _one(gh)["reason"] == "The run ended timed_out."


def test_a_run_from_before_titles_is_listed_with_its_raw_title(gh):
    run = gh.add_run("agent-sandbox", status="completed", conclusion="success")
    gh.pulls[f"chidionyema:agent/claude-code-{run['id']}"] = [
        {"number": 4515, "html_url": "u", "state": "closed", "merged_at": _iso()}
    ]
    j = _one(gh)
    assert (j["harness"], j["task"], j["stage"]) == (None, "agent-sandbox", "merged")


def test_the_list_is_newest_first_and_capped(gh):
    for i in range(15):
        gh.add_run(f"agent (pi): n{i}", status="queued")
    body, _ = aj.list_jobs(limit=10)
    assert [j["task"] for j in body["jobs"]] == [f"n{i}" for i in range(14, 4, -1)]


def test_polling_is_served_from_a_short_cache(gh):
    gh.add_run("agent (pi): a", status="queued")
    aj.list_jobs()
    n = len(gh.requests)
    aj.list_jobs()
    assert len(gh.requests) == n


def test_a_submit_makes_the_next_poll_fresh(gh):
    aj.list_jobs()
    aj.submit("new one", "pi")
    body, _ = aj.list_jobs()
    assert body["jobs"][0]["task"] == "new one"


def test_a_list_github_will_not_answer_is_unavailable_not_empty(gh):
    gh.fail[r"GET .*/runs\?"] = (503, {"message": "down"}, {})
    body, status = aj.list_jobs()
    assert (status, body["available"], body["jobs"]) == (502, False, [])
    assert "503" in body["error"]


def test_a_list_with_no_credential_is_unavailable_not_empty(gh, monkeypatch):
    monkeypatch.delenv("FLEETVIEW_GITHUB_TOKEN_FILE")
    body, status = aj.list_jobs()
    assert (status, body["available"]) == (503, False)


# ── the contract with the workflow ────────────────────────────────────────────────────────


def test_the_workflow_titles_its_runs_the_way_this_module_reads_them():
    wf = yaml.safe_load(WORKFLOW.read_text())
    rendered = (
        wf["run-name"]
        .replace("${{ inputs.harness }}", "pi")
        .replace("${{ inputs.task }}", "fix: the thing (now)")
    )
    assert rendered == aj.title_for("pi", "fix: the thing (now)")
    m = aj._TITLE.match(rendered)
    assert (m.group("harness"), m.group("task")) == ("pi", "fix: the thing (now)")


def test_the_harnesses_offered_are_exactly_the_workflows_options():
    wf = yaml.safe_load(WORKFLOW.read_text())
    on = wf.get("on") or wf.get(True)
    inputs = on["workflow_dispatch"]["inputs"]
    assert sorted(inputs["harness"]["options"]) == sorted(aj.HARNESSES)
    assert set(inputs) == {"harness", "task"}


# ── what the page sends ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("body", [None, [], "fix it", 3, {"harness": "pi"}])
def test_a_malformed_post_is_a_400_sentence_and_nothing_is_sent(gh, body):
    out, status = aj.handle_post(body)
    assert status == 400
    assert isinstance(out["error"], str) and out["error"]
    assert gh.calls("POST", r"/dispatches$") == []


def test_a_post_with_no_harness_runs_pi_and_records_who_asked(gh):
    out, status = aj.handle_post({"task": "from the phone", "by": "founder"})
    assert status == 201
    assert (out["harness"], out["by"]) == ("pi", "founder")


def test_every_refusal_reaches_the_page_as_its_status_and_sentence(gh):
    for i in range(aj.MAX_ACTIVE):
        gh.add_run(f"agent (pi): busy {i}", status="in_progress", age=600)
    out, status = aj.handle_post({"task": "one too many", "harness": "pi"})
    assert status == 429
    assert "already running" in out["error"]


# ── by voice ──────────────────────────────────────────────────────────────────────────────

vi = _member("voice_intents")


@pytest.fixture
def voice(gh, tmp_path, monkeypatch):
    (tmp_path / "intents").mkdir()
    monkeypatch.setenv("FLEETVIEW_INTENTS_DIR", str(tmp_path / "intents"))
    monkeypatch.setenv("FLEETVIEW_INTENT_LOG", str(tmp_path / "voice.jsonl"))
    vi._PENDING.clear()
    vi._PENDING_TASK.clear()
    gh.log = tmp_path / "voice.jsonl"
    return gh


@pytest.mark.parametrize(
    "said,task",
    [
        ("Give an agent a job: fix the typo in README.", "fix the typo in README"),
        ("give agent a job, add a test for idp-shadow", "add a test for idp-shadow"),
        ("Hey, agent job - rename the fleet pill", "rename the fleet pill"),
        ("OK. Please, give an agent a job: fix it.", "fix it"),
        ("agent job rename the fleet pill", "rename the fleet pill"),
        ("Ask an agent to tidy docs/index.md", "tidy docs/index.md"),
        ("okay have an agent bump ruff to 0.15.18.", "bump ruff to 0.15.18"),
        ("what is the agent doing", None),
        ("the agent job failed yesterday", None),
    ],
)
def test_the_phrase_is_heard_and_the_task_is_what_came_after_it(said, task):
    assert vi.agent_job_task(said) == task


def test_a_spoken_job_is_read_back_and_nothing_is_sent_before_yes(voice):
    r = vi.handle("Give an agent a job: fix the typo in README.", "s1")
    assert r["status"] == "pending_confirmation"
    assert r["text"] == "Send an agent to: fix the typo in README? Say yes to confirm."
    assert voice.calls("POST", r"/dispatches$") == []


def test_yes_sends_it_on_pi_and_names_the_run(voice):
    vi.handle("give an agent a job fix the typo in README", "s1")
    r = vi.handle("Yes.", "s1")
    assert (r["status"], r["intent"]) == ("ok", "agent-job")
    assert r["text"] == f"Sent. Run {voice.runs[-1]['id']}. Watch it on Fleet."
    (post,) = voice.calls("POST", r"/dispatches$")
    assert post["body"]["inputs"] == {"harness": "pi", "task": "fix the typo in README"}


def test_no_cancels_and_nothing_is_sent(voice):
    vi.handle("give an agent a job fix the typo", "s1")
    r = vi.handle("no", "s1")
    assert r["status"] == "cancelled"
    assert voice.calls("POST", r"/dispatches$") == []


def test_a_yes_after_the_window_sends_nothing(voice, monkeypatch):
    vi.handle("give an agent a job fix the typo", "s1")
    real = time.monotonic
    monkeypatch.setattr(vi.time, "monotonic", lambda: real() + vi.PENDING_TTL_S + 1)
    assert vi.handle("yes", "s1") is None
    assert voice.calls("POST", r"/dispatches$") == []


def test_a_yes_in_another_session_sends_nothing(voice):
    vi.handle("give an agent a job fix the typo", "phone")
    assert vi.handle("yes", "glasses") is None
    assert voice.calls("POST", r"/dispatches$") == []


def test_saying_something_else_drops_the_pending_job(voice):
    vi.handle("give an agent a job fix the typo", "s1")
    vi.handle("what time is it", "s1")
    assert vi.handle("yes", "s1") is None
    assert voice.calls("POST", r"/dispatches$") == []


def test_a_second_job_replaces_the_first_before_yes(voice):
    vi.handle("give an agent a job first thing", "s1")
    vi.handle("give an agent a job second thing", "s1")
    vi.handle("yes", "s1")
    (post,) = voice.calls("POST", r"/dispatches$")
    assert post["body"]["inputs"]["task"] == "second thing"


def test_the_phrase_alone_asks_for_the_job(voice):
    r = vi.handle("give an agent a job", "s1")
    assert r["status"] == "error"
    assert "then what to do" in r["text"]
    assert vi.handle("yes", "s1") is None


def test_a_spoken_secret_is_refused_before_the_read_back_and_never_logged(voice):
    r = vi.handle(
        "give an agent a job set MINIMAX_API_KEY=abcdef0123456789abcdef", "s1"
    )
    assert r["status"] == "error"
    assert "abcdef0123456789abcdef" not in r["text"]
    assert "abcdef0123456789abcdef" not in voice.log.read_text()
    assert vi.handle("yes", "s1") is None
    assert voice.requests == []


def test_githubs_refusal_is_spoken(voice):
    for i in range(aj.MAX_ACTIVE):
        voice.add_run(f"agent (pi): busy {i}", status="in_progress", age=600)
    vi.handle("give an agent a job one more", "s1")
    r = vi.handle("yes", "s1")
    assert r["status"] == "error"
    assert "already running" in r["text"]


def test_saying_it_twice_is_one_job(voice):
    vi.handle("give an agent a job same thing", "s1")
    vi.handle("yes", "s1")
    vi.handle("give an agent a job same thing", "s1")
    r = vi.handle("yes", "s1")
    assert r["text"].startswith("That job is already running")
    assert len(voice.calls("POST", r"/dispatches$")) == 1


def test_every_spoken_job_is_in_the_audit_log(voice):
    vi.handle("give an agent a job audit me", "s1")
    vi.handle("yes", "s1")
    rows = [json.loads(line) for line in voice.log.read_text().splitlines()]
    assert [(r["intent"], r["status"]) for r in rows] == [
        ("agent-job", "pending_confirmation"),
        ("agent-job", "ok"),
    ]


# ── in the cluster ────────────────────────────────────────────────────────────────────────

OKE = ROOT / "platform/backstage/overlays/oke"


def _sidecar() -> dict:
    kust = yaml.safe_load((OKE / "kustomization.yaml").read_text())

    def walk(node):
        if isinstance(node, dict):
            if node.get("name") == "fleetview-backend" and "image" in node:
                yield node
            for v in node.values():
                yield from walk(v)
        elif isinstance(node, list):
            for v in node:
                yield from walk(v)
        elif isinstance(node, str) and "fleetview-backend" in node and "\n" in node:
            yield from walk(yaml.safe_load(node))

    (c,) = list(walk(kust))
    return c


def test_the_minted_token_carries_exactly_the_backstage_lane():
    lanes = json.loads((ROOT / "platform/github-app/lanes.json").read_text())
    gen = next(
        d
        for d in yaml.safe_load_all((OKE / "github-token.yaml").read_text())
        if d and d.get("kind") == "GithubAccessToken"
    )
    assert gen["spec"]["permissions"] == lanes["backstage"]


def test_the_sidecar_reads_the_portal_token_from_the_file_the_pod_already_holds():
    c = _sidecar()
    env = {e["name"]: e.get("value") for e in c["env"]}
    mounts = {m["name"]: m for m in c["volumeMounts"]}
    path = env["FLEETVIEW_GITHUB_TOKEN_FILE"]
    m = mounts["backstage-github"]
    assert m.get("readOnly") is True
    assert path == m["mountPath"] + "/GITHUB_TOKEN"
    assert (
        "GITHUB_TOKEN" not in env
    )  # a file, never an env var (kyverno secrets policy)
    kust = (OKE / "kustomization.yaml").read_text()
    assert (
        "secret: {secretName: backstage-github" in kust
    )  # the pod-level volume it mounts
