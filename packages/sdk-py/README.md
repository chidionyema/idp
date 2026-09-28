# FleetView Voice Python SDK

A fully typed Python SDK for voice events over NATS.

## Installation

```bash
pip install fleetview-voice
```

Or install from source:

```bash
cd packages/sdk-py
pip install -e .
```

## Quick Start

```python
import asyncio
from fleetview_voice import VoiceEventClient, VoiceEvent, EventPayload

async def main():
    # Create the client
    client = VoiceEventClient(
        token="your-nats-token",
        nats_url="nats://localhost:4222"
    )

    # Register event handlers using decorators
    @client.on("steer")
    async def handle_steer(event: VoiceEvent) -> None:
        print(f"{event.author} commanded: {event.transcript}")
        print(f"Action: {event.action}, Target: {event.target}")

    @client.on("done")
    async def handle_done(event: VoiceEvent) -> None:
        print(f"Task completed: {event.action}")

    # Connect and run
    async with client:
        # Emit an event
        await client.emit("done", EventPayload(
            action="deploy",
            transcript="deployment complete",
            target="production",
            env="prod"
        ))

        # Keep running to receive events
        await asyncio.sleep(60)

asyncio.run(main())
```

## API Reference

### VoiceEventClient

The main client for sending and receiving voice events.

```python
client = VoiceEventClient(
    token="auth-token",           # Required: NATS auth token
    nats_url="nats://host:4222",  # Optional: NATS URL (default: localhost:4222)
    author="my-service",          # Optional: Default author for events
    reconnect_attempts=-1         # Optional: Reconnect attempts (-1 = infinite)
)
```

#### Methods

- `client.on(event_type)` - Decorator to register an event handler
- `client.add_handler(event_type, handler)` - Register a handler programmatically
- `client.remove_handler(event_type, handler)` - Remove a handler
- `await client.connect()` - Connect to NATS
- `await client.disconnect()` - Disconnect from NATS
- `await client.emit(event_type, payload)` - Emit an event
- `client.is_connected` - Check connection status

#### Context Manager

```python
async with client:
    # Client is connected
    await client.emit("done", payload)
# Client is automatically disconnected
```

### VoiceEvent

A voice event received from NATS.

```python
@dataclass(frozen=True, slots=True)
class VoiceEvent:
    id: str                          # Unique event ID
    type: Literal['steer', 'done', 'speak']  # Event type
    action: str                      # The action
    target: str | None               # Target entity
    env: str | None                  # Environment
    confidence: float                # Recognition confidence (0.0-1.0)
    transcript: str                  # Raw transcript
    author: str                      # Event author
    timestamp: datetime              # Event timestamp
```

#### Methods

- `event.to_dict()` - Serialize to dictionary
- `event.to_json()` - Serialize to JSON string
- `VoiceEvent.from_dict(data)` - Deserialize from dictionary
- `VoiceEvent.from_json(json_str)` - Deserialize from JSON

### EventPayload

Payload for emitting events.

```python
@dataclass
class EventPayload:
    action: str                      # Required: Action to perform
    transcript: str                  # Required: Voice transcript
    target: str | None = None        # Optional: Target entity
    env: str | None = None           # Optional: Environment
    confidence: float = 1.0          # Optional: Confidence score
```

## Event Types

| Type | Description |
|------|-------------|
| `steer` | Steering commands from voice input |
| `done` | Task completion notifications |
| `speak` | Speech synthesis requests |

## Features

### Automatic Reconnection

The client automatically reconnects with exponential backoff:
- Initial delay: 1 second
- Maximum delay: 30 seconds
- Multiplier: 2x per attempt

### Connection Pooling

The client reuses NATS connections for efficiency.

### Full Type Hints

The SDK is fully typed for Python 3.10+ and passes strict mypy checks.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run type checks
mypy fleetview_voice

# Run linter
ruff check fleetview_voice

# Run tests
pytest
```

## License

MIT
