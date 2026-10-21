/**
 * How loud the face is, in one place. (idp#6784: "i can barely hear what is being said, the voice
 * volume is low".)
 *
 * WHY THIS EXISTS. Every voice the face has (Kokoro in the browser, the pod's voices, the router's
 * Piper) hands the page raw PCM, and each of them turned that PCM into an AudioBuffer at whatever
 * level the model happened to produce -- Kokoro and Piper both come out well under full scale --
 * and played it at gain 1. There was no gain stage anywhere and no setting, so the only loudness
 * control the founder had was the phone's own volume key. This module is the stage that was
 * missing.
 *
 * HOW. Each clause is peak-normalised to `PEAK_CEILING * level` before it is queued. Normalising
 * rather than multiplying by a fixed amount is what makes the slider mean something: a fixed boost
 * clips a loud voice and leaves a quiet one quiet, while a normalised clause reaches the same peak
 * whichever engine made it, so switching voice does not change the volume. The ceiling is under
 * full scale, so nothing here can clip; `MAX_GAIN` stops a near-silent clause (a breath, a
 * trailing "uh") being blown up into noise.
 *
 * The function is pure on purpose: the same samples and level always give the same samples, so
 * "the face is loud enough" is a test with numbers in it, not a thing a person has to listen for.
 * It does NOT replace the device volume -- level 1 is the loudest this page can make a clause, and
 * a phone at half volume is still half volume.
 */

export const VOLUME_KEY = 'estate.face.volume';
/** 0..1. Not full: leaves the slider somewhere to go, and a phone speaker distorts at the top. */
export const DEFAULT_LEVEL = 0.85;
/** Linear peak at level 1. Below 1.0 so no sample the stage produces can clip. */
export const PEAK_CEILING = 0.95;
/** The most a clause is ever amplified: a quiet clause is lifted, a silent one is not made noise. */
export const MAX_GAIN = 8;
/** Below this peak a clause is treated as silence and passed through untouched. */
export const SILENCE_PEAK = 1e-4;

export const clampLevel = (x: number): number =>
  Number.isFinite(x) ? Math.min(1, Math.max(0, x)) : DEFAULT_LEVEL;

/** The loudest sample's magnitude. */
export function peakOf(pcm: Float32Array): number {
  let p = 0;
  for (let i = 0; i < pcm.length; i += 1) {
    const a = Math.abs(pcm[i]);
    if (a > p) p = a;
  }
  return p;
}

/** The linear gain that takes a clause with this peak to `PEAK_CEILING * level`. */
export function gainFor(peak: number, level: number): number {
  const l = clampLevel(level);
  if (l <= 0) return 0;
  if (!(peak > SILENCE_PEAK)) return 1;
  return Math.min(MAX_GAIN, (PEAK_CEILING * l) / peak);
}

/** A new array: the clause at this level. The input is never modified (it may be a shared view). */
export function applyLoudness(pcm: Float32Array, level: number = getLevel()): Float32Array {
  const g = gainFor(peakOf(pcm), level);
  const out = new Float32Array(pcm.length);
  for (let i = 0; i < pcm.length; i += 1) out[i] = pcm[i] * g;
  return out;
}

// --- the setting: one number, remembered on the device, readable from anywhere -----------------

type Store = Pick<Storage, 'getItem' | 'setItem'>;

const browserStore = (): Store | null => {
  try {
    return typeof localStorage !== 'undefined' ? localStorage : null;
  } catch {
    return null;
  }
};

export function readLevel(store: Pick<Storage, 'getItem'> | null = browserStore()): number {
  try {
    const raw = store?.getItem(VOLUME_KEY);
    if (raw == null || raw === '') return DEFAULT_LEVEL;
    return clampLevel(Number(raw));
  } catch {
    return DEFAULT_LEVEL;
  }
}

let level: number | null = null;
const listeners = new Set<() => void>();

/** The level in force now. Read from the device once, then held, so a clause costs no storage read. */
export function getLevel(): number {
  if (level === null) level = readLevel();
  return level;
}

/** Set the level, remember it, and tell whoever is showing it. Never throws (private mode). */
export function setLevel(next: number, store: Store | null = browserStore()): number {
  level = clampLevel(next);
  try {
    store?.setItem(VOLUME_KEY, String(level));
  } catch {
    /* quota or private mode: the level holds for this visit, which is what the person asked for */
  }
  listeners.forEach((l) => l());
  return level;
}

export function subscribeLevel(fn: () => void): () => void {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}

/** Test seam: forget the held level so the next read comes from the store again. */
export function resetLevelForTest(): void {
  level = null;
  listeners.clear();
}
