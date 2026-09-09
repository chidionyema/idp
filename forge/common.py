"""Pure pieces of the Forge that a laptop can test without a GPU or a Langfuse."""

import math
import os
import pathlib
import random
import yaml

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


# Modal free-credit ceiling guard. The estate's Modal account is on the Starter plan's
# $30/month free credit pool (spec 2026-09-06 line 58/256), with NO native monthly aggregate cap
# and NO fail-closed below-a-card. This refunds a run that would spend the ledger past the cap
# BEFORE a GPU bills, so a card can never be reached. Default $5 is a working guard far under the
# $30 credit; raise it only with founder sign-off on the spend.
DEFAULT_MONTHLY_CAP_USD = 5.00


def _record_usd(front: dict) -> float:
    """usd a completed Forge run actually billed, from its front matter; 0 for plans/refusals with
    no spend field or a None value. A run that did not happen has no usd to count."""
    v = front.get("usd")
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def spend_from_ledger(experiments_dir: str | os.PathLike[str]) -> list[dict]:
    """Every spend-bearing record under experiments_dir, as {file, usd}. Reads the YAML front
    matter between the first `---` pair of each committed forge/experiments/<stamp>-<task>.md .
    Returns [] when the dir is absent or empty (no runs => no spend)."""
    import re

    root = pathlib.Path(experiments_dir)
    if not root.is_dir():
        return []
    rows: list[dict] = []
    for path in sorted(root.glob("[0-9]*T*-*.md")):
        text = path.read_text(encoding="utf-8")
        m = re.match(r"\A---\n(.*?)\n---", text, re.S)
        if not m:
            continue
        try:
            front = yaml.safe_load(m.group(1)) or {}
        except (
            yaml.YAMLError,
            ValueError,
        ):  # malformed front matter is not a spend record
            continue
        usd = _record_usd(front)
        if usd:
            rows.append({"file": path.name, "usd": round(usd, 4)})
    return rows


def total_spend(experiments_dir: str | os.PathLike[str]) -> float:
    """Cumulative Modal USD across all recorded forge runs in the ledger."""
    return round(sum(r["usd"] for r in spend_from_ledger(experiments_dir)), 4)


def modal_spend_gate(
    experiments_dir: str | os.PathLike[str],
    cap_usd: float = DEFAULT_MONTHLY_CAP_USD,
) -> str | None:
    """None when cumulative logged spend is under the cap, else a refusal string. Fail closed: once
    the ledger total is at/over the cap no new Modal run may dispatch. The one pre-launch money
    guard next to cost_gate (per-run); this is the aggregate one."""
    tot = total_spend(experiments_dir)
    if tot >= cap_usd:
        return (
            f"cumulative Modal spend ${tot:.2f} is at/over the ${cap_usd:.2f} cap; "
            "refusing dispatch so no card payment is reached (forge/common.py modal_spend_gate)"
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


# --- the capability envelope -------------------------------------------------------------
# Founder, 2026-09-09: "we need to prove that it can be useful oeprtionally ... we neeedto
# find itslinits also, what it cannot doreliably ... and whatis can ... and where th edge is
# ... and if anywy to nove tht edgefrowrd int he firectionof tnprovenen."
#
# One agreement number cannot answer any of those. A model that answers only the easy 80% of
# a lopsided set scores 98% and is still useless on the label anyone cares about. So the eval
# reports what it took on, what it got wrong, per label; where the confident/decline boundary
# actually sits; and which lever moves that boundary. Every number below is computed from the
# same (expected, predicted, margin) rows the gates are computed from -- no second GPU pass.

FRONTIER_STEPS = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99)
THIN_SUPPORT = 30  # held-out rows under which a per-label reading is not worth quoting


def majority_agreement(rows: list[tuple[str, str, float]]) -> dict:
    """The score of answering every row with whichever label is commonest. The floor any
    trained model has to beat before 'it learned something' means anything."""
    if not rows:
        return {"label": None, "agreement": 0.0}
    counts: dict[str, int] = {}
    for expected, _, _ in rows:
        counts[expected] = counts.get(expected, 0) + 1
    label = max(counts, key=lambda k: (counts[k], k))
    return {"label": label, "agreement": counts[label] / len(rows)}


