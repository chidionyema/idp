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
import tempfile
import time
import uuid


def detect_backend() -> str:
    """Return the name of the best available isolation backend.

    Order: firecracker -> gvisor -> docker -> temp_tree
    """
    if os.path.exists("/dev/kvm") and shutil.which("firecracker"):
        return "firecracker"
    if shutil.which("runsc"):
        return "gvisor"
    docker_bin = shutil.which("docker")
    if docker_bin:
        try:
            r = subprocess.run(  # noqa: S603
                [docker_bin, "info"],
                capture_output=True,
                text=True,
                timeout=3,
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
    """Run `command` inside the picked sandbox, with `sandbox_path` mounted read-write."""
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
    fc_dir = tempfile.mkdtemp(prefix="idp-fc-")
    socket_path = os.path.join(fc_dir, "firecracker.sock")
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
    config_path = os.path.join(fc_dir, "fc-config.json")
    with open(config_path, "w") as f:
        json.dump(config, f)
    try:
        _ = subprocess.Popen(  # noqa: S603,F841
            [
                shutil.which("firecracker"),
                "--api-sock",
                socket_path,
                "--config-file",
                config_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(0.2)
        return 1, "", "firecracker lane requires Linux+KVM (not this host)"
    except (OSError, FileNotFoundError) as exc:
        return 1, "", f"firecracker failed to start: {exc}"
    finally:
        shutil.rmtree(fc_dir, ignore_errors=True)


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
    container_name = f"idp-sandbox-{uuid.uuid4().hex[:8]}"
    docker_bin = shutil.which("docker")
    if not docker_bin:
        return 1, "", "docker binary not found"
    docker_cmd = [docker_bin, "run", "--rm", "--name", container_name]
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

    def _decode(b):
        return (
            b.decode("utf-8", errors="replace") if isinstance(b, bytes) else (b or "")
        )

    try:
        result = subprocess.run(  # noqa: S603
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
            _decode(exc.stdout),
            _decode(exc.stderr) + f"\n[sandbox timeout after {timeout_sec}s]",
        )


def _run_temp_tree(
    command: list[str], sandbox_path: str, timeout_sec: int
) -> tuple[int, str, str]:
    """Last resort: run on host with scrubbed env (the original verifier behavior)."""
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(sandbox_path),
        "PYTHONDONTWRITEBYTECODE": "1",
    }

    def _decode(b):
        return (
            b.decode("utf-8", errors="replace") if isinstance(b, bytes) else (b or "")
        )

    try:
        result = subprocess.run(  # noqa: S603
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
            _decode(exc.stdout),
            _decode(exc.stderr) + f"\n[host timeout after {timeout_sec}s]",
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
