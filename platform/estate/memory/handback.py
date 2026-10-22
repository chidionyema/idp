"""No hand-back: a turn that ends by returning work to the founder is refused (idp lane/no-handback).

The founder, 2026-10-22: "i need proactive workkers not narrators and shrikers ... once given a
feature every model should drive it thru to fully operational and proven before contacting founder
or pausing". An agent that closes with "Still open: ...", "want me to ...?", "let me know if ..."
has stopped short and turned the founder into its project manager. This module is the one
definition of that behaviour, used by every harness:

    bin/estate-memory-enforce stop     Claude Code, and any runtime with a Stop hook
    opencode / pi plugins              shell out to `python3 handback.py check`
    platform/llm/no_handback.py        the router injects DIRECTIVE into every model's call

Deterministic: regexes, no model, no sampling (a guard that refuses correct work is an outage, R38).
Blind input (no text, unreadable transcript) allows -- a Stop hook that blocks on its own blindness
traps every session. `stop_hook_active` allows -- one retry, never a loop.

The one exception is the one AGENTS.md section 3 allows: a blocker that carries its evidence, the
intent that was run (`estate-execute <intent>` / `estate_invoke`), its exit status and the line it
printed.

    python3 handback.py check            agent text on stdin; prints {"block": bool, "reason": str, ...}
    python3 handback.py directive        prints DIRECTIVE, for a plugin to put in the system prompt
"""

from __future__ import annotations

import json
import re
import sys

DIRECTIVE = (
    "Drive every task through to operational and proven before you stop. Never end a turn by "
    "handing work back: no 'still open' or 'remaining' lists, no 'want me to...?', 'shall I...?' "
    "or 'let me know if...', no steps left for the founder. If something is undone, do it now; if "
    "a step failed, diagnose and retry a different way. Stop only when the work is done and "
    "proven on its real path, or irrevocably blocked after you have tried to unblock yourself. "
    "A blocker is reported with its evidence: the intent you ran (estate-execute <intent>), its "
    "exit status, and the line it printed."
)

# Phrases that return work to the reader. Narrow on purpose: each is hand-back phrasing, not a word
# an honest report would contain.
HANDBACK = (
    ("still open", re.compile(r"\bstill[ -]open\b", re.I)),
    (
        "deferred-work heading",
        re.compile(
            r"^[\s>*#_-]*(?:what(?:'s| is) )?(?:still open|remaining(?: work| items| tasks| steps)?"
            r"|open items|outstanding(?: items| work)?|next steps?|follow[- ]?ups?|todo|to[- ]do"
            r"|not (?:yet )?done)\b[\s*_]*(?::|—|–|-{1,2}\s|$)",
            re.I | re.M,
        ),
    ),
    (
        "offers to continue",
        re.compile(r"\b(?:want|would you like|do you want) me to\b[^.\n]*\?", re.I),
    ),
    ("asks permission", re.compile(r"\b(?:shall|should|may|can) I\b[^.\n]*\?", re.I)),
    (
        "waits for the founder",
        re.compile(r"\blet me know (?:if|when|whether|how|what|which)\b", re.I),
    ),
    (
        "waits for the founder",
        re.compile(r"\b(?:i'?ll|i will) (?:wait|stand by|hold) (?:for|until)\b", re.I),
    ),
    (
        "steps left to the founder",
        re.compile(
            r"\b(?:next steps?|follow[- ]?ups?|remaining (?:work|steps?|items?)) (?:for you|is for you|are for you)\b"
            r"|\byou(?:'ll| will) (?:still )?(?:need|have) to\b"
            r"|\bwhen you(?:'re| are) ready\b"
            r"|\b(?:i'?ll|i will) leave (?:this|that|it|the rest) (?:to|with|for) you\b",
            re.I,
        ),
    ),
)

