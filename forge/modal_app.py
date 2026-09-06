# ruff: noqa: S603,S607  argv lists, our own scripts and the oras binary baked into the image
"""Ephemeral GPU launcher. The base weights live on a Modal Volume so a run never downloads.

modal run forge/modal_app.py --task example-classify [--task-file task.yaml] [--data file.jsonl]
                             [--dry-run] [--max-steps 10] [--record forge-run.json]

Every run, passed, refused or dry, returns one JSON record (eval, dataset hash, trace, artifact,
verdict) and the local entrypoint writes it to --record; forge/experiment_record.py turns that
into the experiment write-up under forge/experiments/. Runs come from .github/workflows/forge-train.yml.
"""

import json
import os
import pathlib
import subprocess
import time

import modal

ORAS_VERSION = "1.2.0"
REMOTE = "/root/forge"
GPU = "T4"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "curl", "cmake", "build-essential")
    .pip_install("unsloth", "langfuse<3", "pyyaml", "datasets")
    .run_commands(
        f"curl -sSL https://github.com/oras-project/oras/releases/download/v{ORAS_VERSION}/oras_{ORAS_VERSION}_linux_amd64.tar.gz"
        " | tar -zx -C /usr/local/bin oras"
    )
    .add_local_dir(os.path.dirname(os.path.abspath(__file__)), remote_path=REMOTE)
)
hf_cache = modal.Volume.from_name("huggingface-cache", create_if_missing=True)
app = modal.App("model-forge")


@app.function(
    image=image,
    gpu=GPU,
    timeout=3600,
    secrets=[
        modal.Secret.from_name("estate-ghcr"),
        modal.Secret.from_name("estate-langfuse"),
    ],
    volumes={"/root/.cache/huggingface": hf_cache},
)
def run_forge(
    task: str,
    data: bytes | None,
    dry_run: bool = False,
    max_steps: int = -1,
    task_file: str = "task.yaml",
) -> dict:
    env = {**os.environ, "DATASET_NAME": task}
    if data:  # a client file, the default road; Langfuse export is the optional one
        pathlib.Path(REMOTE, "dataset.jsonl").write_bytes(data)
    else:
        subprocess.run(
            ["python", "export_langfuse.py"], cwd=REMOTE, env=env, check=True
        )
    started = time.time()
    proc = subprocess.run(
        ["python", "train.py", "--task", task_file, "--max-steps", str(max_steps)],
        cwd=REMOTE,
        env=env,
        check=False,
    )
    record = {
        "task": task,
        "task_file": task_file,
        "dry_run": dry_run,
        "max_steps": max_steps,
        "gpu": GPU,
        "seconds": round(time.time() - started),
        "trace": None,
        "artifact": None,
    }
    eval_path = pathlib.Path(REMOTE, "artifact", "eval.json")
    if not eval_path.exists():
        raise RuntimeError(
            f"train.py exited {proc.returncode} before writing eval.json; no result to record"
        )
    record["eval"] = json.loads(eval_path.read_text(encoding="utf-8"))
    record["dataset"] = record["eval"].pop("dataset", None)
    if os.environ.get("LANGFUSE_PUBLIC_KEY"):
        from langfuse import Langfuse

        trace = Langfuse().trace(name="forge-run", metadata=record)
        record["trace"] = trace.id
    if proc.returncode != 0:
        record["verdict"] = "refused"
        return record
    if dry_run:
        record["verdict"] = "dry-run"
        return record
    user = os.environ["GHCR_USER"]
    subprocess.run(
        ["oras", "login", "ghcr.io", "-u", user, "--password-stdin"],
        input=os.environ["GHCR_PAT"].encode(),
        check=True,
    )
    ref = f"ghcr.io/{user}/models/{task}:v1.{int(time.time())}"
    subprocess.run(
        [
            "oras",
            "push",
            ref,
            "model.gguf:application/vnd.gguf.model",
            "model-card.yaml:application/yaml",
            "eval.json:application/json",
            "tokenizer.json:application/json",
            "dataset.jsonl:application/jsonl",
        ],
        cwd=f"{REMOTE}/artifact",
        check=True,
    )
    record["artifact"] = ref
    record["verdict"] = "shipped"
    return record


@app.local_entrypoint()
def main(
    task: str = "example-classify",
    task_file: str = "task.yaml",
    data: str = "",
    dry_run: bool = False,
    max_steps: int = -1,
    record: str = "forge-run.json",
):
    payload = pathlib.Path(data).read_bytes() if data else None
    result = run_forge.remote(task, payload, dry_run, max_steps, task_file)
    pathlib.Path(record).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))
    if result["verdict"] == "refused":
        raise SystemExit(1)
