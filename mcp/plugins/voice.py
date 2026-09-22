"""Datasette plugin: voice MCP tools for any agent framework (crew#180 CP6).

Exposes voice intents to any MCP-compatible agent (Claude, Cursor, LangChain, etc.):
- `voice_intent_stream` — subscribe to voice intents from the estate bus
- `voice_speak` — trigger speech responses back to the user
- `voice_last_intent` — get the last N voice intents for context

WHAT THIS IS, AND WHY IT EXISTS.

The voice transport (backstage/plugins/fleetview-backend/src/voice_media.py) publishes
meaning to the estate bus: each utterance is an `estate.agent.event` with kind=steer,
and the answer's completion is a kind=done row. That transport serves the FleetView
page; this plugin serves ANY MCP CLIENT that wants to subscribe to voice or speak back.

Three lines of code is the success criterion: any MCP client can subscribe with:
    async for intent in voice_intent_stream():
        handle(intent)

SUBJECTS (the estate bus contract).
  estate.agent.sovereign.*.steer — intents from users (voice commands)
  estate.agent.sovereign.speak   — speech requests to clients

CONFIG (LAW 46 — no path or port is a literal in code that decides behaviour):
  NATS_URL                          the bus; unset means voice tools degrade
  VOICE_INTENT_HISTORY_PATH         where the last N intents are cached for context
                                     (default /data/voice-intents.jsonl)
  VOICE_INTENT_HISTORY_LIMIT        max intents to keep (default 100)

DEGRADES, NEVER RAISES. A bus that is down must not break an agent's turn, so every
failure path returns a payload with an `error` field, the same shape as estate_memory.py.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncGenerator

if TYPE_CHECKING:
    pass

# See mcp/plugins/estate_inventory.py for why this import is guarded: the offline CI
# venv that runs tests has no datasette installed.
try:
    from datasette import hookimpl
except ImportError:  # pragma: no cover - exercised only in the datasette-less CI venv

    def hookimpl(fn):
        return fn


# The runtime name for voice events, matching voice_media.py's RUNTIME constant.
RUNTIME = "sovereign"

# Connection budget: same values as nats_adapter.py, and for the same reason — a one-shot
# publish/subscribe must not inherit nats-py's 120-second retry budget.
_CONNECT_TIMEOUT_S = float(os.environ.get("NATS_CONNECT_TIMEOUT_S", "2"))
_CONNECT_ATTEMPTS = int(os.environ.get("NATS_CONNECT_ATTEMPTS", "1"))
_RETRY_WAIT_S = float(os.environ.get("NATS_RETRY_WAIT_S", "0.1"))


def config() -> dict:
    return {
        "nats_url": os.environ.get("NATS_URL", "").strip(),
        "history_path": os.environ.get(
            "VOICE_INTENT_HISTORY_PATH", "/data/voice-intents.jsonl"
        ),
        "history_limit": int(os.environ.get("VOICE_INTENT_HISTORY_LIMIT", "100")),
    }


def _require_nats():
    """Raise if nats-py is not installed — the estate rule is that a missing required
    service raises, never silently succeeds."""
    try:
        import nats  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("nats-py not installed") from exc


async def _connect(nats_url: str):
    """A connection with bounded retry budget — see nats_adapter.py's docblock."""
    import nats

    return await nats.connect(
        nats_url,
        connect_timeout=_CONNECT_TIMEOUT_S,
        max_reconnect_attempts=_CONNECT_ATTEMPTS,
        reconnect_time_wait=_RETRY_WAIT_S,
    )


def _append_to_history(intent: dict, cfg: dict | None = None) -> None:
    """Append one intent to the history file (JSONL), trimming to the limit."""
    cfg = cfg or config()
    path = Path(cfg["history_path"])
    limit = cfg["history_limit"]

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing, append, trim
    lines = []
    if path.exists():
        try:
            lines = path.read_text(encoding="utf-8").strip().splitlines()
        except OSError:
            lines = []

    lines.append(json.dumps(intent, separators=(",", ":")))

    # Keep only the most recent `limit` intents
    if len(lines) > limit:
        lines = lines[-limit:]

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_history(limit: int, cfg: dict | None = None) -> list[dict]:
    """Read the last N intents from the history file, newest first."""
    cfg = cfg or config()
    path = Path(cfg["history_path"])

    if not path.exists():
        return []

    try:
        lines = path.read_text(encoding="utf-8").strip().splitlines()
    except OSError:
        return []

    # Reverse so newest is first, then take limit
    lines = lines[-limit:][::-1]
    intents = []
    for line in lines:
        try:
            intents.append(json.loads(line))
        except (ValueError, TypeError):
            continue
    return intents


