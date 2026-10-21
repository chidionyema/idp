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
import { applyLoudness } from './faceAudio';
import { DEFAULT_AVATAR, readAvatar, type Avatar } from './faceAvatars';

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

/**
 * Where speech actually is in a clause: the first and last 10ms window louder than the floor.
 *
 * The voices pad each clause with silence (macOS `say` leads with ~100-300ms), and spreading the
 * words over the WHOLE clip opened the mouth before the voice and kept it moving after: the lips
 * and the sound visibly out of step. The words are spread over this span instead. Pure.
 */
export function voicedSpan(
  f32: Float32Array,
  rate: number,
  floor = 0.02,
): { startMs: number; endMs: number } {
  const win = Math.max(1, Math.round(rate / 100));
  let first = -1;
  let last = -1;
  for (let i = 0; i < f32.length; i += win) {
    let sum = 0;
    const end = Math.min(f32.length, i + win);
    for (let j = i; j < end; j++) sum += f32[j] * f32[j];
    if (Math.sqrt(sum / (end - i)) > floor) {
      if (first < 0) first = i;
      last = end;
    }
  }
  const total = (f32.length / rate) * 1000;
  if (first < 0) return { startMs: 0, endMs: total };
  return { startMs: (first / rate) * 1000, endMs: (last / rate) * 1000 };
}

export interface EstateFace extends ClauseSink {
  /** The mood the face is currently resting in (continuity reflects this back to the visit). */
  mood(): string;
  /** The opening line this visit earns, from stored continuity. */
  greet(): string;
  /** Swap the model in place. Rejects with a named reason and leaves the current avatar on screen. */
  setAvatar(a: Pick<Avatar, 'url' | 'body'>): Promise<void>;
  dispose(): void;
}

/**
 * LIFE (spec docs/specs/2026-10-03-face-experience-10x.md section 3): the face is never inert.
 * Between utterances it blinks, it breathes, and every so often it settles into a new micro-gesture,
 * so the thing on screen reads as present rather than as a paused render. All of it is scheduled
 * from this pure list -- no DOM, no timers, no runtime -- so the cadence is testable and the same
 * cadence runs on every surface.
 *
 * Each `IdleBeat` is a delay in ms and what to do at that beat: a blink is `mood` unchanged with
 * `blink: true`; a settle is a new `mood` (the runtime's own names: neutral, happy, sad, love,
 * fear, disgust, angry, sleep); a shift is `gesture: true` (the runtime leans/nods). The sequence
 * is deliberately irregular -- a metronome reads as a machine.
 */
export interface IdleBeat {
  afterMs: number;
  blink?: boolean;
  mood?: string;
  gesture?: boolean;
  lookAhead?: number;
}

/** The estate's resting repertoire: blink often, settle rarely, lean occasionally. */
export const IDLE_BEATS: IdleBeat[] = [
  { afterMs: 2600, blink: true },
  { afterMs: 3100, blink: true },
  { afterMs: 8900, mood: 'happy', gesture: true },
  { afterMs: 2400, blink: true },
  { afterMs: 10700, mood: 'neutral' },
  { afterMs: 1900, blink: true },
  { afterMs: 3300, blink: true, lookAhead: 0.35 },
  { afterMs: 12100, mood: 'love', gesture: true },
  { afterMs: 2800, blink: true },
  { afterMs: 9700, mood: 'neutral', lookAhead: -0.25 },
];

/** The beat after `i` in a loop of `n`, wrapping. Pure so the loop is tested, not timed. */
export function nextBeat(i: number, n = IDLE_BEATS.length): IdleBeat {
  return IDLE_BEATS[i % n];
}

/**
 * CONTINUITY (spec section 4): the visit survives the page. A founder who was on /face, tapped
 * away to Fleet and comes back should not be met by a stranger -- the face remembers the mood it
 * had settled into and how many times it has seen them, so "second visit" is a real, observable
 * fact rather than a fresh mount. Stored as one small JSON string; every failure (no storage, bad
 * JSON, a shape from an older build) degrades to first-visit rather than throwing in the face.
 */
