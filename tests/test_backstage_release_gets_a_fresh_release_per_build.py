"""2026-10-13: every `Build & Release Backstage` run on main went red at "Upload to Release" with
"Cannot upload asset backstage-app.tar.gz to an immutable release". The repo has immutable
releases on; the workflow uploaded every build to one fixed tag, `backstage-latest`, which was
published once (2026-09-29, with no assets) and could take none after that. A release that is
published cannot be appended to, so each build has to make its own.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "backstage-release.yml"


def _release_step():
    wf = yaml.safe_load(WORKFLOW.read_text())
    for step in wf["jobs"]["build-backstage"]["steps"]:
        if str(step.get("uses", "")).startswith("softprops/action-gh-release"):
            return step["with"]
    raise AssertionError("the workflow no longer has a release upload step")


def test_each_build_uploads_to_a_tag_of_its_own():
    tag = _release_step()["tag_name"]
    assert "${{ github.run_number }}" in tag or "${{ github.sha }}" in tag, (
        f"tag_name {tag!r} is the same on every build; on an immutable-release repo the second "
        "build cannot upload to it"
    )


def test_the_release_is_not_a_prerelease_and_not_marked_latest():
    w = _release_step()
    assert w.get("prerelease") is False
    assert w.get("make_latest") is False
