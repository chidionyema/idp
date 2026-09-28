# tests/test_sandbox_sweep.py — the in-cluster sandbox sweeper's contract.
# The CronJob in platform/sandbox/vcluster/sweeper.yaml runs bin/idp-sandbox-sweep in an
# alpine/git image; these tests drive it with a local bare remote, never the network.
import pathlib
import subprocess

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin/idp-sandbox-sweep"
BRANCH = "sandbox/launch"


@pytest.fixture
def remote(tmp_path):
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    return bare


@pytest.fixture
def run(tmp_path, monkeypatch):
    token = tmp_path / "token"
    token.write_text("anything\n")

    def _run(remote, **env):
        for k in (
            "SANDBOX_EXPIRES_AT",
            "SANDBOX_LAUNCHED_AT",
            "SANDBOX_HOLD",
            "GITHUB_REPOSITORY",
            "SANDBOX_SWEEPER_TOKEN_FILE",
            "SANDBOX_BRANCH",
            "SANDBOX_RUN_REF",
            "SANDBOX_SWEEPER_REMOTE",
        ):
            monkeypatch.delenv(k, raising=False)
        monkeypatch.setenv("GITHUB_REPOSITORY", "chidionyema/idp")
        monkeypatch.setenv("SANDBOX_SWEEPER_TOKEN_FILE", str(token))
        monkeypatch.setenv("SANDBOX_SWEEPER_REMOTE", str(remote))
        for k, v in env.items():
            monkeypatch.setenv(k, str(v))
        return subprocess.run(
            ["sh", str(SCRIPT)], capture_output=True, text=True, timeout=60
        )

    return _run


def branch_files(remote):
    out = subprocess.run(
        ["git", "--git-dir", str(remote), "ls-tree", "-r", "--name-only", BRANCH],
        capture_output=True,
        text=True,
    )
    if out.returncode != 0:
        return None
    names = out.stdout.split()
    return {
        n: subprocess.run(
            ["git", "--git-dir", str(remote), "show", f"{BRANCH}:{n}"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        for n in names
    }


def test_script_parses_under_sh():
    proc = subprocess.run(["sh", "-n", str(SCRIPT)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr


def test_a_live_hold_is_never_touched(remote, run):
    proc = run(remote, SANDBOX_EXPIRES_AT="2999-01-01T00:00:00Z")
    assert proc.returncode == 0, proc.stderr
    assert "not yet" in proc.stdout
    assert branch_files(remote) is None


def test_an_expired_hold_is_ended_and_the_end_is_idempotent(remote, run):
    proc = run(
        remote,
        SANDBOX_EXPIRES_AT="2001-01-01T00:00:00Z",
        SANDBOX_LAUNCHED_AT="2001-01-01T00:00:00Z",
        SANDBOX_HOLD="4h",
    )
    assert proc.returncode == 0, proc.stderr
    files = branch_files(remote)
    assert files is not None and set(files) == {"kustomization.yaml", "state.yaml"}
    assert "state.yaml" in files["kustomization.yaml"]
    assert "demo-sandbox.yaml" not in files["kustomization.yaml"]
    state = yaml.safe_load(files["state.yaml"])
    assert state["metadata"]["namespace"] == "flux-system"
    assert state["data"]["state"] == "idle"
    assert state["data"]["expires_at"] == "2001-01-01T00:00:00Z"
    assert state["data"]["hold"] == "4h"
    again = run(remote, SANDBOX_EXPIRES_AT="2001-01-01T00:00:00Z")
    assert again.returncode == 0, again.stderr


def test_a_malformed_expiry_refuses_and_pushes_nothing(remote, run):
    proc = run(remote, SANDBOX_EXPIRES_AT="soon")
    assert proc.returncode == 2
    assert "BLIND" in proc.stdout
    assert branch_files(remote) is None


def test_a_missing_token_file_refuses_and_pushes_nothing(
    remote, run, tmp_path, monkeypatch
):
    proc = run(
        remote,
        SANDBOX_EXPIRES_AT="2001-01-01T00:00:00Z",
        SANDBOX_SWEEPER_TOKEN_FILE=str(tmp_path / "absent"),
    )
    assert proc.returncode == 2
    assert "BLIND" in proc.stdout
    assert branch_files(remote) is None
