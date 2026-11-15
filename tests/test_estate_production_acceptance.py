import importlib.machinery
import importlib.util
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "bin" / "estate-production-acceptance"
loader = importlib.machinery.SourceFileLoader("release_qa", str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
qa = importlib.util.module_from_spec(spec)
loader.exec_module(qa)

SHA = "a" * 40
OTHER = "b" * 40


def fixture(**changes):
    check_change = changes.pop("job", {})
    run = dict(
        id=2,
        run_attempt=1,
        head_sha=SHA,
        status="completed",
        conclusion="success",
        event="push",
        head_branch="queue/demo",
    )
    run.update(changes.pop("run", {}))
    profile = changes.pop("profile", "crew")
    _, required = qa.PROFILES.get(profile, qa.DEFAULT)
    jobs = [
        dict(
            name=name,
            head_sha=SHA,
            runner_id=123,
            steps=[
                {"name": step, "conclusion": "success"}
                for step in steps or ["actual test"]
            ],
            conclusion="success",
        )
        for name, steps in required.items()
    ]
    jobs[0].update(check_change)

    def read(path):
        if "/actions/workflows/" in path:
            return {"workflow_runs": [run]}
        if "/actions/runs/" in path:
            assert "/attempts/1/jobs" in path
            return {"jobs": jobs}
        if "/git/ref/heads/" in path:
            return {"object": {"sha": "c" * 40}}
        if "/contents/" in path:
            if not path.endswith(SHA):
                return {"sha": SHA}
            if "/workflows/" in path:
                return {"sha": changes.get("candidate_workflow", SHA)}
            return {"sha": changes.get("candidate_gate", SHA)}
        return {"default_branch": "main"}

    return read


def test_all_required_jobs_on_exact_revision_pass():
    assert qa.observe("chidionyema/crew", SHA, fixture())["state"] == "passed"


def test_false_green_missing_runner_wrong_sha_and_skipped_check_are_refused():
    for row in (
        {"runner_id": 0},
        {"head_sha": OTHER},
        {"conclusion": "skipped"},
        {"steps": []},
    ):
        assert (
            qa.observe("chidionyema/crew", SHA, fixture(job=row))["state"]
            == "checks-incomplete"
        )


def test_an_old_run_does_not_prove_the_candidate():
    assert (
        qa.observe("chidionyema/crew", SHA, fixture(run={"head_sha": OTHER}))["state"]
        == "missing-run"
    )
    assert (
        qa.observe("chidionyema/crew", SHA, fixture(run={"status": "queued"}))["state"]
        == "pending"
    )


def test_candidate_cannot_swap_out_workflow():
    assert (
        qa.observe("chidionyema/crew", SHA, fixture(candidate_workflow=OTHER))["state"]
        == "workflow-changed"
    )


def test_candidate_cannot_certify_itself_with_a_replaced_gate_script():
    for profile in ("idp", "argon", "crew"):
        assert (
            qa.observe(
                f"chidionyema/{profile}",
                SHA,
                fixture(
                    profile=profile,
                    candidate_gate=OTHER,
                ),
            )["state"]
            == "policy-changed"
        )


def test_idp_pr_workflow_can_checkout_a_different_merge_tree():
    read = fixture(
        profile="idp", run={"event": "pull_request", "head_branch": "lane/demo"}
    )
    assert qa.observe("chidionyema/idp", SHA, read)["state"] == "missing-run"


def test_release_ref_stops_when_the_hosted_checks_are_missing(monkeypatch):
    monkeypatch.setattr(qa, "observe", lambda *_: {"state": "missing-run"})
    assert (
        qa.pre_push("chidionyema/crew", [f"HEAD {SHA} refs/heads/release/demo {OTHER}"])
        == 1
    )
    assert (
        qa.pre_push("chidionyema/crew", [f"HEAD {SHA} refs/heads/propose/demo {OTHER}"])
        == 0
    )
