// voice/presence.ts
// The room listens continuously. It does not record. It does not transcribe
// what is not addressed to it. It uses a VAD (voice activity detector) and
// an address gate to decide what reaches the cloud.

import type { EventBus, RoomEvents } from '../core/events';
import type { Utterance, UtteranceId, UserId } from '../core/types';
import { asUtteranceId } from '../core/types';

export interface PresenceConfig {
  /** dB threshold. Below this is silence. */
  readonly vadThresholdDb: number;
  /** ms of continuous silence before we consider speech ended. */
  readonly silenceHangoverMs: number;
  /** ms of continuous speech before we emit a partial. */
  readonly minSpeechMs: number;
  /** The user this room belongs to. */
  readonly userId: UserId;
}

export const DEFAULT_PRESENCE: Omit<PresenceConfig, 'userId'> = {
  vadThresholdDb: -45,
  silenceHangoverMs: 700,
  minSpeechMs: 180,
};

export interface AudioFrame {
  readonly pcm: Float32Array;
  readonly sampleRate: number;
  readonly at: number;
}

export class VoicePresence {
  private config: PresenceConfig;
  private speaking = false;
  private speechStartedAt = 0;
  private lastLoudAt = 0;
  private currentUtteranceId: UtteranceId | null = null;

  constructor(
    private readonly events: EventBus<RoomEvents>,
    userId: UserId,
    config?: Partial<Omit<PresenceConfig, 'userId'>>,
  ) {
    this.config = { ...DEFAULT_PRESENCE, ...config, userId };
  }

  /** Feed a frame. The presence decides whether it is speech. */
  feed(frame: AudioFrame): void {
    const db = rmsDb(frame.pcm);
    const loud = db > this.config.vadThresholdDb;
    const now = frame.at;

    if (loud) {
      this.lastLoudAt = now;
      if (!this.speaking) {
        this.speaking = true;
        this.speechStartedAt = now;
        this.currentUtteranceId = asUtteranceId(newId());
      }
    } else {
      if (this.speaking && now - this.lastLoudAt > this.config.silenceHangoverMs) {
        this.speaking = false;
        this.currentUtteranceId = null;
        this.events.emit('voice:silence', { at: now });
      }
    }

    // Emit a partial if we've had enough speech.
    if (
      this.speaking &&
      now - this.speechStartedAt >= this.config.minSpeechMs &&
      this.currentUtteranceId
    ) {
      const partial: Utterance = {
        id: this.currentUtteranceId,
        speaker: { kind: 'user', userId: this.config.userId },
        text: '', // filled by STT
        isPartial: true,
        at: now,
        confidence: 0,
      };
      // Note: STT fills the text. This is a shape signal.
      void partial;
    }
  }

  isSpeaking(): boolean {
    return this.speaking;
  }

  currentId(): UtteranceId | null {
    return this.currentUtteranceId;
  }

  /** Feed a fully transcribed utterance. */
  emitFinal(utterance: Utterance): void {
    this.events.emit('voice:final', { utterance });
  }

  emitPartial(utterance: Utterance): void {
    this.events.emit('voice:partial', { utterance });
  }
}

function rmsDb(pcm: Float32Array): number {
  let sum = 0;
  for (let i = 0; i < pcm.length; i++) sum += pcm[i] * pcm[i];
  const rms = Math.sqrt(sum / pcm.length);
  if (rms === 0) return -Infinity;
  return 20 * Math.log10(rms);
}

function newId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}
