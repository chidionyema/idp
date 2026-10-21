/*
 * The face's loudness stage (idp#6784). The founder could not hear it; the cause was that nothing
 * between the voice model and the speaker raised a quiet clause or let anyone set a level. These
 * pin the numbers: a quiet clause comes out at the level's peak, nothing clips, silence stays
 * silent, and the level survives a reload.
 */
import {
  applyLoudness,
  clampLevel,
  DEFAULT_LEVEL,
  gainFor,
  MAX_GAIN,
  PEAK_CEILING,
  peakOf,
  readLevel,
  resetLevelForTest,
  setLevel,
  getLevel,
  subscribeLevel,
  VOLUME_KEY,
} from './faceAudio';

const tone = (peak: number, n = 480): Float32Array =>
  Float32Array.from({ length: n }, (_, i) => peak * Math.sin((i / n) * Math.PI * 8));

const memory = () => {
  const m = new Map<string, string>();
  return {
    getItem: (k: string) => (m.has(k) ? (m.get(k) as string) : null),
    setItem: (k: string, v: string) => void m.set(k, v),
  };
};

describe('applyLoudness', () => {
  it('lifts a quiet clause (Kokoro-sized, peak 0.3) to the level\'s peak', () => {
    const out = applyLoudness(tone(0.3), 1);
    expect(peakOf(out)).toBeCloseTo(PEAK_CEILING, 2);
  });

  it('brings a quiet voice and a loud voice to the same peak, so changing voice does not change volume', () => {
    const quiet = peakOf(applyLoudness(tone(0.2), 0.85));
    const loud = peakOf(applyLoudness(tone(0.9), 0.85));
    expect(Math.abs(quiet - loud)).toBeLessThan(0.01);
  });

  it('never clips, whatever the input or level', () => {
    for (const p of [0.01, 0.2, 0.7, 1, 4]) {
      for (const l of [0.1, 0.5, 1, 7]) {
        expect(peakOf(applyLoudness(tone(p), l))).toBeLessThanOrEqual(PEAK_CEILING + 1e-6);
      }
    }
  });

  it('scales with the level: half the level, half the peak', () => {
    const full = peakOf(applyLoudness(tone(0.3), 1));
    const half = peakOf(applyLoudness(tone(0.3), 0.5));
    expect(half / full).toBeCloseTo(0.5, 2);
  });

  it('level 0 is mute', () => {
    expect(peakOf(applyLoudness(tone(0.5), 0))).toBe(0);
  });

  it('leaves silence silent instead of amplifying the noise floor', () => {
    const hush = new Float32Array(480).fill(0.00001);
    expect(gainFor(peakOf(hush), 1)).toBe(1);
    expect(peakOf(applyLoudness(hush, 1))).toBeCloseTo(0.00001, 8);
  });

  it('caps the boost so a near-silent clause is not blown up into noise', () => {
    expect(gainFor(0.001, 1)).toBe(MAX_GAIN);
  });

  it('does not modify the input (it can be a view on a shared buffer)', () => {
    const src = tone(0.3);
    const before = Array.from(src);
    applyLoudness(src, 1);
    expect(Array.from(src)).toEqual(before);
  });

  it('handles an empty clause', () => {
    expect(applyLoudness(new Float32Array(0), 1)).toHaveLength(0);
  });
});

describe('the remembered level', () => {
  beforeEach(resetLevelForTest);

  it('is the default until someone sets one', () => {
    expect(readLevel(memory())).toBe(DEFAULT_LEVEL);
  });

  it('reads back what was written', () => {
    const s = memory();
    setLevel(0.4, s);
    expect(readLevel(s)).toBeCloseTo(0.4, 5);
    expect(s.getItem(VOLUME_KEY)).toBe('0.4');
  });

  it('treats a corrupt stored value as the default, and clamps out-of-range ones', () => {
    const s = memory();
    s.setItem(VOLUME_KEY, 'loud');
    expect(readLevel(s)).toBe(DEFAULT_LEVEL);
    expect(clampLevel(9)).toBe(1);
    expect(clampLevel(-3)).toBe(0);
    expect(clampLevel(NaN)).toBe(DEFAULT_LEVEL);
  });

  it('survives a store that throws (private mode): the level still holds for the visit', () => {
    const angry = {
      getItem: () => {
        throw new Error('denied');
      },
      setItem: () => {
        throw new Error('denied');
      },
    };
    expect(readLevel(angry)).toBe(DEFAULT_LEVEL);
    expect(() => setLevel(0.3, angry)).not.toThrow();
    expect(getLevel()).toBeCloseTo(0.3, 5);
  });

  it('tells subscribers, and stops when they unsubscribe', () => {
    const seen: number[] = [];
    const off = subscribeLevel(() => seen.push(getLevel()));
    setLevel(0.2, memory());
    off();
    setLevel(0.9, memory());
    expect(seen).toEqual([0.2]);
  });
});
