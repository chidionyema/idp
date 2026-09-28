//! FleetView Voice SDK for Rust
//!
//! A fully typed SDK for voice events over NATS.
//!
//! # Example
//!
//! ```rust,no_run
//! use fleetview_voice::{VoiceClient, Config, EmitPayload};
//! use std::env;
//!
//! #[tokio::main]
//! async fn main() -> fleetview_voice::Result<()> {
//!     let client = VoiceClient::new(Config::builder()
//!         .token(env::var("API_TOKEN").unwrap())
//!         .nats_url("nats://localhost:4222")
//!         .build()?);
//!
//!     client.on("steer", |event| {
//!         println!("{} commanded: {}", event.author, event.transcript);
//!     }).await?;
//!
//!     client.connect().await?;
//!     client.emit("done", EmitPayload::new("completed", "task finished")).await?;
//!     client.disconnect().await?;
//!
//!     Ok(())
//! }
//! ```

mod error;
mod types;

pub use error::{Result, VoiceError};
pub use types::{EmitPayload, Event, EventType};

use async_nats::Client as NatsClient;
use chrono::Utc;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::{Mutex, RwLock};
use tokio::task::JoinHandle;
use tracing::{debug, error, info, warn};

/// Configuration for the VoiceClient.
#[derive(Debug, Clone)]
pub struct Config {
    /// Authentication token for the NATS server.
    pub token: String,
    /// NATS server URL (e.g., "nats://localhost:4222").
    pub nats_url: String,
    /// Subject prefix for voice events (default: "voice").
    pub subject_prefix: String,
    /// Author name for emitted events.
    pub author: String,
    /// Maximum reconnection attempts (default: 10).
    pub max_reconnect_attempts: u32,
    /// Initial backoff delay for reconnection (default: 1s).
    pub initial_backoff: Duration,
    /// Maximum backoff delay for reconnection (default: 30s).
    pub max_backoff: Duration,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            token: String::new(),
            nats_url: "nats://localhost:4222".to_string(),
            subject_prefix: "voice".to_string(),
            author: "unknown".to_string(),
            max_reconnect_attempts: 10,
            initial_backoff: Duration::from_secs(1),
            max_backoff: Duration::from_secs(30),
        }
    }
}

/// Builder for creating a Config instance.
#[derive(Debug, Default)]
pub struct ConfigBuilder {
    config: Config,
}

impl ConfigBuilder {
    /// Creates a new ConfigBuilder with default values.
    pub fn new() -> Self {
        Self::default()
    }

    /// Sets the authentication token.
    pub fn token(mut self, token: impl Into<String>) -> Self {
        self.config.token = token.into();
        self
    }

    /// Sets the NATS server URL.
    pub fn nats_url(mut self, url: impl Into<String>) -> Self {
        self.config.nats_url = url.into();
        self
    }

    /// Sets the subject prefix for voice events.
    pub fn subject_prefix(mut self, prefix: impl Into<String>) -> Self {
        self.config.subject_prefix = prefix.into();
        self
    }

    /// Sets the author name for emitted events.
    pub fn author(mut self, author: impl Into<String>) -> Self {
        self.config.author = author.into();
        self
    }

    /// Sets the maximum reconnection attempts.
    pub fn max_reconnect_attempts(mut self, attempts: u32) -> Self {
        self.config.max_reconnect_attempts = attempts;
        self
    }

    /// Sets the initial backoff delay for reconnection.
    pub fn initial_backoff(mut self, duration: Duration) -> Self {
        self.config.initial_backoff = duration;
        self
    }

    /// Sets the maximum backoff delay for reconnection.
    pub fn max_backoff(mut self, duration: Duration) -> Self {
        self.config.max_backoff = duration;
        self
    }

    /// Builds the Config instance.
    pub fn build(self) -> Result<Config> {
        if self.config.token.is_empty() {
            return Err(VoiceError::InvalidConfig("token is required".to_string()));
        }
        if self.config.nats_url.is_empty() {
            return Err(VoiceError::InvalidConfig(
                "nats_url is required".to_string(),
            ));
        }
        Ok(self.config)
    }
}

