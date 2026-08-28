"""crew#412 (R38): the founder's three questions are answered by a generated page, never by a session.

Incident, 2026-08-28: the founder asked "where is the founders gods view", "wtf has shipped",
"what changed for me", "what is stuck" and got typed answers three times in one night. This
test pins the page that answers instead: what shipped (every merged PR, by repository, with its
issue), what changed for you (only the merged PRs carrying a `Use:` line), what is stuck (open
PRs with no REVIEW: verdict after the window, and checkpoints that name the founder). Offline:
every input is a file, no network.
"""
import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin" / "estate-founder"
spec = importlib.util.spec_from_loader("estate_founder", importlib.machinery.SourceFileLoader("estate_founder", str(BIN)))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

NOW = "2026-08-28T06:30Z"


def _inputs(tmp: Path) -> dict:
    merged = [
        {"repo": "chidionyema/idp", "number": 529, "title": "crew#554: drills run on the estate's clock",
         "body": "Built: a CronJob.\nUse: `bin/idp-drills-row` shows `N dispatched by the App`\nExpect: rows",
         "url": "https://github.com/chidionyema/idp/pull/529", "merged_at": "2026-08-28T05:10:00Z", "created_at": "2026-08-28T01:00:00Z"},
        {"repo": "chidionyema/idp", "number": 540, "title": "crew#539: node-drain retires the node (#540)",
         "body": "internal playbook, no founder surface",
         "url": "https://github.com/chidionyema/idp/pull/540", "merged_at": "2026-08-28T06:00:00Z", "created_at": "2026-08-28T05:00:00Z"},
        {"repo": "chidionyema/claude-guards", "number": 183, "title": "guard: feed stdin",
         "body": "Use: nothing; the hook runs on its own.", "url": "https://github.com/chidionyema/claude-guards/pull/183",
         "merged_at": "2026-08-27T22:00:00Z", "created_at": "2026-08-27T21:00:00Z"},
    ]
    open_prs = [
        {"repo": "chidionyema/idp", "number": 527, "title": "crew#554: schedule row counts firings", "body": "",
         "url": "https://github.com/chidionyema/idp/pull/527", "merged_at": "", "created_at": "2026-08-28T02:00:00Z", "verdict": ""},
        {"repo": "chidionyema/idp", "number": 600, "title": "fresh PR", "body": "",
         "url": "https://github.com/chidionyema/idp/pull/600", "merged_at": "", "created_at": "2026-08-28T06:00:00Z", "verdict": ""},
        {"repo": "chidionyema/idp", "number": 601, "title": "graded PR", "body": "",
         "url": "https://github.com/chidionyema/idp/pull/601", "merged_at": "", "created_at": "2026-08-28T01:00:00Z", "verdict": "KEEP"},
        {"repo": "chidionyema/haworks", "number": 5, "title": "Compiling", "body": "",
         "url": "https://github.com/chidionyema/haworks/pull/5", "merged_at": "", "created_at": "2026-04-25T01:00:00Z", "verdict": ""},
    ]
    issues = [
        {"number": 503, "title": "founder polish", "url": "https://github.com/chidionyema/crew/issues/503",
         "body": "- [x] CP1 done\n- [ ] CP4 Every founder surface opened and graded\n- [ ] CP5 Founder opens the home page and confirms here (`DONE:` needs that receipt)."},
        {"number": 412, "title": "god view", "url": "https://github.com/chidionyema/crew/issues/412",
         "body": "- [ ] Built: merged and green"},
    ]
    paths = {}
    for name, data in {"merged": merged, "open": open_prs, "issues": issues}.items():
        p = tmp / f"{name}.json"
        p.write_text(json.dumps(data))
        paths[name] = p
    return paths


