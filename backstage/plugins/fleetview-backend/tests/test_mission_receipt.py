"""fleetview_backend.agent_jobs: the mission receipt -- one dispatched cloud mission, projected honestly.

WHAT THESE TESTS ARE FOR. The founder's requirement (INS-00011) is that a dispatched Legion
mission is visible on the Founder Surface with honest status. The dishonest cases are the
dangerous ones, so most of these tests are about what the receipt must REFUSE to say:

  * a worker that never started is not a result;
  * a run that ended green having produced nothing is NOT VERIFIED -- that is the negative
    control the mission names;
  * a run whose conclusion disagrees with its own agent job is a conflict, not a success;
  * a merge is not a live effect, and the receipt says so instead of implying one;
  * missing upstream, an empty credential and malformed evidence are refusals with
    machine-readable codes, never a fabricated receipt.
"""

from __future__ import annotations

import json

import pytest

from fleetview_backend import agent_jobs

REPO = "chidionyema/idp"
RUN_ID = 43074179589
BASE_SHA = "0a4abe6a4bcba03e94fc98afa25e45f8c9046171"
LANE_SHA = "b" * 40
NOW = 1794362400.0  # 2026-11-11T02:00:00Z, fixed, so an age is a measurement and not a race


def _run(
    *,
    status: str = "completed",
    conclusion: str = "success",
    title: str = "agent (gemini): LEGION #7932",
    head_sha: str = BASE_SHA,
    updated: str = "2026-11-11T01:59:30Z",
) -> dict:
    return {
        "id": RUN_ID,
        "name": WORKFLOW_NAME,
        "display_title": title,
        "event": "issues",
        "status": status,
        "conclusion": conclusion,
        "head_sha": head_sha,
        "html_url": f"https://github.com/{REPO}/actions/runs/{RUN_ID}",
        "created_at": "2026-11-11T00:00:00Z",
        "run_started_at": "2026-11-11T00:00:05Z",
        "updated_at": updated,
        "actor": {"login": "chidionyema"},
        "triggering_actor": {"login": "chidionyema"},
    }


WORKFLOW_NAME = "agent-sandbox"


def _job(
    name: str, *, status: str = "completed", conclusion: str = "success", jid: int = 1
):
    return {
        "id": jid,
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "steps": [],
    }


def _wire(
    monkeypatch,
    *,
    run=None,
    jobs=None,
    log: str = "",
    lane: bool = True,
    pr_merged: bool = True,
    in_main: bool = True,
    comments=None,
    gh_fail: Exception | None = None,
    text_fail: Exception | None = None,
):
    """Wire the GitHub reads with canonical-shaped fixtures. No network, no credential."""
    run = run if run is not None else _run()
    jobs = (
        jobs
        if jobs is not None
        else [_job("agent"), _job("firewall", jid=2), _job("submit-lane", jid=3)]
    )

    def gh_get(path: str):
        if gh_fail is not None:
            raise gh_fail
        if "/actions/workflows/" in path and "/runs?" in path:
            return 200, {"workflow_runs": [run]}
        if "/actions/runs/" in path and path.endswith("/jobs"):
            return 200, {"jobs": jobs}
        if "/actions/runs/" in path:
            return 200, run
        if "/git/ref/heads/" in path:
            if not lane:
                return 404, {"message": "Not Found"}
            return 200, {
                "ref": "refs/heads/lane/x",
                "object": {"sha": LANE_SHA, "type": "commit"},
            }
        if "/commits/" in path:
            return 200, {
                "sha": LANE_SHA,
                "files": [
                    {
                        "filename": "backstage/x.py",
                        "status": "modified",
                        "additions": 4,
                        "deletions": 1,
                    },
                    {
                        "filename": "tests/test_x.py",
                        "status": "modified",
                        "additions": 9,
                        "deletions": 0,
                    },
                ],
                "commit": {
                    "message": "agent-sandbox (gemini): do the thing\n\nClaim: #7932\n"
                },
            }
        if "/pulls?" in path:
            if not pr_merged:
                return 200, []
            return 200, [
                {
                    "number": 7999,
                    "state": "closed",
                    "merged_at": "2026-11-11T01:00:00Z",
                    "html_url": f"https://github.com/{REPO}/pull/7999",
                    "merge_commit_sha": "c" * 40,
                }
            ]
        if "/compare/" in path:
            commits = [{"sha": LANE_SHA}] if in_main else []
            return 200, {"commits": commits, "status": "behind"}
        if "/issues/" in path and path.endswith("/comments?per_page=100"):
            return 200, list(comments or [])
        if "/contents/" in path:
            import base64

            raw = base64.b64encode(
                b'pi -p --provider minimax --model MiniMax-M2.7 "$TASK"\n'
                b'pi -p --provider google --model "${MODEL:-gemini-3.5-flash}" "$TASK"\n'
            ).decode()
            return 200, {"content": raw, "encoding": "base64"}
        raise AssertionError(f"unexpected path {path}")

    def gh_text(path: str):
        if text_fail is not None:
            raise text_fail
        return 200, log

    monkeypatch.setenv("FLEETVIEW_AGENT_REPO", REPO)
    monkeypatch.setattr(agent_jobs, "gh_get", gh_get)
    monkeypatch.setattr(agent_jobs, "gh_text", gh_text)


