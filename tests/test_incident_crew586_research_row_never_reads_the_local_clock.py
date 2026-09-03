"""crew#586 (guard crew#583): the research row measures ledger freshness against the API's clock.
A ledger stamped by a machine whose clock reset reads stale in either direction, never fresh."""

import datetime as dt
import pathlib
import sys

IDP = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(IDP / "bin" / "lib"))
from ledger_fresh import ledger_fresh  # noqa: E402

NOW = dt.datetime(2026, 8, 28, 12, 0, tzinfo=dt.timezone.utc)


def _ledger(tmp_path, *dates):
    p = tmp_path / "RESEARCH-LEDGER.jsonl"
    p.write_text("".join(f'{{"date": "{d}", "q": "x"}}\n' for d in dates))
    return p


def test_an_entry_inside_the_window_is_fresh(tmp_path, capsys):
    assert ledger_fresh(_ledger(tmp_path, "2026-08-27T12:00:00Z"), 168, now=NOW) == 0
    assert "from the API clock" in capsys.readouterr().out


def test_a_1970_stamp_is_stale_and_a_future_stamp_is_a_clock_behind_the_ledger(
    tmp_path, capsys
):
    assert ledger_fresh(_ledger(tmp_path, "1970-01-01T00:00:00Z"), 168, now=NOW) == 1
    assert ledger_fresh(_ledger(tmp_path, "2027-08-28T12:00:00Z"), 168, now=NOW) == 2
    assert "behind the ledger" in capsys.readouterr().out


def test_the_same_ledger_grades_the_same_whatever_this_machine_thinks(tmp_path):
    led = _ledger(tmp_path, "2026-08-27T12:00:00Z")
    assert ledger_fresh(led, 168, now=NOW) == ledger_fresh(led, 168, now=NOW) == 0


def test_no_ledger_is_blind(tmp_path):
    assert ledger_fresh(tmp_path / "none.jsonl", 168, now=NOW) == 2
