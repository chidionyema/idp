/**
 * Zero-dependency Web Audio API aerospace telemetry synthesizer &
 * Dual-engine Executive Voice Player (Gemini 24kHz WAV + Browser SpeechSynthesis).
 * Zero external .mp3/.wav file fetches -> Zero 404 network errors.
 */

export type ChimeKind = 'lock' | 'clarify' | 'execute' | 'blast' | 'refuse' | 'incident_klaxon';

let sharedAudioCtx: AudioContext | null = null;

function getAudioCtx(): AudioContext | null {
  if (typeof window === 'undefined') return null;
  const Ctor =
    window.AudioContext ||
    (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!Ctor) return null;
  if (!sharedAudioCtx) {
    try {
      sharedAudioCtx = new Ctor();
    } catch {
      return null;
    }
  }
  if (sharedAudioCtx.state === 'suspended') {
    sharedAudioCtx.resume().catch(() => {
      // Autoplay policy before gesture; ignore silently
    });
  }
  return sharedAudioCtx;
}

export function playSovereignChime(kind: ChimeKind, enabled: boolean = true): void {
  if (!enabled) return;
  if (
    typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  ) {
    return;
  }

  const ctx = getAudioCtx();
  if (!ctx) return;

  const now = ctx.currentTime;
  const master = ctx.createGain();
  master.gain.setValueAtTime(0.0001, now);
  master.connect(ctx.destination);

  const scheduleTone = (
    freqHz: number,
    startOffsetSec: number,
    durationSec: number,
    type: OscillatorType = 'sine',
    peakGain: number = 0.045
  ) => {
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freqHz, now + startOffsetSec);

    g.gain.setValueAtTime(0.0001, now + startOffsetSec);
    g.gain.exponentialRampToValueAtTime(peakGain, now + startOffsetSec + 0.015);
    g.gain.exponentialRampToValueAtTime(0.0001, now + startOffsetSec + durationSec);

    osc.connect(g);
    g.connect(ctx.destination);
    osc.start(now + startOffsetSec);
    osc.stop(now + startOffsetSec + durationSec + 0.02);
  };

  switch (kind) {
    case 'lock':
      scheduleTone(528, 0, 0.09, 'sine', 0.035);
      scheduleTone(792, 0.04, 0.12, 'sine', 0.03);
      break;
    case 'clarify':
      scheduleTone(440, 0, 0.11, 'triangle', 0.04);
      scheduleTone(587.33, 0.07, 0.14, 'triangle', 0.035);
      break;
    case 'execute':
      scheduleTone(440, 0, 0.1, 'sine', 0.04);
      scheduleTone(659.25, 0.05, 0.12, 'sine', 0.04);
      scheduleTone(880, 0.1, 0.18, 'sine', 0.035);
      break;
    case 'blast':
      scheduleTone(146.83, 0, 0.28, 'sine', 0.055);
      scheduleTone(293.66, 0.03, 0.22, 'triangle', 0.03);
      break;
    case 'refuse':
      scheduleTone(330, 0, 0.11, 'sawtooth', 0.025);
      scheduleTone(246.94, 0.09, 0.16, 'sawtooth', 0.025);
      break;
    case 'incident_klaxon':
      scheduleTone(880, 0, 0.14, 'sawtooth', 0.065);
      scheduleTone(622.25, 0.15, 0.14, 'sawtooth', 0.065);
      scheduleTone(880, 0.31, 0.16, 'sawtooth', 0.07);
      break;
  }
}

export function playSovereignHeartbeatPulse(
  posture: 'NOMINAL_STEADY' | 'ELEVATED_TEMPO' | 'INCIDENT_RAPID' = 'NOMINAL_STEADY',
  enabled: boolean = true
): void {
  if (!enabled) return;
  const ctx = getAudioCtx();
  if (!ctx) return;

  const now = ctx.currentTime;
  const scheduleLubDub = (freqHz: number, offsetSec: number, durSec: number, peak: number) => {
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.type = posture === 'INCIDENT_RAPID' ? 'triangle' : 'sine';
    osc.frequency.setValueAtTime(freqHz, now + offsetSec);
    osc.frequency.exponentialRampToValueAtTime(Math.max(38, freqHz * 0.72), now + offsetSec + durSec);

    g.gain.setValueAtTime(0.0001, now + offsetSec);
    g.gain.exponentialRampToValueAtTime(peak, now + offsetSec + 0.018);
    g.gain.exponentialRampToValueAtTime(0.0001, now + offsetSec + durSec);

    osc.connect(g);
    g.connect(ctx.destination);
    osc.start(now + offsetSec);
    osc.stop(now + offsetSec + durSec + 0.02);
  };

  if (posture === 'INCIDENT_RAPID') {
    scheduleLubDub(110, 0, 0.11, 0.055);
    scheduleLubDub(146.83, 0.13, 0.13, 0.048);
  } else if (posture === 'ELEVATED_TEMPO') {
    scheduleLubDub(78, 0, 0.13, 0.042);
    scheduleLubDub(104, 0.16, 0.15, 0.036);
  } else {
    // Calm 60 BPM NASA / Submarine reactor lub-dub
    scheduleLubDub(65.41, 0, 0.14, 0.038);
    scheduleLubDub(87.31, 0.18, 0.16, 0.03);
  }
}

