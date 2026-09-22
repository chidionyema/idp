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
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "bin/idp-image-only-diff"


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


def test_the_llm_kustomization_no_longer_carries_the_line_the_controller_strips():
    """Proving the classifier alone would leave the lane shut: #3839 also carries the
    blank-line deletion above. Removing it at the source is what makes the controller's
    next write a tag-only diff."""
    text = (REPO / "platform/llm/kustomization.yaml").read_text()
    assert "disableNameSuffixHash: false\n\n" not in text, (
        "the blank line after generatorOptions is back; image-automation-controller "
        "strips it on every write, which makes every deploy PR non-landable"
    )


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-q"]))
