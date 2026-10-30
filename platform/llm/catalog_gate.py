"""Catalog gate: ask every provider this router depends on, live, whether the exact model and
key llm/config.yaml pins still work -- not a hand-maintained list, not a comment with last
month's measurement, not a liveness ping against our own process.

WHY THIS EXISTS (2026-10-30). A caller hit deepseek-v4-flash, minimax and minimax_m31f, and
gemini in the same fallback chain in one request and every one of them failed: two providers
rejected the key, and Google had retired the pinned model entirely. Nothing caught any of the
three before a real caller did, because the only thing in this estate that calls a provider and
checks "does this still work" (router_catalog.py) runs beside bin/litellm-local's own process
and nowhere else -- never on a schedule, never from the cloud, never as a gate before a cutover
points production traffic at a host. That is the defect: live validation existed and was wired
to exactly one place nobody was watching between requests.

This script has no dependency on any other process, host, or physical machine. It reads
llm/config.yaml directly, calls litellm.completion() once per (model, key) pair with
max_tokens=1, and classifies the result:
  RED    the provider rejected the key or the model by name (4xx: authentication_error,
         invalid_request_error, not_found, and the Google "no longer available" shape) --
         this lane will fail every real call exactly the way it just failed one.
  GREEN  the provider answered.
  UNKNOWN  a timeout or a 5xx -- the provider's trouble this second, not proof the lane is dead
         (router_catalog.answers() draws the same line). Never counted against a lane.

Exit code is the number of RED lanes (0 means every lane answered or was merely UNKNOWN), so a
caller that wants this as a hard gate just checks the exit code; a caller that wants a standing
watch runs it on a schedule and reads the JSON report regardless of exit code.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "llm" / "config.yaml"


def _lanes(config_path: Path) -> list[dict]:
    """Every distinct (model_name, litellm model string, key env var) triple worth a live call.
    A lane with no api_key (anthropic/claude-*, the router's own pass-through) is not ours to
    probe -- it carries no provider credential this estate controls."""
    import yaml

    cfg = yaml.safe_load(config_path.read_text())
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for m in cfg.get("model_list", []):
        lp = m.get("litellm_params", {})
        model = str(lp.get("model", ""))
        key_param = str(lp.get("api_key", ""))
        if not key_param.startswith("os.environ/") or "*" in model:
            continue
        key_var = key_param.split("/", 1)[1]
        dedupe = (model, key_var)
        if dedupe in seen:
            continue
        seen.add(dedupe)
        out.append({"lane": m.get("model_name"), "model": model, "key_var": key_var})
    return out


def _classify(exc: Exception) -> tuple[str, str]:
    """(status, reason) from a litellm exception. RED only for a provider that named the key or
    the model as the problem; everything else is UNKNOWN, never held against the lane."""
    import litellm

    text = str(exc)
    if isinstance(exc, (litellm.AuthenticationError, litellm.NotFoundError)):
        return "RED", text[:300]
    if isinstance(exc, litellm.BadRequestError):
        # Google's own retirement shape and a plain "model not found" both land here; a bad
        # request that is actually about tokens/content would too, so only count the ones that
        # name the key or the model, never a generic 400.
        if re.search(
            r"invalid|not found|no longer available|does not exist", text, re.I
        ):
            return "RED", text[:300]
        return "UNKNOWN", text[:300]
    if isinstance(
        exc, (litellm.RateLimitError, litellm.Timeout, litellm.ServiceUnavailableError)
    ):
        return "UNKNOWN", text[:300]
    return "UNKNOWN", text[:300]


def probe(lane: dict) -> dict:
    import litellm

    key_var = lane["key_var"]
    key = os.environ.get(key_var, "")
    if not key:
        return {**lane, "status": "UNKNOWN", "reason": f"{key_var} not set in this run"}
    try:
        litellm.completion(
            model=lane["model"],
            api_key=key,
            messages=[{"role": "user", "content": "1"}],
            max_tokens=1,
            timeout=20,
        )
        return {**lane, "status": "GREEN", "reason": ""}
    except Exception as e:  # noqa: BLE001 -- classified below, never swallowed
        status, reason = _classify(e)
        return {**lane, "status": status, "reason": reason}


def main(argv: list[str]) -> int:
    config_path = Path(argv[1]) if len(argv) > 1 else DEFAULT_CONFIG
    lanes = _lanes(config_path)
    results = [probe(lane) for lane in lanes]
    red = [r for r in results if r["status"] == "RED"]
    report = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "config": str(config_path),
        "lanes_checked": len(results),
        "red": red,
        "results": results,
    }
    print(json.dumps(report, indent=1))
    for r in red:
        print(f"RED   {r['lane']:<20} {r['model']:<35} {r['reason']}", file=sys.stderr)
    return len(red)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
