"""crew#586 CP5: the portal card is rendered from the receipt (LAW 50), red rows first, with a
trend, and the daily run lands it through a PR with auto-merge, never a direct push."""
import json
import os
import pathlib
import subprocess
import sys

import yaml

IDP = pathlib.Path(__file__).resolve().parents[1]
WF = IDP / ".github" / "workflows" / "conscience.yml"


def _render(tmp_path, tenets):
    rep = tmp_path / "r.json"
    rep.write_text(json.dumps({"measured_at": "2026-08-28T07:23:00+00:00", "host": "runner",
                               "score": {"green": sum(t["ok"] is True for t in tenets), "total": len(tenets)},
                               "blind": any(t["ok"] is None for t in tenets), "tenets": tenets}))
    env = {**os.environ, "CONSCIENCE_REPORT": str(rep), "CONSCIENCE_PAGE": str(tmp_path / "p.md"),
           "CONSCIENCE_HISTORY": str(tmp_path / "h.jsonl")}
    return subprocess.run([sys.executable, str(IDP / "bin" / "idp-conscience"), "--page"], env=env, capture_output=True, text=True)


def _row(name, ok, how="exit 0"):
    return {"name": name, "ethos": "e", "measure": "true", "reads": "exit", "green": "== 0",
            "pr_rule": f"r_{name}", "mode": "warn", "value": 0, "how": how, "ok": ok}


def test_page_puts_red_rows_first_and_reads_the_score_from_the_receipt(tmp_path):
    p = _render(tmp_path, [_row("aaa", True), _row("zzz", False, "exit 1"), _row("mmm", None, "exit 2 (BLIND)")])
    assert p.returncode == 0, p.stderr
    page = (tmp_path / "p.md").read_text()
    assert "**🧠 1/3 tenets green — red: zzz.**" in page
    assert page.index("| 🔴 | zzz") < page.index("| ⚪ BLIND | mmm") < page.index("| 🟢 | aaa")
    assert "first reading" in page


def test_second_render_appends_history_and_reports_the_move(tmp_path):
    _render(tmp_path, [_row("a", False, "exit 1"), _row("b", True)])
    p = _render(tmp_path, [_row("a", True), _row("b", True)])
    assert p.returncode == 0, p.stderr
    assert len((tmp_path / "h.jsonl").read_text().splitlines()) == 2
    page = (tmp_path / "p.md").read_text()
    assert "moved +1 since the last reading" in page
    assert "## Trend, last 2 readings" in page


def test_page_without_a_receipt_is_blind(tmp_path):
    env = {**os.environ, "CONSCIENCE_REPORT": str(tmp_path / "none.json"), "CONSCIENCE_PAGE": str(tmp_path / "p.md")}
    p = subprocess.run([sys.executable, str(IDP / "bin" / "idp-conscience"), "--page"], env=env, capture_output=True, text=True)
    assert p.returncode == 2 and "BLIND" in p.stderr


def test_daily_run_lands_the_page_through_an_auto_merge_pr_and_the_portal_lists_it():
    wf = yaml.safe_load(WF.read_text())
    steps = {s.get("name"): s for s in wf["jobs"]["grade"]["steps"]}
    run = steps["portal page"]["run"]
    assert "23 7 * * *" in steps["portal page"]["if"]
    assert "bin/idp-conscience --page" in run
    assert '--force-with-lease origin "HEAD:refs/heads/$BRANCH"' in run
    assert 'gh pr merge "$n" --auto --squash' in run
    assert "push origin main" not in run and "HEAD:main" not in run
    assert wf["permissions"]["contents"] == "write" and wf["permissions"]["pull-requests"] == "write"
    nav = yaml.safe_load((IDP / "mkdocs.yml").read_text())["nav"]
    assert {"Conscience": "CONSCIENCE.md"} in nav
