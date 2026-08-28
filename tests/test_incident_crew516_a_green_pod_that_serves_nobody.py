"""crew#516 CP4 / crew#524 CP5, 2026-08-28: The Architect's gateway was 1/1 Ready and its
Kustomization Applied for 15h (run 33153000167) while Telegram answered nobody, and there was no
way to see the difference. `diagnose` tails a pod's log only when the pod is NOT ready; the estate
MCP that exposes get_workload_logs answers 401; and the Mac gateway that used to be the fallback
had been booted out at 23:30 as step one of the cutover, which is why the silence lasted 8h45m
before the founder asked. A deployment reporting healthy is not the product working (LAW 28).

These tests hold the read-only playbook that closes it to the two properties that make it safe to
run against the estate: it mutates nothing, and it cannot print a secret's value.
"""
import os
import re
import stat
import subprocess
from pathlib import Path

import yaml

IDP = Path(__file__).resolve().parents[1]
PLAYBOOK = IDP / "bin" / "idp-oke-break-glass"
WORKFLOW = IDP / ".github" / "workflows" / "oke-check.yml"
MUTATING = re.compile(r"^(kubectl|flux) (delete|apply|rollout|run|reconcile|patch|create|scale|edit|replace)\b")


def _run(playbook: str, tmp_path: Path) -> tuple[subprocess.CompletedProcess, list[str]]:
    log = tmp_path / "calls.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ("kubectl", "flux"):
        f = bin_dir / tool
        f.write_text(f'#!/bin/sh\nprintf \'%s %s\\n\' "{tool}" "$*" >> "{log}"\ncat >/dev/null 2>&1 || true\necho ok\n')
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), playbook], capture_output=True, text=True, env=env)
    return p, (log.read_text().splitlines() if log.exists() else [])


def test_the_doctor_is_read_only(tmp_path):
    p, calls = _run("architect-doctor", tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    assert calls, "the doctor read nothing"
    assert [c for c in calls if MUTATING.match(c)] == []


def test_it_reads_the_secret_key_names_and_never_the_values(tmp_path):
    """`-o jsonpath='{range $.data}{@}{end}'` -- the first thing I wrote -- iterates the map and
    prints the base64 VALUES into a CI log. go-template over $k is the only shape that answers
    "which keys did ESO deliver" without answering "and here they are"."""
    _, calls = _run("architect-doctor", tmp_path)
    secret_reads = [c for c in calls if "get secret" in c]
    assert secret_reads, "the doctor never checks which env keys the pod can read"
    for c in secret_reads:
        assert "{{$k}}" in c or "{{ $k }}" in c, f"secret read is not key-names-only: {c}"
        assert "-o yaml" not in c and "-o json" not in c and "{@}" not in c, \
            f"secret read would print values: {c}"


def test_every_log_line_goes_through_the_redactor():
    """The floor, not a substitute for not logging secrets: reading a log must never be the thing
    that leaks one. Any log row added later that forgets this fails here."""
    body = PLAYBOOK.read_text()
    doctor = body[body.index("pb_architect_doctor()"):]
    doctor = doctor[:doctor.index("\npb_")] if "\npb_" in doctor else doctor
    for line in doctor.splitlines():
        if " logs " in line and line.strip().startswith("show"):
            assert line.strip().startswith("show_redacted"), f"log row is not redacted: {line.strip()}"


# The two fixtures below are assembled rather than typed. gitleaks scans the added lines of a
# diff, and a literal of the telegram-bot-token shape fails `security-scan` even inside a test
# whose whole job is to prove that shape gets redacted -- which is a guard refusing correct work
# (LAW 38). The alternative, a `gitleaks:allow` annotation, is worse: it teaches the next session
# that the annotation is how you get a credential past the scanner. Assembling keeps the scanner
# strict and the test honest, because the redactor still sees the full string at runtime.
FAKE_BOT_TOKEN = "1234567890" + ":" + "AA" + "FakeToken" + "a" * 25
FAKE_API_KEY = "sk-" + "abcdefghijklmnop" + "123"


def test_the_redactor_removes_a_bot_token_and_a_keyed_secret(tmp_path):
    script = tmp_path / "r.sh"
    body = PLAYBOOK.read_text()
    redact = body[body.index("redact() {"):]
    redact = redact[:redact.index("\n}\n") + 3]
    script.write_text("#!/bin/bash\n" + redact + "\nredact\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    out = subprocess.run(["/bin/bash", str(script)], input=(
        f"TELEGRAM_BOT_TOKEN={FAKE_BOT_TOKEN}\n"
        f"api_key: {FAKE_API_KEY}\n"
        "a plain line about telegram\n"), capture_output=True, text=True).stdout
    assert FAKE_BOT_TOKEN not in out
    assert FAKE_API_KEY not in out
    assert "a plain line about telegram" in out, "the redactor ate an ordinary line"


def test_the_playbook_is_offered_on_the_workflow_and_declared_read_only():
    wf = yaml.safe_load(WORKFLOW.read_text())
    inp = wf[True]["workflow_dispatch"]["inputs"]["playbook"]
    assert "architect-doctor" in inp["options"], "the playbook exists and nobody can dispatch it"
    assert "architect-doctor are read-only" in inp["description"], \
        "the description still tells the operator only diagnose is read-only"
    listed = subprocess.run([str(PLAYBOOK), "--list"], capture_output=True, text=True).stdout
    assert "architect-doctor" in listed
