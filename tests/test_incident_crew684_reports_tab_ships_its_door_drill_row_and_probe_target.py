"""Incident guard (crew#684 CP1, reports tab): a portal route that ships as a door
only — no login-drill row, no blackbox probe target — is invisible to the drills
that grade the estate. This test is the control the reports PR ships: it proves
the /reports route has its drill row, its probe target, and that the drill marker
is the page's own lead sentence (no selector, R53), from two angles (LAW 15).
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DRILL = ROOT / "bin" / "idp-login-drill"
PROBE = ROOT / "platform" / "monitoring" / "rules" / "founder-surfaces-probe.yaml"
PAGE = (
    ROOT / "backstage" / "packages" / "app" / "src" / "modules" / "home" / "Reports.tsx"
)

MARKER = "produced on a clock"


def test_login_drill_publishes_the_reports_row():
    text = DRILL.read_text()
    assert '("reports", "text=produced on a clock")' in text, (
        "bin/idp-login-drill has no PUBLISHED row for the reports route"
    )


def test_founder_surfaces_probe_targets_the_reports_page():
    text = PROBE.read_text()
    assert "/reports" in text, (
        "founder-surfaces-probe.yaml has no blackbox target for /reports"
    )


def test_drill_marker_is_the_pages_own_lead_sentence():
    # Two angles: the string the drill waits for must be text the page renders,
    # so a rewrite of the lead that breaks the drill fails here first.
    assert MARKER in PAGE.read_text(), (
        "Reports.tsx no longer renders the sentence the login drill waits for"
    )
    assert MARKER in DRILL.read_text()


def test_probe_target_is_not_a_selector():
    # R53: drills grade features, never look and feel.
    drill_line = next(
        line for line in DRILL.read_text().splitlines() if '"reports"' in line
    )
    for banned in ("data-testid", "css=", "xpath", "#", ".Mui"):
        assert banned not in drill_line


def test_publish_jobs_force_the_add_past_the_state_branch_ignore():
    """Run 33701059541 (2026-09-03): the first real publish on main died at `git add
    docs/reports` because the STATE BRANCH's .gitignore holds `reports/` -- a rule written for
    locally rendered reports that also swallows the published ones. The job checkouts
    state/live-diagram, so main's .gitignore never applies; only a forced add lands the report.
    The class (LAW 45): a writer graded green on a branch whose ignore rules it never met."""
    for wf in ("estate-state.yml", "estate-inventory.yml"):
        text = (ROOT / ".github" / "workflows" / wf).read_text()
        adds = [
            ln for ln in text.splitlines() if "git add" in ln and "docs/reports" in ln
        ]
        assert adds, (
            f"{wf} no longer publishes docs/reports; update this test with the mover"
        )
        for ln in adds:
            assert "git add -f docs/reports" in ln, (wf, ln)
