//! Error types for the FleetView Voice SDK.

use thiserror::Error;

/// Errors that can occur when using the VoiceClient.
#[derive(Error, Debug)]
pub enum VoiceError {
    /// Failed to connect to NATS server.
    #[error("connection failed: {0}")]
    Connection(#[from] async_nats::ConnectError),

    /// Failed to subscribe to a subject.
    #[error("subscription failed: {0}")]
    Subscription(#[from] async_nats::SubscribeError),

    /// Failed to publish a message.
    #[error("publish failed: {0}")]
    Publish(#[from] async_nats::PublishError),

    /// Failed to serialize or deserialize an event.
    #[error("serialization failed: {0}")]
    Serialization(#[from] serde_json::Error),

    /// Client is not connected.
    #[error("client is not connected")]
    NotConnected,

    /// Invalid configuration.
    #[error("invalid configuration: {0}")]
    InvalidConfig(String),

    /// Connection was closed unexpectedly.
    #[error("connection closed")]
    ConnectionClosed,

    /// Maximum reconnection attempts exceeded.
    #[error("max reconnection attempts exceeded after {attempts} tries")]
    MaxReconnectExceeded { attempts: u32 },
}

/// Result type alias for VoiceClient operations.
pub type Result<T> = std::result::Result<T, VoiceError>;
