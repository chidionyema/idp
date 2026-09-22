"""`deploy-when-green` lands a Flux image bump on its own only when
`bin/idp-image-only-diff` can prove the pull request is nothing but controller-written
image tags. On 2026-09-22 it could not prove that for ANY bump, and the whole deploy
lane had stopped: main still pinned `zeroedge:main-2` while `main-5` sat on
`flux/image-updates`, and every tick of the workflow printed

    ok      deploy-when-green  #3839 is not a plain image bump; it waits for the founder

The cause was not the pull request. image-automation-controller writes its marker onto
whichever key the manifest author put it on -- `newTag:` for the kustomize `images:`
form, `tag:` for the Helm values form -- and the pattern knew only `newTag:`. One
`tag:` marker anywhere in the estate (platform/dagster/dagster.yaml has three) sends
every bump to the founder, including the eleven files that were in the old shape.

These tests hold the widened pattern to the same trust boundary as before: the
`$imagepolicy` marker, not the key name, is what proves the controller owns a line.

Widening it is necessary and not sufficient. Two more things kept the lane shut, and
both are covered below: the controller's YAML round-trip drops a blank line in
platform/llm/kustomization.yaml, and -- because `gh pr diff` is the THREE-DOT diff --
that hunk is measured against a merge-base no merge to main can ever move. The loop
could not clear it, because the refresh that would lived behind the classifier the
stale hunk was failing.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "bin/idp-image-only-diff"
BASH = shutil.which("bash") or "/bin/bash"


def _load():
    spec = importlib.util.spec_from_loader(
        "idp_image_only_diff",
        importlib.machinery.SourceFileLoader("idp_image_only_diff", str(SCRIPT)),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["idp_image_only_diff"] = mod
    spec.loader.exec_module(mod)
    return mod


grade = _load().grade


def diff(path: str, *pairs: tuple[str, str]) -> str:
    """A unified diff over one file, given (removed, added) line pairs."""
    out = [
        f"diff --git a/{path} b/{path}",
        "index 1111111..2222222 100644",
        f"--- a/{path}",
        f"+++ b/{path}",
        "@@ -1,3 +1,3 @@",
    ]
    for removed, added in pairs:
        out += [f"-{removed}", f"+{added}"]
    return "\n".join(out) + "\n"


MARK = '# {"$imagepolicy": "flux-system:estate-scheduler:tag"}'
OLD = "main-11643-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
NEW = "main-11644-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


# ----------------------------------------------- the defect that stopped the lane


def test_the_helm_values_tag_form_is_recognised():
    """platform/dagster/dagster.yaml's shape, verbatim: a quoted value under `tag:`.
    This is the line #3839 was refused on."""
    d = diff(
        "platform/dagster/dagster.yaml",
        (f'        tag: "{OLD}" {MARK}', f'        tag: "{NEW}" {MARK}'),
    )
    ok, why = grade(d)
    assert ok is True, why


def test_the_kustomize_newtag_form_still_passes():
    d = diff(
        "platform/llm/kustomization.yaml",
        (f"    newTag: {OLD} {MARK}", f"    newTag: {NEW} {MARK}"),
    )
    ok, why = grade(d)
    assert ok is True, why


def test_both_forms_in_one_pull_request_pass_together():
    """#3839's actual shape: eleven kustomize files and one Helm values file."""
    d = diff(
        "platform/llm/kustomization.yaml",
        (f"    newTag: {OLD} {MARK}", f"    newTag: {NEW} {MARK}"),
    ) + diff(
        "platform/dagster/dagster.yaml",
        (f'        tag: "{OLD}" {MARK}', f'        tag: "{NEW}" {MARK}'),
    )
    ok, why = grade(d)
    assert ok is True, why


# ------------------------------------------- the boundary the widening must not move


