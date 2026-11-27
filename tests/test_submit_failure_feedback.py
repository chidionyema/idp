"""Execute submit owner reporting with real shell/Python and fixture GitHub responses."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40


def execute(tmp_path, logs_available=True, wrong_head=False):
    flow = yaml.safe_load((ROOT / ".github/workflows/submit-gate.yml").read_text())
    job = flow["jobs"]["tell-the-owner"]
    bindir = tmp_path / "tools"
    bindir.mkdir()
    fake = bindir / "gh"
    fake.write_text(
        f"#!{sys.executable}\n"
        + """import json, os, pathlib, sys
a = sys.argv[1:]
if "-X" in a and a[a.index("-X")+1] == "POST":
    form = next(x for x in a if x.startswith("body="))
    body = pathlib.Path(form[6:]).read_text() if form.startswith("body=@") else form[5:]
    pathlib.Path("comment.txt").write_text(body)
elif any(x.endswith("/jobs") for x in a):
    print(json.dumps({"jobs":[{"id":101,"name":"gate / fast-gate","conclusion":"failure","head_sha":os.environ["FIXTURE_HEAD"],"check_run_url":"https://api.github.com/repos/chidionyema/idp/check-runs/101"}]}))
elif any(x.endswith("/annotations") for x in a):
    print(json.dumps([{"path":"tests/bad.py","start_line":4,"message":"Process completed with exit code 1."}]))
elif any(x.endswith("/logs") for x in a):
    if os.environ["FIXTURE_LOGS"] == "no":
        print("unavailable", file=sys.stderr)
        sys.exit(1)
    print("preamble\\n" * 40 + "FAIL ruff-fmt tests/bad.py\\nFAIL registry snapshot lags\\n::error::Process completed with exit code 1.\\nPost job cleanup.\\n" + "cleanup\\n" * 40)
else:
    raise SystemExit("Unexpected API fixture call: " + repr(a))
"""
    )
    fake.chmod(0o755)
    git = bindir / "git"
    git.write_text(
        '#!/bin/sh\nprintf "Claim: chidionyema/idp#8455\\nAgent: fixture-owner\\n"\n'
    )
    git.chmod(0o755)
    env = dict(
        os.environ,
        PATH=str(bindir) + os.pathsep + os.environ["PATH"],
        GITHUB_REPOSITORY="chidionyema/idp",
        GITHUB_RUN_ID="123",
        SHA=SHA,
        REF="submit/fixture",
        RUN="https://github.com/chidionyema/idp/actions/runs/123",
        RUNNER_TEMP=str(tmp_path),
        FIXTURE_HEAD="b" * 40 if wrong_head else SHA,
        FIXTURE_LOGS="yes" if logs_available else "no",
    )
    for step in job["steps"]:
        if "run" not in step:
            continue
        script = step["run"]
        for key, value in {"github.run_id": "123", "github.sha": SHA}.items():
            script = script.replace("${{ " + key + " }}", value)
        result = subprocess.run(
            ["bash", "-e", "-c", script],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
    return (tmp_path / "comment.txt").read_text(), job


def test_real_failures_and_annotations_are_in_owner_comment(tmp_path):
    body, job = execute(tmp_path)
    assert "FAIL ruff-fmt tests/bad.py" in body
    assert "FAIL registry snapshot lags" in body
    assert "tests/bad.py:4" in body
    assert "cleanup" not in body
    assert job["permissions"]["actions"] == "read"


def test_log_read_failure_is_unknown_and_owner_is_still_notified(tmp_path):
    body, _ = execute(tmp_path, logs_available=False)
    assert "UNKNOWN" in body
    assert "tests/bad.py:4" in body
    assert "fixture-owner" in body


def test_another_head_cannot_supply_failure_evidence(tmp_path):
    body, _ = execute(tmp_path, wrong_head=True)
    assert "UNKNOWN" in body
    assert "FAIL ruff-fmt" not in body
