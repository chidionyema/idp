"""The delivery ledger is the estate's own witness that pinned agent work landed.

2026-11-14: an agent reported a pushed branch, an R2 upload and full coverage for AI Studio
applet fe43cf69; none existed, and nothing in the estate noticed because the only witness was
the agent itself. These tests keep the witness independent of every agent and model.
"""

import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github/workflows/delivery-ledger.yml"
INTAKE = ROOT / ".github/workflows/genesis-aistudio-source-intake.yml"


def _wf():
    return yaml.safe_load(WF.read_text())


def test_runs_on_a_schedule_with_no_agent_or_model_in_the_loop():
    s = WF.read_text()
    on = _wf()[True]
    assert on["schedule"][0]["cron"]
    assert "workflow_dispatch" in on
    for word in (
        "llm.",
        "anthropic",
        "openai",
        "gemini-",
        "minimax",
        "estate_invoke",
        "sb start",
    ):
        assert word not in s.lower(), word


def test_only_trusted_main_obtains_the_app_token():
    s = WF.read_text()
    assert "if: github.ref == 'refs/heads/main'" in s
    assert "pull_request" not in s
    assert "persist-credentials: false" in s
    assert "lane: agent-workforce" in s


def test_never_writes_anywhere():
    s = WF.read_text()
    assert _wf()["permissions"]["contents"] == "read"
    for word in (
        "git push",
        "git commit",
        "--method POST",
        "-X POST",
        "--method PUT",
        "upload-artifact",
    ):
        assert word not in s, word


def test_the_pin_is_read_from_the_intake_not_copied():
    s = WF.read_text()
    for sha in re.findall(r"[0-9a-f]{64}", INTAKE.read_text()):
        assert sha not in s, "pin duplicated into the ledger"
    assert re.search(r"releases/assets/\d+", s) is None


def test_the_pin_extraction_resolves_against_the_real_intake():
    step = next(st for st in _wf()["jobs"]["ledger"]["steps"] if st.get("id") == "pin")
    out = ROOT / ".delivery-ledger-test-output"
    try:
        r = subprocess.run(
            ["bash", "-c", step["run"]],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env={"GITHUB_OUTPUT": str(out), "PATH": "/usr/bin:/bin"},
            timeout=30,
        )
        assert r.returncode == 0, r.stderr
        got = dict(line.split("=", 1) for line in out.read_text().splitlines())
    finally:
        out.unlink(missing_ok=True)
    assert got["asset"].isdigit()
    assert re.fullmatch(r"[0-9a-f]{64}", got["sha"])
    assert got["lane"].startswith("lane/aistudio-")
    assert got["sha"] in INTAKE.read_text() and got["asset"] in INTAKE.read_text()


def test_every_check_can_fail_and_reaches_the_founder_on_edge():
    s = WF.read_text()
    for check in ("FAIL D1", "FAIL D2", "FAIL D3"):
        assert check in s
    assert 'test -z "$red"' in s
    assert "never-run" in s, "an intake that never ran must grade red, not pass"
    assert "SEED_HERMES_TELEGRAM_BOT_TOKEN" in s
    assert "steps.prev.outputs.conclusion == 'failure'" in s, (
        "recovery must be announced"
    )
    assert 'test "$code" = 200' in s, (
        "a Telegram send that fails must not pass silently"
    )
