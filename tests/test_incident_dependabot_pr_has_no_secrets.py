"""Incident 2026-08-26 (run 32979902578, idp#113): oke-check ran on a dependabot pull request, which
GitHub gives no repository secrets, so `oidc_client_identifier: ${{ secrets.OIDC_CLIENT_IDENTIFIER }}`
was empty and the job failed before it graded anything. Rule (rung 4): a job that reads
a repository secret (`secrets.X`, not the always-present `secrets.GITHUB_TOKEN`) in a workflow triggered by pull_request carries a condition excluding dependabot,
unless the workflow itself never runs on pull_request. Both ways: the fixed oke-check passes,
and a job with the secret and no condition is refused."""

import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO_SECRET = re.compile(r"secrets\.(?!GITHUB_TOKEN\b)[A-Za-z_]")
DEPENDABOT = re.compile(
    r"github\.actor\s*!=\s*'dependabot\[bot\]'|github\.event_name\s*!=\s*'pull_request'"
)


def _offenders(text: str) -> list[str]:
    wf = yaml.safe_load(text)
    on = wf.get("on") or wf.get(True) or {}
    if isinstance(on, list):
        on = {k: {} for k in on}
    if "pull_request" not in on and "pull_request_target" not in on:
        return []
    bad = []
    for name, job in (wf.get("jobs") or {}).items():
        uses_secrets = bool(REPO_SECRET.search(yaml.safe_dump(job)))
        guarded = bool(DEPENDABOT.search(str(job.get("if", ""))))
        if uses_secrets and not guarded:
            bad.append(name)
    return bad


def test_the_incident_shape_is_refused_and_the_fixed_shape_permitted():
    incident = """
on: {pull_request: {}}
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: x/y@v1
        with: {token: "${{ secrets.T }}"}
"""
    assert _offenders(incident) == ["check"]
    fixed = incident.replace(
        "    runs-on:", "    if: github.actor != 'dependabot[bot]'\n    runs-on:"
    )
    assert _offenders(fixed) == []
    assert _offenders(incident.replace("pull_request", "schedule")) == []
    assert _offenders(incident.replace("secrets.T", "secrets.GITHUB_TOKEN")) == []
