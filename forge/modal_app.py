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
import sys
import time

import modal
import yaml

# Modal stages the entrypoint script at the image ROOT (/root/modal_app.py) while
# add_local_dir copies forge/ to /root/forge, so `common` and friends live one level down
# from the executed module -- never importable from the module dir alone. A 2026-09-06 run died
# on exactly this: `ModuleNotFoundError: No module named 'common'` at /root/modal_app.py, the
# runner then spun to the 90-minute ceiling, and no experiment record was ever filed. The fix:
# put both the module dir (a local `python modal_app.py`) and the remote layout on the path.
# REMOTE is this file's own deployment constant, not a hardcoded lease in another file.
ORAS_VERSION = "1.2.0"
# llama.cpp is baked in at a pinned release and called directly by train.py. unsloth's own
# save_pretrained_gguf clones and builds llama.cpp at run time and asks the terminal for
# permission to apt-get its dependencies first; on a headless container that prompt reads EOF
# and the export dies after the GPU has already been paid for. Run 34401515600 (2026-09-09)
# trained, passed both gates -- agreement 0.9773, abstain 0.175 -- and then lost the model to
# "RuntimeError: Unsloth: GGUF conversion failed: EOF when reading a line".
LLAMA_CPP_TAG = "b10883"
LLAMA_CPP_DIR = "/opt/llama.cpp"
REMOTE = "/root/forge"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append(REMOTE)
from common import compute_plan, cost_gate, modal_spend_gate, usd_for  # noqa: E402

GPU = "T4"  # the decorator default; main() rebinds gpu and timeout from the task's compute block

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "curl", "cmake", "build-essential")
    .pip_install("unsloth", "langfuse<3", "pyyaml", "datasets")
    .run_commands(
        f"curl -sSL https://github.com/oras-project/oras/releases/download/v{ORAS_VERSION}/oras_{ORAS_VERSION}_linux_amd64.tar.gz"
        " | tar -zx -C /usr/local/bin oras",
        f"git clone --depth 1 --branch {LLAMA_CPP_TAG} https://github.com/ggml-org/llama.cpp {LLAMA_CPP_DIR}",
        # Only the quantiser is built, and with curl off: nothing here fetches a model, so the
        # rest of llama.cpp is minutes of build time for a binary no run opens. The converter is
        # the checked-out convert_hf_to_gguf.py, which needs no build at all.
        f"cmake -S {LLAMA_CPP_DIR} -B {LLAMA_CPP_DIR}/build -DCMAKE_BUILD_TYPE=Release"
        " -DLLAMA_CURL=OFF -DGGML_NATIVE=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF"
        " -DLLAMA_BUILD_SERVER=OFF",
        f"cmake --build {LLAMA_CPP_DIR}/build --target llama-quantize -j 4",
        # The converter's own requirements pin torch and transformers; installing them would
        # move the versions unsloth trained against. It runs on the image's existing torch,
        # numpy and transformers, and finds gguf through the checkout's own gguf-py.
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
    gpu: str = GPU,
) -> dict:
    env = {**os.environ, "DATASET_NAME": task, "LLAMA_CPP_DIR": LLAMA_CPP_DIR}
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
        "gpu": gpu,
        # what train.py exited with: a refusal after the gates (the GGUF export, the oras
        # push) leaves eval.json saying `passed` and is only visible here
        "exit_code": proc.returncode,
        "seconds": round(time.time() - started),
        "usd": usd_for(gpu, time.time() - started),
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
    # THE ONE PUBLISHER'S RULES, APPLIED HERE TOO.
    #
    # `.github/actions/publish-model-artifact` is the canonical writer: the oras pin, the login, the
    # media types, the versioned tag and the file list all live there, because two publishers write
    # the same artifact shape and `platform/edge-runtime` reads one shape.
    #
    # THIS FUNCTION CANNOT CALL THAT ACTION -- it runs inside a Modal GPU container, miles from any
    # GitHub workflow -- so the rules are REPEATED here rather than shared. That is a real duplicate
    # and it is named as one:
    #
    #   oras 1.2.0                 pinned in .github/actions/publish-model-artifact/action.yml
    #   GHCR_USER / GHCR_PAT       the Forge's secret; the action uses secrets.GITHUB_TOKEN
    #   application/vnd.gguf.model the media type a reader looks for
    #   ghcr.io/<user>/models/<t>:v1.<epoch>   never a bare v1, which is overwritten
    #
    # CHANGE ONE AND CHANGE THE OTHER. A test in tests/ compares the two where it can read them.
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
            "adapter:application/vnd.forge.lora-adapter.tar",  # oras tars a directory
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
    task_yaml = yaml.safe_load(
        pathlib.Path(os.path.dirname(os.path.abspath(__file__)), task_file).read_text(
            encoding="utf-8"
        )
    )
    plan = compute_plan(task_yaml)
    refusal = cost_gate(task_yaml)  # per-run worst-case budget
    # Aggregate fail-closed guard (real spend control, founder 2026-09-09): refuse BEFORE any
    # GPU bills once the committed forge/experiments/ ledger total is at/over the cap, so a card
    # cannot be reached on the free-credit plan. The ledger is the git-tracked dir on the branch
    # the workflow dispatches from (main sees every merged record).
    ledger = pathlib.Path(os.path.dirname(os.path.abspath(__file__)), "experiments")
    agg_refusal = modal_spend_gate(ledger) if ledger.is_dir() else None
    refusal = refusal or agg_refusal
    if refusal:  # the pre-launch gates: nothing is billed, the record still says why
        result = {
            "task": task,
            "task_file": task_file,
            "dry_run": dry_run,
            "max_steps": max_steps,
            "gpu": plan["gpu"],
            "exit_code": None,  # train.py never ran
            "seconds": 0,
            "usd": 0.0,
            "budget_usd": plan["budget_usd"],
            "trace": None,
            "artifact": None,
            "verdict": "refused",
            "eval": {"verdict": "refused", "refusal": refusal},
        }
    else:
        fn = run_forge.with_options(
            gpu=str(plan["gpu"]), timeout=int(plan["timeout_s"])
        )
        result = fn.remote(
            task, payload, dry_run, max_steps, task_file, str(plan["gpu"])
        )
        result["budget_usd"] = plan["budget_usd"]
    pathlib.Path(record).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))
    if result["verdict"] == "refused":
        raise SystemExit(1)
