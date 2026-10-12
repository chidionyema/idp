"""The twin sweep has to finish inside the 180 seconds the acceptance suite gives it.

`sovereign/tests/bdd/test_estate_twin.py::_run` kills the build at 180 seconds. Two things made
the sweep exceed that, both measured on 2026-10-12:

  * five cluster reads, each paying a full dial timeout when a kubeconfig exists but its server
    does not answer -- 23.3s each, 116s of a 218s sweep, the whole build then SIGKILLed, so the
    graph was never written at all;
  * 526 `git` processes: a `git log -1` and a `git diff` for each of 263 branches.

These tests fail against the twin as it was: the first two against reads that are never cached,
the third against the per-branch spawn count.

Run:
    pytest tests/test_the_twin_sweep_fits_its_budget.py -v
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "bin" / "estate-twin-runtime"

BRANCHES = 12


def _twin():
    """The twin itself, loaded as a module -- these tests grade the real code path."""
    loader = importlib.machinery.SourceFileLoader("twin_budget", str(TWIN))
    spec = importlib.util.spec_from_loader("twin_budget", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class _CountingSubprocess:
    """Stand in for the module's `subprocess` and record everything it spawns."""

    def __init__(self, real):
        self.real = real
        self.calls: list[list[str]] = []

    def run(self, args, **kwargs):
        self.calls.append(list(args))
        return self.real.run(args, **kwargs)


def _stub_kubectl(
    tmp_path: Path, stderr: str, sleep_s: float = 0.0
) -> tuple[Path, Path]:
    """A kubectl that answers slowly and refuses, and records how often it was dialled."""
    counter = tmp_path / "dials.txt"
    stub = tmp_path / "kubectl"
    stub.write_text(
        "#!/bin/sh\n"
        f'echo "$@" >> {counter}\n'
        f"sleep {sleep_s}\n"
        f"echo '{stderr}' >&2\n"
        "exit 1\n"
    )
    stub.chmod(0o755)
    return stub, counter


def _dialled(counter: Path) -> int:
    return len(counter.read_text().splitlines()) if counter.exists() else 0


def test_one_unreachable_cluster_is_dialled_once_not_once_per_domain(
    tmp_path, monkeypatch
):
    """Five domains asking one unanswerable API server is one dial, not five."""
    module = _twin()
    stub, counter = _stub_kubectl(
        tmp_path,
        "Unable to connect to the server: dial tcp 10.0.0.1:6443: i/o timeout",
        sleep_s=0.3,
    )
    monkeypatch.setenv("KUBECTL", str(stub))
    monkeypatch.setenv("ESTATE_TWIN_KUBECTL_S", "5")
    monkeypatch.setattr(module, "_KUBECTL_UNREACHABLE", None)

    results = [module._kubectl(["get", "pods", "-A"]) for _ in range(5)]

    assert [ok for ok, _ in results] == [False] * 5
    assert _dialled(counter) == 1, (
        f"the cluster was dialled {_dialled(counter)} times for five reads; on a kubeconfig "
        "whose server does not answer that is five full dial timeouts inside a 180s budget"
    )
    assert len({why for _, why in results}) == 1, (
        "the five reads reported different reasons, so a caller cannot tell one dead cluster "
        "from five different failures"
    )


def test_a_per_resource_failure_is_not_remembered_as_a_dead_cluster(
    tmp_path, monkeypatch
):
    """Forbidden on one resource must not blind the domains that can still be read."""
    module = _twin()
    stub, counter = _stub_kubectl(
        tmp_path, "Error from server (Forbidden): pods is forbidden"
    )
    monkeypatch.setenv("KUBECTL", str(stub))
    monkeypatch.setattr(module, "_KUBECTL_UNREACHABLE", None)

    results = [module._kubectl(["get", "pods", "-n", "kube-system"]) for _ in range(3)]

    assert [ok for ok, _ in results] == [False] * 3
    assert _dialled(counter) == 3, (
        "a per-resource failure was cached as 'the cluster is unreachable': every later read "
        "would report BLIND for a reason that was never about the cluster"
    )
    assert module._KUBECTL_UNREACHABLE is None


