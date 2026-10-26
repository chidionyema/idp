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
# The router this tier calls is the cluster's, and its key is model-allowlisted
# (default, ollama, deepseek, gemini, kimi, minimax, minimax_m27, groq, ... --
# 'gpt-4o-mini' was never on it, so this tier could not have made a call). The
# default is 'minimax_m27' (openai/MiniMax-M2.7) because it is the lane that
# ANSWERS: the reasoning lanes (gpt-oss-120b on groq, glm-5.3, deepseek,
# cerebras) spend their whole token budget on reasoning_content and return an
# empty answer, which turned every verdict into "uncertain" (2026-10-26).
# LLM_MODEL still overrides.
MODEL = os.environ.get("LLM_MODEL", "minimax_m27")
API_KEY = (
    os.environ.get("OPENAI_API_KEY", "")
    or os.environ.get("LITELLM_API_KEY", "")
    or os.environ.get("ANTHROPIC_API_KEY", "")
)

# The tiers hand off through FILES, not env. The intent runs each tier as its own
# step, and a step's env does not survive into the next one, so Tier 0/1's findings
# never reached Tier 2 and Tier 2's verdicts never reached Tier 3 (2026-10-26: the
# pipeline advertised four tiers and ran two). The intent writes each tier's JSON
# here; a direct invocation can still set T0_FINDINGS/T1_FINDINGS/T2_VERDICTS.
REVIEW_DIR = Path(
    os.environ.get("ESTATE_REVIEW_DIR") or (HOME / ".estate/review/latest")
)

# Micro-Token FR-1 (2026-10-26): the prompt carries touched symbols, not a raw byte cap.
# The slicer is a sibling in libexec so the runtime sync delivers both together.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import symbol_slicer  # noqa: E402