impl Config {
    /// Creates a new ConfigBuilder.
    pub fn builder() -> ConfigBuilder {
        ConfigBuilder::new()
    }
}

type EventHandler = Arc<dyn Fn(Event) + Send + Sync>;

/// Client state for connection management.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConnectionState {
    /// Client is disconnected.
    Disconnected,
    /// Client is connecting.
    Connecting,
    /// Client is connected.
    Connected,
    /// Client is reconnecting after a disconnection.
    Reconnecting,
}

/// Voice client for sending and receiving voice events over NATS.
pub struct VoiceClient {
    config: Config,
    client: RwLock<Option<NatsClient>>,
    state: RwLock<ConnectionState>,
    handlers: Mutex<HashMap<String, Vec<EventHandler>>>,
    subscription_handles: Mutex<Vec<JoinHandle<()>>>,
}

impl VoiceClient {
    /// Creates a new VoiceClient with the given configuration.
    pub fn new(config: Config) -> Arc<Self> {
        Arc::new(Self {
            config,
            client: RwLock::new(None),
            state: RwLock::new(ConnectionState::Disconnected),
            handlers: Mutex::new(HashMap::new()),
            subscription_handles: Mutex::new(Vec::new()),
        })
    }

    /// Returns the current connection state.
    pub async fn state(&self) -> ConnectionState {
        *self.state.read().await
    }

    /// Registers an event handler for the given event type.
    ///
    /// The handler will be called whenever an event of the specified type is received.
    pub async fn on<F>(self: &Arc<Self>, event_type: &str, handler: F) -> Result<()>
    where
        F: Fn(Event) + Send + Sync + 'static,
    {
        let mut handlers = self.handlers.lock().await;
        handlers
            .entry(event_type.to_string())
            .or_default()
            .push(Arc::new(handler));
        debug!(event_type = event_type, "registered event handler");
        Ok(())
    }

    /// Connects to the NATS server.
    ///
    /// This method will attempt to connect with exponential backoff on failure.
    pub async fn connect(self: &Arc<Self>) -> Result<()> {
        let mut attempt = 0;
        let mut backoff = self.config.initial_backoff;

        loop {
            *self.state.write().await = if attempt == 0 {
                ConnectionState::Connecting
            } else {
                ConnectionState::Reconnecting
            };

            match self.try_connect().await {
                Ok(()) => {
                    *self.state.write().await = ConnectionState::Connected;
                    info!(url = %self.config.nats_url, "connected to NATS server");
                    self.start_subscriptions().await?;
                    return Ok(());
                }
                Err(e) => {
                    attempt += 1;
                    if attempt >= self.config.max_reconnect_attempts {
                        *self.state.write().await = ConnectionState::Disconnected;
                        return Err(VoiceError::MaxReconnectExceeded { attempts: attempt });
                    }

                    warn!(
                        error = %e,
                        attempt = attempt,
                        backoff_ms = backoff.as_millis(),
                        "connection failed, retrying"
                    );

                    tokio::time::sleep(backoff).await;
                    backoff = std::cmp::min(backoff * 2, self.config.max_backoff);
                }
            }
        }
    }

    async fn try_connect(&self) -> Result<()> {
        let options = async_nats::ConnectOptions::new().token(self.config.token.clone());

        let client = options.connect(&self.config.nats_url).await?;
        *self.client.write().await = Some(client);
        Ok(())
    }

    async fn start_subscriptions(self: &Arc<Self>) -> Result<()> {
        let handlers = self.handlers.lock().await;
        let client = self.client.read().await;
        let client = client.as_ref().ok_or(VoiceError::NotConnected)?;

        for event_type in handlers.keys() {
            let subject = format!("{}.{}", self.config.subject_prefix, event_type);
            let subscriber = client.subscribe(subject.clone()).await?;
            let self_clone = Arc::clone(self);
            let event_type = event_type.clone();

            let handle = tokio::spawn(async move {
                self_clone
                    .handle_subscription(subscriber, event_type)
                    .await;
            });

            self.subscription_handles.lock().await.push(handle);
            debug!(subject = subject, "started subscription");
        }

        Ok(())
    }

