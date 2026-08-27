"""Binds features/assurance/estate-next.feature (crew#403 CP6). Steps run bin/estate-next for real
over an issues JSON file and a feed file; no network."""
import json
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("features/assurance/estate-next.feature")

IDP = Path(__file__).resolve().parents[3]
NOW = "2026-08-27T13:00Z"


def _run(tmp: Path, issues: list, feed: str) -> str:
    (tmp / "issues.json").write_text(json.dumps(issues))
    (tmp / "feed.md").write_text(feed)
    out = tmp / "NEXT.md"
    r = subprocess.run([sys.executable, str(IDP / "bin" / "estate-next"), "--issues", str(tmp / "issues.json"),
                        "--feed", str(tmp / "feed.md"), "--out", str(out), "--taken", NOW, "--now", NOW],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return out.read_text()


def _issue(n: int, body: str) -> dict:
    return {"number": n, "title": f"t{n}", "body": body, "url": f"https://x/{n}"}


@pytest.fixture
def ctx(tmp_path):
    return {"tmp": tmp_path}


@given("an issue with an open checkpoint row and no Expect line")
def _nodate(ctx):
    ctx["issues"] = [_issue(7, "- [ ] CP1 build it\n- [x] CP0 done\n")]
    ctx["feed"] = ""


@given("an issue with an open checkpoint row, an Expect line, and a lane whose red line names it")
def _blocking(ctx):
    ctx["issues"] = [_issue(7, "- [ ] CP1 build it\n    Expect: 2026-08-29\n")]
    ctx["feed"] = "## 2026-08-27T12:40Z · abc · code\n🔴 Blocked: crew#7 waits on billing\n🟡 Active: crew#70\n"


@given("an issue named only by a handoff from yesterday")
def _stale(ctx):
    ctx["issues"] = [_issue(7, "- [ ] CP1 build it\n    Expect: 2026-08-29\n")]
    ctx["feed"] = "## 2026-08-26T12:40Z · abc · code\n🟡 Active: crew#7\n"


@when("estate-next renders the page")
def _render(ctx):
    ctx["page"] = _run(ctx["tmp"], ctx["issues"], ctx["feed"])


@then("the row carries NO DATE")
def _t_nodate(ctx):
    assert "| PLANNED | [crew#7](https://x/7) | CP1 | build it | **NO DATE** |" in ctx["page"]
    assert "**1 NO DATE**" in ctx["page"]


@then("the row is BLOCKING with its date")
def _t_blocking(ctx):
    assert "| BLOCKING | [crew#7](https://x/7) | CP1 | build it | 2026-08-29 |" in ctx["page"]
    assert "**0 NO DATE**" in ctx["page"] and "**1 BLOCKING**" in ctx["page"]
    # crew#70 on the amber line must not match crew#7
    assert "| ACTIVE |" not in ctx["page"]


@then("the row is PLANNED")
def _t_planned(ctx):
    assert "| PLANNED | [crew#7](https://x/7) | CP1 | build it | 2026-08-29 |" in ctx["page"]
    assert "Lanes reporting: none" in ctx["page"]
