"""The one-line zero-noise receipt (R5, spec 2.2).

    [✓] DOC_COMMIT | file:docs/a.md | hash:8f2a1b3c | tags:#ml | budget:-1.2k | state:a3d9e2

One line, no prose. Every receipt carries the hash of the signed chain
row it came from, the token delta, and the state hash. `from_record`
turns a row of sovereign.engine.receipts into that line; `format_line`
is the pure formatter behind it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sovereign.presence import config_keys

_STATUS_FAILED = ("halted", "failed", "denied", "stopped", "error")


@dataclass(frozen=True)
class Receipt:
    """A receipt as a value. `text` is the one line; the fields are kept
    so a caller (undo, the digest) does not have to parse the line."""

    ok: bool
    op: str
    hash: str
    budget_delta: int
    state: str
    file: str | None = None
    tags: tuple[str, ...] = ()

    @property
    def text(self) -> str:
        return format_line(
            ok=self.ok, op=self.op, hash=self.hash, budget_delta=self.budget_delta,
            state=self.state, file=self.file, tags=self.tags,
        )


def humanize_delta(tokens: int) -> str:
    """-1200 -> "-1.2k"; 0 -> "0"; 340 -> "340"; -50000 -> "-50k"."""
    kilo = int(config_keys.resolve("presence.budget_kilo"))
    if abs(tokens) < kilo:
        return str(tokens)
    value = tokens / kilo
    text = f"{value:.1f}".rstrip("0").rstrip(".")
    return f"{text}k"


def format_line(
    *,
    ok: bool,
    op: str,
    hash: str,
    budget_delta: int,
    state: str,
    file: str | None = None,
    tags: tuple[str, ...] = (),
) -> str:
    mark = config_keys.resolve("presence.receipt_ok_mark" if ok else "presence.receipt_fail_mark")
    sep = str(config_keys.resolve("presence.receipt_field_sep"))
    hash_chars = int(config_keys.resolve("presence.receipt_hash_chars"))
    state_chars = int(config_keys.resolve("presence.receipt_state_chars"))
    fields = [f"{mark} {_one_token(op).upper()}"]
    if file:
        fields.append(f"file:{_one_token(file)}")
    fields.append(f"hash:{_one_token(hash)[:hash_chars]}")
    if tags:
        fields.append("tags:" + ",".join(_tag(t) for t in tags))
    fields.append(f"budget:{humanize_delta(budget_delta)}")
    fields.append(f"state:{_one_token(state)[:state_chars]}")
    return sep.join(fields)


def _one_token(value: str) -> str:
    """A field never carries a newline or the separator; a receipt is one
    line whatever a caller put in a filename or an op name."""
    sep = str(config_keys.resolve("presence.receipt_field_sep")).strip()
    cleaned = " ".join(str(value).split())
    return cleaned.replace(sep, "-") if sep else cleaned


def _tag(tag: str) -> str:
    tag = _one_token(tag).replace(",", "")
    return tag if tag.startswith("#") else f"#{tag}"


def from_record(row: dict[str, Any]) -> Receipt:
    """A row of the signed receipt chain (sovereign.engine.receipts.append
    returns one) as a one-line receipt."""
    status = str(row.get("status") or "")
    tokens = int(row.get("tokens") or 0)
    state = str(row.get("commit") or row.get("state_hash") or row.get("fsm_state") or row.get("hash") or "")
    return Receipt(
        ok=status not in _STATUS_FAILED,
        op=str(row.get("kind") or "receipt"),
        hash=str(row.get("hash") or ""),
        budget_delta=-tokens,
        state=state,
        file=row.get("file") or None,
        tags=tuple(row.get("tags") or ()),
    )
