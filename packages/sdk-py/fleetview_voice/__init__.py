"""FleetView Voice Python SDK.

A fully typed Python SDK for voice events over NATS.

Example:
    >>> from fleetview_voice import VoiceEventClient, VoiceEvent, EventPayload
    >>>
    >>> client = VoiceEventClient(
    ...     token="my-auth-token",
    ...     nats_url="nats://localhost:4222"
    ... )
    >>>
    >>> @client.on("steer")
    ... async def handle_steer(event: VoiceEvent) -> None:
    ...     print(f"{event.author} commanded: {event.transcript}")
    >>>
    >>> async with client:
    ...     await client.emit("done", EventPayload(
    ...         action="deploy",
    ...         transcript="deployment complete"
    ...     ))
"""

from .client import VoiceEventClient
from .types import EventPayload, VoiceEvent, VoiceEventType

__version__ = "0.1.0"
__all__ = [
    "VoiceEventClient",
    "VoiceEvent",
    "VoiceEventType",
    "EventPayload",
    "__version__",
]