export function speakLiveEstateHeadline(spokenText: string, enabled: boolean = true): boolean {
  if (!enabled || !spokenText.trim()) return false;
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) return false;
  try {
    window.speechSynthesis.cancel();
    const utt = new SpeechSynthesisUtterance(spokenText.trim());
    utt.rate = 1.06;
    utt.pitch = 0.98;
    window.speechSynthesis.speak(utt);
    return true;
  } catch {
    return false;
  }
}

export interface SpeechPlaybackHandle {
  mode: 'GEMINI_24KHZ_WAV' | 'BROWSER_SPEECH_SYNTHESIS' | 'TRANSCRIPT_ONLY';
  stop: () => void;
}

let activeHtmlAudio: HTMLAudioElement | null = null;

export function stopAllSovereignSpeech(): void {
  if (activeHtmlAudio) {
    try {
      activeHtmlAudio.pause();
      activeHtmlAudio.currentTime = 0;
    } catch {
      // Ignore
    }
    activeHtmlAudio = null;
  }
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    try {
      window.speechSynthesis.cancel();
    } catch {
      // Ignore
    }
  }
}

export async function playExecutiveSpeech(
  script: string,
  wavBase64: string | null | undefined,
  onEnded?: () => void
): Promise<SpeechPlaybackHandle> {
  stopAllSovereignSpeech();

  if (wavBase64) {
    try {
      const audio = new Audio(`data:audio/wav;base64,${wavBase64}`);
      activeHtmlAudio = audio;
      audio.onended = () => {
        activeHtmlAudio = null;
        onEnded?.();
      };
      audio.onerror = () => {
        activeHtmlAudio = null;
        onEnded?.();
      };
      await audio.play();
      return {
        mode: 'GEMINI_24KHZ_WAV',
        stop: () => stopAllSovereignSpeech(),
      };
    } catch {
      activeHtmlAudio = null;
      // Fall through to Web Speech API or transcript display
    }
  }

  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    try {
      const utterance = new SpeechSynthesisUtterance(script);
      utterance.rate = 1.04;
      utterance.pitch = 0.98;
      utterance.onend = () => onEnded?.();
      utterance.onerror = () => onEnded?.();
      window.speechSynthesis.speak(utterance);
      // In headless browsers without OS TTS voices, onend may not fire quickly; guard with timer
      const estimatedMs = Math.min(18000, Math.max(2500, script.length * 48));
      const fallbackTimer = window.setTimeout(() => {
        onEnded?.();
      }, estimatedMs);
      return {
        mode: 'BROWSER_SPEECH_SYNTHESIS',
        stop: () => {
          window.clearTimeout(fallbackTimer);
          stopAllSovereignSpeech();
          onEnded?.();
        },
      };
    } catch {
      // Fall through
    }
  }

  onEnded?.();
  return {
    mode: 'TRANSCRIPT_ONLY',
    stop: () => {},
  };
}

export interface BrowserSpeechRecognizerHandle {
  supported: boolean;
  start: () => void;
  stop: () => void;
}

export function createBrowserSpeechRecognizer(callbacks: {
  onTranscript: (text: string, isFinal: boolean) => void;
  onError: (msg: string) => void;
  onEnd: () => void;
}): BrowserSpeechRecognizerHandle {
  if (typeof window === 'undefined') {
    return { supported: false, start: () => {}, stop: () => {} };
  }

  const SpeechRecCtor =
    (window as unknown as { SpeechRecognition?: new () => SpeechRecognitionInstance }).SpeechRecognition ||
    (window as unknown as { webkitSpeechRecognition?: new () => SpeechRecognitionInstance })
      .webkitSpeechRecognition;

  if (!SpeechRecCtor) {
    return { supported: false, start: () => {}, stop: () => {} };
  }

  const rec = new SpeechRecCtor();
  rec.continuous = false;
  rec.interimResults = true;
  rec.lang = 'en-US';

  rec.onresult = (event: SpeechRecognitionResultEventLike) => {
    let combined = '';
    let isFinal = false;
    for (let i = 0; i < event.results.length; i++) {
      const r = event.results[i];
      combined += r[0]?.transcript ?? '';
      if (r.isFinal) isFinal = true;
    }
    if (combined.trim()) {
      callbacks.onTranscript(combined.trim(), isFinal);
    }
  };

  rec.onerror = (ev: { error?: string }) => {
    callbacks.onError(ev?.error || 'speech-recognition-error');
  };

  rec.onend = () => {
    callbacks.onEnd();
  };

  return {
    supported: true,
    start: () => {
      try {
        rec.start();
      } catch (e) {
        callbacks.onError(e instanceof Error ? e.message : 'Unable to start speech recognition');
      }
    },
    stop: () => {
      try {
        rec.stop();
      } catch {
        // Ignore
      }
    },
  };
}

interface SpeechRecognitionResultEventLike {
  results: ArrayLike<{
    isFinal: boolean;
    0?: { transcript?: string };
  }>;
}

interface SpeechRecognitionInstance {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((ev: SpeechRecognitionResultEventLike) => void) | null;
  onerror: ((ev: { error?: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
}
