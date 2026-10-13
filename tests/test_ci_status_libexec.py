"""platform/estate/libexec/ci-status.py against a fake `gh` on PATH."""

import json
import pathlib
import subprocess
import sys

SCRIPT = (
    pathlib.Path(__file__).resolve().parents[1] / "platform/estate/libexec/ci-status.py"
)

FAKE_GH = """#!/usr/bin/env python3
import json, sys
path = sys.argv[2]
if path.endswith("/commits/main"):
    print(json.dumps({"sha": "a1df4b42c0ffee", "commit": {"message": "head of main\\n\\nbody"}}))
elif "/check-runs" in path:
    print(json.dumps({"check_runs": [
        {"name": "lint", "conclusion": "success"},
        {"name": "greenlane", "conclusion": "failure", "html_url": "u"},
        {"name": "e2e", "conclusion": None},
    ]}))
else:
    sys.exit(1)
"""


def _run(tmp_path, *args):
    gh = tmp_path / "gh"
    gh.write_text(FAKE_GH)
    gh.chmod(0o755)
    env = {"PATH": f"{tmp_path}:/usr/bin:/bin"}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def test_no_pr_or_sha_reports_the_head_of_main(tmp_path):
    r = _run(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    body = json.loads(r.stdout)
    assert body["sha"] == "a1df4b42"
    assert body["branch"] == "main"
    assert body["title"] == "head of main"


def test_the_summary_is_one_sayable_sentence(tmp_path):
    body = json.loads(_run(tmp_path).stdout)
    assert body["summary"] == "CI on main: 1 passed, 1 failed: greenlane."
    assert body["failed"] == 1 and body["running"] == 1
