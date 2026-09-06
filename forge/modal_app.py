# ruff: noqa: S603,S607  argv lists, our own scripts and the oras binary baked into the image
"""Ephemeral GPU launcher. The base weights live on a Modal Volume so a run never downloads.

modal run forge/modal_app.py --task example-classify [--dry-run] [--max-steps 10]
"""

import os
import pathlib
import subprocess
import time

import modal

ORAS_VERSION = "1.2.0"
REMOTE = "/root/forge"

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
    gpu="T4",
    timeout=3600,
    secrets=[
        modal.Secret.from_name("estate-ghcr"),
        modal.Secret.from_name("estate-langfuse"),
    ],
    volumes={"/root/.cache/huggingface": hf_cache},
)
def run_forge(
    task: str, data: bytes | None, dry_run: bool = False, max_steps: int = -1
) -> str:
    env = {**os.environ, "DATASET_NAME": task}
    if data:  # a client file, the default road; Langfuse export is the optional one
        pathlib.Path(REMOTE, "dataset.jsonl").write_bytes(data)
    else:
        subprocess.run(
            ["python", "export_langfuse.py"], cwd=REMOTE, env=env, check=True
        )
    subprocess.run(
        ["python", "train.py", "--max-steps", str(max_steps)],
        cwd=REMOTE,
        env=env,
        check=True,
    )
    with open(f"{REMOTE}/artifact/eval.json", encoding="utf-8") as f:
        eval_json = f.read()
    from langfuse import Langfuse

    trace = Langfuse().trace(
        name="forge-run", metadata={"task": task, "dry_run": dry_run, "eval": eval_json}
    )
    if dry_run:
        return f"dry run, no push; eval {eval_json}; trace {trace.id}"
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
        ],
        cwd=f"{REMOTE}/artifact",
        check=True,
    )
    return f"pushed {ref}; eval {eval_json}; trace {trace.id}"


@app.local_entrypoint()
def main(
    task: str = "example-classify",
    data: str = "",
    dry_run: bool = False,
    max_steps: int = -1,
):
    payload = pathlib.Path(data).read_bytes() if data else None
    print(run_forge.remote(task, payload, dry_run, max_steps))