    async fn handle_subscription(
        self: Arc<Self>,
        mut subscriber: async_nats::Subscriber,
        event_type: String,
    ) {
        while let Some(message) = subscriber.next().await {
            match serde_json::from_slice::<Event>(&message.payload) {
                Ok(event) => {
                    let handlers = self.handlers.lock().await;
                    if let Some(event_handlers) = handlers.get(&event_type) {
                        for handler in event_handlers {
                            handler(event.clone());
                        }
                    }
                }
                Err(e) => {
                    error!(error = %e, "failed to deserialize event");
                }
            }
        }
    }

    /// Emits an event of the given type with the specified payload.
    pub async fn emit(&self, event_type: &str, payload: EmitPayload) -> Result<()> {
        let client = self.client.read().await;
        let client = client.as_ref().ok_or(VoiceError::NotConnected)?;

        let event_type_enum: EventType = event_type
            .parse()
            .map_err(|e: String| VoiceError::InvalidConfig(e))?;

        let event = Event {
            id: uuid::Uuid::new_v4().to_string(),
            event_type: event_type_enum,
            action: payload.action,
            target: payload.target,
            env: payload.env,
            confidence: payload.confidence.unwrap_or(1.0),
            transcript: payload.transcript,
            author: self.config.author.clone(),
            timestamp: Utc::now(),
        };

        let subject = format!("{}.{}", self.config.subject_prefix, event_type);
        let data = serde_json::to_vec(&event)?;

        client.publish(subject.clone(), data.into()).await?;
        debug!(subject = subject, event_id = event.id, "emitted event");

        Ok(())
    }

    /// Disconnects from the NATS server.
    pub async fn disconnect(&self) -> Result<()> {
        // Cancel all subscription handles
        let mut handles = self.subscription_handles.lock().await;
        for handle in handles.drain(..) {
            handle.abort();
        }

        // Flush and close the connection
        if let Some(client) = self.client.write().await.take() {
            if let Err(e) = client.flush().await {
                warn!(error = %e, "failed to flush on disconnect");
            }
        }

        *self.state.write().await = ConnectionState::Disconnected;
        info!("disconnected from NATS server");
        Ok(())
    }

    /// Returns true if the client is connected.
    pub async fn is_connected(&self) -> bool {
        *self.state.read().await == ConnectionState::Connected
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_builder() {
        let config = Config::builder()
            .token("test-token")
            .nats_url("nats://example.com:4222")
            .subject_prefix("custom")
            .author("test-author")
            .max_reconnect_attempts(5)
            .build()
            .unwrap();

        assert_eq!(config.token, "test-token");
        assert_eq!(config.nats_url, "nats://example.com:4222");
        assert_eq!(config.subject_prefix, "custom");
        assert_eq!(config.author, "test-author");
        assert_eq!(config.max_reconnect_attempts, 5);
    }

    #[test]
    fn test_config_builder_missing_token() {
        let result = Config::builder().nats_url("nats://localhost:4222").build();

        assert!(matches!(result, Err(VoiceError::InvalidConfig(_))));
    }

    #[test]
    fn test_config_builder_missing_url() {
        let result = Config::builder().token("token").nats_url("").build();

        assert!(matches!(result, Err(VoiceError::InvalidConfig(_))));
    }

    #[tokio::test]
    async fn test_voice_client_creation() {
        let config = Config::builder()
            .token("test-token")
            .nats_url("nats://localhost:4222")
            .build()
            .unwrap();

        let client = VoiceClient::new(config);
        assert_eq!(client.state().await, ConnectionState::Disconnected);
    }
}