def _git_repo(tmp_path: Path, branches: int = BRANCHES) -> Path:
    """A repo with `branches` branches off main, each adding one file main does not have."""
    repo = tmp_path / "repo"
    repo.mkdir()

    def run(*args: str) -> None:
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)

    run("init", "-q", "-b", "main")
    run("config", "user.email", "twin@example.com")
    run("config", "user.name", "twin")
    (repo / "base.txt").write_text("base\n")
    run("add", "base.txt")
    run("commit", "-q", "-m", "base")
    for i in range(branches):
        run("checkout", "-q", "-b", f"stranded-{i}", "main")
        (repo / f"file-{i}.txt").write_text("x\n")
        run("add", f"file-{i}.txt")
        run("commit", "-q", "-m", f"add {i}")
    run("checkout", "-q", "main")
    return repo


def test_the_branch_scan_does_not_spawn_two_processes_per_branch(tmp_path, monkeypatch):
    """One process per branch, not two -- and the count it reports is unchanged."""
    module = _twin()
    repo = _git_repo(tmp_path)
    monkeypatch.setattr(module, "ROOT", repo)
    shim = _CountingSubprocess(subprocess)
    monkeypatch.setattr(module, "subprocess", shim)

    con = sqlite3.connect(":memory:")
    result = module.sweep_code(con, base="main")

    assert result["branches"] == BRANCHES
    assert result["files_absent"] == BRANCHES
    spawned = len(shim.calls)
    assert spawned <= BRANCHES + 3, (
        f"the branch scan spawned {spawned} processes for {BRANCHES} branches; it used to spawn "
        "two per branch (a git log for the date and a git diff for the files), which is 526 "
        "processes on the real checkout"
    )
    assert all("for-each-ref" in call or "diff" in call for call in shim.calls), (
        "the scan spawned something other than the ref listing and the diffs: "
        f"{[c[1:] for c in shim.calls]}"
    )

    # Folding the date into the ref listing must yield the same date `%cs` would have.
    expected = subprocess.run(
        ["git", "log", "-1", "--format=%cs", "stranded-0"],
        cwd=repo,
        capture_output=True,
        text=True,
    ).stdout.strip()
    meta = json.loads(
        con.execute(
            "select metadata from nodes where domain = 'code' and type = 'branch' "
            "and json_extract(metadata, '$.branch') = 'stranded-0'"
        ).fetchone()[0]
    )
    assert meta["last_commit"] == expected
    assert meta["unmerged_files"] == 1


def test_the_receipt_is_read_once_per_sweep(monkeypatch):
    """The runtime half and the domains half both ask for it; one object, one read."""
    module = _twin()
    body = '{"at": "2026-10-12T00:00:00Z", "deploy_short": []}'
    calls: list[list[str]] = []

    def fake(args):
        calls.append(list(args))
        return True, body

    monkeypatch.setattr(module, "_kubectl_or_cloud", fake)
    monkeypatch.setattr(module, "_RECEIPT", None)

    first = module.read_receipt()
    second = module.read_receipt()

    assert first == second == json.loads(body)
    assert len(calls) == 1, (
        f"the receipt was fetched {len(calls)} times in one sweep; it is the same object both "
        "times and it costs 9.1s a fetch"
    )


def test_a_failed_receipt_is_not_remembered(monkeypatch):
    """Only a success is cached, so a read that failed is still retried by the next caller."""
    module = _twin()
    calls: list[list[str]] = []

    def fake(args):
        calls.append(list(args))
        return False, "no session"

    monkeypatch.setattr(module, "_kubectl_or_cloud", fake)
    monkeypatch.setattr(module, "_RECEIPT", None)

    assert module.read_receipt() is None
    assert module.read_receipt() is None
    assert len(calls) == 2
