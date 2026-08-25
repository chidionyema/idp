"""Auto-distillation (R18/R20, spec 3.3): every successful frontier step
becomes a training row; routing follows a measured number.

The pipeline, in order, each step a function here:

1. `capture()`  -- a step that finished "done" on a frontier model lands
   in the distillation queue and in the Langfuse dataset for its task
   class (prompt, completion, tool calls, tagged with the class).
2. `train()`    -- the queue feeds a local LoRA job. The tool is chosen by
   config (distill.trainer: ollama or axolotl) and invoked as a
   subprocess from a config command template; this module never
   reimplements either tool.
3. `grade()`    -- a deterministic grader (normalized exact match against
   the recorded completion) runs the local model over the dataset and
   produces local_accuracy. No model judges another model.
4. `route()`    -- at or above distill.route_accuracy the LiteLLM route
   for that class is set to the local model, and the change is a receipt.
   Below it, nothing changes and the receipt says so.

Langfuse is the mature dataset store (LAW 43) and is used when
configured. Every item is also mirrored to a local JSONL under
$ESTATE_HOME/sovereign/distill, for two reasons: the grade must never
depend on the network being up (spec 5: blind execution is unacceptable,
and a grade that could not read its own dataset would be exactly that),
and the acceptance suite has to be able to assert an item exists without
a Langfuse server.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import uuid
from pathlib import Path
from typing import Any, Callable

import httpx

from sovereign import config
from sovereign.engine import receipts as receipts_mod
from sovereign.engine import tracing
from sovereign.shadow import config_keys as ck

Completer = Callable[[str], str]

_WS_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def distill_dir() -> Path:
    base = ck.get("distill.dir")
    d = Path(base) if base else config.SOVEREIGN_HOME / "distill"
    d.mkdir(parents=True, exist_ok=True)
    return d


def queue_path() -> Path:
    return distill_dir() / str(ck.get("distill.queue_filename"))


def dataset_path() -> Path:
    return distill_dir() / str(ck.get("distill.dataset_filename"))


def routes_path() -> Path:
    return distill_dir() / str(ck.get("distill.routes_filename"))


def dataset_name(task_class: str) -> str:
    return str(ck.get("distill.dataset_name_format")).format(task_class=task_class)


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out


# ---------------------------------------------------------------------------
# 1. capture
# ---------------------------------------------------------------------------


def is_frontier(model: str) -> bool:
    name = str(model).strip().lower()
    return any(name == f or name.startswith(f) for f in (str(x).lower() for x in ck.get("distill.frontier_models")))


def _push_to_langfuse(item: dict[str, Any]) -> bool:
    """Best effort: the mirror is already written. Returns True only when
    Langfuse accepted the item."""
    if not tracing.configured():
        return False
    client = tracing._get_client()  # pyright: ignore[reportPrivateUsage]
    if client is None:
        return False
    try:
        name = item["dataset"]
        client.create_dataset(name=name)
    except Exception:
        pass
    try:
        client.create_dataset_item(
            dataset_name=item["dataset"],
            input=item["input"],
            expected_output=item["expected_output"],
            metadata=item["metadata"],
            id=item["id"],
        )
        return True
    except Exception:
        return False


def capture(step: dict[str, Any]) -> dict[str, Any] | None:
    """Spec 3.3 steps 1-2. `step` carries session_id, task_class, model,
    status, prompt, completion, tool_calls. Returns the dataset item, or
    None when the step is not a frontier success and nothing was
    captured."""
    if str(step.get("status")) != str(ck.get("distill.done_status")):
        return None
    if not is_frontier(str(step.get("model") or step.get("runner") or "")):
        return None
    task_class = str(step["task_class"])
    item = {
        "id": uuid.uuid4().hex,
        "dataset": dataset_name(task_class),
        "task_class": task_class,
        "input": str(step.get("prompt", "")),
        "expected_output": str(step.get("completion", "")),
        "metadata": {
            "tool_calls": list(step.get("tool_calls") or []),
            "tags": [task_class],
            "session_id": step.get("session_id"),
            "model": step.get("model") or step.get("runner"),
            "context": step.get("context", ""),
        },
    }
    _append_jsonl(queue_path(), {"item_id": item["id"], "task_class": task_class, "session_id": step.get("session_id")})
    item["langfuse"] = _push_to_langfuse(item)
    _append_jsonl(dataset_path(), item)
    return item


def items(task_class: str) -> list[dict[str, Any]]:
    return [i for i in _read_jsonl(dataset_path()) if i.get("task_class") == task_class]


# ---------------------------------------------------------------------------
# 2. train
# ---------------------------------------------------------------------------


def _write_ollama_modelfile(task_class: str, dataset: Path) -> Path:
    """Ollama takes a Modelfile; the adapter it names is what the LoRA
    job produces. The base model is the configured local model."""
    path = distill_dir() / f"{task_class}.Modelfile"
    path.write_text(
        f"FROM {ck.get('distill.local_model')}\n"
        f"# distilled from {dataset}\n"
        f"ADAPTER ./{task_class}-lora\n"
    )
    return path


def _write_axolotl_config(task_class: str, dataset: Path) -> Path:
    path = distill_dir() / f"{task_class}.axolotl.yml"
    path.write_text(
        f"base_model: {ck.get('distill.local_model')}\n"
        "adapter: lora\n"
        "datasets:\n"
        f"  - path: {dataset}\n"
        "    type: completion\n"
        f"output_dir: {distill_dir() / (task_class + '-lora')}\n"
    )
    return path


def train_command(task_class: str) -> list[str]:
    trainer = str(ck.get("distill.trainer")).strip().lower()
    dataset = dataset_path()
    model = f"{ck.get('distill.local_model')}-{task_class}"
    if trainer == "axolotl":
        cfg = _write_axolotl_config(task_class, dataset)
        template = str(ck.get("distill.axolotl_command"))
        return shlex.split(template.format(config=cfg, dataset=dataset, model=model, task_class=task_class))
    if trainer == "ollama":
        modelfile = _write_ollama_modelfile(task_class, dataset)
        template = str(ck.get("distill.ollama_command"))
        return shlex.split(template.format(model=model, modelfile=modelfile, dataset=dataset, task_class=task_class))
    raise ValueError(f"distill.trainer must be ollama or axolotl, not {trainer!r}")


def train(task_class: str) -> dict[str, Any]:
    """Run the local LoRA job through the configured tool. The command is
    the whole contract: swapping trainers is a config change."""
    argv = train_command(task_class)
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=int(ck.get("distill.train_timeout_s")))
    return {
        "trainer": str(ck.get("distill.trainer")),
        "command": argv,
        "returncode": int(proc.returncode),
        "ok": proc.returncode == 0,
        "stderr_tail": (proc.stderr or "")[-500:],
    }


# ---------------------------------------------------------------------------
# 3. grade
# ---------------------------------------------------------------------------


def normalize(text: str) -> str:
    return _WS_RE.sub(" ", str(text)).strip().lower()


def local_completer(model: str | None = None) -> Completer:
    """One completion against the local model through LiteLLM."""
    model_name = model or str(ck.get("distill.local_model"))
    if not config.LITELLM_BASE_URL:
        raise RuntimeError("LITELLM_BASE_URL is not configured; the local model cannot be graded")
    url = str(config.LITELLM_BASE_URL) + config.LITELLM_CHAT_COMPLETIONS_PATH
    headers = {"Authorization": f"Bearer {config.LITELLM_API_KEY}"} if config.LITELLM_API_KEY else {}

    def _complete(prompt: str) -> str:
        body = {"model": model_name, "temperature": 0, "max_tokens": int(ck.get("distill.grade_max_tokens")),
                "messages": [{"role": "user", "content": prompt}]}
        resp = httpx.post(url, json=body, headers=headers, timeout=float(ck.get("distill.grade_timeout_s")))
        resp.raise_for_status()
        choices = resp.json().get("choices") or [{}]
        return str((choices[0].get("message") or {}).get("content") or "")

    return _complete


def grade(task_class: str, complete: Completer) -> dict[str, Any]:
    """Deterministic grader: the local model's answer matches the recorded
    frontier completion after whitespace/case normalization. One number
    per item, no judge model."""
    rows = items(task_class)
    minimum = int(ck.get("distill.min_items"))
    if len(rows) < minimum:
        return {"task_class": task_class, "items": len(rows), "min_items": minimum, "measured": False,
                "correct": 0, "local_accuracy": None}
    correct = 0
    for row in rows:
        try:
            answer = complete(str(row.get("input", "")))
        except Exception:
            answer = ""
        if normalize(answer) == normalize(str(row.get("expected_output", ""))):
            correct += 1
    return {"task_class": task_class, "items": len(rows), "min_items": minimum, "measured": True,
            "correct": correct, "local_accuracy": correct / len(rows)}


# ---------------------------------------------------------------------------
# 4. route
# ---------------------------------------------------------------------------


def routes() -> dict[str, str]:
    p = routes_path()
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return {str(k): str(v) for k, v in dict(data).items()}


def _write_routes(table: dict[str, str]) -> None:
    p = routes_path()
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(table, sort_keys=True, indent=2) + "\n")
    os.replace(tmp, p)


def route(task_class: str, graded: dict[str, Any], frontier_model: str | None = None) -> dict[str, Any]:
    """Flip the route only on a measured number at or above the
    threshold. Every call writes a receipt, flip or not, so a class that
    stays on the frontier has evidence of why."""
    threshold = float(ck.get("distill.route_accuracy"))
    local = str(ck.get("distill.local_model"))
    table = routes()
    accuracy = graded.get("local_accuracy")
    current = table.get(task_class, frontier_model or "")
    flipped = graded.get("measured", False) and accuracy is not None and float(accuracy) >= threshold
    model = local if flipped else current
    if flipped:
        table[task_class] = local
        _write_routes(table)
    line = str(ck.get("distill.receipt_line_format")).format(
        task_class=task_class, accuracy=float(accuracy or 0.0), model=model or "frontier"
    )
    receipt = receipts_mod.append(
        {
            "session_id": f"distill-{task_class}",
            "kind": str(ck.get("distill.receipt_kind")),
            "by": "engine",
            "text": line,
            "step": 0,
            "status": "done",
            "task_class": task_class,
            "local_accuracy": accuracy,
            "items": graded.get("items", 0),
            "threshold": threshold,
            "routing": model or None,
            "flipped": bool(flipped),
        }
    )
    return {"task_class": task_class, "local_accuracy": accuracy, "threshold": threshold, "routing": model or None,
            "flipped": bool(flipped), "receipt": receipt, "text": line}


def run(task_class: str, complete: Completer | None = None, *, do_train: bool = True) -> dict[str, Any]:
    """`sb distill --task-class X`: train, grade, route, receipt."""
    out: dict[str, Any] = {"task_class": task_class, "items": len(items(task_class))}
    if out["items"] < int(ck.get("distill.min_items")):
        out["measured"] = False
        out["local_accuracy"] = None
        out["min_items"] = int(ck.get("distill.min_items"))
        out["routing"] = routes().get(task_class)
        return out
    if do_train:
        out["train"] = train(task_class)
    graded = grade(task_class, complete or local_completer())
    out.update({k: graded[k] for k in ("measured", "correct", "local_accuracy", "min_items")})
    routed = route(task_class, graded)
    out.update({"routing": routed["routing"], "flipped": routed["flipped"], "receipt": routed["receipt"],
                "text": routed["text"], "threshold": routed["threshold"]})
    return out
