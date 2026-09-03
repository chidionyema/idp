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


def test_founder_surfaces_probe_targets_the_reports_page():
    text = PROBE.read_text()
    assert "/reports" in text, (
        "founder-surfaces-probe.yaml has no blackbox target for /reports"
    )


def test_probe_target_is_not_a_selector():
    # R53: drills grade features, never look and feel.
    drill_line = next(
        line for line in DRILL.read_text().splitlines() if '"reports"' in line
    )
    for banned in ("data-testid", "css=", "xpath", "#", ".Mui"):
        assert banned not in drill_line


def test_no_ignore_rule_reaches_the_published_reports():
    """Founder ruling 2026-09-03: production publishing must never depend on a repo hygiene
    file. Runs 33701059541 and 33704425141 died at `git add docs/reports` because an
    UNANCHORED `reports/` rule (written for bin/supply-chain SBOM output at the repo root)
    also matched the published Reports pages -- on main and on the state branch's own copy.
    The first fix (-f at each call site) was refused as a future headache: every new
    publisher forgets it. The property graded here is the root one: no ignore rule may
    match the published path, and no publisher may need force to land it."""
    rules = [
        ln.strip()
        for ln in (ROOT / ".gitignore").read_text().splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    # the SBOM rule stays, anchored to the root so it can never swallow docs/reports
    assert "/reports/" in rules
    matching = [
        r
        for r in rules
        if r.rstrip("/").lstrip("/") == "reports" and not r.startswith("/")
    ]
    assert not matching, (
        f"unanchored rule(s) {matching} would swallow docs/reports again"
    )
    for wf in ("estate-state.yml", "estate-inventory.yml"):
        text = (ROOT / ".github" / "workflows" / wf).read_text()
        adds = [
            ln for ln in text.splitlines() if "git add" in ln and "docs/reports" in ln
        ]
        assert adds, (
            f"{wf} no longer publishes docs/reports; update this test with the mover"
        )
        for ln in adds:
            assert "add -f" not in ln, (
                wf,
                "a forced add hides an ignore rule instead of removing it",
                ln,
            )
    render = (ROOT / "bin" / "catalog-render").read_text()
    assert '"add", "-f"' not in render, (
        "a forced add hides an ignore rule instead of removing it"
    )
