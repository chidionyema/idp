"""op-verify is the only read-only cluster door an agent has. These tests run its
steps as plain scripts against a stub `kubectl`, because a door nobody can execute
outside GitHub Actions is a door nobody can prove.

Three defects are pinned here, all measured 2026-09-22 while trying to establish
whether zeroedge (#3834) had reached the cluster:

  1. The ExternalSecret table was `head -35`. kubectl sorts by namespace, the estate
     has more rows than that, and the cut landed on `edge-runtime` -- so `llm` and
     everything alphabetically after it was invisible. The question being asked was
     "did llm/ghcr-pull sync, or did the cluster's secret cap refuse it", and the
     door silently answered about a different part of the alphabet.

  2. Nothing in the workflow printed a log line, so the estate's own bar for done --
     "prove it with a real production log line" -- could not be reached through it.

  3. idp is a PUBLIC repository, so the fix for (2) must never be a raw `kubectl
     logs` tail. Only lines matching an anchored pattern may be printed. The last
     test holds that line: a pod printing a credential must not get it published.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github/workflows/op-verify.yml"

# Resolved once, absolutely: a bare "bash" in the argv is a partial executable path
# (ruff S607) -- the interpreter a test shells out to should not depend on PATH order.
BASH = shutil.which("bash") or "/bin/bash"

PROOF_STEP = "Proof of operation (a real log line, not a pod phase)"
# not SECRET_STEP: ruff S105 reads any name ending in _SECRET* as a hardcoded credential.
ES_SYNC_STEP = "ExternalSecret sync state"


def step_script(name: str) -> str:
    doc = yaml.safe_load(WORKFLOW.read_text())
    for step in doc["jobs"]["verify"]["steps"]:
        if step.get("name") == name:
            return step["run"]
    raise AssertionError(f"no step named {name!r} in {WORKFLOW}")


def run_step(
    name: str, kubectl_body: str, tmp_path: Path
) -> subprocess.CompletedProcess:
    """Run one workflow step with `kubectl` replaced by a stub on PATH."""
    binder = tmp_path / "bin"
    binder.mkdir(exist_ok=True)
    stub = binder / "kubectl"
    stub.write_text("#!/usr/bin/env bash\n" + kubectl_body)
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)

    summary = tmp_path / "summary.md"
    summary.touch()
    env = dict(os.environ)
    env["PATH"] = f"{binder}:{env['PATH']}"
    env["RUNNER_TEMP"] = str(tmp_path)
    env["GITHUB_STEP_SUMMARY"] = str(summary)
    return subprocess.run(  # noqa: S603 -- fixed argv, no shell
        [BASH, "-e", "-c", step_script(name)],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
    )


@pytest.fixture(autouse=True)
def _need_bash():
    if shutil.which("bash") is None:  # pragma: no cover - every supported host has bash
        pytest.skip("bash is required to execute a workflow step")


# --------------------------------------------------------------- proof of operation

HEALTH_LINE = '10.244.3.17 - - [22/Sep/2026 03:12:44] "GET /health HTTP/1.1" 200 -'


def test_a_serving_pod_yields_its_real_log_line(tmp_path):
    p = run_step(PROOF_STEP, f"echo {HEALTH_LINE!r}\n", tmp_path)
    assert p.returncode == 0, p.stderr
    assert "OPERATING" in p.stdout, p.stdout
    assert HEALTH_LINE in p.stdout, (
        "the door must print the real line, not a verdict about it:\n" + p.stdout
    )


def test_a_pod_with_no_matching_line_is_reported_as_built_not_operating(tmp_path):
    p = run_step(PROOF_STEP, 'echo "starting up"\n', tmp_path)
    assert p.returncode == 0, p.stderr
    assert "NO LINE" in p.stdout, p.stdout
    assert "built, not operating" in p.stdout, (
        "a missing line must say which of the two facts is missing:\n" + p.stdout
    )
    assert "OPERATING " not in p.stdout, p.stdout


def test_an_unreachable_workload_does_not_fail_the_step(tmp_path):
    """The door reports; it does not go red because a workload is down. A read-only
    snapshot that exits non-zero on the first absent pod stops printing the rest."""
    p = run_step(PROOF_STEP, "exit 1\n", tmp_path)
    assert p.returncode == 0, p.stderr
    assert "NO LINE" in p.stdout, p.stdout


def test_the_door_publishes_only_lines_matching_its_anchored_pattern(tmp_path):
    """idp is public and this log is world-readable. A pod that prints a credential
    must not have it republished: only the anchored pattern may reach the output."""
    leak = "LITELLM_MASTER_KEY=sk-not-a-real-key-0123456789abcdef"
    p = run_step(PROOF_STEP, f"echo {leak!r}\necho {HEALTH_LINE!r}\n", tmp_path)
    assert p.returncode == 0, p.stderr
    assert HEALTH_LINE in p.stdout
    assert leak not in p.stdout, "the door republished a line it was never asked for"
    assert leak not in (tmp_path / "summary.md").read_text()


# --------------------------------------------------- the secret table is not truncated


def _external_secrets_table(rows: int, tail_ns: str) -> str:
    """kubectl output shaped like the real one: header, `rows` synced rows sorted by
    namespace, and one final row in `tail_ns` which sorts last."""
    body = ["NS                 NAME              STORE          STATUS"]
    for i in range(rows):
        body.append(
            f"aaa{i:03d}            some-secret       estate-vault   SecretSynced"
        )
    body.append(f"{tail_ns:<18} ghcr-pull         ghcr-pull      SecretSyncedError")
    return "cat <<'EOF'\n" + "\n".join(body) + "\nEOF\n"


def test_a_row_past_the_old_thirty_five_line_cut_is_still_printed(tmp_path):
    p = run_step(ES_SYNC_STEP, _external_secrets_table(60, "llm"), tmp_path)
    assert p.returncode == 0, p.stderr
    assert "llm" in p.stdout and "SecretSyncedError" in p.stdout, (
        "the row the question was about fell off the end of the table:\n" + p.stdout
    )


def test_a_not_synced_row_is_surfaced_ahead_of_the_full_table(tmp_path):
    p = run_step(ES_SYNC_STEP, _external_secrets_table(60, "llm"), tmp_path)
    assert p.returncode == 0, p.stderr
    assert p.stdout.index("SecretSyncedError") < p.stdout.index("aaa000"), (
        "a failing ExternalSecret must be visible without reading 60 rows first:\n"
        + p.stdout
    )


def test_an_all_green_estate_says_so_rather_than_printing_nothing(tmp_path):
    table = "cat <<'EOF'\nNS   NAME   STORE   STATUS\nllm  ghcr-pull  ghcr-pull  SecretSynced\nEOF\n"
    p = run_step(ES_SYNC_STEP, table, tmp_path)
    assert p.returncode == 0, p.stderr
    assert "none" in p.stdout, (
        "an empty result must state the finding; a blank block is not an answer:\n"
        + p.stdout
    )
