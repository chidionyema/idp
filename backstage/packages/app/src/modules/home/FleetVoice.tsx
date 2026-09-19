import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Button, Chip, TextField } from '@mui/material';
import { dark as T } from '../theme/tokens';
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
  /** Optional: called whenever the state word changes. */
  onStateChange?: (state: VoiceState) => void;
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

function resolveSession(
  sessions: Session[],
  target: string,
): Session | undefined {
  const needle = target.toLowerCase();
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

export default function FleetVoice({
  sessions = [],
  onFilter,
  onOpenDeck,
  onHighlight,
  onStateChange,
}: FleetVoiceProps): JSX.Element {
  const recognitionCtor = useMemo(() => getRecognitionCtor(), []);
  const synthesisAvailable = useMemo(() => hasSynthesis(), []);
  const supported = recognitionCtor !== null && synthesisAvailable;

  const [state, setState] = useState<VoiceState>('idle');
  const [interim, setInterim] = useState<string>('');
  const [pending, setPending] = useState<VoiceIntent | null>(null);
  const [notice, setNotice] = useState<string>('');
  const [deckText, setDeckText] = useState<string>('');
  const [deckOpen, setDeckOpen] = useState<boolean>(false);

  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const graceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const finalTranscriptRef = useRef<string>('');
  /** Only the not-yet-final words. Distinct from `interim`, which is the display string. */
  const interimTailRef = useRef<string>('');
  const holdingRef = useRef<boolean>(false);
  const stateRef = useRef<VoiceState>('idle');

  useEffect(() => {
    stateRef.current = state;
    if (onStateChange) onStateChange(state);
  }, [state, onStateChange]);

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

  const speak = useCallback(
    (text: string) => {
      if (!hasSynthesis() || text.trim().length === 0) {
        setState('idle');
        return;
      }
      try {
        window.speechSynthesis.cancel();
        const utter = new window.SpeechSynthesisUtterance(text);
        utter.onend = () => {
          if (stateRef.current === 'speaking') setState('idle');
        };
        utter.onerror = () => {
          if (stateRef.current === 'speaking') setState('idle');
        };
        setState('speaking');
        window.speechSynthesis.speak(utter);
      } catch {
        setState('idle');
      }
    },
    [],
  );

  const applyIntent = useCallback(
    (intent: VoiceIntent) => {
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
        const session = resolveSession(sessions, intent.target);
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
        const session = resolveSession(sessions, intent.target);
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

      setNotice(`Did not understand: ${intent.raw}`);
      speak('I did not understand that.');
    },
    [onFilter, onHighlight, onOpenDeck, sessions, speak],
  );

  const startListening = useCallback(() => {
    if (!supported || !recognitionCtor) return;
    cancelSynthesis();
    clearGrace();
    setPending(null);
    setNotice('');
    setInterim('');
    finalTranscriptRef.current = '';
    interimTailRef.current = '';

    try {
      const rec = new recognitionCtor();
      rec.lang = 'en-US';
      rec.continuous = true;
      rec.interimResults = true;

      rec.onresult = (event: any) => {
        let interimText = '';
        let finalText = '';
        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          const result = event.results[i];
          const transcript = result[0]?.transcript ?? '';
          if (result.isFinal) {
            finalText += transcript;
          } else {
            interimText += transcript;
          }
        }
        if (finalText) {
          finalTranscriptRef.current = `${finalTranscriptRef.current} ${finalText}`.trim();
        }
        // The DISPLAY string a person watches, and the INTERIM TAIL the stop handler needs.
        // They are different values and keeping them in one variable is what caused the duplicate.
        interimTailRef.current = interimText;
        const shown = `${finalTranscriptRef.current} ${interimText}`.trim();
        setInterim(shown);
      };

      rec.onerror = () => {
        setNotice('Microphone unavailable');
        setState('idle');
      };

      rec.onend = () => {
        if (holdingRef.current) return;
        setState((prev) => (prev === 'listening' ? 'idle' : prev));
      };

      recognitionRef.current = rec;
      rec.start();
      setState('listening');
    } catch {
      setNotice('Microphone unavailable');
      setState('idle');
    }
  }, [cancelSynthesis, clearGrace, recognitionCtor, supported]);

  const stopListening = useCallback(() => {
    const rec = recognitionRef.current;
    if (rec) {
      try {
        rec.stop();
      } catch {
        /* ignore */
      }
    }

    // THE RECOGNITION STAYS ALIVE THROUGH THINKING AND SPEAKING, and that is what makes barge-in
    // possible at all. The generated version nulled this ref here and stopped the mic on mouseUp,
    // so the barge-in effect below never had a recognition object to intercept -- a person could
    // not talk over the agent, which is the one interaction the research singled out: "VAD detects
    // speech while SPEAKING, cancel the stream, flush playback, resume capture".
    //
    // The mic therefore keeps listening while the agent thinks and speaks, and the result handler
    // distinguishes the modes: while SPEAKING a result IS the barge-in; while THINKING it is the
    // next utterance and accumulates normally.

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
    graceTimerRef.current = setTimeout(() => {
      graceTimerRef.current = null;
      applyIntent(intent);
    }, GRACE_MS);
  }, [applyIntent, clearGrace, interim]);

  const cancelPending = useCallback(() => {
    clearGrace();
    setPending(null);
    setInterim('');
    setNotice('Cancelled');
    setState('idle');
  }, [clearGrace]);

  // --- push-to-talk handlers ------------------------------------------------

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
        background: T.surface1,
        border: `1px solid ${T.border}`,
        borderRadius: 8,
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
        onMouseDown={handlePressStart}
        onMouseUp={handlePressEnd}
        onMouseLeave={handlePressEnd}
        onTouchStart={handlePressStart}
        onTouchEnd={handlePressEnd}
        style={{
          background: supported ? T.accent : T.surface3,
          color: supported ? T.inkOnAccent : T.textMuted,
          borderRadius: 8,
          textTransform: 'none',
          fontSize: 14,
        }}
      >
        🎤 Hold to talk
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
