import json
import os
import fcntl
from pathlib import Path
from datetime import datetime, timezone

LEDGER = Path(os.environ.get("FACTORY_LEDGER", "ledger"))


def write(stream: str, payload: dict) -> None:
    LEDGER.mkdir(parents=True, exist_ok=True)
    path = LEDGER / f"{stream}.ndjson"
    line = (
        json.dumps(
            {**payload, "at": datetime.now(timezone.utc).isoformat()}, sort_keys=True
        )
        + "\n"
    )
    with path.open("a") as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write(line)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def read(stream: str) -> list[dict]:
    path = LEDGER / f"{stream}.ndjson"
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out