export interface FaceMemory {
  visits: number;
  mood: string;
  lastSeen: number;
}

export const CONTINUITY_KEY = 'estate.face.memory.v1';
const RESTING_MOODS = ['neutral', 'happy', 'love'];

/** Read the visit memory. `store` is injectable so the whole function is tested off-browser. */
export function readMemory(store: Pick<Storage, 'getItem'> | null): FaceMemory {
  const blank: FaceMemory = { visits: 0, mood: 'neutral', lastSeen: 0 };
  if (!store) return blank;
  try {
    const raw = store.getItem(CONTINUITY_KEY);
    if (!raw) return blank;
    const m = JSON.parse(raw) as Partial<FaceMemory>;
    if (typeof m.visits !== 'number' || !RESTING_MOODS.includes(String(m.mood))) return blank;
    return { visits: m.visits, mood: String(m.mood), lastSeen: Number(m.lastSeen) || 0 };
  } catch {
    return blank;
  }
}

/** Advance the memory for this visit and write it back. Never throws. */
export function recordVisit(
  store: Pick<Storage, 'getItem' | 'setItem'> | null,
  now: number,
  mood: string,
): FaceMemory {
  const prev = readMemory(store);
  const next: FaceMemory = {
    visits: prev.visits + 1,
    mood: RESTING_MOODS.includes(mood) ? mood : prev.mood,
    lastSeen: now,
  };
  try {
    store?.setItem(CONTINUITY_KEY, JSON.stringify(next));
  } catch {
    /* private mode, quota -- memory lives in-session instead */
  }
  return next;
}

/**
 * The opening line a returning visitor hears -- the reason continuity is not just a counter.
 * First visit greets; a returning visit names the familiarity without inventing a name it does
 * not have. Pure: same memory in, same sentence out.
 */
export function greeting(m: FaceMemory): string {
  if (m.visits <= 1) return 'The estate is up. Tap me and speak.';
  if (m.visits === 2) return 'You are back. Welcome again.';
  return `Welcome back, visit ${m.visits}.`;
}

