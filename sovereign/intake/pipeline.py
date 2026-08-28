"""Spec 2.3, steps 2 to 4, as one function.

    intake(request) -> IntakeResult

R42 says documents arrive from a phone, a chat and a laptop through one
function; the three entry points in __init__.py are one-line wrappers over
this. R8 says the photo becomes structured JSON, then a committed markdown
file, then one receipt line. R4 says presence is never moved to Converse by
intake. R6 says the receipt is the founder's handle for `undo`, so the
receipt line carries the commit hash and the receipt record carries the
file path, the commit and the tags.

What is deliberately not here: the extracted text is never sent to the
reply callable. The only thing that reaches the thread is the receipt line.
"""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from sovereign.engine import ops, receipts
from sovereign.intake import config_keys as ck
from sovereign.intake.presence import GhostPresence, PresenceGate
from sovereign.intake.vision import Extraction, VisionCall, extract

ReplyFn = Callable[[str, str], Any]
"""(channel, text) -> anything. The thread the request came from."""


class IntakeRefused(RuntimeError):
    """The governance kernel refused the write (budget) or the target repo
    is not a git checkout. Nothing was written and no receipt was appended."""


class PresenceViolation(RuntimeError):
    """Presence moved to Converse during intake (R4). The commit stands and
    the receipt stands; the caller is told, so the gate that moved it can be
    found. Raised after the receipt so the audit trail is complete."""


@dataclass(frozen=True)
class IntakeRequest:
    image: bytes
    caption: str
    repo: Path
    source: str
    channel: str
    session_id: str | None = None
    budget_remaining: int | None = None
    mime: str | None = None


@dataclass(frozen=True)
class IntakeResult:
    path: Path
    relative_path: str
    commit: str
    receipt_line: str
    receipt: dict[str, Any]
    extraction: Extraction
    tokens_charged: int
    presence_before: str
    presence_after: str
    replies_sent: int = field(default=1)


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=float(ck.get("intake.git_timeout_s")),
    )
    if proc.returncode != 0:
        raise IntakeRefused(f"git {args[0]} failed in {repo}\n{proc.stderr.strip()}")
    return proc.stdout.strip()


def _target_path(repo: Path, slug: str) -> Path:
    docs = repo / str(ck.get("intake.docs_dir"))
    docs.mkdir(parents=True, exist_ok=True)
    suffix = str(ck.get("intake.file_suffix"))
    candidate = docs / f"{slug}{suffix}"
    n = 1
    while candidate.exists():
        n += 1
        candidate = docs / f"{slug}_{n}{suffix}"
    return candidate


def render_markdown(ex: Extraction, caption: str, source: str) -> str:
    tags = " ".join(f"#{t}" for t in ex.tags)
    return f"# {ex.title}\n\n{tags}\n\nsource: {source}\ncaption: {caption}\n\n{ex.markdown.rstrip()}\n"


def receipt_line(relative_path: str, commit: str, tags: tuple[str, ...], tokens: int) -> str:
    short = commit[: int(ck.get("intake.hash_short_len"))]
    tag_text = ",".join(f"#{t}" for t in tags)
    return f"[✓] {ck.get('intake.receipt_tag')} | file:{relative_path} | hash:{short} | tags:{tag_text} | budget:-{tokens}"


def intake(
    request: IntakeRequest,
    *,
    vision: VisionCall | None = None,
    reply: ReplyFn | None = None,
    presence: PresenceGate | None = None,
    now: Callable[[], float] = time.time,
) -> IntakeResult:
    """Photo in, one committed file and one receipt line out."""
    gate: PresenceGate = presence or GhostPresence()
    before = gate.current()
    repo = Path(request.repo)
    if not (repo / ".git").exists():
        raise IntakeRefused(f"{repo} is not a git checkout")

    # Step 3, the budget half: classify and check before spending a token.
    op_name = str(ck.get("intake.op_name"))
    spec = ops.classify(op_name)
    tokens = spec.tokens
    if request.budget_remaining is not None:
        decision = ops.check(op_name, request.budget_remaining)
        if not decision.allowed:
            raise IntakeRefused(f"{op_name} refused, {decision.reason}, remaining {decision.remaining_after}")
        tokens = decision.tokens

    # Step 2: extraction, silent.
    ex = extract(request.image, request.caption, call=vision, mime=request.mime)

    # Step 3, the write half. A non-destructive op needs no quorum.
    target = _target_path(repo, ex.slug)
    target.write_text(render_markdown(ex, request.caption, request.source))
    rel = target.relative_to(repo).as_posix()
    _git(repo, "add", "--", rel)
    _git(repo, "commit", "-q", "-m", f"{ck.get('intake.commit_prefix')}: {ex.title} ({rel})")
    commit = _git(repo, "rev-parse", "HEAD")

    # Step 4: one receipt line, appended to the signed chain first so the
    # thread never sees a line the chain does not hold.
    line = receipt_line(rel, commit, ex.tags, tokens)
    record = receipts.append(
        {
            "session_id": request.session_id or str(ck.get("intake.session_id")),
            "kind": str(ck.get("intake.receipt_kind")),
            "by": request.source,
            "text": line,
            "step": 0,
            "status": "committed",
            "task": request.caption,
            "runner": str(ck.get("intake.runner_name")),
            "ts": now(),
            "op": op_name,
            "file": rel,
            "commit": commit,
            "repo": str(repo),
            "tags": list(ex.tags),
            "model": ex.model,
            "tokens": tokens,
            "channel": request.channel,
        }
    )
    if reply is not None:
        reply(request.channel, line)

    after = gate.current()
    result = IntakeResult(
        path=target,
        relative_path=rel,
        commit=commit,
        receipt_line=line,
        receipt=record,
        extraction=ex,
        tokens_charged=tokens,
        presence_before=before,
        presence_after=after,
        replies_sent=1 if reply is not None else 0,
    )
    converse = str(ck.get("intake.converse_state_name"))
    if after == converse and before != converse:
        raise PresenceViolation(f"presence moved {before} -> {after} during intake of {rel}")
    return result
