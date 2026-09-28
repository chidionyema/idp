//! Types for the FleetView Voice SDK.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// The type of voice event.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum EventType {
    /// A steering command from a user.
    Steer,
    /// Acknowledgment that a task is complete.
    Done,
    /// A spoken response to emit.
    Speak,
}

impl std::fmt::Display for EventType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            EventType::Steer => write!(f, "steer"),
            EventType::Done => write!(f, "done"),
            EventType::Speak => write!(f, "speak"),
        }
    }
}

impl std::str::FromStr for EventType {
    type Err = String;

    fn from_str(s: &str) -> std::result::Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "steer" => Ok(EventType::Steer),
            "done" => Ok(EventType::Done),
            "speak" => Ok(EventType::Speak),
            _ => Err(format!("unknown event type: {}", s)),
        }
    }
}

/// A voice event transmitted over NATS.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Event {
    /// Unique identifier for this event.
    pub id: String,

    /// The type of event.
    #[serde(rename = "type")]
    pub event_type: EventType,

    /// The action to perform or that was performed.
    pub action: String,

    /// Optional target of the action (e.g., service name, resource).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub target: Option<String>,

    /// Optional environment context (e.g., "production", "staging").
    #[serde(skip_serializing_if = "Option::is_none")]
    pub env: Option<String>,

    /// Confidence score of the voice recognition (0.0 to 1.0).
    pub confidence: f64,

    /// The raw transcript of what was spoken.
    pub transcript: String,

    /// The author/speaker of the event.
    pub author: String,

    /// When this event was created.
    pub timestamp: DateTime<Utc>,
}

impl Event {
    /// Creates a new Event with the given parameters.
    pub fn new(
        event_type: EventType,
        action: impl Into<String>,
        transcript: impl Into<String>,
        author: impl Into<String>,
    ) -> Self {
        Self {
            id: uuid::Uuid::new_v4().to_string(),
            event_type,
            action: action.into(),
            target: None,
            env: None,
            confidence: 1.0,
            transcript: transcript.into(),
            author: author.into(),
            timestamp: Utc::now(),
        }
    }

    /// Sets the target for this event.
    pub fn with_target(mut self, target: impl Into<String>) -> Self {
        self.target = Some(target.into());
        self
    }

    /// Sets the environment for this event.
    pub fn with_env(mut self, env: impl Into<String>) -> Self {
        self.env = Some(env.into());
        self
    }

    /// Sets the confidence score for this event.
    pub fn with_confidence(mut self, confidence: f64) -> Self {
        self.confidence = confidence.clamp(0.0, 1.0);
        self
    }
}

/// Payload for emitting events.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmitPayload {
    /// The action being performed.
    pub action: String,

    /// Optional target of the action.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub target: Option<String>,

    /// Optional environment context.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub env: Option<String>,

    /// The transcript or message content.
    pub transcript: String,

    /// Optional confidence score override.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub confidence: Option<f64>,
}

impl EmitPayload {
    /// Creates a new EmitPayload with the given action and transcript.
    pub fn new(action: impl Into<String>, transcript: impl Into<String>) -> Self {
        Self {
            action: action.into(),
            target: None,
            env: None,
            transcript: transcript.into(),
            confidence: None,
        }
    }

    /// Sets the target for this payload.
    pub fn with_target(mut self, target: impl Into<String>) -> Self {
        self.target = Some(target.into());
        self
    }

    /// Sets the environment for this payload.
    pub fn with_env(mut self, env: impl Into<String>) -> Self {
        self.env = Some(env.into());
        self
    }

    /// Sets the confidence for this payload.
    pub fn with_confidence(mut self, confidence: f64) -> Self {
        self.confidence = Some(confidence);
        self
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_event_type_serialization() {
        assert_eq!(
            serde_json::to_string(&EventType::Steer).unwrap(),
            "\"steer\""
        );
        assert_eq!(
            serde_json::to_string(&EventType::Done).unwrap(),
            "\"done\""
        );
        assert_eq!(
            serde_json::to_string(&EventType::Speak).unwrap(),
            "\"speak\""
        );
    }

    #[test]
    fn test_event_type_deserialization() {
        assert_eq!(
            serde_json::from_str::<EventType>("\"steer\"").unwrap(),
            EventType::Steer
        );
        assert_eq!(
            serde_json::from_str::<EventType>("\"done\"").unwrap(),
            EventType::Done
        );
        assert_eq!(
            serde_json::from_str::<EventType>("\"speak\"").unwrap(),
            EventType::Speak
        );
    }

    #[test]
    fn test_event_builder() {
        let event = Event::new(EventType::Steer, "deploy", "deploy to prod", "alice")
            .with_target("my-service")
            .with_env("production")
            .with_confidence(0.95);

        assert_eq!(event.event_type, EventType::Steer);
        assert_eq!(event.action, "deploy");
        assert_eq!(event.target, Some("my-service".to_string()));
        assert_eq!(event.env, Some("production".to_string()));
        assert_eq!(event.confidence, 0.95);
    }

    #[test]
    fn test_confidence_clamping() {
        let event = Event::new(EventType::Done, "test", "test", "bob").with_confidence(1.5);
        assert_eq!(event.confidence, 1.0);

        let event = Event::new(EventType::Done, "test", "test", "bob").with_confidence(-0.5);
        assert_eq!(event.confidence, 0.0);
    }
}
