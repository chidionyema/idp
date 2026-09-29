"""bin/litellm-local takes vendor keys from Bitwarden (ESO human-* secrets in the llm namespace).

Runs the script's own loader block under macOS /bin/bash 3.2 -- the shell launchd uses, and the
one that mis-parsed the first version -- against a fake kubectl. No real secret is read.
"""

from __future__ import annotations

import base64
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "bin" / "litellm-local").read_text()
START = "  # Vendor keys from Bitwarden"
END = 'vendor lanes will be dropped"\n'
LOADER = SCRIPT[SCRIPT.index(START) : SCRIPT.index(END) + len(END)]
BASH = "/bin/bash" if Path("/bin/bash").exists() else "bash"
VENV_PY = Path.home() / ".cache/estate-tools/litellm-venv/bin/python"
PY = str(VENV_PY) if VENV_PY.exists() else "python3"


def _b64(s: str) -> str:
    return base64.b64encode(s.encode()).decode()


NASTY = "fake-ds 'q' \"dq\" $HOME `x`"
SECRETS = {
    "items": [
        {
            "metadata": {"name": "human-deepseek"},
            "data": {"DEEPSEEK_API_KEY": _b64(NASTY)},
        },
        {
            "metadata": {"name": "human-groq"},
            "data": {"GROQ_API_KEY_2": _b64("g2"), "bad-name": _b64("x")},
        },
        {"metadata": {"name": "github-app"}, "data": {"PEM": _b64("must-not-load")}},
    ]
}


def _run(
    tmp_path: Path, kubectl: str | None, probe: str
) -> subprocess.CompletedProcess:
    home = tmp_path / "home"
    (home / ".rd" / "bin").mkdir(parents=True)
    if kubectl is not None:
        k = home / ".rd" / "bin" / "kubectl"
        k.write_text(kubectl)
        k.chmod(0o755)
    (tmp_path / "secrets.json").write_text(json.dumps(SECRETS))
    (tmp_path / "loader.sh").write_text(LOADER)
    # the loader calls "$VENV/bin/python": point it at a real interpreter
    venv = tmp_path / "venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").symlink_to(shutil.which(PY) or PY)
    prog = f"set -euo pipefail; VENV={venv}; f() {{ source {tmp_path}/loader.sh; {probe}; }}; f"
    env = {"HOME": str(home), "PATH": "/usr/bin:/bin"}
    return subprocess.run(
        [BASH, "-c", prog], env=env, capture_output=True, text=True, timeout=60
    )


def test_human_secrets_load_exactly_and_nothing_else(tmp_path):
    r = _run(
        tmp_path,
        f"#!/bin/sh\ncat {tmp_path}/secrets.json\n",
        'printf "%s\\n%s\\n%s\\n" "$DEEPSEEK_API_KEY" "$GROQ_API_KEY_2" "${PEM:-unset}"',
    )
    assert r.returncode == 0, r.stderr
    lines = r.stdout.splitlines()
    assert lines[-3:] == [NASTY, "g2", "unset"]
    assert "keys   bitwarden: 2 DEEPSEEK_API_KEY,GROQ_API_KEY_2" in lines


@pytest.mark.parametrize(
    "kubectl", ["#!/bin/sh\nexit 1\n", None], ids=["kubectl-fails", "no-kubectl"]
)
def test_unreadable_vault_warns_and_does_not_abort(tmp_path, kubectl):
    r = _run(tmp_path, kubectl, 'echo "DS=${DEEPSEEK_API_KEY:-unset}"')
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines()[-1] == "DS=unset"
    assert "warn  bitwarden keys unreadable" in r.stdout


def test_loader_leaves_no_helper_variables(tmp_path):
    r = _run(
        tmp_path,
        f"#!/bin/sh\ncat {tmp_path}/secrets.json\n",
        'echo "${bw_py:-unset}|${bw_env:-unset}"',
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines()[-1] == "unset|unset"
