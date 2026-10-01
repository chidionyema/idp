/**
 * The estate face: one talking head for every surface that speaks (Fleet, Otto, Concierge).
 *
 * It adds a face to the voice the estate already has; it does not replace any of it. Hearing,
 * thinking and speaking stay server-side (/voice/hear, /voice/stream, /voice/say), so a phone
 * downloads only the face (~7 MB, vendored under /face/ by bin/estate-face-vendor), never a model.
 * The founder tried two in-browser demos on 2026-09-30 and both were "too slow to load": they pull
 * ~590 MB of models onto the device. That is the mistake this avoids.
 *
 * Each clause `/voice/say` returns (24 kHz float32 PCM) is handed to TalkingHead with the clause's
 * words spread over its duration, and TalkingHead plays it, moving the lips to those words.
 */
import type { ClauseSink } from './useEstateVoice';

export const FACE_ASSETS = '/face/';
const TTS_RATE = 24000;

export interface WordTimings {
  words: string[];
  wtimes: number[];
  wdurations: number[];
}

/**
 * Spread a clause's words over `ms` of audio, each word weighted by its length (a long word takes
 * longer to say), after a short lead-in. Pure, so it is tested without a browser.
 */
export function wordTimings(text: string, ms: number, leadMs = 60): WordTimings {
  const words = text.split(/\s+/).filter(Boolean);
  if (!words.length || ms <= 0) return { words: [], wtimes: [], wdurations: [] };
  const lead = Math.min(leadMs, ms * 0.1);
  const span = ms - lead;
  const weights = words.map((w) => w.replace(/[^\p{L}\p{N}]/gu, '').length + 1);
  const total = weights.reduce((a, b) => a + b, 0);
  const wtimes: number[] = [];
  const wdurations: number[] = [];
  let t = lead;
  for (const w of weights) {
    const d = (span * w) / total;
    wtimes.push(Math.round(t));
    wdurations.push(Math.round(d));
    t += d;
  }
  return { words, wtimes, wdurations };
}

export interface EstateFace extends ClauseSink {
  dispose(): void;
}

/** Mount the face into `el`. Resolves once the avatar is on screen; rejects with a named reason. */
export async function mountFace(el: HTMLElement): Promise<EstateFace> {
  // webpackIgnore: the face ships as plain ES modules under /face/, loaded from our own origin at
  // run time, not bundled into the app (three.js twice would cost every page, not just this one).
  const mod = await import(/* webpackIgnore: true */ `${FACE_ASSETS}talkinghead.mjs`);
  const head = new mod.TalkingHead(el, {
    ttsEndpoint: null,
    lipsyncModules: ['en'],
    lipsyncLang: 'en',
    cameraView: 'upper',
    avatarMood: 'neutral',
  });
  await head.showAvatar({ url: `${FACE_ASSETS}brunette.glb`, body: 'F', lipsyncLang: 'en' });
  return {
    speak(pcm: ArrayBuffer, text: string) {
      const f32 = new Float32Array(pcm);
      if (!f32.length) return;
      const ctx: AudioContext = head.audioCtx;
      if (ctx.state === 'suspended') ctx.resume().catch(() => undefined);
      const audio = ctx.createBuffer(1, f32.length, TTS_RATE);
      audio.copyToChannel(f32, 0);
      head.speakAudio({ audio, ...wordTimings(text, audio.duration * 1000) }, { lipsyncLang: 'en' });
    },
    stop() {
      head.stopSpeaking();
    },
    dispose() {
      try {
        head.stopSpeaking();
        head.stop();
      } catch {
        /* already gone */
      }
      el.replaceChildren();
    },
  };
}
