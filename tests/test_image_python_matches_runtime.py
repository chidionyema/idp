"""A Python image built in one interpreter and run in another loads no compiled extension.

Measured 2026-10-13: platform/jit/Dockerfile installed its packages on python:3.12-slim and ran
them on distroless/python3-debian12, which is Debian 12's Python 3.11. cffi's backend landed as
_cffi_backend.cpython-312-*.so, the broker died importing cryptography, and jit-broker sat in
CrashLoopBackOff for days (1112 restarts) while the Flux row reported only "stalled".

Every Dockerfile that copies a python:X build into a distroless runtime must build on the
runtime's own X.
"""

from __future__ import annotations

import os
import re
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The Python each distroless runtime ships: its Debian release's python3.
RUNTIME_PYTHON = {"debian12": "3.11"}


def _pairs() -> list[tuple[str, str, str]]:
    files = subprocess.run(
        ["git", "ls-files", "*Dockerfile*"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    out = []
    for f in files:
        with open(os.path.join(ROOT, f)) as fh:
            text = fh.read()
        build = re.search(r"(?mi)^FROM\s+python:(\d+\.\d+)", text)
        run = re.search(r"(?mi)^FROM\s+\S*distroless/python3-(debian\d+)", text)
        if build and run:
            out.append((f, build.group(1), run.group(1)))
    return out


def test_the_jit_broker_is_one_of_the_pairs_graded():
    assert "platform/jit/Dockerfile" in [f for f, _, _ in _pairs()]


@pytest.mark.parametrize(("dockerfile", "build", "runtime"), _pairs())
def test_build_python_is_the_runtime_python(dockerfile, build, runtime):
    assert runtime in RUNTIME_PYTHON, (
        f"{dockerfile}: add distroless {runtime}'s Python to RUNTIME_PYTHON"
    )
    assert build == RUNTIME_PYTHON[runtime], (
        f"{dockerfile}: builds on python:{build} but distroless/python3-{runtime} runs "
        f"{RUNTIME_PYTHON[runtime]}; compiled extensions (cffi, pyyaml) will not import"
    )
