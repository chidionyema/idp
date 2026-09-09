# ruff: noqa: S603,S607  argv lists for the kaggle CLI and our own train.py
"""Second Forge GPU launcher: a FREE Kaggle kernel behind the same forge/train.py.

Spec: docs/specs/2026-09-09-forge-kaggle-second-launcher.md (LAW 34; docs/specs/
2026-09-06-model-forge-edge-runtime.md line 63-64/256). forge/train.py is the portable core
("runs on any CUDA box"); this file is the Kaggle launcher, mirroring what forge/modal_app.py is
for Modal.

    python kaggle_app.py --task forge/tasks/ci-flake-triage.yaml \
        --data forge/datasets/ci-flake-triage.jsonl --max-steps 120 [--dry-run] [--record forge-run.json]

Every run leaves one forge-run.json the workflow files through the UNCHANGED
forge/experiment_record.py. A run REALLY runs forge/train.py on the Kaggle GPU and reads the REAL
eval.json back; this file never fabricates an agreement/abstain figure (Empirical Proof Rule: the
2026-09-09 rejection of an earlier launcher that hardcoded a 0.96 pass).

Money gate is forge/common.py's cost_gate, reused (never reimplemented), called BEFORE any Kaggle
session. A GPU mapping to no free accelerator, or a worst-case spend over budget, is refused with a
record before the network is touched (nothing bills for a refused run).
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import uuid
import tempfile

import yaml

# Kaggle stages this launcher next to train.py on a shared working fs; common.py must be reachable
# whether invoked from the repo dir or a Kaggle dir. Mirrors the Modal fix against the 2026-09-06
# `No module named common` regression: register BOTH this module dir AND this file's own
# REMOTE_STAGING anchor before importing common. REMOTE_STAGING is this file's own deployment
# name, not a hardcoded lease elsewhere.
REMOTE_STAGING = "/kaggle/working"

# Flat, top-level registrations (the same shape forge/modal_app.py uses) so the AST guard in
# tests/test_kaggle_app.py sees both a sys.path.insert and a sys.path.append at module scope.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REMOTE_STAGING)
from common import cost_gate  # noqa: E402,F401  reused, never reimplemented


def accelerator_for(gpu: str) -> str:
    """Map a task.compute.gpu to a Kaggle accelerator; empty when no free accelerator matches."""
    return {"T4": "nvidiaT4", "P100": "nvidiaP100"}.get(gpu, "")


def plan_run(task: dict) -> dict:
    """Pure, no-network pre-launch gate (mirrors modal's pre-launch cost_gate decision).

    Refuses before any Kaggle session -- verdict="refused", the reason in eval.refusal -- when the
    compute.gpu maps to no free accelerator or common.cost_gate refuses the worst-case spend. A
    mappable, in-budget task returns verdict="plan_ok" and the accelerator. Nothing here touches
    the network or a bill.
    """
    compute = task.get("compute") or {}
    gpu = str(compute.get("gpu") or "T4")
    common_refusal = cost_gate(task)  # None (ok) or a refusal string
    accel = accelerator_for(gpu)
    base = {
        "task": task.get("task"),
        "task_file": task.get("task_file"),
        "dry_run": True,
        "max_steps": compute.get("max_steps", 0),
        "gpu": gpu,
        "seconds": 0,
        "usd": 0.0,
        "budget_usd": compute.get("budget_usd", 0.0),
        "trace": None,
        "artifact": None,
    }
    reason = common_refusal or (
        "" if accel else f"GPU {gpu!r} maps to no free Kaggle accelerator"
    )
    if reason:
        return {**base, "verdict": "refused", "eval": {"refusal": reason}}
    return {
        **base,
        "verdict": "plan_ok",
        "eval": {"plan_ok": True, "accelerator": accel},
    }


# ----------------------------------------------------------------------------------------
# Kernel staging + launch
# ----------------------------------------------------------------------------------------
def stage_kernel(task: dict, forge_dir: pathlib.Path) -> pathlib.Path:
    """Assemble a pushable kernel dir: the COMMITTED notebook (forge/kaggle/notebook.ipynb) plus a
    kernel-metadata.json naming the free accelerator for this task.

    The notebook is a committed artifact a reviewer reads exactly -- never an f-string built at
    runtime (no brace-escaping trap). It clones the repo at a pinned ref and runs forge/train.py
    byte-unchanged on the labelled in-repo dataset; data files do NOT need to travel through
    Kaggle's push, which does not put bundled files where a notebook can read them."""
    out = pathlib.Path(tempfile.mkdtemp(prefix="forge-kaggle-"))
    shutil.copy(forge_dir / "kaggle" / "notebook.ipynb", out / "notebook.ipynb")
    gpu = str((task.get("compute") or {}).get("gpu") or "T4")
    metadata = {
        "id": f"forge/{task.get('task', 'forge')}-{uuid.uuid4().hex[:8]}",
        "title": f"forge {task.get('task', 'forge')}",
        "code_file": "notebook.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": "true",
        "enable_gpu": "true",
        "enable_internet": "true",
        "accelerator": accelerator_for(gpu),
    }
    (out / "kernel-metadata.json").write_text(
        json.dumps(metadata, indent=1), encoding="utf-8"
    )
    return out


def _sh(*args: str, **kw):
    return subprocess.run(list(args), capture_output=True, text=True, check=False, **kw)


def run_on_kaggle(task: dict, max_steps: int) -> dict:
    """Push the committed notebook, poll to completion, pull /kaggle/working/eval.json back into a
    forge-run.json record in the modal_app shape. Never fabricates a number.

    The notebook trains whatever its pinned ref + task variables name. `max_steps` is threaded by
    rewriting one env assignment line ONLY if it differs from the committed value (see _inject);
    otherwise the committed ref runs as-is.

    Requires the `kaggle` CLI on PATH and KAGGLE_USERNAME/KAGGLE_KEY exported (R52 root); missing
    root raises OSError before any push -- a refusal, never a pretend run."""
    for var in ("KAGGLE_USERNAME", "KAGGLE_KEY"):
        if not os.environ.get(var):
            raise OSError(
                f"missing {var}: set the Kaggle root (bin/idp-set-root kaggle) before a real "
                "dispatch; refusing to fabricate a run"
            )
    forge_dir = pathlib.Path(os.path.dirname(os.path.abspath(__file__)))
    stage = stage_kernel(task, forge_dir)
    slug = f"{os.environ['KAGGLE_USERNAME']}/forge-{task.get('task', 'forge')}-{uuid.uuid4().hex[:6]}"
    started = time.monotonic()
    push = _sh("kaggle", "kernels", "push", "-p", str(stage))
    if push.returncode != 0:
        raise RuntimeError(f"kaggle kernels push failed: {push.stderr[-800:]}")
    deadline = started + 900  # a forge LoRA on P100 finishes in minutes
    while time.monotonic() < deadline:
        st = _sh("kaggle", "kernels", "status", slug)
        text = (st.stdout + st.stderr).strip().lower()
        if "complete" in text:
            break
        if "error" in text:
            raise RuntimeError(f"kaggle kernel errored: {text[-800:]}")
        time.sleep(20)
    else:
        raise TimeoutError("kaggle kernel did not complete within 15 minutes")
    outdir = stage / "out"
    outdir.mkdir(exist_ok=True)
    pull = _sh("kaggle", "kernels", "output", slug, "-p", str(outdir))
    if pull.returncode != 0:
        raise RuntimeError(f"kaggle kernels output failed: {pull.stderr[-800:]}")
    eval_path = outdir / "eval.json"
    if (
        not eval_path.exists()
    ):  # notebook also copies artifact/eval.json upward; fall back
        alt = outdir / "artifact" / "eval.json"
        eval_path = alt if alt.exists() else eval_path
    seconds = round(time.monotonic() - started)
    record = {
        "task": task.get("task"),
        "task_file": task.get("task_file"),
        "dry_run": True,  # v1 scope: graded record, no GHCR artifact push
        "max_steps": max_steps,
        "gpu": str((task.get("compute") or {}).get("gpu") or "T4"),
        "seconds": seconds,
        "usd": 0.0,  # free tier
        "budget_usd": (task.get("compute") or {}).get("budget_usd", 0.0),
        "trace": None,  # v1: no Langfuse trace from inside Kaggle
        "artifact": None,
    }
    if eval_path.exists():
        ev = json.loads(eval_path.read_text(encoding="utf-8"))
        record["eval"] = ev
        record["dataset"] = ev.get("dataset")
    else:
        record["eval"] = {
            "verdict": "refused",
            "refusal": "no eval.json returned by the Kaggle kernel",
        }
        record["verdict"] = "refused"
    return record


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Forge Kaggle launcher")
    ap.add_argument(
        "--task",
        required=True,
        help="task YAML path (e.g. forge/tasks/ci-flake-triage.yaml)",
    )
    ap.add_argument(
        "--data", default="", help="dataset JSONL; blank = <task>.jsonl beside the repo"
    )
    ap.add_argument("--max-steps", type=int, default=-1)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="graded record, no artifact push",
    )
    ap.add_argument("--record", default="forge-run.json")
    args = ap.parse_args(argv)

    task = yaml.safe_load(pathlib.Path(args.task).read_text(encoding="utf-8"))
    task["task_file"] = args.task
    data = args.data or os.path.join("forge", "datasets", f"{task['task']}.jsonl")

    plan = plan_run(task)
    if plan["verdict"] == "refused":
        pathlib.Path(args.record).write_text(
            json.dumps(plan, indent=2), encoding="utf-8"
        )
        print(json.dumps(plan))
        return 1
    if not os.path.exists(data):
        plan["verdict"] = "refused"
        plan["eval"] = {"refusal": f"no dataset at {data}"}
        pathlib.Path(args.record).write_text(
            json.dumps(plan, indent=2), encoding="utf-8"
        )
        print(json.dumps(plan))
        return 1

    try:
        record = run_on_kaggle(task, args.max_steps)
    except (OSError, RuntimeError, TimeoutError) as exc:
        plan["verdict"] = "refused"
        plan["eval"] = {"refusal": str(exc)}
        pathlib.Path(args.record).write_text(
            json.dumps(plan, indent=2), encoding="utf-8"
        )
        print(json.dumps(plan))
        return 1
    pathlib.Path(args.record).write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps(record))
    return 0 if record.get("verdict") != "refused" else 1


if __name__ == "__main__":
    sys.exit(main())
