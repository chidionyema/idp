"""crew#412, 2026-08-28: a second `gh workflow run oke-check.yml` while one dispatch was pending
CANCELLED the first (run 33172458777 catalogue-roll, displaced by diagnose 33172481714 twenty
seconds later). GitHub keeps exactly one pending run per concurrency group and has no queue-depth
setting, so bin/idp-oke-dispatch is the guard: it refuses (exit 75) while a workflow_dispatch run
is pending, refuses an unknown playbook (exit 64) and dispatches otherwise. `gh` is a stub on
PATH; no network is opened."""

import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-oke-dispatch"
WORKFLOW = ROOT / ".github" / "workflows" / "oke-check.yml"


def _stub_gh(tmp_path: Path, pending_ids: str) -> dict:
    """A `gh` that answers `run list` with PENDING_IDS and records every `workflow run`."""
    log = tmp_path / "gh.log"
    gh = tmp_path / "gh"
    gh.write_text(
        "#!/usr/bin/env bash\n"
        f'echo "$@" >> "{log}"\n'
        'if [ "$1" = run ] && [ "$2" = list ]; then\n'
        '  case "$*" in *"--status queued"*) printf "%s" "$PENDING_IDS";; *) :;; esac\n'
        "  exit 0\n"
        "fi\n"
        "exit 0\n"
    )
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    env = dict(os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}", PENDING_IDS=pending_ids)
    return {"env": env, "log": log}


def _run(args, env):
    return subprocess.run([str(SCRIPT), *args], env=env, capture_output=True, text=True, timeout=30)


def test_workflow_keeps_one_pending_run_per_group():
    text = WORKFLOW.read_text()
    assert "cancel-in-progress: false" in text, "the guard exists because the group does not cancel in progress"


def test_refuses_while_a_dispatch_is_pending(tmp_path):
    stub = _stub_gh(tmp_path, "33172458777\n")
    r = _run(["diagnose"], stub["env"])
    assert r.returncode == 75, r.stdout + r.stderr
    assert "33172458777" in r.stdout and "cancel" in r.stdout
    assert "workflow run" not in stub["log"].read_text()


def test_dispatches_when_nothing_is_pending(tmp_path):
    stub = _stub_gh(tmp_path, "")
    r = _run(["catalogue-roll"], stub["env"])
    assert r.returncode == 0, r.stdout + r.stderr
    logged = stub["log"].read_text()
    assert "workflow run oke-check.yml --ref main -f mode=break-glass -f playbook=catalogue-roll" in logged


def test_unknown_playbook_is_refused_before_any_gh_call(tmp_path):
    stub = _stub_gh(tmp_path, "")
    r = _run(["no-such-playbook"], stub["env"])
    assert r.returncode == 64
    assert not stub["log"].exists(), "gh was called before the playbook name was checked"
