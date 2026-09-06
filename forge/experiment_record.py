"""One Forge run, written up as an experiment: forge/experiments/<utc>-<task>.md

    python forge/experiment_record.py --task forge/task.yaml --run forge-run.json \
        [--data forge/datasets/<task>.jsonl] [--out forge/experiments]

The record has a YAML front matter (machine-readable: verdict, agreement, dataset hash, trace,
artifact) and seven sections: hypothesis, setup, data, pre-registered gates, results, provenance,
reproduce. Every run leaves one, refused or dry or shipped; a run with no record did not happen.
"""

import argparse
import json
import math
import os
import pathlib
import subprocess
import sys
import time
from collections import Counter

import yaml

MIN_EXAMPLES = 500  # forge/common.py; the split refuses under it


def git_sha() -> str:
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    try:
        return subprocess.run(  # noqa: S603,S607
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def run_url() -> str | None:
    if not os.environ.get("GITHUB_RUN_ID"):
        return None
    return f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{os.environ['GITHUB_RUN_ID']}"


def langfuse_host() -> str | None:
    zone = os.environ.get("ESTATE_ZONE")
    return os.environ.get("LANGFUSE_HOST") or (
        f"https://langfuse.{zone}" if zone else None
    )


def data_summary(rows: list[dict] | None) -> dict:
    if not rows:
        return {"per_label": {}, "teachers": [], "splits": {}}
    return {
        "per_label": dict(sorted(Counter(r.get("output", "") for r in rows).items())),
        "teachers": sorted({r["teacher"] for r in rows if r.get("teacher")}),
        "splits": dict(Counter(r.get("split", "") for r in rows)),
    }


def half_width(p: float, n: int) -> float:
    """95% normal-approximation half width of a proportion; what n held-out rows can resolve."""
    return 1.96 * math.sqrt(p * (1 - p) / n) if n else 1.0


def table(pairs: list[tuple[str, object]]) -> str:
    out = ["| field | value |", "|---|---|"]
    for k, v in pairs:
        out.append(f"| {k} | {'' if v is None else v} |")
    return "\n".join(out)


def render(task: dict, run: dict, rows: list[dict] | None, context: dict) -> str:
    ev = run.get("eval", {})
    ds = run.get("dataset") or {}
    summary = data_summary(rows)
    stamp = context["stamp"]
    verdict = run.get("verdict", "unknown")
    agreement = ev.get("agreement")
    abstain = ev.get("abstain_rate")
    held = ev.get("held_out", 0)
    front = {
        "experiment": f"{stamp}-{task['task']}",
        "task": task["task"],
        "base": task["base"],
        "verdict": verdict,
        "dry_run": bool(run.get("dry_run")),
        "held_out": held,
        "agreement": agreement,
        "abstain_rate": abstain,
        "min_agreement": task["min_agreement"],
        "max_abstain": task["max_abstain"],
        "dataset_sha256": ds.get("sha256"),
        "dataset_rows": ds.get("rows"),
        "trace": run.get("trace"),
        "artifact": run.get("artifact"),
        "forge_commit": context["sha"],
        "run_url": context.get("run_url"),
    }
    hypothesis = task.get("hypothesis") or (
        f"A LoRA (r={task['lora']['r']}) on {task['base']}, trained on the teacher-labelled "
        f"train split, agrees with the teacher on at least {task['min_agreement']:.0%} of the "
        f"held-out rows it answers while abstaining on at most {task['max_abstain']:.0%} of them "
        f"(abstain when the top-two label margin is under {task['abstain_below']})."
    )
    labels = ", ".join(f"`{k}` = {v}" for k, v in task["labels"].items())
    trace_line = run.get("trace")
    if trace_line and context.get("langfuse_host"):
        trace_line = f"{context['langfuse_host']}/trace/{run['trace']}"
    if verdict == "shipped":
        outcome = f"PASSED both gates; model pushed as `{run['artifact']}`."
    elif verdict == "dry-run":
        outcome = "Dry run: gates graded, nothing pushed."
    elif verdict == "refused":
        outcome = f"REFUSED: {ev.get('refusal')}. No model left the Forge."
    else:
        outcome = f"Verdict `{verdict}`."
    if held:
        hw = half_width(agreement or 0.0, held)
        resolution = (
            f"{held} held-out rows resolve agreement to about ±{hw:.1%} (95%, normal "
            f"approximation), so a reading within that band of {task['min_agreement']:.0%} is "
            "not a settled pass or fail; label more rows before trusting it."
        )
    else:
        resolution = "No held-out rows were graded."
    reproduce = f"""```
# 1. label (the teacher through the router; persisted to Langfuse + git)
uv run --with anthropic --with pyyaml --with 'langfuse<3' forge/generate_teacher_dataset.py \\
    --task {context["task_path"]} --input raw.jsonl --output forge/datasets/{task["task"]}.jsonl
# 2. train on Modal from CI (the only road; the root is set once by bin/idp-set-root modal)
gh workflow run forge-train.yml -f task_file={context["task_path"]} -f dry_run={str(bool(run.get("dry_run"))).lower()} -f max_steps={run.get("max_steps", -1)}
# 3. this record
python forge/experiment_record.py --task {context["task_path"]} --run forge-run.json --data forge/datasets/{task["task"]}.jsonl
```"""
    body = f"""---
{yaml.safe_dump(front, sort_keys=False).rstrip()}
---

# Forge experiment {stamp}: {task["task"]}

{outcome}

## 1. Hypothesis

{hypothesis}

## 2. Setup

{
        table(
            [
                ("base model", task["base"]),
                ("kind", task["kind"]),
                ("labels", labels),
                (
                    "LoRA",
                    f"r={task['lora']['r']}, alpha={task['lora']['alpha']}, epochs={task['lora']['epochs']}, lr={task['lora']['lr']}",
                ),
                ("max_steps", run.get("max_steps", -1)),
                ("GPU", run.get("gpu")),
                ("train wall time (s)", run.get("seconds")),
                ("forge commit", context["sha"]),
                ("task file", context["task_path"]),
                ("CI run", context.get("run_url")),
            ]
        )
    }

Prompt template:

```
{task["prompt_template"].rstrip()}
```

## 3. Data

{
        table(
            [
                ("rows", ds.get("rows")),
                ("train / eval", f"{ds.get('train')} / {ds.get('eval')}"),
                ("sha256", ds.get("sha256")),
                ("per label", json.dumps(summary["per_label"])),
                (
                    "teacher(s)",
                    ", ".join(summary["teachers"]) or "not recorded in rows",
                ),
                ("Langfuse dataset", ds.get("langfuse_dataset")),
                ("file", context.get("data_path")),
            ]
        )
    }

Labels come from the teacher run (forge/generate_teacher_dataset.py), never from a public
benchmark; rows the teacher marked unsure are in the `-unsure` Langfuse dataset and not here.

## 4. Pre-registered gates

{
        table(
            [
                ("minimum rows", f"{MIN_EXAMPLES} (80/20 split, seed 0)"),
                (
                    "abstain_below",
                    f"{task['abstain_below']} margin between the top two label probabilities",
                ),
                ("min_agreement", f"{task['min_agreement']} on answered held-out rows"),
                ("max_abstain", f"{task['max_abstain']} of held-out rows"),
            ]
        )
    }

Both gates are graded before any export. Agreement bought by abstaining is refused by the
second gate.

## 5. Results

{
        table(
            [
                ("held-out rows", held),
                ("agreement (answered rows)", agreement),
                ("abstain rate", abstain),
                (
                    "min_agreement met",
                    None if agreement is None else agreement >= task["min_agreement"],
                ),
                (
                    "max_abstain met",
                    None if abstain is None else abstain <= task["max_abstain"],
                ),
                ("verdict", verdict),
                ("refusal", ev.get("refusal")),
            ]
        )
    }

{resolution}

## 6. Provenance

{
        table(
            [
                ("Langfuse trace", trace_line),
                ("artifact (GHCR)", run.get("artifact")),
                ("dataset sha256", ds.get("sha256")),
                ("forge commit", context["sha"]),
                ("CI run", context.get("run_url")),
            ]
        )
    }

## 7. Reproduce

{reproduce}
"""
    return body


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--task", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--data", default=None)
    ap.add_argument("--out", default="forge/experiments")
    args = ap.parse_args(argv)
    task = yaml.safe_load(pathlib.Path(args.task).read_text(encoding="utf-8"))
    run = json.loads(pathlib.Path(args.run).read_text(encoding="utf-8"))
    rows = None
    if args.data and pathlib.Path(args.data).exists():
        rows = [
            json.loads(line)
            for line in pathlib.Path(args.data).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    context = {
        "stamp": time.strftime("%Y%m%dT%H%MZ", time.gmtime()),
        "sha": git_sha(),
        "run_url": run_url(),
        "langfuse_host": langfuse_host(),
        "task_path": args.task,
        "data_path": args.data,
    }
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{context['stamp']}-{task['task']}.md"
    path.write_text(render(task, run, rows, context), encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
