"""Teacher labelling, as a batch job outside any chat session.

Raw rows in, rows in the schema train.py reads out. The teacher is a Claude model called
through the Anthropic SDK with a JSON schema on the output, so every row is a label from the
task's own label set plus a one-sentence reason. Rows the teacher marks unsure go to a rejects
file and never into the training set.

    uv run --with anthropic --with pyyaml forge/generate_teacher_dataset.py \
        --task forge/task.yaml --input client_raw.jsonl --output client_labeled.jsonl [--limit 5] [--batch]

Input: one JSON object per line with "input" (or "text"). Output: {"input", "output", "reason",
"teacher", "split"}; "output" is the label key train.py appends to the prompt. --limit N labels
the first N rows to check the schema before the full run and skips the 500-row floor.
--batch sends everything through the Message Batches API at half price and polls until done.

The door to the model is the estate's router (LAW 34): LITELLM_BASE_URL and LITELLM_API_KEY,
which the proxy answers on its Anthropic-compatible /v1/messages route, so --model is a router
alias (default: the router's `default` lane). ANTHROPIC_BASE_URL / ANTHROPIC_API_KEY, when set,
win, for a client who brings a direct Anthropic key. Nothing here names a host.

Every run persists what it labelled where a person can see it: the Langfuse dataset named after
the task (unsure rows in `<task>-unsure`), item ids derived from the text so a rerun upserts
instead of duplicating. LANGFUSE_HOST, or https://langfuse.$ESTATE_ZONE, with
LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY. The file is written first; a run that cannot reach
Langfuse exits 2 and says so, unless --no-langfuse. Commit the file under forge/datasets/ (LAW 24).
"""

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import yaml

from common import MIN_EXAMPLES, split

UNSURE = "unsure"
MAX_TOKENS = 512


def router_root(url: str | None) -> str | None:
    """The SDK appends /v1/messages itself; the router's variable is set with /v1 on the end."""
    if not url:
        return None
    url = url.rstrip("/")
    return url[: -len("/v1")] if url.endswith("/v1") else url


def read_inputs(path: str, limit: int = 0) -> list[str]:
    """Distinct non-empty inputs in file order; --limit keeps the first N."""
    seen: set[str] = set()
    out: list[str] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            text = str(row.get("input") or row.get("text") or "").strip()
            if text and text not in seen:
                seen.add(text)
                out.append(text)
            if limit and len(out) >= limit:
                break
    return out


def label_names(task: dict) -> dict[str, str]:
    """label name -> label key. task.yaml maps key -> name; the teacher speaks in names."""
    return {str(name): str(key) for key, name in task["labels"].items()}


def system_prompt(task: dict) -> str:
    names = "\n".join(f"- {name}" for name in label_names(task))
    return (
        f"You label examples for the task '{task['task']}'. The exact instruction the trained "
        f"model will see is:\n\n{task['prompt_template'].strip()}\n\n"
        f"Choose exactly one label from:\n{names}\n\n"
        f"Answer '{UNSURE}' only when the text genuinely fits none of the labels or more than "
        "one equally; that row is dropped, not guessed. Give a one-sentence reason."
    )


def output_schema(task: dict) -> dict:
    return {
        "type": "object",
        "properties": {
            "label": {"type": "string", "enum": [*label_names(task), UNSURE]},
            "reason": {"type": "string"},
        },
        "required": ["label", "reason"],
        "additionalProperties": False,
    }


