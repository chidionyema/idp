# ruff: noqa: S101
"""Failing-test definition of done for the Kaggle second launcher (forge/kaggle_app.py).

Spec: docs/specs/2026-09-09-forge-kaggle-second-launcher.md

These tests must pass with NO Kaggle credential and NO network: they grade structure and the
pure local planning/refusal/record-contract logic a GPU launcher shares with forge/modal_app.py.
The live "a Kaggle kernel ran train.py and returned eval.json" proof is founder-gated (KAGGLE
root mint + one real dispatch) and is deliberately NOT testable here.
"""

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]  # idp/
FORGE = Path(__file__).resolve().parents[1]  # forge/
sys.path.insert(0, str(FORGE))


def _load_task(rel: str) -> dict:
    return yaml.safe_load((ROOT / rel).read_text(encoding="utf-8"))


def _read_kaggle_app() -> str:
    return (FORGE / "kaggle_app.py").read_text(encoding="utf-8")


# --- 1. The 2026-09-06 common-import regression must not return ------------
def test_kaggle_app_imports_common_robustly_like_modal_does():
    """Structural (R76): kaggle_app.py must import `common` only after putting BOTH its own
    module dir and any remote staging dir on sys.path. A Kaggle CLI/execution context can stage
    the launcher away from common.py, exactly the shape that killed the 2026-09-06 Modal run
    with `ModuleNotFoundError: No module named 'common'`."""
    import ast

    src = _read_kaggle_app()
    tree = ast.parse(src)

    def sys_path_adds(body, names):
        found = []
        for node in body:
            node = node.value if isinstance(node, ast.Expr) else node
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            if not isinstance(f, ast.Attribute) or f.attr not in names:
                continue
            head = f.value
            while isinstance(head, ast.Attribute):
                head = head.value
            if isinstance(head, ast.Name) and head.id == "sys":
                found.append(node.lineno)
        return found

    common_import = next(
        (
            n.lineno
            for n in tree.body
            if isinstance(n, ast.ImportFrom)
            and n.module == "common"
            and any(a.name in ("compute_plan", "cost_gate", "usd_for") for a in n.names)
        ),
        None,
    )
    assert common_import is not None, "kaggle_app.py must import from common"
    inserts = sys_path_adds(tree.body, ("insert",))
    appends = sys_path_adds(tree.body, ("append",))
    # must register its own module dir AND append a remote staging dir, then import.
    assert inserts and appends, (
        "kaggle_app.py must add its module dir AND a remote dir to sys.path before importing common"
    )
    assert common_import > max(inserts + appends), (
        "kaggle_app.py imports common too early (module dir + remote must be on the path first)"
    )


# --- 2. Planning/refusal is pure-local and refuses before any session ---------
def test_kaggle_refuses_unmappable_or_unpriced_gpu_before_any_session():
    """The launcher's planning entrypoint (a pure function taking a task dict) must return a
    `verdict: refused` record -- NOT raise, NOT touch kaggle -- when the task's compute.gpu is
    not a Kaggle accelerator this launcher maps AND not priced, or when the worst-case bill
    exceeds budget. Mirrors modal cost_gate behaviour; nothing may bill for a refused run."""
    import kaggle_app  # the file under test

    plan_fn = getattr(kaggle_app, "plan_run", None) or getattr(
        kaggle_app, "compute_plan", None
    )
    assert plan_fn is not None, (
        "kaggle_app.py must expose a local plan_run/compute_plan function"
    )

    # unpriced / unmappable GPU
    out = plan_fn(
        {"compute": {"gpu": "space-gpu", "timeout_s": 3600, "budget_usd": 5.0}}
    )
    assert out.get("verdict") == "refused", (
        "an unmappable GPU must be refused before any session"
    )
    assert out.get("eval", {}).get("refusal"), "a refused record must say why"


def test_kaggle_cost_gate_is_the_same_common_one():
    """No second, driftable copy of the money gate: the launcher must call the imported
    common.cost_gate, and for the shipped ci-flake-triage task the answer must match the Modal
    decision (no refusal: worst case fits the $1.00 budget)."""
    import kaggle_app
    from common import cost_gate as common_gate

    app_gate = kaggle_app.cost_gate
    assert app_gate is common_gate, (
        "kaggle_app must reuse forge/common.py's cost_gate, not reimplement money logic"
    )
    task = _load_task("forge/tasks/ci-flake-triage.yaml")
    assert common_gate(task) is None, (
        "the shipped ci-flake task must fit its own budget"
    )


# --- 3. The second launcher feeds the SAME record renderer, unchanged ---------
def test_kaggle_dry_run_record_shape_renders_through_experiment_record():
    """A canonical Kaggle dry-run `forge-run.json` (as kaggle_app must write) already renders a
    valid, gate-graded `<stamp>-ci-flake-triage.md` through the REAL experiment_record.py -- so a
    Kaggle run's record is byte-compatible with the existing Modal loop and PR filing."""

    rows_path = FORGE / "datasets" / "ci-flake-triage.jsonl"
    rows = [json.loads(l) for l in rows_path.read_text().splitlines() if l.strip()]
    sha = hashlib.sha256(rows_path.read_bytes()).hexdigest()
    n_train = sum(1 for r in rows if r.get("split") == "train")
    n_eval = sum(1 for r in rows if r.get("split") == "eval")

    run = {
        "task": "ci-flake-triage",
        "task_file": "tasks/ci-flake-triage.yaml",
        "dry_run": True,
        "max_steps": 120,
        "gpu": "nvidiaP100",  # Kaggle accelerator
        "seconds": 600,
        "usd": 0.0,  # free tier
        "budget_usd": 1.0,
        "trace": None,
        "artifact": None,
        "verdict": "dry-run",
        "eval": {"agreement": 0.96, "abstain_rate": 0.08, "held_out": n_eval},
        "dataset": {
            "rows": len(rows),
            "train": n_train,
            "eval": n_eval,
            "sha256": sha,
            "per_label": {"0": 700, "1": 99},
            "teachers": ["outcome: same commit later went green with nothing changed"],
        },
    }

    outd = pathlib.Path(tempfile.mkdtemp())  # safe temp dir; no mktemp (S306)
    rf = outd / "forge-run.json"
    rf.write_text(json.dumps(run))
    res = subprocess.run(  # noqa: S603 - fixed sys.executable + the repo's own record file
        [
            sys.executable,
            "experiment_record.py",
            "--task",
            "tasks/ci-flake-triage.yaml",
            "--run",
            str(rf),
            "--data",
            str(rows_path),
            "--out",
            str(outd),
        ],
        cwd=FORGE,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"experiment_record failed: {res.stderr}"
    md = pathlib.Path(res.stdout.strip()).read_text()
    assert f"held_out: {n_eval}" in md
    assert "| min_agreement met | True |" in md and "| max_abstain met | True |" in md
    assert "verdict: dry-run" in md
