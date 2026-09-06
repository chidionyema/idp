"""Pure pieces of the Forge that a laptop can test without a GPU or a Langfuse."""

import math
import random

MIN_EXAMPLES = 500

# Modal on-demand list prices, USD per GPU-hour, read from modal.com/pricing on 2026-09-06. A GPU
# not in this table is refused: an unpriced run cannot be budgeted (fail closed).
GPU_USD_PER_HOUR = {
    "T4": 0.59,
    "L4": 0.80,
    "A10G": 1.10,
    "L40S": 1.95,
    "A100": 2.10,
    "A100-80GB": 2.50,
    "H100": 3.95,
    "H200": 4.54,
    "B200": 6.25,
}
DEFAULT_COMPUTE = {"gpu": "T4", "timeout_s": 3600, "budget_usd": 1.00}


def compute_plan(task: dict) -> dict:
    """The task's compute block with defaults filled; the worst case a run may bill."""
    return {**DEFAULT_COMPUTE, **(task.get("compute") or {})}


def usd_for(gpu: str, seconds: float) -> float:
    return round(GPU_USD_PER_HOUR[gpu] * seconds / 3600, 4)


def cost_gate(task: dict) -> str | None:
    """None when the worst-case bill fits the task's budget, else the refusal. Kind, base and
    model size are never grounds for refusal; cost is the only pre-launch gate."""
    plan = compute_plan(task)
    gpu = str(plan["gpu"])
    if gpu not in GPU_USD_PER_HOUR:
        return f"GPU {gpu!r} has no price in GPU_USD_PER_HOUR; an unpriced run cannot be budgeted"
    worst = usd_for(gpu, float(plan["timeout_s"]))
    if worst > float(plan["budget_usd"]):
        return (
            f"worst case ${worst:.2f} ({gpu} x {plan['timeout_s']}s) exceeds budget_usd "
            f"{float(plan['budget_usd']):.2f}; lower timeout_s, pick a cheaper GPU or raise the budget"
        )
    return None


def split(
    records: list[dict],
    seed: int = 0,
    train_share: float = 0.8,
    minimum: int = MIN_EXAMPLES,
) -> list[dict]:
    """Deterministic 80/20 split. Same records and seed give the same split, byte for byte.

    `minimum` is the refusal floor; only a schema check (--limit) lowers it."""
    if len(records) < minimum:
        raise ValueError(
            f"Refusal: dataset under {minimum} examples (found {len(records)})"
        )
    order = list(range(len(records)))
    random.Random(seed).shuffle(order)  # noqa: S311  a split, not a secret
    cut = int(len(records) * train_share)
    out = []
    for rank, idx in enumerate(order):
        row = dict(records[idx])
        row["split"] = "train" if rank < cut else "eval"
        out.append(row)
    return out


def label_probs(label_logits: dict[str, float]) -> tuple[str, float, float]:
    """Softmax over the label candidates only. Returns (top label, its p, margin to second)."""
    m = max(label_logits.values())
    exps = {k: math.exp(v - m) for k, v in label_logits.items()}
    z = sum(exps.values())
    ranked = sorted(((e / z, k) for k, e in exps.items()), reverse=True)
    top_p, top = ranked[0]
    second = ranked[1][0] if len(ranked) > 1 else 0.0
    return top, top_p, top_p - second


def grade(rows: list[tuple[str, str, float]], abstain_below: float) -> dict:
    """rows: (expected label, predicted label, margin). Agreement counts answered rows only,
    so it is gated together with abstain_rate: a model that abstains its way to agreement fails
    task.yaml max_abstain."""
    total = len(rows)
    abstains = sum(1 for _, _, margin in rows if margin < abstain_below)
    correct = sum(
        1 for exp, pred, margin in rows if margin >= abstain_below and exp == pred
    )
    answered = total - abstains
    return {
        "held_out": total,
        "agreement": (correct / answered) if answered else 0.0,
        "abstain_rate": (abstains / total) if total else 1.0,
    }
