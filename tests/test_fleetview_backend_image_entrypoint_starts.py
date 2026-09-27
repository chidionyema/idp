"""The fleetview-backend image's own ENTRYPOINT must start both listeners.

2026-09-27: the catalogue Deployment never went Ready. Its fleetview-backend sidecar exited 2 on
every start with "can't open file '/app/backstage/plugins/fleetview-backend/src/serve.py'": the
src-layout move (2e364b4b) put serve.py under src/fleetview_backend/ and the Dockerfile kept the
old path. Behind that, the two-port start it would have reached called
`uvicorn.Server(configs=[...])`, which uvicorn has never accepted, so the pod would have
crash-looped on a TypeError next.

This runs the ENTRYPOINT argv as written in fleetview-backend.Dockerfile (with /app mapped to this
checkout, the ports moved off the ones a local board may hold, and python3 resolved to this
interpreter) and asks both listeners for /healthz, the thing the kubelet's probe does.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "fleetview-backend.Dockerfile"

pytest.importorskip("fastapi")
pytest.importorskip("uvicorn")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _image_command() -> tuple[list[str], dict[str, str]]:
    argv: list[str] = []
    env: dict[str, str] = {}
    for line in DOCKERFILE.read_text().splitlines():
        if line.startswith("ENTRYPOINT "):
            argv = json.loads(line[len("ENTRYPOINT ") :])
        elif line.startswith("ENV "):
            k, _, v = line[len("ENV ") :].partition("=")
            env[k.strip()] = v.strip()
    assert argv, "fleetview-backend.Dockerfile has no ENTRYPOINT"
    return argv, env


def _get(port: int) -> int:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2) as r:
        return r.status


def test_the_image_entrypoint_answers_healthz_on_both_ports(tmp_path):
    argv, image_env = _image_command()
    main_port, executor_port = _free_port(), _free_port()
    ports = {"18790": str(main_port), "8091": str(executor_port)}
    cmd = [
        sys.executable
        if a == "python3"
        else ports.get(a, a.replace("/app/", f"{ROOT}/"))
        for a in argv
    ]
    env = dict(os.environ)
    env.pop("NATS_URL", None)
    env.update({k: v.replace("/app/", f"{ROOT}/") for k, v in image_env.items()})
    env["ESTATE_DB"] = str(tmp_path / "estate.db")
    proc = subprocess.Popen(
        cmd,
        env=env,
        cwd=str(tmp_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        got: dict[int, int] = {}
        deadline = time.time() + 60
        while time.time() < deadline and len(got) < 2 and proc.poll() is None:
            for port in (main_port, executor_port):
                if port not in got:
                    try:
                        got[port] = _get(port)
                    except OSError:
                        pass
            time.sleep(0.5)
        if proc.poll() is not None:
            pytest.fail(
                f"ENTRYPOINT exited {proc.returncode}:\n{proc.stdout.read()[-2000:]}"
            )
        assert got == {main_port: 200, executor_port: 200}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
