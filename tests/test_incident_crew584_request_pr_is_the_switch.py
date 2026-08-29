"""crew#584 CP-K, founder 2026-08-29: "how does the self service lean vs enterprise, not seeing it
at all". The portal template opened a pull request that only recorded the request; the flip was
`bin/idp-features enable`, a script a person had to run (LAW 31). The feature-request-enable
workflow runs enable on the request pull request's own branch and pushes the switch changes with
the estate's GitHub App token, so merging the pull request is the switch."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "feature-request-enable.yml"
TPL = ROOT / "backstage" / "templates" / "enable-platform-feature" / "template.yaml"


def _wf():
    return yaml.safe_load(WF.read_text())


def test_the_request_pull_request_runs_enable_on_its_own_branch():
    wf = _wf()
    assert wf[True]["pull_request"]["paths"] == ["platform/features/requests.yaml"]
    job = wf["jobs"]["enable"]
    steps = job["steps"]
    checkout = next(s for s in steps if str(s.get("uses", "")).startswith("actions/checkout@"))
    assert checkout["with"]["ref"] == "${{ github.event.pull_request.head.ref }}"
    run = next(s["run"] for s in steps if "bin/idp-features enable" in s.get("run", ""))
    assert "git push origin" in run and "git diff --quiet" in run, "idempotent: nothing to commit means no push, no loop"
    assert "exit 1" in run and "gh pr comment" in run, "a refused tier is a red run with the reason on the pull request"


def test_the_push_uses_the_app_token_so_the_checks_run_on_the_new_head():
    steps = _wf()["jobs"]["enable"]["steps"]
    app = next(s for s in steps if str(s.get("uses", "")).startswith("actions/create-github-app-token@"))
    assert app["with"]["app-id"] == "${{ secrets.SEED_GITHUB_APP_ID }}"
    checkout = next(s for s in steps if str(s.get("uses", "")).startswith("actions/checkout@"))
    assert checkout["with"]["token"] == "${{ steps.app.outputs.token }}", "GITHUB_TOKEN pushes raise no events; the checks would never run"
    assert _wf()["jobs"]["enable"]["if"] == "github.event.pull_request.head.repo.full_name == github.repository && github.actor != 'dependabot[bot]'"


def test_the_template_tells_the_founder_that_merging_is_the_switch():
    desc = yaml.safe_load(TPL.read_text())["metadata"]["description"]
    assert "Merging the pull request is the switch" in desc
    assert "stays a separate" not in desc