# -- the happy path, with every claim evidenced --


def test_a_landed_mission_is_verified_and_says_what_proved_it(monkeypatch):
    _wire(
        monkeypatch,
        log=(
            "legion provider fallback: google_failure=model-unavailable fallback=minimax exit=0\n"
            "harness exit 0\n"
            "patch: 2 files changed, 13 insertions(+), 1 deletion(-)\n"
        ),
        comments=[
            {
                "body": "CLAIM agent=gemini paths=backstage/x.py,tests/test_x.py "
                "heartbeat=2026-11-11T00:10:00Z",
                "html_url": f"https://github.com/{REPO}/issues/7932#issuecomment-1",
            }
        ],
    )
    body, status = agent_jobs.receipt(run_id=RUN_ID, now=NOW)
    assert status == 200
    assert body["instruction_id"] == "7932"
    assert body["instruction_url"] == f"https://github.com/{REPO}/issues/7932"
    assert body["run"]["url"] == f"https://github.com/{REPO}/actions/runs/{RUN_ID}"
    assert body["source_sha"] == BASE_SHA
    assert body["stage"] == "greenlane_landed"
    assert body["verification"]["status"] == "VERIFIED"
    assert body["verification"]["codes"] == []
    # The provider is the one that ACTUALLY ran, read out of the log, not the one requested.
    assert body["model"]["provider"] == "minimax"
    assert body["model"]["fallback"] is True
    assert body["model"]["failure_class"] == "model-unavailable"
    assert body["model"]["name"] == "MiniMax-M2.7"
    assert body["model"]["name_source"].startswith("workflow at ")
    # A merge is not a live effect.
    assert body["stages"]["live_effect"] is False
    assert body["operational"]["status"] == "NOT VERIFIED"
    # The role and scope come from the claim of record.
    assert body["provenance"]["role"] == "gemini"
    assert body["provenance"]["scope"] == ["backstage/x.py", "tests/test_x.py"]
    assert body["provenance"]["claim_live"] is True
    # Freshness is a measurement, and every source is linked.
    assert body["freshness"]["stale"] is False
    assert body["freshness"]["read_at"]
    assert {s["kind"] for s in body["sources"]} >= {
        "actions_run",
        "actions_jobs",
        "lane_commit",
        "pull_request",
        "instruction_issue",
    }
    # Bounded: the receipt is a read model, not a transcript.
    assert len(json.dumps(body)) < 20000


# -- the negative controls: what must NOT read as success --


