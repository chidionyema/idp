import * as React from 'react';

// Voice as a progressive enhancement (AGENTS.md §9: voice first). Web Speech API where the browser
// has it; a visible "can't check" state where it does not. Whisper/Kokoro on WebGPU plug in later
// through `engine` without changing callers.
export type VoiceStatus = 'unsupported' | 'idle' | 'listening' | 'speaking' | 'error';

type Recognition = {
  lang: string; interimResults: boolean; continuous: boolean;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal: boolean }> }) => void) | null;
  onerror: (() => void) | null; onend: (() => void) | null; start(): void; stop(): void;
};
type RecognitionCtor = new () => Recognition;

export type VoiceEngine = {
  listen(onText: (text: string, final: boolean) => void, onDone: () => void, onError: () => void): () => void;
  speak(text: string, onDone: () => void): void;
};

function webSpeechEngine(lang: string): VoiceEngine | null {
  if (typeof window === 'undefined') return null;
  const w = window as unknown as { SpeechRecognition?: RecognitionCtor; webkitSpeechRecognition?: RecognitionCtor; speechSynthesis?: SpeechSynthesis };
  const Ctor = w.SpeechRecognition ?? w.webkitSpeechRecognition;
  if (!Ctor) return null;
  return {
    listen(onText, onDone, onError) {
      const r = new Ctor();
      r.lang = lang; r.interimResults = true; r.continuous = false;
      r.onresult = (e) => { const last = e.results[e.results.length - 1]; onText(last[0].transcript, last.isFinal); };
      r.onerror = onError; r.onend = onDone;
      r.start();
      return () => r.stop();
    },
    speak(text, onDone) {
      if (!w.speechSynthesis) return onDone();
      const u = new SpeechSynthesisUtterance(text); u.lang = lang; u.onend = onDone; u.onerror = onDone;
      w.speechSynthesis.speak(u);
    },
  };
}

export function useEstateVoice(opts: { lang?: string; engine?: VoiceEngine | null; onFinal?: (text: string) => void } = {}) {
  const lang = opts.lang ?? 'en-GB';
  const [status, setStatus] = React.useState<VoiceStatus>('idle');
  const [transcript, setTranscript] = React.useState('');
  const engineRef = React.useRef<VoiceEngine | null>(null);
  const stopRef = React.useRef<(() => void) | null>(null);
  React.useEffect(() => {
    engineRef.current = opts.engine === undefined ? webSpeechEngine(lang) : opts.engine;
    setStatus(engineRef.current ? 'idle' : 'unsupported');
  }, [lang, opts.engine]);

  const listen = React.useCallback(() => {
    const e = engineRef.current; if (!e) return;
    setTranscript(''); setStatus('listening');
    stopRef.current = e.listen(
      (t, final) => { setTranscript(t); if (final) opts.onFinal?.(t); },
      () => setStatus('idle'),
      () => setStatus('error'),
    );
  }, [opts]);
  const stop = React.useCallback(() => { stopRef.current?.(); stopRef.current = null; }, []);
  const speak = React.useCallback((text: string) => {
    const e = engineRef.current; if (!e) return;
    setStatus('speaking'); e.speak(text, () => setStatus('idle'));
  }, []);
  return { status, supported: status !== 'unsupported', transcript, listen, stop, speak };
}

const WORD: Record<VoiceStatus, string> = { unsupported: "Voice can't run here", idle: 'Press to talk', listening: 'Listening', speaking: 'Speaking', error: 'Did not catch that' };

/** Press to talk. State is a dot, a word and a tint, like every other state in the estate. */
export function VoiceButton({ onFinal, lang, className }: { onFinal?: (text: string) => void; lang?: string; className?: string }) {
  const v = useEstateVoice({ onFinal, lang });
  const tint = v.status === 'listening' ? 'text-state-running-ink bg-state-running-bg' : v.status === 'error' ? 'text-state-red-ink bg-state-red-bg' : v.status === 'unsupported' ? 'text-state-blind-ink bg-state-blind-bg' : 'text-text bg-surface-3';
  return React.createElement(
    'button',
    {
      type: 'button',
      disabled: !v.supported,
      'aria-pressed': v.status === 'listening',
      onClick: v.status === 'listening' ? v.stop : v.listen,
      className: `inline-flex items-center gap-2 rounded-pill px-4 min-h-(--size-tap-min) text-sm font-medium border border-current/30 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-70 ${tint} ${className ?? ''}`,
    },
    React.createElement('span', { 'aria-hidden': true, className: `size-2 rounded-pill ${v.status === 'unsupported' ? 'border border-current' : 'bg-current'} ${v.status === 'listening' ? 'animate-pulse' : ''}` }),
    React.createElement('span', null, v.transcript && v.status === 'listening' ? v.transcript : WORD[v.status]),
  );
}
