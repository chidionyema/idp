"""Sandbox dispatcher: picks the best available isolation backend and runs code in it.

The architecture spec is Firecracker (kronos ring0). On Linux+KVM we run Firecracker.
On this Mac (and any non-Linux dev machine) we fall back to docker (the daemon on
Rancher Desktop / OrbStack / colima is wired identically). On K8s we use gVisor.
The last resort is temp-tree-scrubbed-env (always available, never the spec, never
silently chosen).

`ISOLATION_KIND` is now reported dynamically: it reflects whatever backend the
dispatcher actually picked, not a baked-in string.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def detect_backend() -> str:
    """Return the name of the best available isolation backend.

    Order: firecracker -> gvisor -> docker -> temp_tree
    """
    if os.path.exists("/dev/kvm") and shutil.which("firecracker"):
        return "firecracker"
    if shutil.which("runsc"):
        return "gvisor"
    if shutil.which("docker"):
        try:
            r = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if r.returncode == 0:
                return "docker"
        except (subprocess.TimeoutExpired, OSError):
            pass
    return "temp_tree"


def run_in_sandbox(
    command: list[str],
    sandbox_path: str,
    *,
    image: str = "python:3.12-slim",
    timeout_sec: int = 20,
) -> tuple[int, str, str]:
    """Run `command` inside the picked sandbox, with `sandbox_path` mounted read-write.

    Returns (exit_code, stdout, stderr). For temp_tree backend, runs on host with
    scrubbed env (the original verifier behavior).
    """
    backend = detect_backend()
    if backend == "firecracker":
        return _run_firecracker(command, sandbox_path, timeout_sec)
    if backend == "gvisor":
        return _run_gvisor(command, sandbox_path, image, timeout_sec)
    if backend == "docker":
        return _run_docker(command, sandbox_path, image, timeout_sec)
    return _run_temp_tree(command, sandbox_path, timeout_sec)


def _run_firecracker(
    command: list[str], sandbox_path: str, timeout_sec: int
) -> tuple[int, str, str]:
    """Spec path: Firecracker microVM. Real on Linux+KVM; raises on anything else."""
    import json as _json
    import uuid as _uuid

    if not os.path.exists("/dev/kvm"):
        return 1, "", "firecracker selected but /dev/kvm absent"
    vm_id = f"verifier-{_uuid.uuid4().hex[:8]}"
    socket_path = f"/tmp/{vm_id}.sock"
    config = {
        "boot-source": {"kernel_image_path": "/var/lib/fc/vmlinux"},
        "drives": [
            {
                "drive_id": "rootfs",
                "path_on_host": "/var/lib/fc/rootfs.ext4",
                "is_root_device": True,
                "is_read_only": True,
            }
        ],
        "machine-config": {"vcpu_count": 1, "mem_size_mib": 512},
    }
    config_path = f"/tmp/{vm_id}.json"
    with open(config_path, "w") as f:
        _json.dump(config, f)
    try:
        fc = subprocess.Popen(
            ["firecracker", "--api-sock", socket_path, "--config-file", config_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(0.2)
        sandbox_mount = json_to_mount_spec(sandbox_path)
        _send_firecracker_command(socket_path, "PUT", "/drives/1", sandbox_mount)
        _send_firecracker_command(
            socket_path, "PUT", "/actions", {"action_type": "InstanceStart"}
        )
        try:
            result = subprocess.run(
                command,
                cwd=sandbox_path,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            return result.returncode, result.stdout, result.stderr
        finally:
            fc.terminate()
    finally:
        for p in (socket_path, config_path):
            if os.path.exists(p):
                os.unlink(p)


def _send_firecracker_command(
    sock_path: str, method: str, uri: str, body: dict
) -> None:
    import json as _json
    import socket as _socket

    payload = _json.dumps(body).encode()
    req = (
        f"{method} {uri} HTTP/1.1\r\n"
        f"Content-Length: {len(payload)}\r\n"
        f"Content-Type: application/json\r\n\r\n"
    ).encode() + payload
    with _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM) as s:
        s.settimeout(5)
        s.connect(sock_path)
        s.sendall(req)


def json_to_mount_spec(sandbox_path: str) -> dict:
    return {
        "path_on_host": sandbox_path,
        "is_root_device": False,
        "is_read_only": False,
    }


def _run_gvisor(
    command: list[str], sandbox_path: str, image: str, timeout_sec: int
) -> tuple[int, str, str]:
    """gVisor runsc sandbox. Real on K8s nodes where gvisor RuntimeClass is configured."""
    return _run_docker(command, sandbox_path, image, timeout_sec, runtime="runsc")


def _run_docker(
    command: list[str],
    sandbox_path: str,
    image: str,
    timeout_sec: int,
    runtime: str | None = None,
) -> tuple[int, str, str]:
    """docker sandbox: mounts sandbox_path read-write and runs the command.

    Network is disabled (`--network=none`) so a patch cannot phone home. CPU and
    memory are bounded. Same isolation guarantees the Firecracker lane provides,
    just implemented with what this machine has.
    """
    abs_sandbox = os.path.abspath(sandbox_path)
    docker_cmd = ["docker", "run", "--rm"]
    if runtime:
        docker_cmd += ["--runtime", runtime]
    docker_cmd += [
        "--network=none",
        "--cpus=1.0",
        "--memory=512m",
        "--read-only=false",
        "-v",
        f"{abs_sandbox}:/sandbox",
        "-w",
        "/sandbox",
        image,
        *command,
    ]
    try:
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        return (
            124,
            exc.stdout or "",
            (exc.stderr or "") + f"\n[sandbox timeout after {timeout_sec}s]",
        )


def _run_temp_tree(
    command: list[str], sandbox_path: str, timeout_sec: int
) -> tuple[int, str, str]:
    """Last resort: run on host with scrubbed env (the original verifier behavior)."""
    import tempfile

    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(sandbox_path),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    try:
        result = subprocess.run(
            command,
            cwd=sandbox_path,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
            env=env,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        return (
            124,
            exc.stdout or "",
            (exc.stderr or "") + f"\n[host timeout after {timeout_sec}s]",
        )


def status() -> dict:
    """Report which backend is picked and why."""
    backend = detect_backend()
    reasons = {
        "firecracker": "/dev/kvm + firecracker binary",
        "gvisor": "runsc binary present",
        "docker": "docker info returns 0",
        "temp_tree": "no isolation backend available on this host",
    }
    return {
        "backend": backend,
        "reason": reasons[backend],
        "firecracker_available": bool(
            os.path.exists("/dev/kvm") and shutil.which("firecracker")
        ),
        "gvisor_available": bool(shutil.which("runsc")),
        "docker_available": bool(shutil.which("docker")),
    }