def test_a_worker_that_never_started_is_not_verified(monkeypatch):
    _wire(
        monkeypatch,
        run=_run(status="in_progress", conclusion=""),
        jobs=[_job("agent", status="queued", conclusion="")],
        lane=False,
        comments=[],
    )
    body, status = agent_jobs.receipt(run_id=RUN_ID, now=NOW)
    assert status == 200
    assert body["verification"]["status"] == "NOT VERIFIED"
    assert "worker-did-not-start" in body["verification"]["codes"]
    assert body["stages"]["started"] is False
    assert body["stages"]["patch_produced"] is False


def test_a_green_run_with_no_output_is_not_verified(monkeypatch):
    """The negative control the mission names: a worker that produced nothing, and a green
    no-op signal, must stay NOT VERIFIED with a machine-readable explanation."""
    _wire(
        monkeypatch,
        log="harness exit 0\npatch: \n",
        jobs=[
            _job("agent"),
            _job("firewall", jid=2),
            _job("submit-lane", conclusion="failure", jid=3),
        ],
        lane=False,
        comments=[],
    )
    body, _status = agent_jobs.receipt(run_id=RUN_ID, now=NOW)
    assert body["verification"]["status"] == "NOT VERIFIED"
    assert "no-output" in body["verification"]["codes"]
    assert "conflict-run-succeeded-without-output" in body["verification"]["codes"]
    assert body["stages"]["patch_produced"] is False


def test_a_run_that_contradicts_its_own_agent_job_is_a_conflict(monkeypatch):
    _wire(
        monkeypatch,
        jobs=[
            _job("agent", conclusion="failure"),
            _job("firewall", jid=2),
            _job("submit-lane", jid=3),
        ],
        log="harness exit 1\npatch: 1 file changed, 1 insertion(+)\n",
        comments=[],
    )
    body, _status = agent_jobs.receipt(run_id=RUN_ID, now=NOW)
    assert body["verification"]["status"] == "NOT VERIFIED"
    assert "conflict-run-succeeded-agent-failed" in body["verification"]["codes"]


def test_a_firewall_that_refused_is_not_verified(monkeypatch):
    _wire(
        monkeypatch,
        jobs=[
            _job("agent"),
            _job("firewall", conclusion="failure", jid=2),
            _job("submit-lane", jid=3),
        ],
        log="harness exit 0\npatch: 2 files changed, 13 insertions(+)\n",
        comments=[],
    )
    body, _status = agent_jobs.receipt(run_id=RUN_ID, now=NOW)
    assert body["verification"]["status"] == "NOT VERIFIED"
    assert "firewall-refused" in body["verification"]["codes"]
    assert body["stages"]["cif_passed"] is False


def test_a_run_in_flight_is_not_judged_as_having_no_output(monkeypatch):
    """A worker that is still working has no result yet; calling it "no output" would be a
    verdict on work in flight."""
    _wire(
        monkeypatch,
        run=_run(status="in_progress", conclusion=""),
        jobs=[_job("agent", status="in_progress", conclusion="")],
        lane=False,
        comments=[],
    )
    body, _status = agent_jobs.receipt(run_id=RUN_ID, now=NOW)
    assert body["verification"]["status"] == "NOT VERIFIED"
    assert body["verification"]["codes"] == ["in-flight"]
    assert "no-output" not in body["verification"]["codes"]
    assert body["stage"] == "started"


def test_the_receipt_names_the_next_executable_recovery(monkeypatch):
    _wire(
        monkeypatch,
        run=_run(status="in_progress", conclusion=""),
        jobs=[_job("agent", status="queued", conclusion="")],
        lane=False,
        comments=[],
    )
    body, _status = agent_jobs.receipt(run_id=RUN_ID, now=NOW)
    codes = [r["code"] for r in body["recovery"]]
    assert "worker-did-not-start" in codes
    entry = next(r for r in body["recovery"] if r["code"] == "worker-did-not-start")
    assert entry["next"]["action"] == "read-the-run"
    assert str(RUN_ID) in entry["next"]["target"]