def _run(tmp: Path, *extra: str) -> subprocess.CompletedProcess:
    p = _inputs(tmp)
    return subprocess.run([sys.executable, str(BIN), "--merged", str(p["merged"]), "--open", str(p["open"]),
                           "--issues", str(p["issues"]), "--out", str(tmp / "FOUNDER.md"), "--now", NOW,
                           "--taken", NOW, *extra], capture_output=True, text=True)


def test_shipped_lists_every_merged_pr_by_repository_with_its_issue(tmp_path):
    r = _run(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    page = (tmp_path / "FOUNDER.md").read_text()
    assert "**3 pull requests merged** in 24h across 2 repositories" in page
    assert "### chidionyema/idp — 2 merged" in page
    assert "| 2026-08-28T05:10Z | crew#554 | [crew#554: drills run on the estate's clock]" in page
    assert "| 2026-08-27T22:00Z | — | [guard: feed stdin]" in page


def test_changed_for_you_is_only_the_use_lines(tmp_path):
    _run(tmp_path)
    page = (tmp_path / "FOUNDER.md").read_text()
    changed = page.split("## What changed for you")[1].split("## What is stuck")[0]
    assert "`bin/idp-drills-row` shows `N dispatched by the App`" in changed
    assert "node-drain" not in changed, "a PR with no Use: line changed nothing the founder touches"
    assert "feed stdin" not in changed and "claude-guards#183" not in changed, "`Use: nothing` is nothing"
    assert "**1** of them carry a `Use:` line" in page


def test_stuck_is_unreviewed_prs_past_the_window_and_checkpoints_that_name_the_founder(tmp_path):
    _run(tmp_path)
    page = (tmp_path / "FOUNDER.md").read_text()
    stuck = page.split("## What is stuck")[1].split("## What shipped")[0]
    assert "| reviewer | crew#554: schedule row counts firings | 4h, no REVIEW: line |" in stuck
    assert "fresh PR" not in stuck, "a PR younger than the review window is not stuck"
    assert "graded PR" not in stuck, "a PR with a REVIEW: verdict is not stuck"
    assert "haworks" not in stuck, "a parked repository (nothing merged in the window) owes no review"
    assert "| you | CP5 Founder opens the home page and confirms here" in stuck
    assert "CP4" not in stuck, "a checkpoint that does not name the founder is not his"
    assert "**1 pull requests** with no `REVIEW:` verdict after 2h; **1 checkpoints wait on you**" in page


def test_check_fails_on_a_stale_page_and_passes_after_a_render(tmp_path):
    (tmp_path / "FOUNDER.md").write_text("# stale\n\nx\n\nold body\n")
    stale = _run(tmp_path, "--check")
    assert stale.returncode == 1 and "FAIL  estate-founder" in stale.stdout
    assert _run(tmp_path).returncode == 0
    fresh = _run(tmp_path, "--check")
    assert fresh.returncode == 0, fresh.stdout + fresh.stderr


def test_an_empty_window_is_a_row_not_a_blank(tmp_path):
    for name in ("merged", "open", "issues"):
        (tmp_path / f"{name}.json").write_text("[]")
    r = subprocess.run([sys.executable, str(BIN), "--merged", str(tmp_path / "merged.json"), "--open", str(tmp_path / "open.json"),
                        "--issues", str(tmp_path / "issues.json"), "--out", str(tmp_path / "F.md"), "--now", NOW, "--taken", NOW],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    page = (tmp_path / "F.md").read_text()
    assert "No pull request merged since" in page
    assert "Nothing is stuck" in page
    assert "nothing you touch changed" in page


def test_the_render_driver_and_the_portal_carry_the_page():
    driver = (ROOT / "bin" / "catalog-render").read_text()
    assert "estate-founder" in driver and 'FOUNDER = "docs/FOUNDER.md"' in driver
    assert "FOUNDER.md" in (ROOT / "mkdocs.yml").read_text()
    founder = (ROOT / "backstage" / "founder" / "catalog-info.yaml").read_text()
    assert "founder-gods-view" in founder and "docs/FOUNDER.md" in founder
