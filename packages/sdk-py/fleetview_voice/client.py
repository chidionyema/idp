"""FleetView Voice event client for NATS."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

import nats
from nats.aio.client import Client as NATSClient
from nats.aio.msg import Msg

from .types import EventPayload, VoiceEvent, VoiceEventType

logger = logging.getLogger(__name__)

# Type alias for event handlers
EventHandler = Callable[[VoiceEvent], Awaitable[None]]


class VoiceEventClient:
    """Client for sending and receiving voice events over NATS.

    This client provides:
    - Decorator-based event handler registration
    - Automatic reconnection with exponential backoff
    - Connection pooling via NATS connection reuse
    - Full async/await support

    Example:
        >>> client = VoiceEventClient(
        ...     token="my-auth-token",
        ...     nats_url="nats://localhost:4222"
        ... )
        >>>
        >>> @client.on("steer")
        ... async def handle_steer(event: VoiceEvent) -> None:
        ...     print(f"{event.author} commanded: {event.transcript}")
        >>>
        >>> await client.connect()
        >>> await client.emit("done", EventPayload(action="deploy", transcript="deploy complete"))
        >>> await client.disconnect()
    """

    # Subject prefix for voice events
    SUBJECT_PREFIX = "voice.events"

    # Reconnection backoff settings
    INITIAL_BACKOFF_SECONDS = 1.0
    MAX_BACKOFF_SECONDS = 30.0
    BACKOFF_MULTIPLIER = 2.0

    def __init__(
        self,
        token: str,
        nats_url: str = "nats://localhost:4222",
        *,
        author: str | None = None,
        reconnect_attempts: int = -1,
    ) -> None:
        """Initialize the voice event client.

        Args:
            token: Authentication token for NATS.
            nats_url: NATS server URL. Defaults to localhost.
            author: Default author for emitted events. Defaults to "sdk-py".
            reconnect_attempts: Number of reconnection attempts. -1 for infinite.
        """
        self._token = token
        self._nats_url = nats_url
        self._author = author or "sdk-py"
        self._reconnect_attempts = reconnect_attempts

        self._nc: NATSClient | None = None
        self._handlers: dict[VoiceEventType, list[EventHandler]] = {
            "steer": [],
            "done": [],
            "speak": [],
        }
        self._subscriptions: list[Any] = []
        self._connected = False
        self._backoff_seconds = self.INITIAL_BACKOFF_SECONDS

    @property
    def is_connected(self) -> bool:
        """Return True if connected to NATS."""
        return self._connected and self._nc is not None and self._nc.is_connected

    def on(self, event_type: VoiceEventType) -> Callable[[EventHandler], EventHandler]:
        """Decorator to register an event handler.

        Args:
            event_type: The event type to handle ('steer', 'done', or 'speak').

        Returns:
            Decorator function that registers the handler.

        Example:
            >>> @client.on("steer")
            ... async def handle_steer(event: VoiceEvent) -> None:
            ...     print(f"Received steer: {event.action}")
        """

        def decorator(handler: EventHandler) -> EventHandler:
            self._handlers[event_type].append(handler)
            logger.debug("Registered handler for %s events: %s", event_type, handler.__name__)
            return handler

        return decorator

    def add_handler(self, event_type: VoiceEventType, handler: EventHandler) -> None:
        """Register an event handler programmatically.

        Args:
            event_type: The event type to handle.
            handler: Async function that receives VoiceEvent.
        """
        self._handlers[event_type].append(handler)
        logger.debug("Added handler for %s events: %s", event_type, handler.__name__)

    def remove_handler(self, event_type: VoiceEventType, handler: EventHandler) -> bool:
        """Remove a previously registered handler.

        Args:
            event_type: The event type.
            handler: The handler function to remove.

        Returns:
            True if the handler was found and removed, False otherwise.
        """
        try:
            self._handlers[event_type].remove(handler)
            logger.debug("Removed handler for %s events: %s", event_type, handler.__name__)
            return True
        except ValueError:
            return False

    async def connect(self) -> None:
        """Connect to the NATS server and subscribe to event subjects.

        Raises:
            nats.errors.Error: If connection fails after all retry attempts.
        """
        if self._connected:
            logger.warning("Already connected to NATS")
            return

        await self._connect_with_backoff()

    async def _connect_with_backoff(self) -> None:
        """Connect to NATS with exponential backoff on failure."""
        attempts = 0
        self._backoff_seconds = self.INITIAL_BACKOFF_SECONDS

        while True:
            try:
                self._nc = await nats.connect(
                    self._nats_url,
                    token=self._token,
                    reconnect_time_wait=self._backoff_seconds,
                    max_reconnect_attempts=self._reconnect_attempts,
                    error_cb=self._error_callback,
                    disconnected_cb=self._disconnected_callback,
                    reconnected_cb=self._reconnected_callback,
                    closed_cb=self._closed_callback,
                )
                self._connected = True
                self._backoff_seconds = self.INITIAL_BACKOFF_SECONDS
                logger.info("Connected to NATS at %s", self._nats_url)

                # Subscribe to all event types
                await self._subscribe_all()
                return

            except Exception as e:
                attempts += 1
                if self._reconnect_attempts >= 0 and attempts >= self._reconnect_attempts:
                    logger.error("Failed to connect after %d attempts", attempts)
                    raise

                logger.warning(
                    "Connection attempt %d failed: %s. Retrying in %.1fs...",
                    attempts,
                    e,
                    self._backoff_seconds,
                )
                await asyncio.sleep(self._backoff_seconds)
                self._backoff_seconds = min(
                    self._backoff_seconds * self.BACKOFF_MULTIPLIER,
                    self.MAX_BACKOFF_SECONDS,
                )

    async def _subscribe_all(self) -> None:
        """Subscribe to all voice event subjects."""
        if self._nc is None:
            return

        for event_type in ("steer", "done", "speak"):
            subject = f"{self.SUBJECT_PREFIX}.{event_type}"
            sub = await self._nc.subscribe(
                subject,
                cb=self._make_message_handler(event_type),  # type: ignore[arg-type]
            )
            self._subscriptions.append(sub)
            logger.debug("Subscribed to %s", subject)

    def _make_message_handler(self, event_type: VoiceEventType) -> Callable[[Msg], Awaitable[None]]:
        """Create a message handler for a specific event type."""

        async def handler(msg: Msg) -> None:
            try:
                data = json.loads(msg.data.decode())
                event = VoiceEvent.from_dict(data)

                for event_handler in self._handlers[event_type]:
                    try:
                        await event_handler(event)
                    except Exception:
                        logger.exception(
                            "Error in handler %s for event %s",
                            event_handler.__name__,
                            event.id,
                        )
            except Exception:
                logger.exception("Failed to process message on %s", msg.subject)

        return handler

    async def disconnect(self) -> None:
        """Disconnect from the NATS server."""
        if not self._connected or self._nc is None:
            return

        # Unsubscribe from all subscriptions
        for sub in self._subscriptions:
            try:
                await sub.unsubscribe()
            except Exception:
                logger.exception("Error unsubscribing")
        self._subscriptions.clear()

        # Drain and close the connection
        try:
            await self._nc.drain()
        except Exception:
            logger.exception("Error draining connection")

        self._connected = False
        self._nc = None
        logger.info("Disconnected from NATS")

    async def emit(
        self,
        event_type: VoiceEventType,
        payload: EventPayload | dict[str, Any],
        *,
        author: str | None = None,
    ) -> VoiceEvent:
        """Emit a voice event.

        Args:
            event_type: The type of event to emit.
            payload: Event payload (EventPayload or dict).
            author: Override the default author for this event.

        Returns:
            The emitted VoiceEvent.

        Raises:
            RuntimeError: If not connected to NATS.
        """
        if not self.is_connected or self._nc is None:
            msg = "Not connected to NATS. Call connect() first."
            raise RuntimeError(msg)

        # Convert dict payload to EventPayload
        if isinstance(payload, dict):
            payload = EventPayload(**payload)

        # Build the full event
        event = VoiceEvent(
            id=str(uuid.uuid4()),
            type=event_type,
            action=payload.action,
            target=payload.target,
            env=payload.env,
            confidence=payload.confidence,
            transcript=payload.transcript,
            author=author or self._author,
            timestamp=datetime.now(timezone.utc),
        )

        # Publish to NATS
        subject = f"{self.SUBJECT_PREFIX}.{event_type}"
        await self._nc.publish(subject, event.to_json().encode())
        logger.debug("Emitted %s event: %s", event_type, event.id)

        return event

    # NATS callbacks
    async def _error_callback(self, e: Exception) -> None:
        """Handle NATS errors."""
        logger.error("NATS error: %s", e)

    async def _disconnected_callback(self) -> None:
        """Handle disconnection events."""
        logger.warning("Disconnected from NATS")
        self._connected = False

    async def _reconnected_callback(self) -> None:
        """Handle reconnection events."""
        logger.info("Reconnected to NATS")
        self._connected = True
        self._backoff_seconds = self.INITIAL_BACKOFF_SECONDS

    async def _closed_callback(self) -> None:
        """Handle connection closed events."""
        logger.info("NATS connection closed")
        self._connected = False

    async def __aenter__(self) -> VoiceEventClient:
        """Async context manager entry - connect to NATS."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit - disconnect from NATS."""
        await self.disconnect()