def test_a_tag_line_without_the_marker_is_still_refused():
    """The marker is the whole proof of ownership. A bare `tag:` -- which a Helm values
    file is full of, and which no controller wrote -- must not become mergeable."""
    d = diff(
        "platform/commerce/app/lago.yaml",
        ('        tag: "v1.2.3"', '        tag: "v9.9.9"'),
    )
    ok, why = grade(d)
    assert ok is False
    assert "not an automation-owned image tag" in why


def test_a_line_that_merely_contains_the_word_tag_is_still_refused():
    d = diff(
        "platform/llm/kustomization.yaml",
        ("    imageTagPolicy: latest", "    imageTagPolicy: newest"),
    )
    ok, why = grade(d)
    assert ok is False, why


def test_switching_which_policy_owns_a_line_is_still_refused():
    other = '# {"$imagepolicy": "flux-system:zeroedge:tag"}'
    d = diff(
        "platform/llm/kustomization.yaml",
        (f"    newTag: {OLD} {MARK}", f"    newTag: {NEW} {other}"),
    )
    ok, why = grade(d)
    assert ok is False
    assert "rewrites which policy owns a line" in why


def test_a_blank_line_change_beside_a_real_bump_is_still_refused():
    """The second thing wrong with #3839: the controller's round-trip dropped a blank
    line in platform/llm/kustomization.yaml. That is a content change and the gate is
    right to refuse it -- so the fix is to remove the blank line at the source, not to
    teach the gate to ignore whitespace. This test is what stops that shortcut."""
    d = (
        diff(
            "platform/llm/kustomization.yaml",
            (f"    newTag: {OLD} {MARK}", f"    newTag: {NEW} {MARK}"),
        )
        + "diff --git a/platform/llm/kustomization.yaml b/platform/llm/kustomization.yaml\n@@ -40 +39 @@\n-\n"
    )
    ok, why = grade(d)
    assert ok is False, why


def test_an_empty_diff_is_blind_rather_than_a_pass():
    ok, why = grade("")
    assert ok is None
    assert "no diff" in why


# ------------------------------- and the source of the blank line is actually removed


def _controller_write_of_the_llm_kustomization() -> str:
    """The diff image-automation-controller's next write to that file would produce.

    Built from the file as it stands, not from a fixture: a tag bump, plus -- if the
    blank line after `disableNameSuffixHash: false` is still there -- the deletion its
    YAML round-trip makes of that line. Re-add the blank line and this diff grows the
    hunk that shut the lane, so the classifier below refuses it.
    """
    lines = (REPO / "platform/llm/kustomization.yaml").read_text().splitlines()
    i = next(i for i, ln in enumerate(lines) if "disableNameSuffixHash" in ln)
    d = diff(
        "platform/llm/kustomization.yaml",
        (f"    newTag: {OLD} {MARK}", f"    newTag: {NEW} {MARK}"),
    )
    if not lines[i + 1].strip():
        d += (
            "diff --git a/platform/llm/kustomization.yaml "
            "b/platform/llm/kustomization.yaml\n"
            f"@@ -{i + 2} +{i + 1} @@\n-\n"
        )
    return d