def load_json(name: str, env_var: str, key: str) -> list[dict]:
    """Findings from the env if set, else from the tier hand-off file."""
    raw = os.environ.get(env_var, "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = None
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and isinstance(parsed.get(key), list):
            return parsed[key]
    try:
        data = json.loads((REVIEW_DIR / name).read_text())
    except Exception:
        return []
    if isinstance(data, dict):
        value = data.get(key, [])
        return value if isinstance(value, list) else []
    return data if isinstance(data, list) else []


def finding_neighborhoods(
    findings: list[dict],
    read_file,
    around: int = 3,
    max_bytes: int = 1600,
) -> str:
    """A few lines around every flagged line.

    The slice covers the symbols the DIFF touched. A finding can sit outside them
    (a static analyser flags the whole file), and a tier that cannot see the
    flagged line can only answer "uncertain" - which is not a judgment, it is a
    shrug. This adds the neighbourhood of each finding, bounded, so the model
    looks at the code the finding is about.
    """
    chunks: list[str] = []
    used = 0
    seen: set[tuple[str, int]] = set()
    for finding in findings:
        path = finding.get("file", "")
        line = int(finding.get("line") or 0)
        if not path or line <= 0 or (path, line) in seen:
            continue
        seen.add((path, line))
        source = read_file(path)
        if not source:
            continue
        lines = source.splitlines()
        if line > len(lines):
            continue
        start = max(0, line - 1 - around)
        end = min(len(lines), line + around)
        block = "\n".join(f"{i + 1}: {lines[i]}" for i in range(start, end))
        chunk = f"### {path}:{line}\n{block}\n"
        if used + len(chunk) > max_bytes:
            break
        chunks.append(chunk)
        used += len(chunk)
    return "".join(chunks)


def build_context(
    diff: str,
    read_file,
    base: str,
    max_bytes: int = 4000,
    raw_diff: str = "",
    findings: list[dict] | None = None,
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
        if findings:
            try:
                sliced = (
                    sliced
                    + "\n<finding-context>\n"
                    + finding_neighborhoods(findings, read_file)
                )
            except Exception:
                pass
        return sliced, "sliced"
    return (raw_diff or diff)[:max_bytes], "raw-diff"


def resolve_target(target: str) -> tuple[Path, str | None]:
    """The repo root for a target, and the pathspec when the target is one file.

    A file target used to yield no diff at all (the old code only diffed when the
    target WAS a repo), so the slicer was handed an empty diff and every review of
    a single file fell back to raw-diff context.
    """
    base = Path(target) if target else IDP
    start = base if base.is_dir() else base.parent
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            cwd=str(start),
            timeout=15,
        )
        root = Path(r.stdout.strip())
    except Exception:
        return IDP, None
    pathspec = None
    if base.is_file():
        try:
            pathspec = str(base.resolve().relative_to(root.resolve()))
        except ValueError:
            pathspec = None
    return root, pathspec


def get_diff(root: Path, since: str, pathspec: str | None = None) -> str:
    cmd = ["git", "diff", "--unified=3", since or "HEAD~1"]
    if pathspec:
        cmd.append(pathspec)
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(root),
            timeout=15,
        )
        return r.stdout[:8000]  # Cap diff size
    except Exception:
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
        # 4096, not 1024: the routed lanes are reasoning models, and they spend
        # tokens on reasoning_content before the answer. With a 1024 cap the model
        # finished on reasoning and the content came back empty, so every verdict
        # degraded to "uncertain" (2026-10-26).
        "max_tokens": 4096,
        "temperature": 0,
    }
    try:
        r = subprocess.run(
            [
                "curl",
                "-s",
                "--max-time",
                "50",
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
            timeout=55,
        )
        if r.stdout:
            resp = json.loads(r.stdout)
            choice = (resp.get("choices") or [{}])[0]
            message = choice.get("message") or {}
            content = message.get("content") or ""
            if not content.strip():
                # Say WHY it was empty, so a truncated or refused completion is not
                # reported as an unparseable model answer.
                return json.dumps(
                    {
                        "error": "empty completion",
                        "finish_reason": choice.get("finish_reason"),
                        "reasoning": (message.get("reasoning_content") or "")[:300],
                    }
                )
            return content
        return ""
    except Exception as e:
        return json.dumps({"error": str(e)})


SYSTEM_PROMPT = """You classify code-review findings. A finding is a false_positive when the code it points at is correct as written - for example a return that only looks unreachable because it sits inside a branch or a loop. Answer with a JSON array of strings, one per finding: real, false_positive, or uncertain. No prose."""


def merge_verdicts(findings: list[dict], verdicts: list) -> list[dict]:
    """Carry each finding's file/line/rule into its verdict.

    Tier 3 re-checks the deterministic rule at that file and line, so a verdict
    without them is unverifiable -- which is why Tier 3 used to reject every verdict
    as "no file specified" even when the model was right.
    """
    judged = []
    allowed = {"real", "false_positive", "uncertain"}
    for index, finding in enumerate(findings):
        verdict = verdicts[index] if index < len(verdicts) else {}
        if not isinstance(verdict, dict):
            verdict = {}
        label = str(verdict.get("verdict", "uncertain")).strip().lower()
        if label not in allowed:
            label = "uncertain"
        judged.append(
            {
                **finding,
                "verdict": label,
                "judged_severity": verdict.get("severity", finding.get("severity")),
                "explanation": verdict.get("explanation", ""),
                "fix": verdict.get("fix", ""),
            }
        )
    return judged


def main():
    tier_arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    target = sys.argv[2] if len(sys.argv) > 2 else ""
    since = sys.argv[3] if len(sys.argv) > 3 else "HEAD~1"

    if tier_arg not in ("2", "all"):
        print(json.dumps({"tier": 2, "skipped": True, "reason": f"tier={tier_arg}"}))
        return

    # Findings from the tier hand-off: the env when a caller sets it, else the files
    # the intent's previous steps wrote.
    t0_findings = load_json("t0.json", "T0_FINDINGS", "findings")
    t1_findings = load_json("t1.json", "T1_FINDINGS", "findings")
    root, pathspec = resolve_target(target)
    diff = get_diff(root, since, pathspec)

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
    # The compact list: the rule, the line and the message are what a judgment
    # needs. The full finding dicts (tool, severity, file, message) doubled the
    # prompt for nothing, and every byte of prompt is reasoning the model spends
    # before it answers (2026-10-26: the verbose protocol took 39s of reasoning
    # for a verdict list that is 11 words long).
    findings_text = json.dumps(
        [
            {
                "n": i + 1,
                "rule": f.get("rule", ""),
                "line": f.get("line", 0),
                "msg": f.get("message", ""),
            }
            for i, f in enumerate(all_findings[:30])
        ],
        indent=1,
    )

    def read_file(rel: str) -> str | None:
        path = root / rel
        try:
            return path.read_text(errors="replace") if path.exists() else None
        except Exception:
            return None

    context, context_mode = build_context(
        diff,
        read_file,
        str(root),
        findings=all_findings,
    )

    user_prompt = f"""Review these deterministic findings from the code review pipeline:

CONTEXT (touched symbols, sliced — mode: {context_mode}):
{context}

FINDINGS ({len(all_findings)} total):
{findings_text}

Decide for each finding whether it is a real problem or a false positive.
Respond with ONLY a JSON array of {len(all_findings[:30])} strings, one per finding, in the same order, each exactly one of: real, false_positive, uncertain. No prose, no explanations, no markdown."""

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
    if isinstance(verdicts, dict):
        # a single object: either one verdict, or the model's "clean" answer
        verdicts = [] if verdicts.get("verdict") == "clean" else [verdicts]
    if not isinstance(verdicts, list):
        verdicts = []
    # The compact protocol answers with one word per finding; the older verbose
    # protocol answered with an object per finding. Both are accepted.
    normalised = []
    for verdict in verdicts:
        if isinstance(verdict, str):
            normalised.append({"verdict": verdict.strip().lower()})
        elif isinstance(verdict, dict):
            normalised.append(verdict)
        else:
            normalised.append({})
    verdicts = normalised

    # Carry each finding's file/line/rule into its verdict.
    judged = merge_verdicts(all_findings, verdicts)

    output = {
        "tier": 2,
        "findings_judged": len(all_findings),
        "context_mode": context_mode,
        "context_bytes": len(context),
        "model": MODEL,
        "verdicts": judged[:30],
        "llm_response": response[:500],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
