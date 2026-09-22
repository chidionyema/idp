"""FleetView Voice event types."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


VoiceEventType = Literal["steer", "done", "speak"]


@dataclass(frozen=True)
class VoiceEvent:
    """A voice event transmitted over NATS.

    Attributes:
        id: Unique identifier for the event.
        type: The event type - 'steer', 'done', or 'speak'.
        action: The action requested or performed.
        target: Optional target entity for the action.
        env: Optional environment context (e.g., 'production', 'staging').
        confidence: Confidence score of the voice recognition (0.0 to 1.0).
        transcript: The raw transcript of the voice input.
        author: Identifier of the person or agent who initiated the event.
        timestamp: When the event occurred.
    """

    id: str
    type: VoiceEventType
    action: str
    confidence: float
    transcript: str
    author: str
    timestamp: datetime
    target: str | None = None
    env: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the event to a dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "action": self.action,
            "target": self.target,
            "env": self.env,
            "confidence": self.confidence,
            "transcript": self.transcript,
            "author": self.author,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_json(self) -> str:
        """Serialize the event to JSON."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VoiceEvent:
        """Deserialize an event from a dictionary.

        Args:
            data: Dictionary containing event fields.

        Returns:
            A VoiceEvent instance.

        Raises:
            ValueError: If required fields are missing or invalid.
            KeyError: If required fields are missing.
        """
        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        event_type = data["type"]
        if event_type not in ("steer", "done", "speak"):
            msg = f"Invalid event type: {event_type}"
            raise ValueError(msg)

        return cls(
            id=data["id"],
            type=event_type,
            action=data["action"],
            target=data.get("target"),
            env=data.get("env"),
            confidence=float(data["confidence"]),
            transcript=data["transcript"],
            author=data["author"],
            timestamp=timestamp,
        )

    @classmethod
    def from_json(cls, json_str: str) -> VoiceEvent:
        """Deserialize an event from JSON.

        Args:
            json_str: JSON string containing event data.

        Returns:
            A VoiceEvent instance.
        """
        return cls.from_dict(json.loads(json_str))


@dataclass
class EventPayload:
    """Payload for emitting a new event.

    Attributes:
        action: The action to perform.
        transcript: The voice transcript.
        target: Optional target entity.
        env: Optional environment context.
        confidence: Confidence score (defaults to 1.0 for programmatic events).
    """

    action: str
    transcript: str
    target: str | None = None
    env: str | None = None
    confidence: float = field(default=1.0)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the payload to a dictionary."""
        result: dict[str, Any] = {
            "action": self.action,
            "transcript": self.transcript,
            "confidence": self.confidence,
        }
        if self.target is not None:
            result["target"] = self.target
        if self.env is not None:
            result["env"] = self.env
        return result
