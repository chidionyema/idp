#!/usr/bin/env python3
"""Claude Code SessionStart(compact) + SessionEnd hook: every compaction summary lands in growmos.

2026-09-26: a session lost its whole intent-engine discussion. The agent had journalled two
one-liners; the pending work, the consultant proposals and the pushbacks lived only in a
compaction summary inside the transcript. Writing back was left to the agent, so it did not
happen. This hook makes it the harness's job: whatever the agent does, each summary Claude
Code writes is journalled verbatim, tagged with the transcript id, exactly once.

Never blocks a session: any failure exits 0 with a note on stderr.
"""

import hashlib
import json
import os
import subprocess
import sys

MARKER = "This session is being continued from a previous conversation"
SEEN = os.path.expanduser("~/.estate/state/journalled-summaries")


def summaries(path):
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get("type") != "user":
            continue
        content = entry.get("message", {}).get("content")
        if isinstance(content, list):
            content = " ".join(
                b.get("text", "") for b in content if isinstance(b, dict)
            )
        if isinstance(content, str) and content.startswith(MARKER):
            yield content


def main():
    event = json.load(sys.stdin)
    path = event.get("transcript_path") or ""
    root = event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or "."
    if not os.path.isfile(path):
        return
    seen = set(open(SEEN).read().split()) if os.path.isfile(SEEN) else set()
    session = os.path.basename(path).removesuffix(".jsonl")
    for text in summaries(path):
        digest = hashlib.sha256(text.encode()).hexdigest()[:16]
        if digest in seen:
            continue
        entry = (
            f"COMPACTION SUMMARY (auto, transcript {session}, sha {digest})\n\n{text}"
        )
        done = subprocess.run(
            ["growmos", "journal", entry], cwd=root, capture_output=True, timeout=60
        )
        if done.returncode != 0:
            print(
                f"journal_compaction: growmos journal rc={done.returncode}",
                file=sys.stderr,
            )
            return
        os.makedirs(os.path.dirname(SEEN), exist_ok=True)
        with open(SEEN, "a") as f:
            f.write(digest + "\n")
        seen.add(digest)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # a hook must never wedge the session
        print(f"journal_compaction: {exc}", file=sys.stderr)
    sys.exit(0)