def build_params(task: dict, text: str, model: str, effort: str) -> dict:
    """The Messages API params for one row, shared by the live and the batch road."""
    return {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "system": [
            {
                "type": "text",
                "text": system_prompt(task),
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "messages": [{"role": "user", "content": f"Text:\n{text}"}],
        "output_config": {
            "effort": effort,
            "format": {"type": "json_schema", "schema": output_schema(task)},
        },
    }


def parse_message(
    task: dict, text: str, message, model: str
) -> tuple[dict | None, dict | None]:
    """(accepted row, rejected row); exactly one is set."""
    if message.stop_reason == "refusal":
        return None, {"input": text, "why": "refusal"}
    answer = next((b.text for b in message.content if b.type == "text"), "")
    try:
        parsed = json.loads(answer)
    except json.JSONDecodeError:
        return None, {"input": text, "why": "unparseable", "raw": answer}
    key = label_names(task).get(str(parsed.get("label")))
    if key is None:
        return None, {"input": text, "why": UNSURE, "reason": parsed.get("reason", "")}
    return {
        "input": text,
        "output": key,
        "reason": parsed.get("reason", ""),
        "teacher": model,
    }, None


def item_id(task_name: str, text: str) -> str:
    """Stable per (task, text): a rerun updates the item instead of adding a twin."""
    return hashlib.sha256(f"{task_name}\x00{text}".encode()).hexdigest()[:32]


def dataset_items(task_name: str, rows: list[dict], rejected: list[dict]) -> list[dict]:
    """Langfuse dataset items in the shape export_langfuse.py reads back."""
    items = [
        {
            "dataset_name": task_name,
            "id": item_id(task_name, r["input"]),
            "input": {"text": r["input"]},
            "expected_output": {"label": r["output"]},
            "metadata": {
                "reason": r.get("reason", ""),
                "teacher": r.get("teacher", ""),
                "split": r.get("split", ""),
            },
        }
        for r in rows
    ]
    items += [
        {
            "dataset_name": f"{task_name}-unsure",
            "id": item_id(task_name, r["input"]),
            "input": {"text": r["input"]},
            "expected_output": {"label": ""},
            "metadata": {k: v for k, v in r.items() if k != "input"},
        }
        for r in rejected
    ]
    return items


def langfuse_host() -> str | None:
    zone = os.environ.get("ESTATE_ZONE")
    return os.environ.get("LANGFUSE_HOST") or (
        f"https://langfuse.{zone}" if zone else None
    )


def persist_langfuse(task_name: str, rows: list[dict], rejected: list[dict]) -> dict:
    from langfuse import Langfuse

    lf = Langfuse(
        host=langfuse_host(),
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
    )
    items = dataset_items(task_name, rows, rejected)
    names = sorted({i["dataset_name"] for i in items})
    for name in names:
        lf.create_dataset(name=name, description=f"Forge training data for {task_name}")
    for item in items:
        lf.create_dataset_item(**item)
    lf.flush()
    return {"host": langfuse_host(), "datasets": names, "items": len(items)}


def label_live(client, task, texts, model, effort, concurrency):
    def one(text):
        return text, client.messages.create(**build_params(task, text, model, effort))

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        for text, message in pool.map(one, texts):
            yield text, message


def label_batch(client, task, texts, model, effort, poll_s=30):
    requests = [
        {"custom_id": f"row-{i}", "params": build_params(task, t, model, effort)}
        for i, t in enumerate(texts)
    ]
    batch = client.messages.batches.create(requests=requests)
    print(f"batch {batch.id}: {len(requests)} rows", file=sys.stderr)
    while client.messages.batches.retrieve(batch.id).processing_status != "ended":
        time.sleep(poll_s)
    by_id = {}
    for result in client.messages.batches.results(batch.id):
        if result.result.type == "succeeded":
            by_id[result.custom_id] = result.result.message
    for i, text in enumerate(texts):  # results arrive in any order; key by id
        message = by_id.get(f"row-{i}")
        if message is not None:
            yield text, message


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--task", default="task.yaml")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--rejects", default=None, help="default: <output>.rejects.jsonl")
    ap.add_argument("--limit", type=int, default=0, help="label only the first N rows")
    ap.add_argument("--model", default="default", help="router alias or model id")
    ap.add_argument("--effort", default="medium", choices=["low", "medium", "high"])
    ap.add_argument(
        "--batch", action="store_true", help="Message Batches API, half price"
    )
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--no-langfuse", action="store_true", help="file only, nothing persisted"
    )
    args = ap.parse_args(argv)

    import anthropic

    with open(args.task, encoding="utf-8") as f:
        task = yaml.safe_load(f)
    texts = read_inputs(args.input, args.limit)
    client = anthropic.Anthropic(
        base_url=router_root(
            os.environ.get("ANTHROPIC_BASE_URL") or os.environ.get("LITELLM_BASE_URL")
        ),
        api_key=os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("LITELLM_API_KEY"),
    )
    road = label_batch if args.batch else label_live
    kwargs = {} if args.batch else {"concurrency": args.concurrency}
    accepted, rejected = [], []
    for text, message in road(client, task, texts, args.model, args.effort, **kwargs):
        row, reject = parse_message(task, text, message, args.model)
        (accepted if row else rejected).append(row or reject)

    rows = split(accepted, seed=args.seed, minimum=0 if args.limit else MIN_EXAMPLES)
    with open(args.output, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    rejects_path = args.rejects or f"{args.output}.rejects.jsonl"
    with open(rejects_path, "w", encoding="utf-8") as f:
        for row in rejected:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    counts = {}
    for row in rows:
        counts[row["output"]] = counts.get(row["output"], 0) + 1
    summary = {
        "input_rows": len(texts),
        "labelled": len(rows),
        "rejected": len(rejected),
        "per_label": counts,
        "output": args.output,
        "rejects": rejects_path,
        "trains": len(rows) >= MIN_EXAMPLES,
        "persisted": None,
    }
    code = 0
    if not args.no_langfuse:
        if langfuse_host() and os.environ.get("LANGFUSE_SECRET_KEY"):
            summary["persisted"] = persist_langfuse(task["task"], rows, rejected)
        else:
            summary["persisted"] = (
                "NOT PERSISTED: no Langfuse door or keys in the environment"
            )
            code = 2
    print(json.dumps(summary), file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
