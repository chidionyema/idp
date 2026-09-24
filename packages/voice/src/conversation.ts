/**
 * Conversation — the memory and turn structure a voice client must have to FEEL continuous.
 *
 * WHY THE EDGE CLIENT NEEDED THIS AND DID NOT HAVE IT. `VoiceClient` was a one-shot command
 * parser: VAD → whisper → intent → `onIntent()`. Every utterance was a cold start with no idea
 * what had just been said, so "what about that one" was unanswerable, "tell me more" was
 * meaningless, and there was no way to interrupt a sentence already being spoken. That is the
 * seam between the edge client and the server (voice.py's `history_block`) — a person had to
 * re-name everything every time.
 *
 * This module is the join. It gives the edge client the SAME conversation primitives the server
 * already has, shaped the SAME way, so a turn that runs on-device and a turn answered by the
 * estate router resolve "it" and "that one" against one shared memory, and a barge-in mid-speech
 * cancels cleanly instead of stacking two voices.
 *
 * WHY IT IS A PURE, SYNCHRONOUS, TESTABLE MODULE. Conversation state is just a bounded buffer of
 * turns plus an interrupt flag. No WebAudio, no microphone, no model — so it can be unit-tested
 * without a browser, which is what turns "the client remembers" from a claim into a gate.
 */

/** A single turn in the conversation, newest-last ordering is `history()`'s job. */
export interface ConversationTurn {
  /** Who spoke: 'person' or 'agent'. Mirrors voice.py's `who` field. */
  who: 'person' | 'agent';
  /** The text that was heard or spoken. */
  text: string;
  /** Epoch milliseconds when the turn completed. */
  at: number;
}

/**
 * A conversation: bounded memory plus the barge-in flag.
 *
 * The cap is a deliberate latency choice, not a default. Every remembered turn is a token that
 * will be sent to the model on the next call, and a prompt that grows with the conversation grows
 * the latency with it. Six turns is the same ceiling the server's `history_block` uses.
 */
export interface Conversation {
  /** Remember a turn. Drops the oldest when past the cap. */
  remember(who: 'person' | 'agent', text: string): void;
  /** The remembered turns, oldest-first, capped. */
  history(): ConversationTurn[];
  /** The last `n` turns with non-empty text, oldest-first — the "it"/"that one" resolver. */
  recent(n?: number): ConversationTurn[];
  /** True when a barge-in has been requested and not yet cleared. */
  readonly bargedIn: boolean;
  /** Request a barge-in (stop speaking and cancel in-flight synthesis). */
  bargeIn(): void;
  /** Clear the barge-in flag. */
  clearBargeIn(): void;
  /** Drop all turns and the barge-in flag. */
  reset(): void;
}

/** The default cap, matching voice.py's `history_block(limit=6)`. */
export const DEFAULT_TURN_CAP = 6;

/**
 * Create a conversation with the given turn cap.
 *
 * @param cap Maximum turns remembered (clamped to >= 1).
 */
export function createConversation(cap: number = DEFAULT_TURN_CAP): Conversation {
  const turns: ConversationTurn[] = [];
  const limit = Math.max(1, Math.floor(cap));
  let _bargedIn = false;

  const remember = (who: 'person' | 'agent', text: string): void => {
    const trimmed = (text ?? '').trim();
    if (!trimmed) {
      // An empty turn is not a turn; it must not displace a real one.
      return;
    }
    turns.push({ who, text: trimmed, at: Date.now() });
    if (turns.length > limit) {
      turns.splice(0, turns.length - limit);
    }
  };

  const history = (): ConversationTurn[] => turns.slice();

  const recent = (n: number = limit): ConversationTurn[] => {
    const k = Math.max(1, Math.floor(n));
    return turns
      .filter((t) => t.text)
      .slice(-k);
  };

  return {
    remember,
    history,
    recent,
    get bargedIn() {
      return _bargedIn;
    },
    bargeIn() {
      _bargedIn = true;
    },
    clearBargeIn() {
      _bargedIn = false;
    },
    reset() {
      turns.splice(0, turns.length);
      _bargedIn = false;
    },
  };
}

/**
 * Render a conversation as the `RECENT CONVERSATION` block the server's prompt expects.
 *
 * This is the wire shape: the same lines `voice.py::history_block` emits, so an edge client and
 * the server produce one indistinguishable prompt and the model never notices which leg handled
 * the last turn. Returns '' for an empty conversation.
 */
export function conversationBlock(convo: Conversation, limit: number = DEFAULT_TURN_CAP): string {
  const tail = convo.recent(limit);
  if (tail.length === 0) {
    return '';
  }
  const lines = ['RECENT CONVERSATION (newest last; use it to resolve "it" and "that one")'];
  for (const t of tail) {
    const who = t.who === 'person' ? 'Person' : 'You';
    lines.push(`${who}: ${t.text.slice(0, 200)}`);
  }
  return lines.join('\n') + '\n\n';
}
