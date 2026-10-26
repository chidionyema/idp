#!/usr/bin/env python3
"""code-review-t2.py — Tier 2: LLM judgment. Only runs on Tier 0+1 output.

The LLM's job is NOT to find issues from scratch. It is to:
  - Classify flagged patterns as real or false positive
  - Verify whether a heuristic finding is genuine
  - Triage deterministic findings by severity
  - Explain what the finding means in context

Key rule: no finding reaches the user without Tier 3 verification.
This tier PROPOSES; Tier 3 DISPOSES.
"""

from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
IDP = HOME / "Documents/code/idp"
ROUTER = "https://llm.mumchimp.com/v1/chat/completions"
MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")
API_KEY = os.environ.get("OPENAI_API_KEY", "") or os.environ.get(
    "ANTHROPIC_API_KEY", ""
)

# Micro-Token FR-1 (2026-10-26): the prompt carries touched symbols, not a raw byte cap.
# The slicer is a sibling in libexec so the runtime sync delivers both together.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import symbol_slicer  # noqa: E402


def build_context(
    diff: str,
    read_file,
    base: str,
    max_bytes: int = 4000,
    raw_diff: str = "",
) -> tuple[str, str]:
    """Sliced symbol context for the prompt, or the raw diff when slicing yields nothing.

    Returns (context, mode) — mode is recorded in the output so a run proves which path
    fed the model instead of asserting it.
    """
    try:
        sliced = symbol_slicer.slice_for_diff(diff, read_file, max_bytes=max_bytes)
    except Exception:
        sliced = ""
    if sliced:
        return sliced, "sliced"
    return (raw_diff or diff)[:max_bytes], "raw-diff"


def get_diff(target: str, since: str) -> str:
    base = Path(target) if target else IDP
    if (base / ".git").exists():
        try:
            r = subprocess.run(
                ["git", "diff", "--unified=3", since or "HEAD~1"],
                capture_output=True,
                text=True,
                cwd=str(base),
                timeout=15,
            )
            return r.stdout[:8000]  # Cap diff size
        except Exception:
            pass
    return ""


def call_llm(messages: list[dict]) -> str:
    """Call the router with a structured prompt."""
    if not API_KEY:
        return json.dumps(
            {"error": "no API key set in OPENAI_API_KEY or ANTHROPIC_API_KEY"}
        )
    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0,
    }
    try:
        r = subprocess.run(
            [
                "curl",
                "-s",
                "--max-time",
                "30",
                "-H",
                f"Authorization: Bearer {API_KEY}",
                "-H",
                "Content-Type: application/json",
                "-d",
                json.dumps(payload),
                ROUTER,
            ],
            capture_output=True,
            text=True,
            timeout=35,
        )
        if r.stdout:
            resp = json.loads(r.stdout)
            return resp.get("choices", [{}])[0].get("message", {}).get("content", "")
        return ""
    except Exception as e:
        return json.dumps({"error": str(e)})


SYSTEM_PROMPT = """You are a code review assistant. Your job is NOT to find bugs from scratch.
You classify and triage findings from the deterministic layer.

For each finding, respond with ONLY a JSON object:
{
  "verdict": "real|false_positive|uncertain",
  "severity": "critical|high|medium|low",
  "explanation": "one sentence explaining why",
  "fix": "one sentence on how to fix it"
}

If there are no findings, respond with: {"verdict": "clean", "severity": "none", "explanation": "No issues found"}"""


def main():
    tier_arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    target = sys.argv[2] if len(sys.argv) > 2 else ""
    since = sys.argv[3] if len(sys.argv) > 3 else "HEAD~1"

    if tier_arg not in ("2", "all"):
        print(json.dumps({"tier": 2, "skipped": True, "reason": f"tier={tier_arg}"}))
        return

    # Read findings from environment (passed from previous tiers)
    t0_findings = json.loads(os.environ.get("T0_FINDINGS", "[]"))
    t1_findings = json.loads(os.environ.get("T1_FINDINGS", "[]"))
    diff = get_diff(target, since)

    if not t0_findings and not t1_findings:
        print(
            json.dumps(
                {
                    "tier": 2,
                    "verdicts": [],
                    "summary": "no findings from Tier 0+1 — nothing to judge",
                }
            )
        )
        return

    all_findings = t0_findings + t1_findings
    findings_text = json.dumps(all_findings[:30], indent=2)

    base = str(Path(target)) if target else str(IDP)
    context, context_mode = build_context(
        diff,
        lambda p: (
            (Path(base) / p).read_text(errors="replace")
            if (Path(base) / p).exists()
            else None
        ),
        base,
    )

    user_prompt = f"""Review these deterministic findings from the code review pipeline:

CONTEXT (touched symbols, sliced — mode: {context_mode}):
{context}

FINDINGS ({len(all_findings)} total):
{findings_text}

For each finding, classify it as real (the issue is genuine), false_positive (the pattern is a false alarm), or uncertain (cannot determine without more context).

Respond with a JSON array of verdicts, one per finding, in the same order."""

    response = call_llm(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )

    verdicts = []
    try:
        verdicts = json.loads(response)
    except Exception:
        verdicts = [
            {
                "verdict": "uncertain",
                "severity": "medium",
                "explanation": f"LLM parse error: {response[:200]}",
            }
        ]

    output = {
        "tier": 2,
        "findings_judged": len(all_findings),
        "context_mode": context_mode,
        "context_bytes": len(context),
        "verdicts": verdicts[:30],
        "llm_response": response[:500],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
