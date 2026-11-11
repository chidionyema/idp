"""Evidence-based Greenlane batch policy and exact-root-cause failure memory.

Only advises candidate formation and repeats. Has no merge authority, external
state, credentials, model decisions, or ability to bypass required checks.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Mapping, Sequence

_HISTORY = 120
_SIZES = (1, 2, 4, 8)
_GATE = re.compile(r"\b(?:fast-gate|offline-gate|claim-gate|dof-gate|executes-gate)\b")
_URL = re.compile(r"https?://\S+")
_SHA = re.compile(r"\b[0-9a-f]{12,40}\b")
_DIAGNOSIS = re.compile(r"\b(?:FAIL|ERROR|violation|invalid|refused|missing|coverage)\b", re.I)


@dataclass(frozen=True)
class Decision:
    size: int
    observed: int
    pass_probability: float
    predicted_ci_per_lane: float

    def receipt(self) -> dict:
        return {
            "mode": "adaptive",
            "size": self.size,
            "observed": self.observed,
            "pass_probability": round(self.pass_probability, 3),
            "predicted_ci_per_lane": round(self.predicted_ci_per_lane, 3),
        }


def fingerprint(reason: str) -> str:
    """Only stable, specific gate diagnoses qualify; bare red checks do not."""
    if not reason or "--" not in reason:
        return ""
    lower = reason.lower()
    if any(w in lower for w in ("flaky", "timed out", "timeout", "rate limit", "http 405")):
        return ""
    gate = _GATE.search(lower)
    if not gate:
        return ""
    diagnosis = reason.rsplit("--", 1)[-1].strip()
    diagnosis = _URL.sub("", diagnosis)
    diagnosis = _SHA.sub("<sha>", diagnosis)
    diagnosis = " ".join(diagnosis.lower().split())
    if len(diagnosis) < 25 or not _DIAGNOSIS.search(diagnosis):
        return ""
    return hashlib.sha256((gate.group() + "\0" + diagnosis).encode()).hexdigest()[:20]


def repeated_exact_failure(history: Sequence[Mapping], lane: str, head: str, base: str, cause: str) -> bool:
    """Never equate different heads, main baselines or failure signatures."""
    return bool(cause) and any(
        row.get("base_full") == base
        and row.get("members") == [lane]
        and row.get("heads") == [head]
        and row.get("failure_id") == cause
        and row.get("outcome") in ("red", "land-refused")
        for row in history[-_HISTORY:]
    )


def _expected_checks(batch: int, p: float) -> float:
    """Proxy for CI executions, including a failed batch's bisection tree."""
    checks = 1.0
    depth = 1
    while (1 << depth) <= batch:
        children = 1 << depth
        parent_size = batch // (children // 2)
        checks += children * (1.0 - p ** parent_size)
        depth += 1
    return checks


def choose_batch_size(history: Sequence[Mapping], waiting: int, ceiling: int) -> Decision:
    """Evaluate bounded alternative sizes on one observation per exact lane/head/base.

    Historical states lacking exact member SHAs cannot train the policy. A
    conservative two-lane cold start collects new evidence; no training sample
    is fabricated by counting retries as independent outcomes.
    """
    cap = max(1, min(waiting, ceiling))
    observations: dict[tuple[str, str, str], bool] = {}
    for row in history[-_HISTORY:]:
        names, heads, base = row.get("members"), row.get("heads"), row.get("base_full")
        if (not isinstance(names, list) or len(names) != 1
            or not isinstance(heads, list) or len(heads) != 1
            or not isinstance(base, str) or len(base) != 40
            or row.get("outcome") not in ("landed", "red", "land-refused")):
            continue
        key = (str(names[0]), str(heads[0]), base)
        observations.setdefault(key, row["outcome"] == "landed")
    n = len(observations)
    p = (sum(observations.values()) + 3.0) / (n + 4.0)
    if n < 8:
        size = min(cap, 2)
    else:
        size = min((v for v in _SIZES if v <= cap),
                   key=lambda v: (_expected_checks(v, p) / v, v))
    return Decision(size, n, p, _expected_checks(size, p) / size)
