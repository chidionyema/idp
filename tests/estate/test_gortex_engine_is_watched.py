"""The gortex engine must be WATCHED, and the watch must be able to fail.

WHY THIS EXISTS. Measured 2026-11-25: the engine's own state file said `"startup_phase":
"serving"` for pid 39356, and no such process existed. Its store was 1,920,581,632 bytes
(1.79 GiB) with a 64 MiB WAL, on a disk with 2.0 GiB free. Nothing in the estate measured the
engine, so it could die without a word and its store could grow until the machine stopped.

So this file is the falsifier for the watch:

  * bin/gortex-health must be RED when the engine is dead (a stale pid file is a proxy; the
    process is the thing)
  * it must be RED when the store is over the budget (R5: every loop has a budget)
  * it must be GREEN when the engine's own door answers and its bytes are within budget
  * the critical-function registry must carry the engine, and the probe it names must be
    registered
  * the Optimus measures must be registered AND must run, printing exactly
    `optimus.<name>=<number>` -- Greenlane reads the measure, not the author's claim
  * the probe must be RED when the engine is wrong (a probe that cannot fail is not a probe)

Every case below is checked against a fixture that breaks it, so the watch is proven to reject
what it claims to reject (estate law, section 9, principle 1).
"""

from __future__ import annotations

import http.server
import importlib.util
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HEALTH = REPO / "bin" / "gortex-health"
REGISTRY = REPO / "catalog" / "critical-functions.json"
METRICS = REPO / "catalog" / "optimus-metrics.json"
PROBE_PATH = REPO / "platform" / "estate" / "libexec" / "critical-probe.py"


def _run(args: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(HEALTH), *args],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
        cwd=str(REPO),
    )


def _engine(tmp_path: Path, *, pid: int, store_bytes: int = 1024) -> list[str]:
    """The paths of a fake engine: a pid file, a store of a given size, no socket."""
    store = tmp_path / "store.sqlite"
    with store.open("wb") as handle:
        handle.truncate(store_bytes)
    pid_file = tmp_path / "daemon.pid"
    pid_file.write_text(str(pid))
    return [
        "--store",
        str(store),
        "--pid-file",
        str(pid_file),
        "--socket",
        str(tmp_path / "daemon.sock"),
    ]


def _dead_pid() -> int:
    """A pid that is certain to be dead: start a process and wait for it."""
    proc = subprocess.Popen([sys.executable, "-c", "pass"])  # noqa: S603 - fixed argv, no shell
    proc.wait()
    return proc.pid


def test_the_health_is_red_when_the_engines_process_is_dead(tmp_path: Path) -> None:
    args = _engine(tmp_path, pid=_dead_pid())
    proc = _run([*args, "--json"])
    assert proc.returncode == 1, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload["status"] == "fail"
    assert any("not alive" in reason for reason in payload["reasons"]), payload[
        "reasons"
    ]


def test_the_health_is_red_when_the_store_is_over_its_budget(tmp_path: Path) -> None:
    # A sparse file: the cap is 2 GiB, so the size is over it without spending a byte of disk.
    args = _engine(tmp_path, pid=os.getpid(), store_bytes=2 * 1024 * 1024 * 1024 + 1)
    proc = _run([*args, "--json"])
    assert proc.returncode == 1, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert any("over the" in reason for reason in payload["reasons"]), payload[
        "reasons"
    ]


def test_the_health_is_green_when_the_engines_own_door_answers(tmp_path: Path) -> None:
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - the stdlib's own name for this method
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *args: object) -> None:
            return

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        args = _engine(tmp_path, pid=os.getpid())
        proc = _run(
            [*args, "--addr", "127.0.0.1:%d" % server.server_address[1], "--json"]
        )
    finally:
        server.shutdown()
        server.server_close()
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload["status"] == "ok", payload
    assert payload["door"]["http_ok"] is True


def test_the_health_is_blind_when_there_is_nothing_to_measure(tmp_path: Path) -> None:
    proc = _run(
        [
            "--store",
            str(tmp_path / "absent.sqlite"),
            "--pid-file",
            str(tmp_path / "absent.pid"),
            "--socket",
            str(tmp_path / "absent.sock"),
            "--json",
        ]
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload["status"] == "blind"


def test_the_measure_prints_exactly_the_optimus_line(tmp_path: Path) -> None:
    proc = _run([*_engine(tmp_path, pid=os.getpid()), "--metric", "gortex.store_bytes"])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.strip() == "optimus.gortex.store_bytes=1024", proc.stdout


def test_the_registry_carries_the_engine() -> None:
    registry = json.loads(REGISTRY.read_text())
    entries = {entry["id"]: entry for entry in registry["functions"]}
    assert "gortex-engine" in entries, sorted(entries)
    entry = entries["gortex-engine"]
    assert entry["liveness"]["type"] == "command"
    assert "gortex-engine" in entry["liveness"]["argv"][-1]
    assert entry["goal"]["field"] == "healthy"
    assert entry["remediation"]["task"]


def test_the_probe_the_registry_names_is_registered() -> None:
    spec = importlib.util.spec_from_file_location("critical_probe_engine", PROBE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert "gortex-engine" in module.PROBES, sorted(module.PROBES)


def test_the_optimus_measures_are_registered_and_run() -> None:
    catalog = json.loads(METRICS.read_text())
    measures = {metric["name"]: metric for metric in catalog["metrics"]}
    for name in ("gortex.store_bytes", "gortex.store_wal_bytes", "gortex.daemon_up"):
        assert name in measures, sorted(measures)
        metric = measures[name]
        argv = metric["measure"]
        assert argv[:2] == ["python3", "bin/gortex-health"], metric
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(REPO),
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert f"optimus.{name}=" in proc.stdout, proc.stdout


def test_the_probe_is_red_when_the_engine_is_wrong(tmp_path: Path) -> None:
    """The probe must fail on a poisoned engine, not merely describe it."""
    fake = tmp_path / "repo"
    (fake / "bin").mkdir(parents=True)
    # repo_root() only accepts a tree that carries the receipt reader, so the fixture has it.
    (fake / "bin" / "idp-cluster-state").write_text("#!/bin/true\n")
    (fake / "bin" / "gortex-health").write_text(
        "#!/usr/bin/env python3\n"
        'print(\'{"status": "fail", "reasons": ["the engine is poisoned"]}\')\n'
    )
    env = dict(os.environ)
    env["ESTATE_REPO"] = str(fake)
    env["ESTATE_STATE_DIR"] = str(tmp_path / "state")
    proc = subprocess.run(
        ["python3", str(PROBE_PATH), "gortex-engine"],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
        cwd=str(REPO),
    )
    assert proc.returncode != 0, proc.stdout + proc.stderr
    assert "poisoned" in (proc.stdout + proc.stderr), proc.stdout + proc.stderr
