import os, subprocess, sys
from pathlib import Path

SANDBOX_RINGS = {
    "subprocess": {
        "env": {"PATH": "/usr/bin:/bin", "NO_NETWORK": "1"},
        "cmd": [sys.executable, "-m", "factory.gates"],
        "timeout": 300,
    },
    "kronos.ring0": {
        "env": {"PATH": "/usr/bin:/bin", "NO_NETWORK": "1", "KRONOS_RING": "0"},
        "cmd": ["firecracker-run"],  # placeholder; runs firecracker microVM
        "timeout": 60,
    },
    "kronos.ring1": {
        "env": {"PATH": "/usr/bin:/bin", "NO_NETWORK": "1", "KRONOS_RING": "1"},
        "cmd": [sys.executable, "-m", "factory.gates"],  # wasmtime in prod
        "timeout": 120,
    },
    "docker": {
        "env": {"PATH": "/usr/bin:/bin"},
        "cmd": [
            "docker",
            "run",
            "--rm",
            "--network=none",
            "--read-only",
            "factory/gate-runner",
        ],
        "timeout": 300,
    },
}


def run_gate(gate: dict, cwd: Path) -> tuple[bool, str]:
    name = gate.get("sandbox")
    term = gate.get("terminal")
    if not term:
        return False, "NO_GATE_TERMINAL"
    cfg = SANDBOX_RINGS.get(name)
    if cfg is None:
        return False, f"UNKNOWN_SANDBOX_{name}"
    clean = {**cfg["env"], "PYTHONPATH": str(Path(__file__).resolve().parent.parent)}
    try:
        r = subprocess.run(
            cfg["cmd"] + [term],
            cwd=cwd,
            env=clean,
            capture_output=True,
            text=True,
            timeout=cfg["timeout"],
        )
        return (r.returncode == 0, (r.stdout or r.stderr or "").strip()[:400])
    except subprocess.TimeoutExpired:
        return False, "GATE_TIMEOUT"
    except FileNotFoundError:
        return False, f"SANDBOX_UNAVAILABLE_{name}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"
