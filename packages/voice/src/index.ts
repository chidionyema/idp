/**
 * @fleetview/voice - Voice control SDK
 *
 * Zero-config voice integration for web applications.
 *
 * @example
 * ```typescript
 * import { VoiceClient } from '@fleetview/voice';
 *
 * const client = new VoiceClient({
 *   onIntent: (intent) => console.log(intent),
 *   onSpeaking: (speaking) => updateUI(speaking),
 * });
 *
 * await client.start();
 * await client.speak("Ready for commands");
 * ```
 *
 * @packageDocumentation
 */

// Main client
export { VoiceClient } from './VoiceClient';

// Conversation (memory + barge-in)
export {
  createConversation,
  conversationBlock,
  DEFAULT_TURN_CAP,
  type Conversation,
  type ConversationTurn,
} from './conversation';

// Individual processors for advanced use
export { VADProcessor, createVADStream } from './vad';
export { ASRProcessor, resampleTo16kHz, audioBufferToFloat32 } from './asr';
export { IntentProcessor } from './intent';
export { TTSProcessor, VOICES } from './tts';
export type { VoiceId } from './tts';

// Model utilities
export {
  loadModel,
  getModelInfo,
  checkCacheStatus,
  clearCache,
  preloadAllModels,
} from './models';

// Types
export type {
  Intent,
  IntentCategory,
  VADState,
  ModelProgress,
  VoiceClientConfig,
  VoiceClientState,
  ASRResult,
  TTSOptions,
  ModelInfo,
} from './types';
