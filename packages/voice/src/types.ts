/**
 * FleetView Voice SDK Types
 */

/** Intent categories recognized by the voice system */
export type IntentCategory =
  | 'navigation'
  | 'action'
  | 'query'
  | 'control'
  | 'system'
  | 'unknown';

/** Parsed intent from voice input */
export interface Intent {
  /** The raw transcript from speech recognition */
  transcript: string;
  /** Parsed intent category */
  category: IntentCategory;
  /** Specific action within the category */
  action: string;
  /** Extracted entities from the utterance */
  entities: Record<string, string | number | boolean>;
  /** Confidence score 0-1 */
  confidence: number;
  /** Timestamp when intent was recognized */
  timestamp: number;
  /** True while user is still speaking (speculative intent) */
  partial?: boolean;
}

/** Voice activity detection state */
export interface VADState {
  /** Whether speech is currently detected */
  speaking: boolean;
  /** Probability of speech 0-1 */
  probability: number;
}

/** Model download progress */
export interface ModelProgress {
  /** Which model is being downloaded */
  model: 'vad' | 'asr' | 'intent' | 'tts';
  /** Progress 0-1 */
  progress: number;
  /** Bytes loaded */
  loaded: number;
  /** Total bytes */
  total: number;
}

/** Voice client configuration */
export interface VoiceClientConfig {
  /** FleetView API token for cloud features (optional for offline) */
  token?: string;

  /** Callback when an intent is recognized */
  onIntent?: (intent: Intent) => void;

  /** Callback when a partial transcript is available (speculative streaming) */
  onPartialTranscript?: (transcript: string) => void;

  /**
   * Callback when a FINAL intent's confidence is below the clarification floor (0.90).
   * The consumer is expected to ask the user one targeted question (via TTS or UI) and
   * feed the answer back into the next utterance. Fires on the FINAL intent only --
   * speculative partials are not clarification-worthy, by definition.
   */
  onClarificationNeeded?: (intent: Intent) => void;

  /** Callback when speaking state changes */
  onSpeaking?: (speaking: boolean) => void;

  /** Callback for errors */
  onError?: (error: Error) => void;

  /** Callback for model download progress */
  onModelProgress?: (progress: ModelProgress) => void;

  /** VAD sensitivity 0-1 (default 0.5) */
  vadSensitivity?: number;

  /** Minimum speech duration in ms before processing (default 300) */
  minSpeechDuration?: number;

  /** Silence duration in ms to end utterance (default 500) */
  silenceDuration?: number;

  /** Custom model cache directory (default: indexedDB in browser) */
  modelCacheDir?: string;

  /** Enable speculative streaming (emit partial intents while speaking) */
  speculativeStreaming?: boolean;

  /** Interval in ms for emitting partial transcripts (default 500) */
  partialInterval?: number;

  /** Enable debug logging */
  debug?: boolean;
}

/** Voice client state */
export type VoiceClientState =
  | 'idle'
  | 'loading'
  | 'ready'
  | 'listening'
  | 'processing'
  | 'speaking'
  | 'error';

/** ASR (Automatic Speech Recognition) result */
export interface ASRResult {
  text: string;
  confidence: number;
  segments?: Array<{
    text: string;
    start: number;
    end: number;
  }>;
}

/** TTS (Text-to-Speech) options */
export interface TTSOptions {
  /** Voice ID to use */
  voice?: string;
  /** Speed multiplier (default 1.0) */
  speed?: number;
  /** Pitch adjustment (-1 to 1, default 0) */
  pitch?: number;
}

/** Model info */
export interface ModelInfo {
  id: string;
  name: string;
  size: number;
  cached: boolean;
  url: string;
}
