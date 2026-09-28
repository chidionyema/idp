/**
 * FleetView Voice SDK
 *
 * TypeScript SDK for voice events over NATS WebSocket.
 *
 * @packageDocumentation
 */

export { VoiceEventClient } from './client.js';
export type {
  VoiceEvent,
  VoiceEventType,
  VoiceEventWire,
  VoiceEventClientOptions,
  VoiceEventHandler,
  VoiceEventPayload,
  ConnectionState,
  VoiceEventMap,
} from './types.js';
