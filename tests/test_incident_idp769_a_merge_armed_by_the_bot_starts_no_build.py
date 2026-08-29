"""Incident 2026-08-29 11:21Z (idp#769, #768, #770, #720): bin/idp-pr-age armed auto-merge under
GITHUB_TOKEN, GitHub merged the four as github-actions[bot], and a push by that token starts no
workflow. ci.yml and build-multiarch.yml never ran on main for 530fefaa..a6e37963; the portal
image for the new front page was never built and nothing said so.

The class: any step that arms auto-merge (or opens the PR it arms) runs under an App installation
token from .github/actions/github-app-token, never under GITHUB_TOKEN / github.token. And
build-multiarch.yml has a hand road back: workflow_dispatch with `since`, pushing like a push.
"""

from __future__ import annotations

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WF = ROOT / ".github/workflows"
ACTION = "github-app-token"

# workflow -> text that marks the step which arms auto-merge
ARMERS = {
    "pr-age.yml": "bin/idp-pr-age --act",
    "conscience.yml": "gh pr merge",
    "kini-finish.yml": "gh pr merge",
    "image-update-pr.yml": "bin/idp-image-update-pr",
    "catalog-render.yml": "bin/catalog-render",
}


def _steps(wf: dict):
    for job in wf["jobs"].values():
        for s in job.get("steps") or []:
            yield job, s


def test_every_step_that_arms_auto_merge_runs_under_the_app_token():
    for name, marker in ARMERS.items():
        wf = yaml.safe_load((WF / name).read_text())
        assert wf["permissions"].get("id-token") == "write", (
            f"{name}: no id-token for the OCI session"
        )
        armed = [(j, s) for j, s in _steps(wf) if marker in (s.get("run") or "")]
        assert armed, f"{name}: no step runs {marker}"
        for job, step in armed:
            tok = (step.get("env") or {}).get("GH_TOKEN", "")
            assert tok == "${{ steps.app.outputs.token }}", (
                f"{name}: {marker} runs under {tok!r}"
            )
            minted = [
                s
                for s in job["steps"]
                if s.get("id") == "app" and ACTION in (s.get("uses") or "")
            ]
            assert minted, f"{name}: no `id: app` step using {ACTION} in the same job"
            assert job["steps"].index(minted[0]) < job["steps"].index(step), (
                f"{name}: token minted after use"
            )


def test_no_arming_workflow_falls_back_to_the_repository_token():
    for name, marker in ARMERS.items():
        text = (WF / name).read_text()
        for _j, s in _steps(yaml.safe_load(text)):
            if marker in (s.get("run") or ""):
                env = yaml.safe_dump(s.get("env") or {})
                assert "GITHUB_TOKEN" not in env and "github.token" not in env, (
                    f"{name}: {marker} sees the bot token"
                )


def test_the_app_token_action_masks_the_token_and_reads_mains_copy():
    a = yaml.safe_load((ROOT / ".github/actions" / ACTION / "action.yml").read_text())
    assert a["runs"]["using"] == "composite"
    steps = a["runs"]["steps"]
    checkout = [s for s in steps if "actions/checkout@" in (s.get("uses") or "")]
    assert checkout and checkout[0]["with"]["ref"] == "main", (
        "the tool comes from main, whatever branch the caller is on"
    )
    mint = [s for s in steps if s.get("id") == "mint"][0]
    assert "bin/idp-github-app token" in mint["run"]
    assert "::add-mask::" in mint["run"], "the token would print in the log"
    assert (
        "$GITHUB_OUTPUT" in mint["run"]
        and a["outputs"]["token"]["value"] == "${{ steps.mint.outputs.token }}"
    )


def test_build_multiarch_can_be_rebuilt_by_hand_and_pushes_when_it_is():
    text = (WF / "build-multiarch.yml").read_text()
    wf = yaml.safe_load(text)
    assert "since" in wf[True]["workflow_dispatch"]["inputs"], (
        "no hand road back after a missed push"
    )
    find = [s for _, s in _steps(wf) if s.get("id") == "find"][0]
    assert "inputs.since" in find["run"] and "${{ github.event.before }}" in find["run"]
    # a dispatch run must push and sign like a push run; only a pull request builds and drops
    assert "github.event_name == 'push' &&" not in text.replace(
        "github.event_name == 'push' && github.sha", ""
    )
    assert text.count("github.event_name != 'pull_request'") >= 5
