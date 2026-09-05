"""crew#583: the conscience `research` row read green on a ledger that had been dead for years.

`bin/idp-conscience --ledger-fresh-hours H` answers "has research happened inside H hours". Until
this commit it answered it like this:

    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours)
    fresh  = [s for s in stamps if s >= cutoff]
    return 0 if fresh else 1

`stamps` are parsed out of crew/science/RESEARCH-LEDGER.jsonl, written by whichever session appended
to it. `cutoff` is this machine's clock. When a MacBook's battery goes flat the RTC resets to a
default epoch, `cutoff` lands decades before every entry in the file, every entry is `>= cutoff`,
and the tenet row prints green on a ledger nobody has touched in years. That is the class crew#583
was opened for, arriving in bin/idp-conscience the same afternoon the guard for it landed -- which
is how it was found: idp#612's guard failed on main against idp#614's new file.

The clock cannot be moved from inside a test, and it does not need to be: a machine 400 days behind
the ledger and a ledger stamped 400 days ahead of the machine are the same subtraction. So the
stamps move and the verdict is asserted at each position.

The property proved here is the weaker of the two in bin/lib/receipt_age.py, and deliberately named
as such: a local file carries no served `date` the way an object head does, so the local clock
cannot be removed from the arithmetic. What is removed is the silent green -- a clock behind the
ledger is BLIND (2), a clock ahead of it reads everything as old (1), and neither prints 0.
"""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONSCIENCE = ROOT / "bin" / "idp-conscience"


def _ledger(tmp_path: Path, *offsets: dt.timedelta, key: str = "ts") -> Path:
    """An estate tree whose crew checkout holds a research ledger stamped at `offsets` from now."""
    now = dt.datetime.now(dt.timezone.utc)
    led = tmp_path / "crew" / "science" / "RESEARCH-LEDGER.jsonl"
    led.parent.mkdir(parents=True)
    led.write_text("".join(json.dumps({key: (now + o).isoformat()}) + "\n" for o in offsets))
    return led


def _row(tmp_path: Path, hours: int = 24) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CONSCIENCE), "--ledger-fresh-hours", str(hours)],
                          capture_output=True, text=True, env={"PATH": "/usr/bin:/bin",
                                                               "ESTATE_CODE": str(tmp_path)})


def test_research_inside_the_window_is_green(tmp_path):
    """The over-fix guard: a reader that refuses everything is not a fix, and this fails it."""
    _ledger(tmp_path, dt.timedelta(hours=-1))
    p = _row(tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "inside 24h" in p.stdout


def test_research_outside_the_window_is_red(tmp_path):
    _ledger(tmp_path, dt.timedelta(days=-365))
    p = _row(tmp_path)
    assert p.returncode == 1, p.stdout + p.stderr
    assert "older than 24h" in p.stdout


@pytest.mark.parametrize("ahead", [dt.timedelta(days=400), dt.timedelta(days=20000)],
                         ids=["clock_400d_behind_the_ledger", "clock_at_the_1970_epoch"])
def test_a_clock_behind_the_ledger_is_blind_and_never_green(tmp_path, ahead):
    """The incident. Every stamp later than `now` means this machine is behind the data it is
    grading; the old cutoff called that "fresh" and exited 0."""
    _ledger(tmp_path, ahead - dt.timedelta(days=365), ahead)
    p = _row(tmp_path)
    assert p.returncode == 2, p.stdout + p.stderr
    assert p.stdout.startswith("BLIND"), p.stdout
    assert "behind the ledger" in p.stdout


def test_the_newest_entry_decides_not_any_entry(tmp_path):
    """A ledger holding one recent entry and a hundred ancient ones is fresh; the old code agreed,
    and the point of asserting it is that measuring the newest is what keeps that true."""
    _ledger(tmp_path, *([dt.timedelta(days=-900)] * 20 + [dt.timedelta(hours=-2)]))
    p = _row(tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "2.0h old" in p.stdout


def test_a_ledger_whose_entries_carry_no_stamp_is_not_fresh(tmp_path):
    """Nothing is not fresh. An empty age used to fall through the list comprehension to `not fresh`
    by luck; here it is a named case."""
    led = tmp_path / "crew" / "science" / "RESEARCH-LEDGER.jsonl"
    led.parent.mkdir(parents=True)
    led.write_text(json.dumps({"note": "no stamp on this row"}) + "\n")
    p = _row(tmp_path)
    assert p.returncode == 1, p.stdout + p.stderr
    assert "no entry carries a stamp" in p.stdout


def test_a_missing_ledger_is_blind_not_green(tmp_path):
    p = _row(tmp_path)
    assert p.returncode == 2, p.stdout + p.stderr
    assert "BLIND" in p.stdout


def test_the_row_parses_no_timestamp_of_its_own(tmp_path):
    """Not a style rule. bin/lib/receipt_age.py is the one place in the estate allowed to put a
    stamp and a clock in the same subtraction, and it is the only file the incident tests for this
    class cover. A second copy of the parse in bin/idp-conscience is a second place to get it wrong,
    and the estate guard would fail on it -- this says so at the file that would grow it."""
    src = CONSCIENCE.read_text()
    assert "fromisoformat" not in src.split('"""')[-1], \
        "bin/idp-conscience parses a stamp again; route it through bin/lib/receipt_age.py"
