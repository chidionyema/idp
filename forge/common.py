"""Pure pieces of the Forge that a laptop can test without a GPU or a Langfuse."""

import math
import random

MIN_EXAMPLES = 500


def split(records: list[dict], seed: int = 0, train_share: float = 0.8) -> list[dict]:
    """Deterministic 80/20 split. Same records and seed give the same split, byte for byte."""
    if len(records) < MIN_EXAMPLES:
        raise ValueError(
            f"Refusal: dataset under {MIN_EXAMPLES} examples (found {len(records)})"
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
    """rows: (expected label, predicted label, margin). Agreement counts answered rows only."""
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
