"""What the receipt says about who wrote it, and what --install says about who runs it.

Why this file exists. Measured 2026-10-24: the answer to "who refreshes the pi monitor?" was wrong
twice in opposite directions. The door said "the estate's one scheduler", while the only job that
fires on this laptop is a launchd one (ai.estate.pi-reaper, StartInterval 600, loaded, LastExitStatus
0) -- and the scheduler's own entry (scheduler/schedule.yml, ai.estate.pi-observe) cannot start
because the checkout's .venv is not executable here. Nothing recorded either fact, so a reader had
to re-derive them from `launchctl list` and a 30 MB log.

So the receipt now carries `provenance`: the writer, the caller as measured from the ancestor whose
parent is launchd, and the launchd job it found. These tests pin that, and pin the door's refusal to
assert a home it has not measured. A future change that goes back to naming a runner which does not
run fails here rather than on the founder's screen.
"""

from __future__ import annotations

import importlib.util
import io
import json
import pathlib
from contextlib import redirect_stdout

OBSERVE = pathlib.Path(__file__).resolve().parents[1] / "bin" / "pi-observe"


def _observe():
    """bin/pi-observe has no .py suffix, so the loader must be named rather than inferred."""
    from importlib.machinery import SourceFileLoader

    loader = SourceFileLoader("pi_observe_provenance", str(OBSERVE))
    spec = importlib.util.spec_from_loader("pi_observe_provenance", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_the_receipt_names_its_writer_and_its_caller():
    p = _observe().provenance(["--json"])
    assert p["written_by"] == "bin/pi-observe"
    assert p["pid"] > 0
    # Whichever of these is true on this host, it must be one of them -- not a guess.
    assert p["started_by"] in {"launchd", "estate-executor", "hand-run", "unknown"}
    assert p["ancestry"], "the receipt must carry the evidence behind started_by"
    assert isinstance(p["launchd_jobs"], list)


def test_a_plist_that_is_not_well_formed_xml_is_still_read(tmp_path):
    """The measured bug: a `--` inside an XML comment makes plistlib raise, while launchd and
    plutil load the same file (`plutil -lint`: OK). ai.estate.pi-reaper.plist has exactly that, so
    without this fallback the door is blind to the job that runs it."""
    p = tmp_path / "ai.estate.x.plist"
    p.write_text(
        '<?xml version="1.0"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        "<!-- reads ~/.estate -- and never ~/Documents -->\n"
        '<plist version="1.0"><dict>'
        "<key>Label</key><string>ai.estate.x</string>"
        "<key>StartInterval</key><integer>600</integer>"
        "</dict></plist>\n"
    )
    body = _observe()._read_plist(str(p))
    assert body is not None
    assert body["Label"] == "ai.estate.x"
    assert body["StartInterval"] == 600


def test_install_names_the_runner_it_measured_not_one_it_hopes_for(monkeypatch):
    m = _observe()
    monkeypatch.setattr(
        m,
        "launchd_jobs_mentioning",
        lambda: [
            {
                "label": "ai.estate.pi-reaper",
                "plist": "/x/a.plist",
                "interval_s": 600,
                "program": "/bin/bash -lc /x/pi-observe --reap --json",
                "loaded": True,
            }
        ],
    )
    monkeypatch.setattr(
        m,
        "local_scheduler",
        lambda: {
            "schedule_yml": "/repo/scheduler/schedule.yml",
            "entry_declared": True,
            "runner": "/repo/.venv/bin/python",
            "runner_executable": False,
        },
    )
    out = io.StringIO()
    with redirect_stdout(out):
        rc = m.explain_install()
    text = out.getvalue()
    assert rc == 1, "nothing is installed; the refusal is the answer"
    assert "Nothing to install" in text
    assert "ai.estate.pi-reaper" in text
    assert "every 600s, loaded" in text
    assert "is NOT executable here" in text


def test_a_ledger_rank_does_not_overwrite_the_monitors_receipt(tmp_path, monkeypatch):
    """Measured 2026-10-24: the live receipt at ~/.estate/pi-observe/latest.json held a pytest
    run's argv and no live row -- `--friction` is a read-only rank of the door's ledger and it was
    writing the monitor's receipt on the way past. A read must not destroy the state it reads."""
    m = _observe()
    receipt = tmp_path / "latest.json"
    receipt.write_text('{"sentinel": true}\n')
    monkeypatch.setattr(m, "RECEIPT_DEFAULT", str(receipt))
    monkeypatch.setattr(m, "STATE_DEFAULT", str(tmp_path / "state.json"))
    ledger = tmp_path / "events.jsonl"
    ledger.write_text(
        json.dumps(
            {"kind": "steer", "shape": "gh run view <n>", "ts": "2026-10-24T00:00:00Z"}
        )
        + "\n"
    )
    rc = m.main(["--friction", "--friction-path", str(ledger), "--json"])
    assert rc == 0
    assert json.loads(receipt.read_text()) == {"sentinel": True}


def test_an_observation_does_write_the_receipt(tmp_path, monkeypatch):
    """The other half of the rule: a pass that looked at the machine writes what it saw."""
    m = _observe()
    receipt = tmp_path / "latest.json"
    monkeypatch.setattr(m, "RECEIPT_DEFAULT", str(receipt))
    monkeypatch.setattr(m, "STATE_DEFAULT", str(tmp_path / "state.json"))
    rc = m.main(["--live", "--sample", "0.2", "--json"])
    body = json.loads(receipt.read_text())
    assert "observed_at" in body and "live" in body and body["provenance"]["written_by"]
    assert rc in (0, 1), "2 would be BLIND: the process table could not be read"


def test_the_scheduler_state_measures_the_runner_not_the_declaration(
    tmp_path, monkeypatch
):
    """A declared cron row is a promise; an executable python is the thing that keeps it."""
    m = _observe()
    (tmp_path / "scheduler").mkdir()
    (tmp_path / "scheduler" / "schedule.yml").write_text(
        "jobs:\n  ai.estate.pi-observe:\n    cron: '*/5 * * * *'\n"
    )
    monkeypatch.setattr(m, "_repo_root", lambda: tmp_path)
    state = m.local_scheduler()
    assert state["entry_declared"] is True
    assert state["runner_executable"] is False
