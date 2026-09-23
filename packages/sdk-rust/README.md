# FleetView Voice SDK for Rust

A fully typed Rust SDK for voice events over NATS.

## Installation

Add this to your `Cargo.toml`:

```toml
[dependencies]
fleetview-voice = "0.1"
tokio = { version = "1", features = ["full"] }
```

## Quick Start

```rust
use fleetview_voice::{VoiceClient, Config, EmitPayload};
use std::env;

#[tokio::main]
async fn main() -> fleetview_voice::Result<()> {
    // Create a client with configuration
    let client = VoiceClient::new(Config::builder()
        .token(env::var("API_TOKEN")?)
        .nats_url("nats://localhost:4222")
        .author("my-service")
        .build()?);

    // Register event handlers before connecting
    client.on("steer", |event| {
        println!("{} commanded: {}", event.author, event.transcript);
        println!("Action: {}, Target: {:?}", event.action, event.target);
    }).await?;

    // Connect to NATS (with automatic reconnection)
    client.connect().await?;

    // Emit events
    client.emit("done", EmitPayload::new("deploy", "deployment completed")
        .with_target("my-service")
        .with_env("production")
    ).await?;

    // Disconnect when done
    client.disconnect().await?;

    Ok(())
}
```

## Configuration

The SDK uses a builder pattern for configuration:

```rust
let config = Config::builder()
    .token("your-api-token")           // Required: NATS auth token
    .nats_url("nats://localhost:4222") // Required: NATS server URL
    .author("service-name")            // Optional: Author for emitted events
    .subject_prefix("voice")           // Optional: Subject prefix (default: "voice")
    .max_reconnect_attempts(10)        // Optional: Max reconnect attempts (default: 10)
    .initial_backoff(Duration::from_secs(1))  // Optional: Initial backoff (default: 1s)
    .max_backoff(Duration::from_secs(30))     // Optional: Max backoff (default: 30s)
    .build()?;
```

## Event Types

The SDK supports three event types:

- `steer` - A steering command from a user
- `done` - Acknowledgment that a task is complete
- `speak` - A spoken response to emit

## Event Structure

```rust
pub struct Event {
    pub id: String,                    // Unique event ID
    pub event_type: EventType,         // steer, done, or speak
    pub action: String,                // The action performed
    pub target: Option<String>,        // Target service/resource
    pub env: Option<String>,           // Environment (prod, staging)
    pub confidence: f64,               // Recognition confidence (0.0-1.0)
    pub transcript: String,            // Raw transcript
    pub author: String,                // Who created the event
    pub timestamp: DateTime<Utc>,      // When it was created
}
```

## Subscribing to Events

Register handlers before calling `connect()`:

```rust
// Handle steer commands
client.on("steer", |event| {
    match event.action.as_str() {
        "deploy" => handle_deploy(event.target),
        "scale" => handle_scale(event.target),
        _ => println!("Unknown action: {}", event.action),
    }
}).await?;

// Handle completion events
client.on("done", |event| {
    println!("Task {} completed by {}", event.action, event.author);
}).await?;
```

## Emitting Events

```rust
// Simple emit
client.emit("done", EmitPayload::new("deploy", "deployment complete")).await?;

// With full payload
client.emit("speak", EmitPayload::new("response", "Hello, how can I help?")
    .with_target("user-123")
    .with_env("production")
    .with_confidence(0.95)
).await?;
```

## Connection Management

The SDK handles reconnection automatically with exponential backoff:

- Starts at 1 second delay
- Doubles each attempt (1s, 2s, 4s, 8s...)
- Caps at 30 seconds maximum
- Gives up after 10 attempts by default

Check connection state:

```rust
if client.is_connected().await {
    // Safe to emit
}

match client.state().await {
    ConnectionState::Connected => { /* ready */ }
    ConnectionState::Reconnecting => { /* temporary issue */ }
    ConnectionState::Disconnected => { /* not connected */ }
    ConnectionState::Connecting => { /* in progress */ }
}
```

## Error Handling

The SDK uses `thiserror` for typed errors:

```rust
use fleetview_voice::{Result, VoiceError};

match client.connect().await {
    Ok(()) => println!("Connected!"),
    Err(VoiceError::Connection(e)) => println!("Connection failed: {}", e),
    Err(VoiceError::MaxReconnectExceeded { attempts }) => {
        println!("Gave up after {} attempts", attempts);
    }
    Err(e) => println!("Other error: {}", e),
}
```

## License

MIT
