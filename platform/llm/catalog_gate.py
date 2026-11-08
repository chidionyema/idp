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


def summarize_report(path: Path) -> dict[str, int]:
    """Validate a complete machine report; never turn corrupt evidence into zero RED."""
    report = json.loads(path.read_text())
    if not isinstance(report, dict):
        raise ValueError("report must be an object")
    results, red = report.get("results"), report.get("red")
    count = report.get("lanes_checked")
    if (
        not isinstance(results, list)
        or not results
        or not isinstance(red, list)
        or type(count) is not int
        or count != len(results)
    ):
        raise ValueError("missing, empty or inconsistent probe evidence")
    if any(
        not isinstance(r, dict)
        or r.get("status") not in ("GREEN", "RED", "UNKNOWN")
        or not isinstance(r.get("lane"), str)
        or not isinstance(r.get("model"), str)
        for r in results
    ):
        raise ValueError("malformed lane verdict")
    actual_red = [r for r in results if r["status"] == "RED"]
    if actual_red != red:
        raise ValueError("RED list disagrees with the individual lane verdicts")
    return {
        "red": len(actual_red),
        "unknown": sum(r["status"] == "UNKNOWN" for r in results),
        "green": sum(r["status"] == "GREEN" for r in results),
        "lanes_checked": count,
    }


def main(argv: list[str]) -> int:
    # The file is the machine contract. Provider SDKs may print diagnostics to
    # stdout before our JSON, so a tee of stdout is NOT a valid receipt.
    if len(argv) == 3 and argv[1] == "--summary":
        try:
            print(json.dumps(summarize_report(Path(argv[2])), sort_keys=True))
            return 0
        except (OSError, ValueError, TypeError) as exc:
            print(f"BLIND catalog report: {exc}", file=sys.stderr)
            return 70

    if len(argv) == 4 and argv[2] == "--output":
        config_path, output = Path(argv[1]), Path(argv[3])
    elif len(argv) <= 2:
        config_path = Path(argv[1]) if len(argv) > 1 else DEFAULT_CONFIG
        output = None
    else:
        print("usage: catalog_gate.py [config.yaml [--output report.json]] | --summary report.json", file=sys.stderr)
        return 64

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
    if output is not None:
        # A partial JSON file must never be mistaken for a clean report.
        tmp = output.with_name(output.name + ".tmp")
        try:
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as stream:
                json.dump(report, stream, indent=1)
                stream.write("\n")
            os.replace(tmp, output)
        except OSError as exc:
            print(f"BLIND catalog report write: {exc}", file=sys.stderr)
            return 70
    else:
        print(json.dumps(report, indent=1))
    for r in red:
        print(f"RED   {r['lane']:<20} {r['model']:<35} {r['reason']}", file=sys.stderr)
    return len(red)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