// The face currently on screen, so a control elsewhere on the page (the deck's Persona tab) can swap
// its avatar without owning the mount. EstateFace sets it on mount and clears it on unmount.
let activeFace: EstateFace | null = null;
export function setActiveFace(f: EstateFace | null): void {
  activeFace = f;
}
export function getActiveFace(): EstateFace | null {
  return activeFace;
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
  // brunette.glb is the avatar the face loads. It is a Ready Player Me model under CC BY-NC 4.0 --
  // non-commercial -- restored by founder decision on 2026-10-10 because the estate-owned
  // alternative (estate.glb, authored by bin/estate-face-avatar: RPM bone names + 53 ARKit
  // blendshapes generated from geometry we compute) rendered as a featureless bust. This is
  // tracked debt, not clearance: bin/face-licence-known-blockers carries the entry and
  // bin/face-licence-gate prints it on every run (issue #5673). Replace it with a commercially
  // licensed or commissioned realistic avatar (spec
  // docs/specs/2026-10-03-face-experience-10x.md section 6) and delete the debt entry in the
  // same change.
  // The visitor's chosen avatar (faceAvatars.ts), brunette by default. A chosen model that fails to
  // load falls back to the default so the face never mounts empty.
  const store =
    typeof localStorage !== 'undefined'
      ? localStorage
      : null;
  const chosen = readAvatar(store, typeof location !== 'undefined' ? location.origin : undefined);
  try {
    await head.showAvatar({ url: chosen.url, body: chosen.body, lipsyncLang: 'en' });
  } catch (e) {
    if (chosen === DEFAULT_AVATAR) throw e;
    await head.showAvatar({ url: DEFAULT_AVATAR.url, body: DEFAULT_AVATAR.body, lipsyncLang: 'en' });
  }

  // CONTINUITY: restore the mood this visitor left the face in, and count the visit. The store is
  // localStorage on a real page; a browser that refuses it (private mode) still works, just
  // without memory -- readMemory/recordVisit degrade to first-visit rather than throwing.
  let memory = recordVisit(store, Date.now(), readMemory(store).mood);
  let mood = memory.mood;
  const applyMood = (m: string) => {
    mood = m;
    try {
      if (typeof head.setMood === 'function') head.setMood(m);
    } catch {
      /* an unknown mood leaves the previous one */
    }
  };
  applyMood(mood);

  // LIFE: run the idle repertoire on a timer. Beats are data (IDLE_BEATS); this loop only reads
  // them. Paused while speaking (the runtime owns the face then) and stopped on dispose.
  let beat = 0;
  let idle: ReturnType<typeof setTimeout> | null = null;
  let speaking = false;
  let speakingUntil = 0;
  const ends = new Set<() => void>();
  const runIdle = () => {
    if (speaking) return;
    const b = nextBeat(beat++);
    try {
      if (b.blink && typeof head.playGesture === 'function') head.playGesture('blink', 0.6, 0.5);
      if (b.gesture && typeof head.playGesture === 'function') head.playGesture('lean', 0.4, 1.2);
      if (b.mood) {
        applyMood(b.mood);
        memory = recordVisit(store, Date.now(), b.mood);
      }
      if (typeof b.lookAhead === 'number' && typeof head.lookAhead === 'function') {
        head.lookAhead(b.lookAhead, 0, false);
      }
    } catch {
      /* a runtime that lacks a call still keeps breathing */
    }
    idle = setTimeout(runIdle, b.afterMs);
  };
  idle = setTimeout(runIdle, IDLE_BEATS[0].afterMs);

  return {
    greet() {
      return greeting(memory);
    },
    mood() {
      return mood;
    },
    async setAvatar(a) {
      // showAvatar replaces the model inside the same renderer: no remount, the clause sink and the
      // idle loop stay attached. If it throws the runtime keeps the previous model.
      await head.showAvatar({ url: a.url, body: a.body, lipsyncLang: 'en' });
      applyMood(mood);
    },
    speak(pcm: ArrayBuffer, text: string) {
      const f32 = new Float32Array(pcm);
      if (!f32.length) return Promise.resolve();
      speaking = true;
      const ctx: AudioContext = head.audioCtx;
      if (ctx.state === 'suspended') ctx.resume().catch(() => undefined);
      const audio = ctx.createBuffer(1, f32.length, TTS_RATE);
      // The clause is raised to the founder's level here, and the voiced span below is read off
      // the ORIGINAL samples: its silence threshold is relative to the model's own level, and
      // measuring the boosted copy would move the mouth's timing (faceAudio.ts, idp#6784).
      audio.copyToChannel(applyLoudness(f32), 0);
      const { startMs, endMs } = voicedSpan(f32, TTS_RATE);
      const t = wordTimings(text, endMs - startMs, 0);
      head.speakAudio(
        { audio, ...t, wtimes: t.wtimes.map((w) => Math.round(w + startMs)) },
        { lipsyncLang: 'en' },
      );
      // TalkingHead QUEUES clauses, so this one ends after every clause already queued, not
      // `duration` from now. The voice waits on this before it listens again: going back to
      // listening while the face was still talking let the mic hear the face.
      const now = performance.now();
      speakingUntil = Math.max(speakingUntil, now) + audio.duration * 1000;
      const until = speakingUntil;
      return new Promise<void>((resolve) => {
        const done = () => {
          if (until === speakingUntil) speaking = false;
          resolve();
        };
        ends.add(done);
        setTimeout(() => {
          ends.delete(done);
          done();
        }, until - now + 250);
      });
    },
    stop() {
      speaking = false;
      speakingUntil = 0;
      head.stopSpeaking();
      for (const done of ends) done();
      ends.clear();
    },
    dispose() {
      if (idle) clearTimeout(idle);
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
