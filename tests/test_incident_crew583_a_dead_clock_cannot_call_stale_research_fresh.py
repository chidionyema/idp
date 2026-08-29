"""crew#583: the conscience `research` row read green on a ledger that had been dead for years.

`bin/idp-conscience --ledger-fresh-hours H` answers "has research happened inside H hours". Until
idp#621 it answered it like this:

    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours)
    fresh  = [s for s in stamps if s >= cutoff]
    return 0 if fresh else 1

`stamps` are parsed out of crew/science/RESEARCH-LEDGER.jsonl, written by whichever session appended
to it. `cutoff` was this machine's clock. When a MacBook's battery goes flat the RTC resets to a
default epoch, `cutoff` lands decades before every entry in the file, every entry is `>= cutoff`,
and the tenet row prints green on a ledger nobody has touched in years. That is the class crew#583
was opened for, arriving in bin/idp-conscience the same afternoon the guard for it landed -- which
is how it was found: idp#612's guard failed on main against idp#614's new file.

idp#619 removes the local clock from the subtraction altogether: `now` is the GitHub API's `Date`
header (bin/lib/ledger_fresh.py), and no header means BLIND (2), never a fall-back to the local
clock. The clock cannot be moved from inside a test, and it does not need to be: a machine 400 days
behind the ledger and a ledger stamped 400 days ahead of the machine are the same subtraction. So
`now` is injected, the stamps move around it, and the verdict is asserted at each position.

No test here opens a socket (estate rule: tests never open network sockets). The subprocess cases
run the CLI with a PATH that holds no `gh`, which is exactly the "no authority clock" branch.
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
sys.path.insert(0, str(ROOT / "bin" / "lib"))
from ledger_fresh import ledger_fresh  # noqa: E402

NOW = dt.datetime(2026, 8, 28, 12, 0, tzinfo=dt.timezone.utc)  # the authority clock, injected


def _ledger(tmp_path: Path, *offsets: dt.timedelta, key: str = "ts") -> Path:
    """An estate tree whose crew checkout holds a research ledger stamped at `offsets` from NOW."""
    led = tmp_path / "crew" / "science" / "RESEARCH-LEDGER.jsonl"
    led.parent.mkdir(parents=True)
    led.write_text("".join(json.dumps({key: (NOW + o).isoformat()}) + "\n" for o in offsets))
    return led


def _row(led: Path, capsys, hours: int = 24) -> tuple[int, str]:
    rc = ledger_fresh(led, hours, now=NOW)
    return rc, capsys.readouterr().out


def _cli(tmp_path: Path, hours: int = 24) -> subprocess.CompletedProcess:
    """The real command with no `gh` on PATH: the only clock it may use is one it cannot reach."""
    return subprocess.run([sys.executable, str(CONSCIENCE), "--ledger-fresh-hours", str(hours)],
                          capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin", "ESTATE_CODE": str(tmp_path)})


def test_research_inside_the_window_is_green(tmp_path, capsys):
    """The over-fix guard: a reader that refuses everything is not a fix, and this fails it."""
    rc, out = _row(_ledger(tmp_path, dt.timedelta(hours=-1)), capsys)
    assert rc == 0, out
    assert "inside 24h" in out


def test_research_outside_the_window_is_red(tmp_path, capsys):
    rc, out = _row(_ledger(tmp_path, dt.timedelta(days=-365)), capsys)
    assert rc == 1, out
    assert "older than 24h" in out


@pytest.mark.parametrize("ahead", [dt.timedelta(days=400), dt.timedelta(days=20000)],
                         ids=["clock_400d_behind_the_ledger", "clock_at_the_1970_epoch"])
def test_a_clock_behind_the_ledger_is_blind_and_never_green(tmp_path, ahead, capsys):
    """The incident. Every stamp later than `now` means the clock is behind the data it is
    grading; the old cutoff called that "fresh" and exited 0."""
    rc, out = _row(_ledger(tmp_path, ahead - dt.timedelta(days=365), ahead), capsys)
    assert rc == 2, out
    assert out.startswith("BLIND"), out
    assert "behind the ledger" in out


def test_the_newest_entry_decides_not_any_entry(tmp_path, capsys):
    """A ledger holding one recent entry and a hundred ancient ones is fresh; the old code agreed,
    and the point of asserting it is that measuring the newest is what keeps that true."""
    led = _ledger(tmp_path, *([dt.timedelta(days=-900)] * 20 + [dt.timedelta(hours=-2)]))
    rc, out = _row(led, capsys)
    assert rc == 0, out
    assert "2.0h old" in out


def test_a_ledger_whose_entries_carry_no_stamp_is_not_fresh(tmp_path, capsys):
    """Nothing is not fresh. An empty age used to fall through the list comprehension to `not fresh`
    by luck; here it is a named case."""
    led = tmp_path / "crew" / "science" / "RESEARCH-LEDGER.jsonl"
    led.parent.mkdir(parents=True)
    led.write_text(json.dumps({"note": "no stamp on this row"}) + "\n")
    rc, out = _row(led, capsys)
    assert rc == 1, out
    assert "no entry carries a stamp" in out


def test_a_missing_ledger_is_blind_not_green(tmp_path):
    p = _cli(tmp_path)
    assert p.returncode == 2, p.stdout + p.stderr
    assert "BLIND" in p.stdout


def test_no_authority_clock_is_blind_never_the_local_clock(tmp_path):
    """The idp#619 property. A fresh ledger and no `gh` on PATH: the old code would have asked
    this machine's clock and printed green; the reader has no clock and says so."""
    _ledger(tmp_path, dt.timedelta(hours=-1))
    p = _cli(tmp_path)
    assert p.returncode == 2, p.stdout + p.stderr
    assert p.stdout.startswith("BLIND"), p.stdout
    assert "no clock to measure against" in p.stdout


def test_the_row_parses_no_timestamp_of_its_own(tmp_path):
    """Not a style rule. bin/lib/ledger_fresh.py is the one place allowed to put a stamp and the
    authority clock in the same subtraction, and it is the only file the incident tests for this
    class cover. A second copy of the parse in bin/idp-conscience is a second place to get it wrong,
    and the estate guard would fail on it -- this says so at the file that would grow it."""
    src = CONSCIENCE.read_text()
    assert "fromisoformat" not in src.split('"""')[-1], \
        "bin/idp-conscience parses a stamp again; route it through bin/lib/ledger_fresh.py"
