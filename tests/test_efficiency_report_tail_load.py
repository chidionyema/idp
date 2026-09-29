"""estate-efficiency-report must answer "the last hour" without parsing the whole ledger.

2026-09-29: the ledger was 31 MB / 30k rows and /fleet polled the hour window every 5 s; `load`
parsed every row to keep 466 (8.6 s), the backend's requests piled up, and the Token Efficiency
HUD never left "waiting for the first ledger frame". The ledger is append-only and chronological,
so a windowed load reads from the tail and stops once it is past the window.
"""

from __future__ import annotations

import datetime as dt
import importlib.machinery
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "bin" / "estate-efficiency-report"


def _load():
    loader = importlib.machinery.SourceFileLoader(
        "estate_efficiency_report", str(SCRIPT)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _row(at: dt.datetime, n: int) -> str:
    return json.dumps(
        {"kind": "outcome", "at": at.strftime("%Y-%m-%dT%H:%M:%SZ"), "n": n}
    )


def _ledger(tmp_path: Path, old: int, new: int) -> tuple[Path, dt.datetime]:
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    lines = [_row(now - dt.timedelta(hours=3, seconds=old - i), i) for i in range(old)]
    lines.append("not json at all")
    lines += [_row(now - dt.timedelta(seconds=new - i), old + i) for i in range(new)]
    p = tmp_path / "ledger.jsonl"
    p.write_text("\n".join(lines) + "\n")
    return p, now


def test_a_windowed_load_returns_only_the_window_in_ledger_order(tmp_path):
    mod = _load()
    path, now = _ledger(tmp_path, old=200, new=5)
    rows = mod.load(path, now - dt.timedelta(hours=1))
    assert [r["n"] for r in rows] == [200, 201, 202, 203, 204]


def test_a_windowed_load_stops_reading_once_it_is_past_the_window(
    tmp_path, monkeypatch
):
    mod = _load()
    path, now = _ledger(tmp_path, old=5000, new=5)
    parsed = []
    real = mod.json.loads
    monkeypatch.setattr(mod.json, "loads", lambda s: (parsed.append(s), real(s))[1])
    rows = mod.load(path, now - dt.timedelta(hours=1))
    assert len(rows) == 5
    # 5 kept + the first row past the window that stops the read; not 5000.
    assert len(parsed) < 20, len(parsed)


def test_an_unbounded_load_still_reads_everything(tmp_path):
    mod = _load()
    path, _now = _ledger(tmp_path, old=30, new=5)
    assert len(mod.load(path, None)) == 35