def test_the_provider_failure_class_and_its_recovery_are_carried(monkeypatch):
    _wire(
        monkeypatch,
        log=(
            "legion provider fallback: google_failure=capacity-or-rate-limit "
            "fallback=minimax exit=0\n"
        ),
        comments=[],
    )
    body, _status = agent_jobs.receipt(run_id=RUN_ID, now=NOW)
    assert body["failure_class"] == "capacity-or-rate-limit"
    assert body["model"]["failed_provider"] == "google"
    assert any(r["code"].startswith("provider-failure:") for r in body["recovery"])


def test_a_run_that_is_only_a_branch_is_not_landed_and_not_verified(monkeypatch):
    _wire(
        monkeypatch,
        pr_merged=False,
        in_main=False,
        log="harness exit 0\npatch: 2 files changed, 13 insertions(+)\n",
        comments=[],
    )
    body, _status = agent_jobs.receipt(run_id=RUN_ID, now=NOW)
    assert body["stages"]["patch_produced"] is True
    assert body["stages"]["greenlane_landed"] is False
    assert body["verification"]["status"] == "NOT VERIFIED"
    assert "not-landed" in body["verification"]["codes"]


# -- the unreadable cases: refusals with codes, never a fabricated receipt --


def test_a_missing_upstream_is_a_refusal_with_a_code(monkeypatch):
    def gh_get(path: str):
        return 404, {"message": "Not Found"}

    monkeypatch.setenv("FLEETVIEW_AGENT_REPO", REPO)
    monkeypatch.setattr(agent_jobs, "gh_get", gh_get)
    with pytest.raises(agent_jobs.ReceiptRefused) as exc:
        agent_jobs.receipt(run_id=99, now=NOW)
    assert exc.value.status == 404
    assert exc.value.code == "not-found"


def test_an_empty_credential_is_a_refusal_and_not_an_empty_receipt(monkeypatch):
    monkeypatch.setenv("FLEETVIEW_AGENT_REPO", REPO)
    monkeypatch.setattr(
        agent_jobs,
        "gh_get",
        lambda path: (_ for _ in ()).throw(
            agent_jobs.JobRefused(503, "Fleet has no GitHub credential.")
        ),
    )
    with pytest.raises(agent_jobs.ReceiptRefused) as exc:
        agent_jobs.receipt(run_id=RUN_ID, now=NOW)
    assert exc.value.status == 503
    assert exc.value.code == "credential-missing"


def test_a_malformed_claim_leaves_the_receipt_honest_about_it(monkeypatch):
    _wire(
        monkeypatch,
        log="harness exit 0\npatch: 2 files changed, 13 insertions(+)\n",
        comments=[
            {
                "body": "CLAIM agent=gemini paths=backstage/x.py heartbeat=not-a-time",
                "html_url": f"https://github.com/{REPO}/issues/7932#issuecomment-2",
            }
        ],
    )
    body, _status = agent_jobs.receipt(run_id=RUN_ID, now=NOW)
    assert body["provenance"]["claim_live"] is False
    assert body["provenance"]["claim_heartbeat"] == "not-a-time"
    # An unreadable heartbeat is not a live claim, and the receipt does not pretend otherwise.
    assert body["provenance"]["claim_age_s"] is None


def test_stale_evidence_is_reported_as_stale(monkeypatch):
    _wire(
        monkeypatch,
        run=_run(updated="2026-10-01T00:00:00Z"),
        log="harness exit 0\npatch: 2 files changed, 13 insertions(+)\n",
        comments=[],
    )
    body, _status = agent_jobs.receipt(run_id=RUN_ID, now=NOW)
    assert body["freshness"]["stale"] is True
    assert body["freshness"]["age_s"] > agent_jobs.RECEIPT_STALE_AFTER_S


