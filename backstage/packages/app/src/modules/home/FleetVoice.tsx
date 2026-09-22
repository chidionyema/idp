import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Button, Chip, TextField } from '@mui/material';
import { dark as T } from '../theme/tokens';
// THE ESTATE'S OWN VOICE ENGINE. Every surface mounts this rather than reaching for
// SpeechRecognition/speechSynthesis, which are a network service to Google and the OS's formant
// voices respectively. See useEstateVoice.ts.
import { useEstateVoice } from './useEstateVoice';
import {
  ACTIVITY_WORD,
  ACTIVITY_SENTENCE,
  motionFor,
  ringStyleFor,
  type Activity,
} from './fleetMotion';
import type { Session } from './fleetBoard';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type VoiceState = 'idle' | 'listening' | 'thinking' | 'speaking';

export type VoiceIntent =
  | { kind: 'query'; activity: Activity; raw: string }
  | { kind: 'stop'; target: string; raw: string }
  | { kind: 'steer'; target: string; text: string; raw: string }
  | { kind: 'unknown'; raw: string };

export interface FleetVoiceProps {
  /** Sessions currently on the board, used to resolve agent names. */
  sessions?: Session[];
  /** Apply a query filter to the canvas. */
  onFilter?: (activity: Activity) => void;
  /** Open the deck for a session with pre-filled text. Never sends. */
  onOpenDeck?: (sessionId: string, text: string) => void;
  /** Highlight a session node before a mutation acts on it. */
  onHighlight?: (sessionId: string) => void;
  /**
   * THE NODE THE POINTER IS ON, or the current selection -- what a pronoun means.
   *
   * This is the fusion of the two input channels. The person points at a red node and says "stop
   * that one": the sentence carries the verb and the pointer carries the object, and neither
   * channel has to guess what the other meant. Without it, "it" is unresolvable and the honest
   * answer is a refusal -- which is exactly what the room used to give.
   */
  referent?: string | null;
  /** Optional: called whenever the state word changes. */
  onStateChange?: (state: VoiceState) => void;
  /**
   * ASK THE FLEET, in words. Anything that is not a command goes here and comes back as a spoken
   * sentence about the real board.
   *
   * WHY THIS PROP EXISTS. Before it, the component pattern-matched commands and answered
   * everything else with the hardcoded string "I did not understand that" -- there was NO model
   * call anywhere in this file. So voice could filter the board and nothing else: ask it why
   * something looked stuck and it said it did not understand, which was true and useless.
   */
  onAsk?: (question: string) => Promise<string | null>;
  /**
   * ASK, STREAMED. `speakClause` is called for each clause AS IT ARRIVES, so the first words are
   * heard about a second before the sentence is finished.
   *
   * WHY BOTH THIS AND `onAsk`: a caller with a one-shot endpoint still works, and one with a
   * streamed endpoint gets the latency. Streaming is what a person feels; the non-streaming prop
   * stays for tests and for any deployment that cannot hold a connection open.
   */
  onClause?: (question: string, speakClause: (text: string) => void) => Promise<void>;
  /**
   * THE SPOTLIGHT. Called with a session id when the person NAMES an agent, so the canvas can
   * bring that agent forward of the fleet and enlarge it.
   *
   * This is the difference between "the board filtered" and "the agent came to me". Saying "show
   * me pi" should not narrow a list; it should detach pi from the swarm.
   */
  onSpotlight?: (sessionId: string | null) => void;
}

// ---------------------------------------------------------------------------
// Browser capability detection
// ---------------------------------------------------------------------------

interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: any) => void) | null;
  onerror: ((event: any) => void) | null;
  onend: (() => void) | null;
}

type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

