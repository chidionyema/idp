// voice/wake.ts
// The room distinguishes ADDRESS from AMBIENT. It does not transcribe what
// was not meant for it. It uses context — gaze, wake words, naming — to
// decide. Uncertain → it waits. Certain → it acts.

import type { EventBus, RoomEvents } from '../core/events';

export interface WakeSignal {
  readonly kind: 'wake_word' | 'gaze' | 'name' | 'gesture' | 'touch';
  readonly word?: string;
  readonly confidence: number;
  readonly at: number;
}

export interface WakeConfig {
  readonly wakeWords: readonly string[];
  readonly requireConfidence: number;
  /** How long after a wake word the room stays "awake". */
  readonly wakeWindowMs: number;
}

export const DEFAULT_WAKE: WakeConfig = {
  wakeWords: ['room', 'fleet', 'hey room'],
  requireConfidence: 0.7,
  wakeWindowMs: 12_000,
};

export class WakeGate {
  private lastWakeAt = 0;
  private config: WakeConfig;

  constructor(
    private readonly events: EventBus<RoomEvents>,
    config?: Partial<WakeConfig>,
  ) {
    this.config = { ...DEFAULT_WAKE, ...config };
  }

  /** Called by the STT layer with the partial transcript of every frame. */
  consider(partial: string, at: number): boolean {
    const lower = partial.toLowerCase().trim();
    for (const w of this.config.wakeWords) {
      if (lower.endsWith(w) || lower === w) {
        this.wake(w, at);
        return true;
      }
    }
    return false;
  }

  /** Called by gaze/gesture/touch layers. */
  signal(s: WakeSignal): void {
    if (s.confidence < this.config.requireConfidence) return;
    this.wake(s.word ?? s.kind, s.at);
  }

  /** Is the room currently in its wake window? */
  isAwake(now: number): boolean {
    return now - this.lastWakeAt < this.config.wakeWindowMs;
  }

  private wake(word: string, at: number): void {
    this.lastWakeAt = at;
    this.events.emit('wake:detected', {
      word, confidence: 1, at,
    });
    this.events.emit('room:wake', { at });
  }
}
