#!/usr/bin/env python3
"""Reduce a claude-code session transcript to its problem-solving skeleton.

Usage: cc-digest.py <transcript.jsonl> <out.txt> [max_text_chars]

Extracts the first real user message (the task) and then, in order, every
tool call (name + truncated input) and every block of Claude's own narration
between calls. The result is small enough to read whole, which is the point:
methodology audits and drift checks run over digests, not multi-MB jsonl.

Evidence: estate-agent, 2026-10-19, claim chidionyema/idp#6607.
"""

import json
import sys
from pathlib import Path


def first_user_task(lines):
    for line in lines:
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("type") != "user":
            continue
        content = rec.get("message", {}).get("content")
        text = ""
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = " ".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ).strip()
        if text and not text.startswith("<") and "tool_result" not in str(content)[:60]:
            return text[:2000]
    return None


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: cc-digest.py <transcript.jsonl> <out.txt> [max_text_chars]")
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    cap = int(sys.argv[3]) if len(sys.argv) > 3 else 1200

    out, task, n_tools = [], None, 0
    for line in src.open():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = rec.get("type")
        if kind == "user" and task is None:
            task = first_user_task([line])
        elif kind == "assistant":
            for item in rec.get("message", {}).get("content", []):
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "tool_use":
                    n_tools += 1
                    out.append(
                        f"[{item.get('name')}] {json.dumps(item.get('input', {}))[:160]}"
                    )
                elif item.get("type") == "text":
                    text = item.get("text", "").strip()
                    if text:
                        out.append(f">>> {text[:cap]}")
                        if len(text) > cap:
                            out.append(f"    ...(+{len(text) - cap} chars)")

    body = "\n".join(out)
    header = f"# {src.name}\n# tool calls: {n_tools}\n"
    if task:
        header += f"\n=== TASK ===\n{task}\n"
    Path(dst).write_text(header + "\n" + body + "\n")
    print(
        f"{src.name}: {n_tools} tool calls, digest {len(header) + len(body)} bytes -> {dst}"
    )


if __name__ == "__main__":
    main()
