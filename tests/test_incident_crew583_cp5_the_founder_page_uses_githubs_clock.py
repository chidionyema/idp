"""crew#583 CP5: the page that tells the founder what is waiting on a person read every age off
this machine's clock, and a clock behind the stamps made "nothing is stuck" the answer.

The shape, from `bin/estate-founder` as it stood at 2026-08-28 (found by
`test_guard_freshness_is_never_measured_against_this_machines_clock`, not by the sweep that wrote
the guard):

    now = datetime.now(timezone.utc)                     # this machine
    stuck = [pr for pr in open_prs if ... hours_since(pr["created_at"], now) >= REVIEW_H]

`created_at` is GitHub's stamp; `now` is the laptop's. Two clocks, and the only bound is the lower
one. A MacBook whose battery dies flat comes back at the RTC's default epoch, every age goes
negative, no age clears REVIEW_H, every unreviewed pull request falls out of the list, and the page
prints "Nothing is stuck: every open pull request has a verdict and no checkpoint names you." The
one page whose job is to surface what a person is sitting on would be the last thing to say so.

`hours_since` had a second way to the same place: `except ValueError: return 0.0` read a stamp it
could not parse as "0 hours ago", the freshest answer available.

Rung 4, incident test, both directions plus the honest case. The fix is not a sign check -- it is
that `now` comes from the `Date` header of the response GitHub served, so the subtraction is one
clock minus itself and this machine's opinion cannot change the answer.
"""
import importlib.machinery
import importlib.util
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin" / "estate-founder"
spec = importlib.util.spec_from_loader("estate_founder", importlib.machinery.SourceFileLoader("estate_founder", str(BIN)))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

#: One unreviewed pull request, opened well past REVIEW_H before the run, in a repository the page
#: counts as live because something merged there inside the window.
OPENED = "2026-08-28T02:00:00Z"
MERGED = "2026-08-28T05:10:00Z"
HONEST_NOW = "2026-08-28T06:30Z"

MERGED_PRS = [{"repo": "chidionyema/idp", "number": 529, "title": "crew#554: drills run on the estate's clock",
               "body": "Use: `bin/idp-drills-row` shows the rows", "created_at": "2026-08-28T01:00:00Z",
               "url": "https://github.com/chidionyema/idp/pull/529", "merged_at": MERGED}]
OPEN_PRS = [{"repo": "chidionyema/idp", "number": 527, "title": "crew#554: schedule row counts firings",
             "body": "", "url": "https://github.com/chidionyema/idp/pull/527", "merged_at": "",
             "created_at": OPENED, "verdict": ""}]


def _page(tmp: Path, now: str) -> str:
    for name, rows in (("merged", MERGED_PRS), ("open", OPEN_PRS), ("issues", [])):
        (tmp / f"{name}.json").write_text(json.dumps(rows))
    out = tmp / "FOUNDER.md"
    rc = mod.main(["--merged", str(tmp / "merged.json"), "--open", str(tmp / "open.json"),
                   "--issues", str(tmp / "issues.json"), "--out", str(out), "--now", now])
    assert rc == 0
    return out.read_text()


@pytest.mark.parametrize("dead_clock,label", [
    ("1970-01-01T00:00Z", "battery_died_rtc_at_the_epoch"),
    ("2025-07-25T06:30Z", "clock_400d_behind_the_stamps"),
])
def test_a_clock_behind_githubs_stamps_never_says_nothing_is_stuck(tmp_path, dead_clock, label):
    """The incident. Before the fix these ages were negative, the `>= REVIEW_H` filter dropped the
    row, and the page told the founder every pull request had a verdict."""
    page = _page(tmp_path, dead_clock)
    assert "Nothing is stuck" not in page, page
    assert "idp#527" in page, page
    assert "BLIND" in page, page


def test_the_blind_row_says_which_clock_it_could_not_get(tmp_path):
    """LAW 28: a row that reads BLIND and does not say what is missing sends somebody looking in
    the wrong place. It must name the clock, not just decline."""
    page = _page(tmp_path, "1970-01-01T00:00Z")
    row = next(l for l in page.splitlines() if "idp#527" in l)
    assert "clock" in row and "no REVIEW: line" in row, row


