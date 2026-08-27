"""Incident test, crew#504 CP7: closed-as-blocked PRs were forgotten until a person remembered.

Both ways: every Blocked-by key landed -> wake; one key still open -> sleep; no Blocked-by line ->
nothing; repo at the cap -> capped, not woken; a free-text key wakes only via --resolved.
"""
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(HERE, "bin", "idp-wake-blocked")
from importlib.machinery import SourceFileLoader  # noqa: E402

spec = importlib.util.spec_from_file_location("wake", BIN, loader=SourceFileLoader("wake", BIN))
wake = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wake)

PRS = [
    {"number": 1, "merged_at": None, "body": "x\nBlocked-by: idp#400\n"},
    {"number": 2, "merged_at": None, "body": "Blocked-by: idp#400, crew#999"},
    {"number": 3, "merged_at": None, "body": "closed as idle, no line"},
    {"number": 4, "merged_at": None, "body": "Blocked-by: secret signoz-root"},
    {"number": 5, "merged_at": "2026-08-27T00:00:00Z", "body": "Blocked-by: idp#400"},
]


def _landed(k):
    return {"idp#400": True, "crew#999": False}.get(k)


def _by(actions):
    return {a["number"]: a for a in actions}


def test_wake_sleep_and_silence():
    got = _by(wake.plan(PRS, _landed, open_count=3, resolved=set()))
    assert got[1]["action"] == "wake" and got[1]["landed"] == ["idp#400"]
    assert got[2]["action"] == "sleep" and got[2]["waiting"] == ["crew#999"]
    assert 3 not in got and 5 not in got
    assert got[4]["action"] == "sleep"


def test_free_text_key_wakes_only_when_resolved():
    got = _by(wake.plan(PRS, _landed, open_count=3, resolved={"secret signoz-root"}))
    assert got[4]["action"] == "wake"


def test_cap_holds_the_wake():
    got = _by(wake.plan(PRS, _landed, open_count=10, resolved=set()))
    assert got[1]["action"] == "capped" and got[1]["open"] == 10


def test_cli_offline_dry_run(tmp_path):
    f = tmp_path / "pulls.json"
    f.write_text(json.dumps(PRS))
    r = subprocess.run([sys.executable, BIN, "--pulls", str(f), "--open", "3", "--landed", "idp#400", "--dry-run"],
                       capture_output=True, text=True, timeout=60, check=False)
    assert r.returncode == 0, r.stderr
    assert "wake-blocked: 3 sleeping, 1 woke, 0 capped, 0 errors, open=3 cap=10" in r.stdout


def test_gone_head_is_skipped_not_woken():
    prs = [{"number": 9, "merged_at": None, "body": "Blocked-by: idp#400", "head": {"repo": None}}]
    got = _by(wake.plan(prs, _landed, open_count=1, resolved=set()))
    assert got[9]["action"] == "skip"


def test_one_failing_wake_does_not_skip_the_rest(monkeypatch, tmp_path, capsys):
    calls = []

    def fake_wake(repo, number, landed):
        calls.append(number)
        if number == 1:
            raise RuntimeError("gh api PUT: 422 head branch gone")
        return "branch updated from base"

    two = [{"number": 1, "merged_at": None, "body": "Blocked-by: idp#400"},
           {"number": 7, "merged_at": None, "body": "Blocked-by: idp#400"}]
    monkeypatch.setattr(wake, "wake", fake_wake)
    monkeypatch.setattr(wake, "gh", lambda *a: json.dumps([two]) if "--paginate" in a else json.dumps([]))
    monkeypatch.setattr(wake, "ref_landed", lambda k: True)
    monkeypatch.setattr(sys, "argv", ["idp-wake-blocked", "--repo", "o/r"])
    assert wake.main() == 0
    out = capsys.readouterr().out
    assert calls == [1, 7]
    assert '"action": "error"' in out and "1 woke, 0 capped, 1 errors" in out
