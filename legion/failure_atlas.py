"""Institutional failure memory for the EXISTING Legion runner, not another engine."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

ATLAS = Path(__file__).with_name("failure_atlas.json")

def load_atlas(path: str | Path = ATLAS) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    modes = data.get("modes")
    if data.get("version") != 1 or not isinstance(modes, list) or not modes:
        raise ValueError("Legion failure atlas invalid")
    seen = set()
    for item in modes:
        if not isinstance(item, dict) or any(
            key not in item for key in
            ("id", "diagnosis", "recovery", "proof", "cooldown_s", "max_identical_attempts")
        ):
            raise ValueError("Legion failure mode incomplete")
        code = item["id"]
        if not isinstance(code, str) or not code.startswith("LEGION_") or code in seen:
            raise ValueError("Legion failure fingerprint duplicate or invalid")
        if not all(isinstance(item[k], str) and item[k].strip()
                   for k in ("diagnosis", "recovery", "proof")):
            raise ValueError("Legion missing diagnostic or recovery route")
        if (type(item["cooldown_s"]) is not int or item["cooldown_s"] < 0 or
            type(item["max_identical_attempts"]) is not int or
            not 1 <= item["max_identical_attempts"] <= 2):
            raise ValueError("Legion failure retry budget invalid")
        seen.add(code)
    if "LEGION_UNKNOWN" not in seen:
        raise ValueError("Legion UNKNOWN quarantine route absent")
    return data

def diagnose(code: str, path: str | Path = ATLAS) -> dict[str, Any]:
    known = {m["id"]: m for m in load_atlas(path)["modes"]}
    result = known.get(code, known["LEGION_UNKNOWN"])
    return {**result, "requested_fingerprint": code,
            "known": code in known, "status": "RECOVERY_REQUIRED"}