def test_an_honest_clock_still_prints_the_hours_the_founder_acts_on(tmp_path):
    """The over-fix guard. A page that answered BLIND for everything would also pass the test
    above; the number a real run produces has to survive."""
    page = _page(tmp_path, HONEST_NOW)
    row = next(l for l in page.splitlines() if "idp#527" in l)
    assert "4h, no REVIEW: line" in row, row
    assert "BLIND" not in row, row


def test_a_stamp_that_cannot_be_parsed_is_not_zero_hours_ago():
    """`except ValueError: return 0.0` was the second silent-fresh path: an unreadable stamp read
    as the newest possible one, on the page that grades by age."""
    now = datetime(2026, 8, 28, 6, 30, tzinfo=timezone.utc)
    assert mod.hours_since("not-a-timestamp", now) is None
    assert mod.hours_since("", now) is None
    assert mod.hours_since(OPENED, now) == pytest.approx(4.5)


def test_a_pull_request_opened_after_the_response_that_listed_it_is_blind_not_fresh():
    """Both stamps come from GitHub, so a negative age is not skew -- it is GitHub disagreeing
    with itself, and it must not read as "not stuck" either."""
    now = datetime(2026, 8, 28, 1, 0, tzinfo=timezone.utc)
    assert mod.hours_since("2026-08-28T02:00:00Z", now) is None


def test_the_clock_comes_from_the_date_header_of_githubs_own_response():
    """The fix itself: `now` is the clock that stamped `created_at`, travelling in the same round
    trip, so a dead RTC on this machine cannot reach the subtraction at all."""
    served = "Fri, 28 Aug 2026 06:30:00 GMT"

    def fake(cmd, **kw):
        assert cmd[:3] == ["gh", "api", "-i"], cmd
        return subprocess.CompletedProcess(cmd, 0, stdout=f"HTTP/2.0 200 OK\r\nDate: {served}\r\n\r\n{{}}\n", stderr="")

    got = mod.github_now(run=fake)
    assert got == datetime(2026, 8, 28, 6, 30, tzinfo=timezone.utc), got


@pytest.mark.parametrize("stdout,label", [
    ("HTTP/2.0 200 OK\r\nETag: x\r\n\r\n{}\n", "no_date_header"),
    ("HTTP/2.0 200 OK\r\nDate: not a date\r\n\r\n{}\n", "unreadable_date_header"),
])
def test_a_response_with_no_usable_clock_is_none_and_never_this_machines(stdout, label):
    """None, not a fallback. Falling back to the local clock here is the defect with a longer code
    path, and the page refuses to build rather than print ages nobody can trust."""
    fake = lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")
    assert mod.github_now(run=fake) is None


def test_the_page_refuses_rather_than_falling_back_when_github_sends_no_clock(tmp_path, monkeypatch, capsys):
    """End to end: no clock, no page. The window itself is `now - 24h`, so there is nothing honest
    to print, and writing yesterday's file over again would be worse than an exit."""
    monkeypatch.setattr(mod, "github_now", lambda *a, **k: None)
    out = tmp_path / "FOUNDER.md"
    for name in ("merged", "open", "issues"):
        (tmp_path / f"{name}.json").write_text("[]")
    rc = mod.main(["--merged", str(tmp_path / "merged.json"), "--open", str(tmp_path / "open.json"),
                   "--issues", str(tmp_path / "issues.json"), "--out", str(out)])
    assert rc == 2
    assert not out.exists()
    assert "BLIND" in capsys.readouterr().err


def test_this_file_no_longer_asks_the_machine_what_time_it_is():
    """The guard in test_guard_freshness_is_never_measured_against_this_machines_clock.py holds
    every script; this says it about the one this incident is in, so the name can leave
    NOT_YET_MIGRATED and stay gone."""
    code = "\n".join(l for l in BIN.read_text(encoding="utf-8").splitlines() if not l.lstrip().startswith("#"))
    body = code.split('"""')
    code = "".join(body[::2])  # drop docstrings: the prose quotes the defect on purpose
    assert "datetime.now(" not in code, code
