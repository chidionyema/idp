"""The chat gate (R13, spec 2.5): the chat carries exactly three things.

1. `FounderReply`     -- conversation the founder started (Converse).
2. `CatastropheAlert` -- integrity failure, lockdown, dead man's switch.
3. `Digest`           -- one signed daily digest of at most six lines.

`send` accepts only that union, so a state diff, a budget warning or a
branch completion has no type it could be sent as. Those go to the alert
inbox (router.py) where the cockpit and the phone read them.

A system-authored message never asks the founder a question: the
constructors of CatastropheAlert and Digest refuse a text that does, so
no such value can exist to be sent (cp32: "no message is sent to the
chat that asks the founder a question").
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from sovereign.presence import config_keys
from sovereign.presence.fsm import CatastropheKind

_QUESTION_MARK = "?"


class AsksAQuestion(ValueError):
    """A system-authored chat message contained a question."""


def _refuse_question(text: str) -> None:
    if _QUESTION_MARK in text:
        raise AsksAQuestion(f"a system message may not ask the founder anything: {text!r}")


@dataclass(frozen=True)
class FounderReply:
    """A reply in a conversation the founder opened. Unbounded."""

    text: str
    in_reply_to: str

    @property
    def kind(self) -> str:
        return "founder"


@dataclass(frozen=True)
class CatastropheAlert:
    """Exactly one message: what broke, the hash, and the command to run."""

    cause: CatastropheKind
    hash: str
    remediation: str
    session_id: str | None = None

    def __post_init__(self) -> None:
        if not self.hash:
            raise ValueError("a catastrophe names the hash it was detected at")
        if not self.remediation:
            raise ValueError("a catastrophe names the remediation command")
        _refuse_question(self.text)

    @property
    def kind(self) -> str:
        return "catastrophe"

    @property
    def text(self) -> str:
        who = f" session {self.session_id}" if self.session_id else ""
        return f"CATASTROPHE {self.cause}{who} at {self.hash}. Halted. Run: {self.remediation}"


@dataclass(frozen=True)
class Digest:
    """At most `presence.digest_max_lines` lines, the last one the hash of
    the receipts file it was built from, signed by the kernel."""

    lines: tuple[str, ...]
    receipts_hash: str
    sig: str

    def __post_init__(self) -> None:
        max_lines = int(config_keys.resolve("presence.digest_max_lines"))
        if not self.lines:
            raise ValueError("a digest has at least the hash line")
        if len(self.lines) > max_lines:
            raise ValueError(f"a digest is at most {max_lines} lines, got {len(self.lines)}")
        if any("\n" in line for line in self.lines):
            raise ValueError("a digest line is one line")
        if not self.lines[-1].endswith(self.receipts_hash):
            raise ValueError("the last digest line ends with the receipts-file hash")
        if not self.sig:
            raise ValueError("a digest is signed")
        _refuse_question(self.text)

    @property
    def kind(self) -> str:
        return "digest"

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


ChatMessage = FounderReply | CatastropheAlert | Digest


class ChatSink(Protocol):
    """Where a chat message goes. The BDD MessageSink and the Telegram
    sender both fit this shape."""

    def send(self, channel: str, text: str, kind: str = ...) -> Any: ...


def send(sink: ChatSink, message: ChatMessage) -> Any:
    """The one door into the chat. Only a ChatMessage fits through it."""
    channel = str(config_keys.resolve("presence.chat_channel"))
    return sink.send(channel, message.text, kind=message.kind)


class TelegramSink:
    """The founder's Telegram home channel, through the otto card's sender
    (the one Telegram client sovereign/ already has)."""

    def send(self, channel: str, text: str, kind: str = "message") -> Any:
        from sovereign.otto import card

        _token, chat_id = card._telegram_creds()
        if not chat_id:
            return None
        return card._send(chat_id, text)