def envelope(rows: list[tuple[str, str, float]], abstain_below: float) -> dict:
    """What the model took on and what it got wrong, per label, on the answered rows.

    `recall` is of the rows that truly carry the label and were answered: the share of real
    label-X cases the model would catch. `precision` is of the rows it called X: how often
    that call is right. A model can hold high agreement while its recall on a rare label is
    zero, and that is the operational limit the single number hides.
    """
    labels = sorted({expected for expected, _, _ in rows} | {p for _, p, _ in rows})
    per: dict[str, dict] = {
        lab: {
            "support": 0,
            "answered": 0,
            "abstained": 0,
            "correct": 0,
            "called": 0,
            "recall_answered": None,
            "precision": None,
        }
        for lab in labels
    }
    confusion: dict[str, dict[str, int]] = {a: {b: 0 for b in labels} for a in labels}
    answered = correct = 0
    for expected, predicted, margin in rows:
        per[expected]["support"] += 1
        if margin < abstain_below:
            per[expected]["abstained"] += 1
            continue
        answered += 1
        per[expected]["answered"] += 1
        per[predicted]["called"] += 1
        confusion[expected][predicted] += 1
        if expected == predicted:
            correct += 1
            per[expected]["correct"] += 1
    for r in per.values():
        if r["answered"]:
            r["recall_answered"] = r["correct"] / r["answered"]
        if r["called"]:
            r["precision"] = r["correct"] / r["called"]
        r["thin"] = r["support"] < THIN_SUPPORT
    return {
        "answered": answered,
        "correct": correct,
        "wrong": answered - correct,
        "declined": len(rows) - answered,
        "per_label": per,
        "confusion": confusion,
    }


def frontier(
    rows: list[tuple[str, str, float]], steps: tuple[float, ...] = FRONTIER_STEPS
) -> list[dict]:
    """Coverage against agreement as the abstain threshold moves: where the edge actually is.

    The threshold in the task file is one point on this curve. The curve says what the other
    points would have bought, which is the only honest way to argue for moving it.
    """
    out = []
    for t in steps:
        answered = [(e, p) for e, p, m in rows if m >= t]
        correct = sum(1 for e, p in answered if e == p)
        out.append(
            {
                "abstain_below": t,
                "coverage": len(answered) / len(rows) if rows else 0.0,
                "answered": len(answered),
                "correct": correct,
                "agreement": correct / len(answered) if answered else 0.0,
            }
        )
    return out


def next_move(
    env: dict, curve: list[dict], task: dict, baseline: dict | None
) -> list[str]:
    """Which lever moves the edge forward, read off the numbers rather than guessed.

    Four levers, in the order they are worth pulling: the model did not learn (retrain or
    change the base), a label has too few held-out rows to judge (label more of it), a label
    is learned but never caught (the data is lopsided), and the threshold is leaving free
    coverage on the table (move the threshold).
    """
    moves: list[str] = []
    lift = None
    if baseline and baseline.get("agreement") is not None:
        lift = env.get("agreement_answered", 0.0) - baseline["agreement"]
        if lift <= 0.0:
            moves.append(
                "the trained model does not beat the untrained one on the same rows: "
                "training bought nothing, so change the base model or the prompt before "
                "spending another GPU hour"
            )
    for lab, r in sorted(env["per_label"].items()):
        if r["thin"]:
            moves.append(
                f"label `{lab}` has {r['support']} held-out rows, under {THIN_SUPPORT}: "
                f"nothing about `{lab}` is settled either way; label more of it"
            )
        elif r["recall_answered"] is not None and r["recall_answered"] < 0.5:
            moves.append(
                f"label `{lab}` is answered but missed more often than caught "
                f"(recall {r['recall_answered']:.0%}): the corpus is lopsided against it, "
                "so add rows of that label rather than rows in general"
            )
    here = task["abstain_below"]
    at_here = next((p for p in curve if abs(p["abstain_below"] - here) < 1e-9), None)
    if at_here:
        cheaper = [
            p
            for p in curve
            if p["abstain_below"] < here
            and p["coverage"] > at_here["coverage"] + 0.05
            and p["agreement"] >= task["min_agreement"]
        ]
        if cheaper:
            best = max(cheaper, key=lambda p: p["coverage"])
            moves.append(
                f"the threshold is set conservatively: at abstain_below {best['abstain_below']} "
                f"the model would answer {best['coverage']:.0%} of rows instead of "
                f"{at_here['coverage']:.0%} and still hold {best['agreement']:.1%} agreement, "
                f"over the {task['min_agreement']:.0%} floor"
            )
    if not moves:
        moves.append(
            "no lever is indicated by this run's numbers: the labels all carry enough rows, "
            "each is caught more often than missed, and the threshold is not leaving "
            "coverage on the table"
        )
    return moves