# AGENTS.md section 3: "a claim of blocked carries its evidence: the intent that was run, its exit
# status, and the line it printed". Checked on the raw text; evidence usually sits in a code fence.
_INTENT = re.compile(r"\bestate[-_]execute\b|\bestate_invoke\b")
_EXIT = re.compile(
    r"\bexit(?:ed)?(?:\s+(?:status|code))?\s*[:=(]?\s*-?\d+\b|\bstatus\s*[:=]\s*-?\d+\b",
    re.I,
)
_BLOCKED = re.compile(r"\b(?:blocked|needs input|failed)\b", re.I)

_FENCED = re.compile(r"```.*?(?:```|\Z)", re.DOTALL)
_QUOTED = re.compile(
    r"`[^`\n]*`|\"[^\"\n]{0,300}\"|“[^”\n]{0,300}”|^\s*>.*$",
    re.MULTILINE,
)

REMEDY = (
    "This turn hands work back to the founder ({found}). Do not stop here. Do the remaining work "
    "now, in this session, and prove it on its real path. If a step failed, diagnose it and try a "
    "different way. Finish only when the work is done and proven, or when you are irrevocably "
    "blocked after trying to unblock yourself -- and then say so with the intent you ran "
    "(`estate-execute <intent>`), its exit status, and the line it printed."
)


def evidenced_blocker(text: str) -> bool:
    return bool(_BLOCKED.search(text) and _INTENT.search(text) and _EXIT.search(text))


def found(text: str) -> list[str]:
    """Which hand-back phrasings the agent's own prose (not code, not quotes) contains."""
    prose = _QUOTED.sub(" ", _FENCED.sub(" ", text))
    out: list[str] = []
    for name, rx in HANDBACK:
        m = rx.search(prose)
        if m:
            out.append(f"{name}: {' '.join(m.group(0).split())[:60]!r}")
    return out


def judge(text: str, stop_hook_active: bool = False) -> dict:
    """{"block": bool, "reason": str, "found": [...]}. Allows on anything it cannot judge."""
    if stop_hook_active or not isinstance(text, str) or not text.strip():
        return {"block": False, "reason": "", "found": []}
    hits = found(text)
    if not hits or evidenced_blocker(text):
        return {"block": False, "reason": "", "found": hits}
    return {
        "block": True,
        "reason": REMEDY.format(found="; ".join(hits[:3])),
        "found": hits,
    }


def _message(entry: dict) -> dict:
    # Claude Code wraps {"type": "assistant", "message": {...}}; pi writes {"type": "message", "message": {...}}.
    msg = entry.get("message")
    return msg if isinstance(msg, dict) else entry


def _text_of(msg: dict) -> str:
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            b["text"]
            for b in content
            if isinstance(b, dict)
            and b.get("type") == "text"
            and isinstance(b.get("text"), str)
        )
    return msg["text"] if isinstance(msg.get("text"), str) else ""


def last_agent_text(transcript: str) -> str | None:
    """The agent's last prose message of the final turn, or None when the transcript is unreadable.

    The final turn is what follows the last human prompt; tool results ride in user-role entries
    and are not prompts. Only the last agent message with text is judged -- a hand-back is how a
    turn ends, and earlier narration between tool calls is not the closing.
    """
    if not isinstance(transcript, str) or not transcript.strip():
        return None
    last = ""
    parsed = 0
    for line in transcript.splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict):
            continue
        parsed += 1
        msg = _message(entry)
        role = msg.get("role") or entry.get("type")
        text = _text_of(msg).strip()
        content = msg.get("content")
        is_prompt = role == "user" and (
            isinstance(content, str)
            or (
                isinstance(content, list)
                and not any(
                    isinstance(b, dict) and b.get("type") == "tool_result"
                    for b in content
                )
            )
        )
        if is_prompt and text:
            last = ""
        elif role == "assistant" and text:
            last = text
    return last if parsed else None


def judge_transcript(transcript: str, stop_hook_active: bool = False) -> dict:
    return judge(last_agent_text(transcript) or "", stop_hook_active)


def main(argv: list[str]) -> int:
    if argv == ["directive"]:
        print(DIRECTIVE)
        return 0
    if argv != ["check"]:
        print(__doc__.split("\n")[0], file=sys.stderr)
        return 2
    print(json.dumps(judge(sys.stdin.read())))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
