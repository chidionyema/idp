"""The existing Greenlane failure workflow delivers all errors in one pass.

No GitHub auth, no real logs, no new workflow or feedback database. The exact
YAML step runs with a fake gh CLI so duplicate agent archaeology does not
silently reappear in the first-failure-only implementation.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import textwrap

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/lane-feedback.yml"

FAKE_GH = textwrap.dedent(r"""
#!/usr/bin/env python3
import json, os, sys
q = sys.argv[2] if len(sys.argv) > 2 else ""
if "/actions/runs/" in q and q.endswith("/jobs?per_page=100"):
    jobs = [
      {"id": 101, "name": "dof-gate", "conclusion": "failure",
       "html_url": "https://github.com/chidionyema/idp/actions/jobs/101",
       "steps": [{"name": "Run base and DoF", "conclusion": "failure"}]},
      {"id": 102, "name": "security-scan", "conclusion": "failure",
       "html_url": "https://github.com/chidionyema/idp/actions/jobs/102",
       "steps": [{"name": "scan", "conclusion": "failure"}]},
      {"id": 103, "name": "ci-success", "conclusion": "failure",
       "html_url": "https://github.com/chidionyema/idp/actions/jobs/103",
       "steps": [{"name": "aggregate", "conclusion": "failure"}]}
    ]
    print(json.dumps({"total_count": len(jobs), "jobs": jobs}))
    sys.exit(0)
if q.endswith("/actions/jobs/101/logs"):
    print("2026-11-08 ##[error]REFUSED dof-gate incident estate-doors remains open")
    sys.exit(0)
if q.endswith("/actions/jobs/102/logs"):
    if os.environ.get("SIMULATE_MISSING_LOG") == "1":
        print("403", file=sys.stderr)
        sys.exit(1)
    print("error: scan unavailable password=supersecret Bearer opaque-secret-value")
    sys.exit(0)
if q.endswith("/actions/jobs/103/logs"):
    print("error: ci-success requires upstream jobs to pass")
    sys.exit(0)
print("unexpected command: " + " ".join(sys.argv), file=sys.stderr)
sys.exit(2)
""")


def _exercise(tmp_path: pathlib.Path, missing_log: bool = False):
    raw = yaml.safe_load(WORKFLOW.read_text())
    steps = raw["jobs"]["post-error"]["steps"]
    script = next(s["run"] for s in steps if "Build one source-bound packet" in s["name"])
    mock = tmp_path / "gh"
    mock.write_text(FAKE_GH.lstrip())
    mock.chmod(0o755)
    output = tmp_path / "output"
    output.write_text("")
    env = {**os.environ, "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"],
           "RUN_ID": "123", "REPO": "chidionyema/idp", "SHA": "ab" * 20,
           "GITHUB_OUTPUT": str(output),
           "SIMULATE_MISSING_LOG": "1" if missing_log else "0"}
    result = subprocess.run(["bash", "-c", script], cwd=tmp_path, env=env,
                            capture_output=True, text=True, timeout=25)
    return result, (tmp_path / "feedback.md").read_text(), output.read_text()


def _packet(md: str):
    raw = md.split("~~~json", 1)[1].split("~~~", 1)[0]
    return json.loads(raw)


def test_every_failed_job_and_step_present_with_source_and_repair(tmp_path):
    result, md, output = _exercise(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "sha=" + "ab" * 20 in output
    packet = _packet(md)
    assert packet["contract"] == "genesis.greenlane.failure-packet.v1"
    assert packet["head_sha"] == "ab" * 20
    assert packet["complete"] is True
    assert packet["failed_job_count"] == 3
    assert {r["job"] for r in packet["failures"]} == {
        "dof-gate", "security-scan", "ci-success"}
    assert {r["step"] for r in packet["failures"]} == {
        "Run base and DoF", "scan", "aggregate"}
    assert {r["failure_class"] for r in packet["failures"]} == {
        "DOF_SCOPE", "SECURITY_SCAN", "AGGREGATOR"}
    assert all(r["fingerprint"] and r["url"] and r["next_estate_action"]
               for r in packet["failures"])
    assert "bin/lane-error" not in md
    assert "supersecret" not in md
    assert "opaque-secret-value" not in md
    assert "[REDACTED]" in md
    digest = hashlib.sha256(json.dumps(packet, sort_keys=True).encode()).hexdigest()
    assert f"packet_sha256: {digest}" in md


def test_missing_job_log_is_partial_not_a_fake_complete_explanation(tmp_path):
    result, md, _ = _exercise(tmp_path, missing_log=True)
    assert result.returncode == 0, result.stderr
    packet = _packet(md)
    assert packet["complete"] is False
    assert "PARTIAL" in md
    assert any(e["evidence_state"] == "LOG_UNAVAILABLE" for e in packet["failures"])
    assert all(e["url"] for e in packet["failures"])


def test_same_workflow_publishes_to_existing_commit_comment_without_new_bus():
    raw = yaml.safe_load(WORKFLOW.read_text())
    steps = raw["jobs"]["post-error"]["steps"]
    publish = next(s["run"] for s in steps if "Publish once" in s["name"])
    assert "commits/$SHA/comments" in publish
    assert "GENESIS_FAILURE_PACKET run=$RUN_ID" in publish
    assert "feedback.md" in publish
    assert "NATS" not in publish
