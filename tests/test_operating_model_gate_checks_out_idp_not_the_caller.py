"""The reusable gate checked out the caller instead of idp, and every gate outside idp was red.

2026-10-01 to 2026-10-25. `.github/workflows/operating-model-gate.yml` is a reusable workflow:
every active estate repo calls it as
`uses: chidionyema/idp/.github/workflows/operating-model-gate.yml@main`, and inside a called
workflow `github.repository` is the CALLER's repository, not idp. So the step that was supposed
to put idp into `.idp` put crew into `.idp`, and the gate died before it graded anything:

    line 6: /home/runner/work/crew/crew/.idp/bin/pr-report: No such file or directory
    ##[error]Process completed with exit code 127.

Measured: idp#6453, crew run 39088289618 job 117559385194, estate-guards PR #287 run
40167021277 job 121090058593 -- the same line, in two repos, three weeks apart. Every pull
request outside idp has carried a red operating-model gate since the owner-free pass
(ecc0ee8b4, crew#987 CP3) changed `repository: chidionyema/idp` into
`repository: ${{ github.repository }}`.

A gate that cannot run is not a gate that refuses; it is a gate that is not there, and the
estate read the red as the policy refusing the work. This test is what makes the difference
visible before the next owner-free pass makes the same edit again: the idp checkout must name
idp, by owner, and never the caller.

It grades the workflow file as it stands in the tree.
"""

from __future__ import annotations

import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "operating-model-gate.yml")


def idp_checkout_step() -> dict:
    """The step that fills .idp -- the one that must hold idp, not the caller."""
    doc = yaml.safe_load(open(WORKFLOW))
    job = doc["jobs"]["operating-model-gate"]
    for step in job["steps"]:
        with_ = step.get("with") or {}
        if with_.get("path") == ".idp":
            return step
    raise AssertionError(
        "the operating-model gate no longer checks idp out to .idp -- without it there is "
        "no policy and no budget, and the gate cannot grade a pull request at all"
    )


def test_the_idp_checkout_is_idp_and_not_the_caller() -> None:
    repository = (idp_checkout_step().get("with") or {}).get("repository", "")
    assert repository != "${{ github.repository }}", (
        "inside a reusable workflow github.repository is the CALLER's repository, so this "
        "checks the caller into .idp and $IDP_ROOT/bin/pr-report does not exist (exit 127)"
    )
    assert "github.repository_owner" in repository, (
        "the idp checkout must name idp by owner, the way "
        ".github/actions/github-app-token/action.yml already does: " + repository
    )


def test_the_policy_runs_out_of_the_idp_checkout() -> None:
    """The gate is judged by .idp/bin/pr-report; that path is the whole point of .idp."""
    step = idp_checkout_step()
    assert step.get("uses", "").startswith("actions/checkout@"), step
    assert (step.get("with") or {}).get("ref"), (
        "the idp checkout must pin a ref (idp_ref)"
    )
