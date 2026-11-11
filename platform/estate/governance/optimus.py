"""The estate's single `optimus.metric.v1` sender for non-router producers."""

from __future__ import annotations

import fcntl
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "optimus.metric.v1"
STATUSES = {"OK", "DEGRADED", "FAILED", "BLIND"}
SAFE = re.compile(r"^[A-Za-z0-9._:/@-]{2,180}$")
SECRET_LABEL = re.compile(r"(api[_-]?key|authorization|password|secret|token)", re.I)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def ledger_path() -> Path:
    return Path(
        os.environ.get("OPTIMUS_METRICS_PATH", "~/.estate/optimus/metrics.jsonl")
    ).expanduser()


def validate(metric: dict) -> None:
    required = {
        "schema",
        "metricId",
        "observedAt",
        "source",
        "subject",
        "metric",
        "value",
        "unit",
        "status",
        "window",
        "evidence",
        "labels",
    }
    missing = sorted(required - set(metric))
    extra = sorted(set(metric) - required)
    if missing or extra:
        raise ValueError(f"fields missing={missing} extra={extra}")
    if metric["schema"] != SCHEMA:
        raise ValueError(f"schema must be {SCHEMA}")
    for field in ("metricId", "source", "subject", "metric"):
        if not isinstance(metric[field], str) or not SAFE.match(metric[field]):
            raise ValueError(f"{field} is not a safe Optimus identifier")
    if not isinstance(metric["value"], (int, float)) or isinstance(
        metric["value"], bool
    ):
        raise ValueError("value must be numeric")
    if metric["status"] not in STATUSES:
        raise ValueError(f"status must be one of {sorted(STATUSES)}")
    if not isinstance(metric["labels"], dict) or len(metric["labels"]) > 32:
        raise ValueError("labels must be an object with at most 32 entries")
    for key, value in metric["labels"].items():
        if SECRET_LABEL.search(key):
            raise ValueError(f"label {key!r} names a credential")
        if not isinstance(value, str) or len(value) > 200:
            raise ValueError(f"label {key!r} must be a string of at most 200 chars")
    if len(str(metric["unit"])) > 40 or len(str(metric["window"])) > 80:
        raise ValueError("unit or window exceeds its contract limit")
    if len(str(metric["evidence"])) > 2000:
        raise ValueError("evidence exceeds 2000 characters")


def emit(metric: dict) -> bool:
    """Append once by metricId. Returns True when written, False for a duplicate."""
    validate(metric)
    path = ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(".lock")
    with lock.open("a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        if path.is_file():
            for line in path.read_text(errors="replace").splitlines():
                try:
                    if json.loads(line).get("metricId") == metric["metricId"]:
                        return False
                except ValueError:
                    continue
        with path.open("a", encoding="utf-8") as out:
            out.write(json.dumps(metric, sort_keys=True, separators=(",", ":")) + "\n")
        os.chmod(path, 0o600)
        fcntl.flock(handle, fcntl.LOCK_UN)
    return True


def metric(
    *,
    source: str,
    subject: str,
    name: str,
    value: float,
    unit: str,
    status: str,
    window: str,
    evidence: str,
    labels: dict[str, str] | None = None,
) -> dict:
    stamp = now_iso()
    return {
        "schema": SCHEMA,
        "metricId": f"{source}:{subject}:{name}:{stamp}",
        "observedAt": stamp,
        "source": source,
        "subject": subject,
        "metric": name,
        "value": value,
        "unit": unit,
        "status": status,
        "window": window,
        "evidence": evidence,
        "labels": labels or {},
    }
