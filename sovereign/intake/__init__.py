"""Document intake: a photo from anywhere becomes a committed markdown file
and one receipt line (spec 2.3; R8, R42, R4, R6).

Three thin entry points over one function (R42):

    from_phone(image, caption, repo, chat_id, ...)   a Telegram photo, via hermes-v2
    from_chat(image, caption, repo, thread, ...)     any other chat surface
    from_laptop(path, caption, repo, ...)            a file on disk, via `sb intake`

The stable call for an adapter that lives outside this repository (hermes-v2)
is `sovereign.intake.from_phone`. Its signature is the contract; the pipeline
behind it can change.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from sovereign.intake import config_keys as ck

if TYPE_CHECKING:
    from sovereign.intake.pipeline import IntakeResult, ReplyFn
    from sovereign.intake.presence import PresenceGate
    from sovereign.intake.vision import VisionCall

# sovereign.config imports sovereign.intake.config_keys while it is still
# initialising, and the pipeline imports sovereign.config through
# engine.receipts. Importing the pipeline here at package load would close
# that circle, so the re-exports below resolve on first use instead.
_LAZY: dict[str, str] = {
    "Extraction": "sovereign.intake.vision",
    "ExtractionError": "sovereign.intake.vision",
    "VisionCall": "sovereign.intake.vision",
    "GhostPresence": "sovereign.intake.presence",
    "PresenceGate": "sovereign.intake.presence",
    "IntakeRefused": "sovereign.intake.pipeline",
    "IntakeRequest": "sovereign.intake.pipeline",
    "IntakeResult": "sovereign.intake.pipeline",
    "PresenceViolation": "sovereign.intake.pipeline",
    "ReplyFn": "sovereign.intake.pipeline",
    "intake": "sovereign.intake.pipeline",
    "receipt_line": "sovereign.intake.pipeline",
}


def __getattr__(name: str) -> Any:
    module_name = _LAZY.get(name)
    if module_name is None:
        raise AttributeError(name)
    import importlib

    return getattr(importlib.import_module(module_name), name)


__all__ = [
    "Extraction",
    "ExtractionError",
    "GhostPresence",
    "IntakeRefused",
    "IntakeRequest",
    "IntakeResult",
    "PresenceGate",
    "PresenceViolation",
    "ReplyFn",
    "VisionCall",
    "from_chat",
    "from_laptop",
    "from_phone",
    "intake",
    "receipt_line",
]


def from_phone(
    image: bytes,
    caption: str,
    repo: Path | str,
    chat_id: str,
    *,
    reply: ReplyFn | None = None,
    presence: PresenceGate | None = None,
    vision: VisionCall | None = None,
    session_id: str | None = None,
    budget_remaining: int | None = None,
    mime: str | None = None,
) -> IntakeResult:
    """A photo from the founder's phone. `chat_id` is the thread the one
    receipt line goes back to."""
    from sovereign.intake.pipeline import IntakeRequest, intake

    req = IntakeRequest(
        image=image, caption=caption, repo=Path(repo), source=str(ck.get("intake.phone_source_name")),
        channel=chat_id, session_id=session_id, budget_remaining=budget_remaining, mime=mime,
    )
    return intake(req, vision=vision, reply=reply, presence=presence)


def from_chat(
    image: bytes,
    caption: str,
    repo: Path | str,
    thread: str,
    *,
    reply: ReplyFn | None = None,
    presence: PresenceGate | None = None,
    vision: VisionCall | None = None,
    session_id: str | None = None,
    budget_remaining: int | None = None,
    mime: str | None = None,
) -> IntakeResult:
    """An image pasted into any chat surface that is not the phone."""
    from sovereign.intake.pipeline import IntakeRequest, intake

    req = IntakeRequest(
        image=image, caption=caption, repo=Path(repo), source=str(ck.get("intake.chat_source_name")),
        channel=thread, session_id=session_id, budget_remaining=budget_remaining, mime=mime,
    )
    return intake(req, vision=vision, reply=reply, presence=presence)


def from_laptop(
    path: Path | str,
    caption: str,
    repo: Path | str,
    *,
    reply: ReplyFn | None = None,
    presence: PresenceGate | None = None,
    vision: VisionCall | None = None,
    session_id: str | None = None,
    budget_remaining: int | None = None,
    mime: str | None = None,
) -> IntakeResult:
    """An image file on the laptop. The receipt line's channel is the CLI."""
    image = Path(path).read_bytes()
    from sovereign.intake.pipeline import IntakeRequest, intake

    req = IntakeRequest(
        image=image, caption=caption, repo=Path(repo), source=str(ck.get("intake.laptop_source_name")),
        channel=str(ck.get("intake.cli_channel")), session_id=session_id,
        budget_remaining=budget_remaining, mime=mime,
    )
    return intake(req, vision=vision, reply=reply, presence=presence)

