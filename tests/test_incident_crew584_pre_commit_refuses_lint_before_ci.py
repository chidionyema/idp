"""crew#584 CP-B (LAW 45): a lint error is refused at git commit, not 11 minutes later in CI.

Incident 2026-08-29: idp#659 lost a full CI cycle to shellcheck SC2034 (an unused loop variable
in bin/idp-cloud) that `shellcheck -S warning` reports in well under a second. The repo had no
.githooks/pre-commit, so nothing ran on the laptop. This proves the hook refuses that exact
class in a scratch repo, and lets a clean commit through.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, ".githooks", "pre-commit")

BAD_SH = "#!/usr/bin/env bash\nset -euo pipefail\nfor i in 1 2; do echo x; done\n"  # SC2034 unused i
GOOD_SH = "#!/usr/bin/env bash\nset -euo pipefail\nfor _ in 1 2; do echo x; done\n"
BAD_PY = "import os\ndef f(:\n    pass\n"


def _repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    os.makedirs(tmp_path / "bin")
    return tmp_path


def _hook(repo, rel, body):
    p = repo / rel
    p.write_text(body)
    p.chmod(0o755)
    subprocess.run(["git", "-C", str(repo), "add", rel], check=True)
    env = dict(os.environ, ESTATE_HOOKS=str(repo / "no-such-dir"))
    return subprocess.run([HOOK], cwd=repo, env=env, capture_output=True, text=True, timeout=60)


def test_hook_is_executable_and_parses():
    assert os.access(HOOK, os.X_OK)
    subprocess.run(["bash", "-n", HOOK], check=True)


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="shellcheck not installed")
def test_the_sc2034_that_cost_a_ci_cycle_is_refused_at_commit(tmp_path):
    out = _hook(_repo(tmp_path), "bin/idp-thing", BAD_SH)
    assert out.returncode != 0
    assert "SC2034" in out.stdout + out.stderr, out.stdout + out.stderr


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="shellcheck not installed")
def test_a_clean_script_commits(tmp_path):
    out = _hook(_repo(tmp_path), "bin/idp-thing", GOOD_SH)
    assert out.returncode == 0, out.stdout + out.stderr


def test_a_python_syntax_error_is_refused_at_commit(tmp_path):
    out = _hook(_repo(tmp_path), "bad.py", BAD_PY)
    assert out.returncode != 0, out.stdout + out.stderr


def test_skip_knob_lets_a_wip_commit_through(tmp_path):
    repo = _repo(tmp_path)
    (repo / "bin" / "idp-thing").write_text(BAD_SH)
    subprocess.run(["git", "-C", str(repo), "add", "bin/idp-thing"], check=True)
    out = subprocess.run([HOOK], cwd=repo, env=dict(os.environ, PRE_COMMIT_SKIP="1"), capture_output=True, text=True)
    assert out.returncode == 0


if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", "-q", __file__]))