def test_an_instruction_that_does_not_match_the_run_is_refused(monkeypatch):
    _wire(monkeypatch)
    with pytest.raises(agent_jobs.ReceiptRefused) as exc:
        agent_jobs.receipt(run_id=RUN_ID, instruction_id=1234, now=NOW)
    assert exc.value.status == 409
    assert exc.value.code == "instruction-mismatch"


def test_a_mission_can_be_found_by_its_instruction_id(monkeypatch):
    _wire(
        monkeypatch,
        log="harness exit 0\npatch: 2 files changed, 13 insertions(+)\n",
        comments=[],
    )
    body, status = agent_jobs.receipt(instruction_id=7932, now=NOW)
    assert status == 200
    assert body["run"]["run_id"] == RUN_ID
    assert body["instruction_id"] == "7932"


def test_an_unreadable_log_does_not_make_up_a_provider(monkeypatch):
    """The run title names the provider that was REQUESTED. When the log cannot be read, the
    provider that actually ran is not evidenced, and the receipt must not guess it."""
    _wire(
        monkeypatch,
        log="",
        comments=[],
    )
    body, _status = agent_jobs.receipt(run_id=RUN_ID, now=NOW)
    assert body["harness"] == "gemini"
    assert body["model"]["provider"] is None
    assert "not evidenced" in body["model"]["provider_source"]


def test_a_receipt_with_no_mission_asked_for_is_refused(monkeypatch):
    with pytest.raises(agent_jobs.ReceiptRefused) as exc:
        agent_jobs.receipt(now=NOW)
    assert exc.value.status == 400
    assert exc.value.code == "no-mission"


def test_the_receipt_is_bounded_whatever_the_run_says(monkeypatch):
    _wire(
        monkeypatch,
        log="harness exit 0\npatch: 900 files changed, 1 insertion(+)\n",
        comments=[],
    )
    body, _status = agent_jobs.receipt(run_id=RUN_ID, now=NOW)
    assert len(body["lane"]["files_changed"]) <= agent_jobs.RECEIPT_MAX_FILES
    assert len(body["title"]) <= agent_jobs.RECEIPT_MAX_TASK_CHARS
    assert len(body["verification"]["codes"]) <= agent_jobs.RECEIPT_MAX_REASONS


def test_the_receipt_matches_the_published_schema(monkeypatch):
    """The schema is the contract Argon consumes; the receipt must satisfy it."""
    jsonschema = pytest.importorskip("jsonschema")
    from pathlib import Path

    schema_path = (
        Path(agent_jobs.__file__).resolve().parents[2]
        / "schemas"
        / "mission-receipt-v1.json"
    )
    schema = json.loads(schema_path.read_text())
    _wire(
        monkeypatch,
        log="harness exit 0\npatch: 2 files changed, 13 insertions(+)\n",
        comments=[],
    )
    body, _status = agent_jobs.receipt(run_id=RUN_ID, now=NOW)
    jsonschema.validate(body, schema)


def test_the_route_answers_a_mission_and_its_refusals(monkeypatch):
    """The trusted server-side adapter: one GET, a receipt or a refusal with its code."""
    pytest.importorskip("fastapi")
    pytest.importorskip("uvicorn")
    from fastapi.testclient import TestClient

    from fleetview_backend import serve

    _wire(
        monkeypatch,
        log="harness exit 0\npatch: 2 files changed, 13 insertions(+)\n",
        comments=[],
    )
    client = TestClient(serve.build_app())
    r = client.get("/mission-receipt", params={"run_id": str(RUN_ID)})
    assert r.status_code == 200, r.text
    assert r.json()["run"]["run_id"] == RUN_ID

    def gh_get(path: str):
        return 404, {"message": "Not Found"}

    monkeypatch.setattr(agent_jobs, "gh_get", gh_get)
    r = client.get("/mission-receipt", params={"run_id": "999999"})
    assert r.status_code == 404
    assert r.json()["code"] == "not-found"