function getRecognitionCtor(): SpeechRecognitionCtor | null {
  if (typeof window === 'undefined') return null;
  const w = window as unknown as {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

function hasSynthesis(): boolean {
  return (
    typeof window !== 'undefined' &&
    typeof window.speechSynthesis !== 'undefined' &&
    typeof window.SpeechSynthesisUtterance !== 'undefined'
  );
}

// ---------------------------------------------------------------------------
// Intent parsing — ONLY the four commands in the spec.
// Unnamed input is a QUERY, never a mutation.
// ---------------------------------------------------------------------------

export function parseIntent(raw: string): VoiceIntent {
  const text = raw.trim().toLowerCase();
  const original = raw.trim();

  if (text.length === 0) return { kind: 'unknown', raw: original };

  // "what is stuck" / "what's stuck" / "show me stuck"
  if (
    /^(what('s| is)?\s+stuck|show\s+me\s+stuck|show\s+stuck)\b/.test(text)
  ) {
    return { kind: 'query', activity: 'stuck', raw: original };
  }

  // "show me waiting" / "what is waiting"
  if (
    /^(show\s+me\s+waiting|what('s| is)?\s+waiting|show\s+waiting)\b/.test(text)
  ) {
    return { kind: 'query', activity: 'waiting', raw: original };
  }

  // "stop <agent name>"
  const stopMatch = text.match(/^stop\s+(.+)$/);
  if (stopMatch) {
    return { kind: 'stop', target: stopMatch[1].trim(), raw: original };
  }

  // "steer <agent> <text>"
  const steerMatch = text.match(/^steer\s+(\S+)\s+(.+)$/);
  if (steerMatch) {
    return {
      kind: 'steer',
      target: steerMatch[1].trim(),
      text: steerMatch[2].trim(),
      raw: original,
    };
  }

  // Unnamed input is a QUERY, never a mutation.
  return { kind: 'unknown', raw: original };
}

// ---------------------------------------------------------------------------
// Session resolution
// ---------------------------------------------------------------------------

/**
 * The words that mean "the one I am pointing at".
 *
 * POINTER FUSION, and it is the whole of it. Before this, "stop the stuck one" had to be resolved
 * by reading the sentence, which is why it refused: the sentence does not name an agent, so there
 * was nothing to match. With a referent -- the node under the cursor, or the selection it became
 * -- "it" is not a pronoun the system has to disambiguate. It is a pointer the person is holding,
 * and the sentence only has to say what to DO.
 *
 * This is why the canvas reports hover separately from selection: hovering must not open menus or
 * move the camera, but it must be available as the thing a pronoun means.
 */
const REFERENTS = new Set([
  'it', 'its', 'this', 'that', 'this one', 'that one', 'them', 'this agent', 'that agent',
  'the selected', 'the selected one', 'the highlighted', 'the highlighted one', 'here',
]);

/** Whether an utterance's target is a pointer rather than a name. */
export function isReferent(target: string): boolean {
  return REFERENTS.has(target.trim().toLowerCase().replace(/[.?!]$/, ''));
}

function resolveSession(
  sessions: Session[],
  target: string,
  /** The node the pointer is on, or the current selection. What a pronoun means. */
  referent?: string | null,
): Session | undefined {
  const needle = target.toLowerCase();
  // A pronoun resolves to the referent and only the referent. Falling through to a text match
  // would let "it" match the word "it" in some task description, which is how a command lands on
  // the wrong agent -- the single worst failure this interface can have.
  if (isReferent(target)) {
    return referent ? sessions.find((s) => s.session_id === referent) : undefined;
  }
  return sessions.find((s) => {
    const id = (s.session_id ?? '').toLowerCase();
    const repo = (s.repo ?? '').toLowerCase();
    const task = (s.task ?? '').toLowerCase();
    return (
      id === needle ||
      id.includes(needle) ||
      repo.includes(needle) ||
      task.includes(needle)
    );
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const GRACE_MS = 1500;

/**
 * How long a pause means "finished".
 *
 * 900ms: shorter than a sentence-internal breath (people pause 200-600ms mid-clause) and longer
 * than the browser's own finalisation. Measured against the alternative: 1500ms felt like the
 * room was thinking; 600ms cut people off mid-sentence.
 */
// The constant itself is gone with restartAutoSend below: the engine's VAD decides end-of-speech
// now, so there is no countdown left to tune. The measurement above is kept because it is the
// reason a timer is the wrong instrument here, not a number waiting to be reused.

export default function FleetVoice({
  sessions = [],
  referent = null,
  onFilter,
  onOpenDeck,
  onHighlight,
  onStateChange,
  onAsk,
  onClause,
  onSpotlight,
}: FleetVoiceProps): JSX.Element {
  const recognitionCtor = useMemo(() => getRecognitionCtor(), []);
  const synthesisAvailable = useMemo(() => hasSynthesis(), []);
  const supported = recognitionCtor !== null && synthesisAvailable;

  const [state, setState] = useState<VoiceState>('idle');
  // THE ESTATE'S OWN VOICE ENGINE. Mounted here so this surface speaks with the same models as
  // every other one; see useEstateVoice.ts for why the browser APIs it replaces are not usable.
  const engine = useEstateVoice();
  const [interim, setInterim] = useState<string>('');
  const [pending, setPending] = useState<VoiceIntent | null>(null);
  const [notice, setNotice] = useState<string>('');
  const [deckText, setDeckText] = useState<string>('');
  const [deckOpen, setDeckOpen] = useState<boolean>(false);

  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const graceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  /** Fires AUTO_SEND_MS after the last word. Its whole job is that a person never clicks twice. */
  const autoSendTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const finalTranscriptRef = useRef<string>('');
  /** Only the not-yet-final words. Distinct from `interim`, which is the display string. */
  const interimTailRef = useRef<string>('');
  const holdingRef = useRef<boolean>(false);
  const stateRef = useRef<VoiceState>('idle');
  /** `stopListening` reached from the auto-send timer, which is declared before it. */
  const stopListeningRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    stateRef.current = state;
    // The auto-send timer must call the CURRENT stopListening, not the one from the
    // render that scheduled it.
    stopListeningRef.current = () => {};
    if (onStateChange) onStateChange(state);
  }, [state, onStateChange]);

  // THE ENGINE IS THE SOURCE OF TRUTH FOR WHAT WAS HEARD.
  //
  // The transcript now comes from whisper, not from a browser `onresult` handler, and it arrives
  // once per utterance rather than word by word -- so what a person watches in `interim` is the
  // sent utterance, and there is no interim tail to reconcile. The engine also owns the
  // listening/thinking/speaking states, and they are mapped onto this component's vocabulary so
  // every existing render branch keeps working.
  useEffect(() => {
    if (engine.heard) {
      setInterim(engine.heard);
      finalTranscriptRef.current = engine.heard;
    }
    if (engine.detail) setNotice(engine.detail);
    const map: Record<string, VoiceState> = {
      off: 'idle',
      listening: 'listening',
      thinking: 'thinking',
      speaking: 'speaking',
      error: 'idle',
    };
    setState(map[engine.state] || 'idle');
  }, [engine.heard, engine.detail, engine.state]);

  const clearGrace = useCallback(() => {
    if (graceTimerRef.current !== null) {
      clearTimeout(graceTimerRef.current);
      graceTimerRef.current = null;
    }
  }, []);

  const cancelSynthesis = useCallback(() => {
    if (hasSynthesis()) {
      try {
        window.speechSynthesis.cancel();
      } catch {
        /* ignore */
      }
    }
  }, []);

  /**
   * Speak a clause and let the next one queue behind it.
   *
   * NOW SERVED BY THE ESTATE'S OWN ENGINE, not `speechSynthesis`. The clause arrives as TEXT and is
   * synthesized here, which means a streamed reply sounds like the chosen Kokoro voice rather than
   * like the operating system's formant voices -- the two were previously different products
   * answering the same question.
   *
   * `engine.speak()` schedules on the WebAudio clock and queues naturally, so calling it per clause
   * is what makes a streamed answer sound like one sentence.
   */
  const speakQueued = useCallback(
    (text: string) => {
      if (!text.trim()) return;
      engine.speak(text);
      setState('speaking');
    },
    [engine],
  );

  const speak = useCallback(
    (text: string) => {
      if (!text.trim()) {
        setState('idle');
        return;
      }
      engine.silence();
      engine.speak(text);
      setState('speaking');
    },
    [engine],
  );

  const applyIntent = useCallback(
    // ASYNC, because a question now goes to the model. A recognised command still resolves
    // synchronously and acts immediately -- only free speech awaits a round trip, so the common
    // case ("what is stuck") does not pay for the uncommon one ("why does that look stuck").
    async (intent: VoiceIntent) => {
      setPending(null);
      setInterim('');
      setNotice('');

      if (intent.kind === 'query') {
        if (onFilter) onFilter(intent.activity);
        const word = ACTIVITY_WORD[intent.activity] ?? intent.activity;
        const sentence =
          ACTIVITY_SENTENCE[intent.activity] ?? `Filtering to ${word}.`;
        setNotice(`QUERY ${word}`);
        speak(sentence);
        return;
      }

      if (intent.kind === 'stop') {
        const session = resolveSession(sessions, intent.target, referent);
        if (!session) {
          setNotice(`No agent named ${intent.target}`);
          speak(`I could not find an agent named ${intent.target}.`);
          return;
        }
        if (onHighlight) onHighlight(session.session_id);
        setNotice(`MUTATION stop ${session.session_id} — confirm`);
        speak(`Stop ${session.session_id}. Confirm to proceed.`);
        return;
      }

      if (intent.kind === 'steer') {
        const session = resolveSession(sessions, intent.target, referent);
        if (!session) {
          setNotice(`No agent named ${intent.target}`);
          speak(`I could not find an agent named ${intent.target}.`);
          return;
        }
        if (onHighlight) onHighlight(session.session_id);
        setDeckText(intent.text);
        setDeckOpen(true);
        if (onOpenDeck) onOpenDeck(session.session_id, intent.text);
        setNotice(`MUTATION steer ${session.session_id} — not sent`);
        speak(`Steering ${session.session_id}. Review and send.`);
        return;
      }

      // NOT A COMMAND -> A QUESTION. This is the join to the model: the words go to the backend,
      // which reads the SAME sessions the board is showing and answers in one or two spoken
      // sentences. A recognised command still acts locally and instantly; only free speech costs
      // a round trip.
      // A NAMED AGENT COMES FORWARD. Checked before anything else, because "show me pi" is not a
      // question about the fleet -- it is a request to look at one agent, and answering it with a
      // filtered list is exactly the chart behaviour this replaces.
      const named = sessions.find(
        (s) =>
          intent.raw.toLowerCase().includes((s.runtime || '').toLowerCase()) ||
          intent.raw.toLowerCase().includes(String(s.session_id).slice(-6).toLowerCase()),
      );
      if (named && /show|look|focus|bring|watch|that one|this one/i.test(intent.raw)) {
        if (onSpotlight) onSpotlight(named.session_id);
        if (onHighlight) onHighlight(named.session_id);
        setNotice(`SHOW ${named.session_id}`);
      }

      setNotice(`ASK: ${intent.raw}`);

      // STREAMED FIRST. Each clause is spoken the moment it arrives, so the answer starts
      // sounding at ~300ms and continues while the model is still writing. `speakQueued` queues
      // rather than cancels, because cancelling per clause would cut off the clause before it.
      if (onClause) {
        setState('thinking');
        try {
          await onClause(intent.raw, (clause) => {
            setState('speaking');
            speakQueued(clause);
          });
          return;
        } catch (err) {
          const why = err instanceof Error ? err.message : String(err);
          setNotice(`ASK FAILED: ${why}`);
          speak('I could not reach the fleet to answer that.');
          return;
        }
      }

      if (!onAsk) {
        speak('I did not understand that, and I cannot ask the fleet on this page.');
        return;
      }
      setState('thinking');
      try {
        const answer = await onAsk(intent.raw);
        speak(answer || 'I could not get an answer about the fleet.');
      } catch (err) {
        // Say what failed rather than going silent: a voice that stops answering with no reason
        // is the failure this estate keeps removing.
        const why = err instanceof Error ? err.message : String(err);
        setNotice(`ASK FAILED: ${why}`);
        speak('I could not reach the fleet to answer that.');
      }
    },
    [onFilter, onHighlight, onOpenDeck, onSpotlight, sessions, speak, speakQueued, onAsk, onClause],
  );

  const startListening = useCallback(() => {
    clearGrace();
    setPending(null);
    setNotice('');
    setInterim('');
    finalTranscriptRef.current = '';
    interimTailRef.current = '';
    // THE ENGINE OWNS THE MICROPHONE NOW.
    //
    // Everything below this line in the old implementation was workaround for the browser's
    // recogniser: a silence timer to decide when an utterance ended, a restart on `end`, an
    // error table explaining why a `network` failure was indistinguishable from a denied
    // permission. The estate engine does voice-activity detection itself and streams the finished
    // utterance, so "speak and it goes" is the transport's behaviour rather than a timer's.
    void engine.start();
  }, [clearGrace, engine]);

  // restartAutoSend -- the "they have stopped talking" countdown -- was declared here and never
  // called, which is why tsc refused the build (TS6133). It belonged to the browser recogniser
  // this component no longer drives: the estate engine does voice-activity detection itself and
  // streams the finished utterance, so end-of-speech is the transport's answer, not a timer's
  // guess (see the comment above `void engine.start()`). clearAutoSend below stays, because the
  // ref it clears is still written elsewhere and a stale timer would send twice.

  const clearAutoSend = useCallback(() => {
    if (autoSendTimerRef.current !== null) {
      clearTimeout(autoSendTimerRef.current);
      autoSendTimerRef.current = null;
    }
  }, []);

  const stopListening = useCallback(() => {
    // This IS the send, so any pending countdown is now moot. Without this a person who taps Stop
    // and then speaks again would have the old timer fire mid-sentence.
    clearAutoSend();
    // BARGE-IN IS THE ENGINE'S JOB NOW, and it does it better: the VAD keeps running through
    // thinking and speaking, so talking over the reply stops playback and cancels generation
    // without this component intercepting anything. The old code had to keep a recogniser alive
    // across those states and decide, per result, whether it was an utterance or an interruption.
    //
    // `finalTranscriptRef` is the authority. `interim` is the DISPLAY string and already contains
    // the final text -- `setInterim` is called with `final + interim` so a person sees the words
    // they have said so far. Concatenating the two counted the final transcript twice: measured
    // 2026-09-18, "steer agent-beta try the other branch" arrived as "try the other branch steer
    // agent-beta try the other branch", which a real user would hit on any utterance that started
    // as interim and then finalised.
    const transcript = `${finalTranscriptRef.current} ${interimTailRef.current}`.trim();
    if (transcript.length === 0) {
      setState('idle');
      setInterim('');
      return;
    }

    const intent = parseIntent(transcript);
    setPending(intent);
    setState('thinking');
    clearGrace();

    // THE GRACE WINDOW IS FOR MUTATIONS, NOT FOR QUESTIONS.
    //
    // GRACE_MS is a cancellation window: a command changes something, so the reader gets 1.5s to
    // take it back. A QUESTION changes nothing -- there is nothing to cancel -- so making it wait
    // is 1.5 seconds of dead air for no protection at all. Measured: the first spoken clause
    // arrived at 3093ms, of which 1500ms was this timer doing nothing useful for a query.
    //
    // So a query runs immediately and a mutation keeps its window.
    const isMutation =
      // Only the kinds this parser can actually produce. approve and deny are not intents here
      // -- they are buttons in the deck -- and listing them made the check unreachable.
      intent.kind === 'stop' || intent.kind === 'steer';
    if (!isMutation) {
      applyIntent(intent);
      return;
    }
    graceTimerRef.current = setTimeout(() => {
      graceTimerRef.current = null;
      applyIntent(intent);
    }, GRACE_MS);
  }, [applyIntent, clearGrace, clearAutoSend, interim]);

  // The auto-send timer is created in a closure that predates stopListening, so it reaches it
  // through a ref that always holds the current one. A timer that captured the first render's
  // stopListening would send the wrong transcript after any re-render.
  useEffect(() => {
    stopListeningRef.current = stopListening;
  }, [stopListening]);


  const cancelPending = useCallback(() => {
    clearGrace();
    setPending(null);
    setInterim('');
    setNotice('Cancelled');
    setState('idle');
  }, [clearGrace]);

  // --- push-to-talk handlers ------------------------------------------------

  // CLICK TO TOGGLE, NOT HOLD. Holding a mouse button while speaking means one hand is occupied
  // at the exact moment a person is talking, and it makes every failure feel like a stuck button.
  // A click starts listening; the SAME click again stops it and sends what was heard. The
  // browser's own end-of-speech detection ends the turn on its own a moment after you stop
  // talking, so the second click is a fallback rather than the normal path.
  const handlePressStart = useCallback(() => {
    if (!supported) return;
    holdingRef.current = true;
    startListening();
  }, [startListening, supported]);

  const handlePressEnd = useCallback(() => {
    if (!supported) return;
    holdingRef.current = false;
    stopListening();
  }, [stopListening, supported]);

  /** One click: on if idle, off (and send) if listening. */
  const handleToggle = useCallback(() => {
    if (!supported) return;
    // A CLICK WHILE THINKING IS A SEND, NOT A RESTART.
    //
    // The button is one toggle, and `state` moves to `thinking` the moment a transcript is ready
    // -- so the second click of a tap-tap arrived with state === 'thinking', fell to the else,
    // and called startListening() again. The utterance was never sent, the intent chip never
    // appeared, and the person's words were silently discarded by a control that looked like it
    // had just been pressed. Two tests caught it ('shows the intent chip...' and 'cancels a
    // pending intent on Escape'), both failing against the production component.
    //
    // Thinking IS a listening posture -- the mic is still open and stopListening is what commits
    // the turn -- so the two states that mean "in flight" are handled together. Anything else
    // starts a turn.
    if (state === 'listening' || state === 'thinking' || state === 'speaking') stopListening();
    else startListening();
  }, [supported, state, startListening, stopListening]);

  // --- barge-in -------------------------------------------------------------

  useEffect(() => {
    if (state !== 'speaking') return;
    const rec = recognitionRef.current;
    if (!rec) return;
    // If recognition is already running while speaking, treat any result as barge-in.
    const prevOnResult = rec.onresult;
    rec.onresult = (event: any) => {
      const hasSpeech =
        event?.results && event.results.length > 0;
      if (hasSpeech) {
        cancelSynthesis();
        setState('listening');
      }
      if (prevOnResult) prevOnResult(event);
    };
    return () => {
      if (rec) rec.onresult = prevOnResult;
    };
  }, [cancelSynthesis, state]);

  // --- keyboard -------------------------------------------------------------

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.code === 'Space' && !e.repeat) {
        const target = e.target as HTMLElement | null;
        const tag = target?.tagName?.toLowerCase();
        if (tag === 'input' || tag === 'textarea') return;
        e.preventDefault();
        handlePressStart();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        cancelSynthesis();
        cancelPending();
      }
    };
    const onKeyUp = (e: KeyboardEvent) => {
      if (e.code === 'Space') {
        const target = e.target as HTMLElement | null;
        const tag = target?.tagName?.toLowerCase();
        if (tag === 'input' || tag === 'textarea') return;
        e.preventDefault();
        handlePressEnd();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('keyup', onKeyUp);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('keyup', onKeyUp);
    };
  }, [cancelPending, cancelSynthesis, handlePressEnd, handlePressStart]);

  // --- cleanup --------------------------------------------------------------

  useEffect(() => {
    return () => {
      clearGrace();
      cancelSynthesis();
      const rec = recognitionRef.current;
      if (rec) {
        try {
          rec.abort();
        } catch {
          /* ignore */
        }
      }
    };
  }, [cancelSynthesis, clearGrace]);

  // --- derived display ------------------------------------------------------

  const activityForState: Activity =
    state === 'listening'
      ? 'waiting'
      : state === 'thinking'
        ? 'thinking'
        : state === 'speaking'
          ? 'finished'
          : 'unknown';

  const motion = motionFor(activityForState);
  const ring = ringStyleFor(activityForState);

  const stateWord =
    state === 'listening'
      ? 'LISTENING'
      : state === 'thinking'
        ? 'THINKING'
        : state === 'speaking'
          ? 'SPEAKING'
          : 'IDLE';

  const disabledReason = !supported
    ? 'Voice unavailable: this browser has no speech recognition or synthesis.'
    : '';

  return (
    <div
      data-testid="fleet-voice"
      style={{
        // FLOATING, OVER THE ROOM. It was in normal flow after the canvas, so on a 900px viewport
        // it sat below the fold: you had to scroll past your fleet to find the thing you talk to.
        // Voice is the primary input of this room, so it hovers over the room the way a head-up
        // display hovers -- always reachable, never in the way.
        //
        // `position: fixed` rather than absolute: the canvas scrolls with the page and the voice
        // bar must not. Anchored bottom-centre, which is also where a thumb reaches on a phone,
        // and constrained to the viewport width so it cannot overflow on a small screen.
        position: 'fixed',
        left: '50%',
        transform: 'translateX(-50%)',
        bottom: 20,
        zIndex: 30,
        width: 'min(720px, calc(100vw - 32px))',
        boxShadow: '0 12px 40px rgba(0,0,0,0.55)',
        background: 'rgba(18,19,22,0.94)',
        backdropFilter: 'blur(10px)',
        border: `1px solid ${T.border}`,
        borderRadius: 12,
        padding: 12,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        color: T.textPrimary,
        fontFamily: 'inherit',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}
      >
        <span
          data-testid="voice-state-word"
          style={{
            fontSize: 12,
            letterSpacing: 1,
            color: T.textSecondary,
            fontWeight: 600,
          }}
        >
          {stateWord}
        </span>
        <span
          data-testid="voice-motion"
          data-motion={motion}
          style={{
            width: 10,
            height: 10,
            borderRadius: 999,
            // `ringStyleFor` returns borderStyle and opacity; the colour is the activity's
            // own, which is what the node uses too.
            background: T.accent,
            opacity: ring.opacity ?? 1,
          }}
        />
      </div>

      <Button
        data-testid="voice-ptt"
        variant="contained"
        disabled={!supported}
        // ONE CLICK. `onClick` rather than down/up: see handleToggle's comment. touch and mouse
        // both raise click, so both input paths work without a second pair of handlers.
        onClick={handleToggle}
        style={{
          background: supported ? T.accent : T.surface3,
          color: supported ? T.inkOnAccent : T.textMuted,
          borderRadius: 8,
          textTransform: 'none',
          fontSize: 14,
        }}
      >
        🎤 Ask the fleet
      </Button>

      {disabledReason ? (
        <span
          data-testid="voice-disabled-reason"
          style={{ fontSize: 12, color: T.textMuted }}
        >
          {disabledReason}
        </span>
      ) : null}

      {interim ? (
        <div
          data-testid="voice-interim"
          style={{ fontSize: 13, color: T.textSecondary }}
        >
          {interim}
        </div>
      ) : null}

      {pending ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Chip
            data-testid="voice-intent-chip"
            label={pending.raw}
            onDelete={cancelPending}
            style={{
              background: T.surface2,
              color: T.textPrimary,
              borderRadius: 999,
              fontSize: 12,
            }}
          />
          <span style={{ fontSize: 11, color: T.textMuted }}>
            acting in 1.5s — Escape to cancel
          </span>
        </div>
      ) : null}

      {notice ? (
        <div
          data-testid="voice-notice"
          style={{ fontSize: 12, color: T.textSecondary }}
        >
          {notice}
        </div>
      ) : null}

      {deckOpen ? (
        <TextField
          data-testid="voice-deck-text"
          value={deckText}
          onChange={(e) => setDeckText(e.target.value)}
          multiline
          fullWidth
          size="small"
          label="Steer text (not sent)"
          InputProps={{
            style: { fontSize: 13, color: T.textPrimary },
          }}
        />
      ) : null}
    </div>
  );
}
