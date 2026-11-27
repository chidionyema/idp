"""The fitness gate at admission, measured end to end with the standard library only (idp#3525).

Greenlane's judge runs each Optimus measure with the runner's bare python3, which has no
pytest. The first measure called pytest.main and died on `import pytest`, so the judge read
UNKNOWN for a gate that holds. These checks need nothing beyond the standard library;
tests/test_legion_admit.py runs the same three checks under pytest.

Each run is bin/legion-admit --harness auto, as the worker runs it, with a dummy key.
HTTPS_PROXY points at a local trap that counts and drops every connection, so a probe is an
observed attempt at inference and never a real request.

  python3 tests/legion_fitness_gate.py   ->   optimus.legion.fitness_gate_enforced=<0|1>

1 only when all three hold: with no record, and with an UNFIT record, the route is refused
before any provider is contacted; with a fresh FIT record it reaches the probe.
"""

from __future__ import annotations

import importlib.util
import json
import os
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADMIT = ROOT / "bin/legion-admit"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout


def make_repo(base: Path) -> Path:
    r = base / "repo"
    (r / "web").mkdir(parents=True)
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.name", "Agent-Test")
    _git(r, "config", "user.email", "test@example.invalid")
    for i in range(8):
        (r / "web" / f"f{i}.txt").write_text(f"{i}\n")
    _git(r, "add", ".")
    # Plumbing, not `git commit`: a fixture commit is no change to anyone's work, and a
    # machine-wide commit hook (core.hooksPath) must not decide whether the measure can run.
    head = _git(r, "commit-tree", _git(r, "write-tree").strip(), "-m", "base").strip()
    _git(r, "update-ref", "refs/heads/main", head)
    _git(r, "update-ref", "refs/remotes/origin/main", head)
    return r


def gate_run(repo: Path, out: Path, ledger: Path | None):
    """(completed process, provider connections) for one auto admission."""
    hits: list = []

    class _Trap(socketserver.BaseRequestHandler):
        def handle(self):
            hits.append(self.client_address)

    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _Trap)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    trap = f"http://127.0.0.1:{srv.server_address[1]}"
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "TASK": "Do it.\nScope: web/f0.txt\n",
        "GROQ_API_KEY": "measure-dummy",
        "HTTPS_PROXY": trap,
        "https_proxy": trap,
        "LEGION_PROBE_TIMEOUT_S": "3",
    }
    if ledger is not None:
        env["LEGION_FITNESS_DIR"] = str(ledger)
    try:
        r = subprocess.run(
            [sys.executable, str(ADMIT), "--harness", "auto", "--out", str(out)],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        srv.shutdown()
        srv.server_close()
    return r, len(hits)


def ledger_for_registry(base: Path, verdict: str) -> Path:
    """One v1 record per real free route the registry offers, at the shape admission asks."""
    loader = SourceFileLoader("legion_admit_measure", str(ADMIT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    routes = mod.auto_candidates(
        ROOT / "platform/llm/pennyd/providers", {"GROQ_API_KEY": "x"}
    )
    if not routes:
        raise RuntimeError("the registry offers no free groq route to measure against")
    led = base / f"ledger-{verdict}"
    led.mkdir()
    exp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 6 * 3600))
    for i, r in enumerate(routes):
        rec = {
            "schema": "estate.lane-fitness.v1",
            "provider": r["provider"],
            "model": r["model"],
            "verdict": verdict,
            "reason": "empty-patch" if verdict != "FIT" else "test-passes",
            "context_window": min(r["context"], 32768),
            "max_tokens": 4096,
            "expires_at": exp,
        }
        (led / f"{i}.json").write_text(json.dumps(rec))
    return led


def _decision(out: Path) -> dict:
    return json.loads((out / "admission.json").read_text())


def check_no_record_refused(base: Path) -> str:
    """'' when no record refuses before inference, else what went wrong."""
    repo, empty = make_repo(base), base / "ledger-empty"
    empty.mkdir()
    r, hits = gate_run(repo, base / "o", empty)
    if r.returncode != 75 or hits != 0:
        return f"rc={r.returncode} hits={hits}: {(r.stdout + r.stderr)[-300:]}"
    if _decision(base / "o")["decision"] != "REFUSED_UNFIT":
        return "decision is not REFUSED_UNFIT"
    if "NO_FIT_LANE before inference" not in r.stdout:
        return "stdout does not name NO_FIT_LANE before inference"
    return ""


def check_unfit_record_refused(base: Path) -> str:
    repo = make_repo(base)
    r, hits = gate_run(repo, base / "o", ledger_for_registry(base, "UNFIT"))
    if r.returncode != 75 or hits != 0:
        return f"rc={r.returncode} hits={hits}: {(r.stdout + r.stderr)[-300:]}"
    if _decision(base / "o")["decision"] != "REFUSED_UNFIT":
        return "decision is not REFUSED_UNFIT"
    return ""


def check_fit_record_reaches_probe(base: Path) -> str:
    # Positive control: the gate is not a wall. A FIT lane reaches the capacity probe (the trap
    # counts it); the probe then fails on transport, which is capacity's verdict, not fitness's.
    repo = make_repo(base)
    r, hits = gate_run(repo, base / "o", ledger_for_registry(base, "FIT"))
    rec = _decision(base / "o")
    if hits < 1:
        return f"no probe reached the trap: {(r.stdout + r.stderr)[-300:]}"
    if rec.get("fitness") != [] or rec.get("decision") == "REFUSED_UNFIT":
        return f"FIT record was refused: {rec.get('decision')} {rec.get('fitness')}"
    return ""


CHECKS = (
    check_no_record_refused,
    check_unfit_record_refused,
    check_fit_record_reaches_probe,
)


def main() -> int:
    failed = 0
    for check in CHECKS:
        with tempfile.TemporaryDirectory() as d:
            try:
                why = check(Path(d))
            except Exception as exc:  # noqa: BLE001 - any break in a check is a 0, named
                why = f"{type(exc).__name__}: {exc}"
        if why:
            failed += 1
            print(f"FAIL {check.__name__}: {why}", file=sys.stderr)
    print(f"optimus.legion.fitness_gate_enforced={0 if failed else 1}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
