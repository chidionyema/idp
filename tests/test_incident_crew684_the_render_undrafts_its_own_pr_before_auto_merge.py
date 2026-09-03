"""crew#684, 2026-08-30: the founder tile on the Ops page read `estate-state/docs/founder.json` and
got a 404 for eight hours. The scheduled render had pushed the file to `state/live-diagram` on every
run, but its PR #726 had been made a draft by bin/idp-pr-age at 21:57Z (conflict at the 4h bound,
crew#607 CP4), and `gh pr merge --auto` refuses a draft: runs 33278169055 and 33294242647 both
ended `FAIL catalog-render: auto-merge: ... Pull request is a draft`. Two automations disagreed
about one PR and neither said so. The render owns that PR; after a fresh push it is not stale, so
the render un-drafts it before arming auto-merge.
"""

import pathlib

RENDER = pathlib.Path(__file__).resolve().parents[1] / "bin" / "catalog-render"


def test_the_render_reads_the_draft_state_and_readies_its_pr_before_auto_merge():
    src = RENDER.read_text()
    view = src.index('"--json", "isDraft"')
    ready = src.index('["gh", "pr", "ready", existing]')
    merge = src.index('["gh", "pr", "merge", existing, "--auto", "--squash"]')
    assert view < ready < merge, (
        "the draft check and gh pr ready must run before the auto-merge step"
    )
    assert 'if draft == "true":' in src