def test_the_controllers_next_write_to_the_llm_kustomization_is_landable(tmp_path):
    """Proving the classifier alone would leave the lane shut: #3839 also carries the
    blank-line deletion above. Removing it at the source is what makes the controller's
    next write a tag-only diff -- and this runs the real script over that write."""
    p = tmp_path / "write.diff"
    p.write_text(_controller_write_of_the_llm_kustomization())
    r = subprocess.run(  # noqa: S603 -- fixed argv, no shell
        [sys.executable, str(SCRIPT), "--diff", str(p)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, (
        "the controller's next write to platform/llm/kustomization.yaml is not landable: "
        f"{r.stdout.strip()} -- the blank line after generatorOptions is back, and its "
        "round-trip strips it on every write"
    )


# ------------------- and the loop can reach a diff the classifier is able to pass at all


GH_STUB = """#!{bash}
# Enough of `gh` for the land job, and it records what it was asked to do.
case "$*" in
  *"pr list"*--head*)            echo 3839 ;;
  *"pr list"*--label*)           ;;
  *"pr view"*isDraft*)           echo '{{}}' ;;
  *"pr view"*mergeStateStatus*)  echo "{state}" ;;
  *api*update-branch*)           echo "STUB-UPDATE-BRANCH" ;;
  *"pr merge"*)                  echo "STUB-MERGE" ;;
esac
"""


def _run_the_land_job(tmp_path, *, classifier_exit: int, state: str):
    """Run the workflow's OWN shell, with `gh` and the two bin/ scripts stubbed.

    The script is read out of deploy-when-green.yml rather than restated here, so the
    test grades the file that actually runs in CI.
    """
    import yaml

    d = yaml.safe_load((REPO / ".github/workflows/deploy-when-green.yml").read_text())
    shell = "\n".join(s["run"] for s in d["jobs"]["land"]["steps"] if "run" in s)

    stub = tmp_path / "stub"
    stub.mkdir()
    (stub / "gh").write_text(GH_STUB.format(bash=BASH, state=state))
    bind = tmp_path / "bin"
    bind.mkdir()
    (bind / "idp-image-only-diff").write_text(f"#!{BASH}\nexit {classifier_exit}\n")
    (bind / "idp-pr-landable").write_text(f'#!{BASH}\necho "MERGE ready"\n')
    for f in (stub / "gh", bind / "idp-image-only-diff", bind / "idp-pr-landable"):
        f.chmod(0o755)

    return subprocess.run(  # noqa: S603 -- fixed argv, no shell
        [BASH, "-c", shell],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={
            "PATH": f"{stub}:{os.environ['PATH']}",
            "GH_REPO": "chidionyema/idp",
            "BRANCH": "flux/image-updates",
            "HOME": str(tmp_path),
        },
    )


def test_a_behind_pull_request_is_refreshed_rather_than_parked(tmp_path):
    """The deadlock that kept the lane shut even with the classifier fixed.

    `gh pr diff` is the THREE-DOT diff, so a hunk against a frozen merge-base survives
    every merge to main -- measured on #3839, whose base d879408 still carries the blank
    line the controller had already dropped from the branch. The only thing that clears it
    is refreshing the branch, and that lived inside try_land, behind the classifier that
    the stale hunk was failing. Row 1 must break that tie itself.
    """
    r = _run_the_land_job(tmp_path, classifier_exit=1, state="BEHIND")
    assert r.returncode == 0, r.stderr
    assert "STUB-UPDATE-BRANCH" in r.stdout, (
        f"a refused bump that is BEHIND was never refreshed: {r.stdout.strip()} -- a stale "
        "merge-base then keeps the lane shut for good, because no merge to main moves it"
    )


def test_a_refused_bump_that_is_not_behind_still_waits_for_the_founder(tmp_path):
    """The refresh must not become a way to retry every refusal. Only a stale base is
    the estate's own fault; anything else is a real content change and his call."""
    r = _run_the_land_job(tmp_path, classifier_exit=1, state="CLEAN")
    assert r.returncode == 0, r.stderr
    assert "STUB-UPDATE-BRANCH" not in r.stdout, r.stdout
    assert "waits for the founder" in r.stdout, r.stdout


def test_refreshing_never_merges(tmp_path):
    """The classifier stays the only thing that can reach a merge. If a refresh could
    merge, a stale base would become a way INTO main rather than a reason to re-grade."""
    r = _run_the_land_job(tmp_path, classifier_exit=1, state="BEHIND")
    assert r.returncode == 0, r.stderr
    assert "STUB-MERGE" not in r.stdout, (
        f"the refresh path merged: {r.stdout.strip()} -- only try_land, downstream of a "
        "passing classifier, may reach a merge"
    )


def test_a_clean_image_only_bump_still_reaches_the_merge(tmp_path):
    """The other direction: when the classifier passes, the bump lands as it always did."""
    r = _run_the_land_job(tmp_path, classifier_exit=0, state="CLEAN")
    assert r.returncode == 0, r.stderr
    assert "STUB-MERGE" in r.stdout, r.stdout


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-q"]))
