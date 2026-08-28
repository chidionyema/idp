"""crew#586, run 33198014582 (2026-08-28): the first live Conscience run graded 5/7 with two rows
BLIND and shipped nothing: no founder line, no issue, no page, because every later step was gated
on `rc != 2`. Both BLIND rows were the runner's, not the estate's: `research` had no GH_TOKEN so
the crew#583 clock had no Date header; `secure` ran `security dump-keychain` on ubuntu, where the
binary does not exist. Rung 4, both ways: the grade step carries the token; a host with no
keychain binary is zero keychain items, an absent vault is BLIND and never zero; the founder line
names BLIND rows apart from red ones; every surface step runs whenever a receipt exists, and the
job still ends red on BLIND."""
import importlib.util
import os
import pathlib
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "conscience.yml"
GATE = ROOT / "bin" / "static-secret-gate"


def _gate():
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader("static_secret_gate", loader=None))
    mod.__file__ = str(GATE)
    exec(compile(GATE.read_text(), str(GATE), "exec"), mod.__dict__)
    return mod


def test_grade_step_carries_the_api_clock_token():
    steps = yaml.safe_load(WF.read_text())["jobs"]["grade"]["steps"]
    grade = next(s for s in steps if s.get("id") == "grade")
    assert grade["env"]["GH_TOKEN"] == "${{ github.token }}"


def test_every_surface_step_runs_on_a_receipt_and_blind_still_fails_the_job():
    text = WF.read_text()
    assert '[ "$rc" -ne 2 ]' in text
    for step in ("receipt to the collector", "one issue per red tenet", "founder line", "portal page"):
        assert step in text
    assert "steps.grade.outputs.rc != '2'" not in text
    assert text.count("!cancelled() && steps.grade.outputs.rc != ''") >= 5


def test_founder_line_names_blind_rows_apart_from_red():
    text = WF.read_text()
    assert "BLIND (not measurable, never green): $blinds" in text
    assert 't["ok"] is None' in text and 't["ok"] is False' in text


def test_no_security_binary_is_zero_keychain_items_not_blind(monkeypatch):
    g = _gate()
    monkeypatch.delenv("STATIC_SECRET_GATE_ROOT", raising=False)

    def no_binary(*a, **k):
        raise FileNotFoundError("security")
    monkeypatch.setattr(g.subprocess, "run", no_binary)
    assert g.keychain_entries() == []


def test_a_keychain_that_cannot_be_dumped_is_still_blind(monkeypatch):
    g = _gate()
    monkeypatch.delenv("STATIC_SECRET_GATE_ROOT", raising=False)

    def dies(*a, **k):
        raise subprocess.TimeoutExpired("security", 30)
    monkeypatch.setattr(g.subprocess, "run", dies)
    assert g.keychain_entries() is None


def test_an_absent_vault_is_blind_never_zero(tmp_path):
    env = {"STATIC_SECRET_GATE_ROOT": str(tmp_path), "ESTATE_CODE": str(tmp_path), "ESTATE_SECRETS": str(tmp_path / "nowhere"), "PATH": os.environ["PATH"]}
    p = subprocess.run([sys.executable, str(GATE)], capture_output=True, text=True, env=env)
    assert p.returncode == 2, p.stdout
    assert "BLIND   vault:" in p.stdout and "absent vault is not an empty one" in p.stdout
    (tmp_path / "vault" / "secrets").mkdir(parents=True)
    env["ESTATE_SECRETS"] = str(tmp_path / "vault")
    p = subprocess.run([sys.executable, str(GATE)], capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stdout
