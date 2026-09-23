/**
 * Voice event types supported by the FleetView Voice SDK.
 */
export type VoiceEventType = 'steer' | 'done' | 'speak';

/**
 * Represents a voice event transmitted over NATS.
 */
export interface VoiceEvent {
  /** Unique identifier for this event */
  id: string;
  /** Type of voice event */
  type: VoiceEventType;
  /** Action to perform or that was performed */
  action: string;
  /** Optional target resource or entity */
  target?: string;
  /** Optional environment context (e.g., 'production', 'staging') */
  env?: string;
  /** Confidence score from speech recognition (0.0 to 1.0) */
  confidence: number;
  /** Original transcript from speech recognition */
  transcript: string;
  /** Author/originator of the event */
  author: string;
  /** Timestamp when the event was created */
  timestamp: Date;
}

/**
 * Wire format for VoiceEvent (JSON serialization).
 * Timestamp is serialized as ISO string.
 */
export interface VoiceEventWire {
  id: string;
  type: VoiceEventType;
  action: string;
  target?: string;
  env?: string;
  confidence: number;
  transcript: string;
  author: string;
  timestamp: string;
}

/**
 * Configuration options for VoiceEventClient.
 */
export interface VoiceEventClientOptions {
  /** Authentication token for NATS connection */
  token: string;
  /** NATS WebSocket URL (e.g., 'wss://nats.example.com:443') */
  natsUrl: string;
  /** Optional subject prefix for voice events (default: 'voice') */
  subjectPrefix?: string;
  /** Optional maximum reconnect attempts (default: unlimited) */
  maxReconnectAttempts?: number;
}

/**
 * Handler function for voice events.
 */
export type VoiceEventHandler<T extends VoiceEventType = VoiceEventType> = (
  event: VoiceEvent & { type: T }
) => void | Promise<void>;

/**
 * Payload for emitting voice events (excludes auto-generated fields).
 */
export type VoiceEventPayload = Omit<VoiceEvent, 'id' | 'timestamp' | 'type'>;

/**
 * Connection state for the client.
 */
export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';

/**
 * Event map for type-safe event handlers.
 */
export interface VoiceEventMap {
  steer: VoiceEvent & { type: 'steer' };
  done: VoiceEvent & { type: 'done' };
  speak: VoiceEvent & { type: 'speak' };
}