async def do_voice_intent_stream(cfg: dict | None = None) -> AsyncGenerator[dict, None]:
    """Subscribe to voice intents from `estate.agent.sovereign.*.steer`.

    Yields each intent as a dict with author, timestamp, confidence.
    Raises RuntimeError("nats-py not installed") when nats-py is absent.
    """
    cfg = cfg or config()
    if not cfg["nats_url"]:
        yield {
            "error": "NATS_URL is unset: voice intent stream is not available",
            "subscribed": False,
        }
        return

    _require_nats()

    nc = await _connect(cfg["nats_url"])
    try:
        js = nc.jetstream()
        # Subscribe to all steer events from the sovereign runtime (voice)
        sub = await js.subscribe(f"estate.agent.{RUNTIME}.*.steer")
        async for msg in sub.messages:
            await msg.ack()
            try:
                event = json.loads(msg.data)
            except (ValueError, UnicodeDecodeError):
                # Malformed message is skipped, not fatal
                continue

            # Extract the steer intent from the event
            steer = event.get("steer") or {}
            intent = {
                "text": steer.get("text", ""),
                "author": steer.get("author", ""),
                "session_id": event.get("session_id", ""),
                "timestamp": event.get("at", ""),
                "confidence": steer.get("confidence"),  # may be None
                "raw_event": event,
            }

            # Persist to history for later retrieval
            _append_to_history(intent, cfg)

            yield intent
    finally:
        await nc.drain()


async def do_voice_speak(
    text: str, voice: str = "af_sky", session_id: str = "", cfg: dict | None = None
) -> dict[str, Any]:
    """Trigger speech on the user's client. Publishes to estate.agent.sovereign.speak.

    Returns when acknowledged or on error.
    """
    cfg = cfg or config()
    if not cfg["nats_url"]:
        return {
            "spoken": False,
            "error": "NATS_URL is unset: voice speak is not available",
        }

    text = (text or "").strip()
    if not text:
        return {"spoken": False, "error": "text is required"}

    _require_nats()

    session_id = (
        session_id
        or f"speak-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    )
    subject = f"estate.agent.{RUNTIME}.speak"
    event = {
        "session_id": session_id,
        "runtime": RUNTIME,
        "kind": "speak",
        "at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "speak": {
            "text": text,
            "voice": voice,
        },
    }
    payload = json.dumps(event).encode()

    try:
        nc = await _connect(cfg["nats_url"])
        try:
            js = nc.jetstream()
            ack = await js.publish(subject, payload)
            return {
                "spoken": True,
                "subject": subject,
                "session_id": session_id,
                "voice": voice,
                "text": text,
                "stream_seq": ack.seq if hasattr(ack, "seq") else None,
            }
        finally:
            await nc.drain()
    except Exception as exc:  # noqa: BLE001 — the reason is reported, never swallowed
        return {"spoken": False, "error": f"{exc.__class__.__name__}: {exc}"}


def do_voice_last_intent(limit: int = 10, cfg: dict | None = None) -> list[dict]:
    """Get the last N voice intents for context, newest first.

    Reads from the local history file, not the live bus — so an agent can catch up
    without subscribing.
    """
    limit = max(1, min(limit, 100))  # clamp to [1, 100]
    return _read_history(limit, cfg)


@hookimpl
def register_mcp_tools(datasette, mcp):
    @mcp.tool()
    async def voice_intent_stream() -> AsyncGenerator[dict, None]:
        """Subscribe to voice intents from estate.agent.sovereign.*.steer.

        Yields intents with: text, author, session_id, timestamp, confidence.
        Any MCP client can subscribe with:

            async for intent in voice_intent_stream():
                handle(intent)

        Returns an error dict if the bus is unavailable.
        """
        async for intent in do_voice_intent_stream():
            yield intent

    @mcp.tool()
    async def voice_speak(
        text: str, voice: str = "af_sky", session_id: str = ""
    ) -> dict:
        """Trigger speech on the user's client.

        Publishes to estate.agent.sovereign.speak. Returns when acknowledged.
        `voice` is the voice name (default af_sky). `session_id` is optional
        and auto-generated if not provided.
        """
        return await do_voice_speak(text, voice, session_id)

    @mcp.tool()
    async def voice_last_intent(limit: int = 10) -> list[dict]:
        """Get the last N voice intents for context, newest first.

        Reads from the local history file — an agent can catch up without
        subscribing to the live stream. `limit` is clamped to [1, 100].
        """
        return do_voice_last_intent(limit)
