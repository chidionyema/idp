import { CAPTURE_WORKLET, decodeFrame, toPanel, voiceRouterUrl } from './useVoiceRouter';

// The capture worklet runs in the browser's audio thread, which jest does not have. It is plain
// JavaScript, so it is executed here against a stub of the two globals that thread provides.
function loadWorklet(sampleRate: number) {
  let Processor: any;
  class AudioWorkletProcessor {
    port = { posted: [] as ArrayBuffer[], postMessage(b: ArrayBuffer) { this.posted.push(b); } };
  }
  // eslint-disable-next-line no-new-func
  new Function('AudioWorkletProcessor', 'registerProcessor', 'sampleRate', CAPTURE_WORKLET)(
    AudioWorkletProcessor,
    (_: string, cls: any) => {
      Processor = cls;
    },
    sampleRate,
  );
  return new Processor();
}

describe('the capture worklet', () => {
  it.each([48000, 44100, 16000])('turns %i Hz microphone audio into 20 ms frames at 16 kHz', (rate) => {
    const p = loadWorklet(rate);
    // One second of a 440 Hz tone in 128-sample render quanta, as the audio thread delivers it.
    const tone = Float32Array.from({ length: rate }, (_, i) => 0.5 * Math.sin((2 * Math.PI * 440 * i) / rate));
    for (let i = 0; i < tone.length; i += 128) p.process([[tone.subarray(i, i + 128)]]);
    const frames: Int16Array[] = p.port.posted.map((b: ArrayBuffer) => new Int16Array(b));
    expect(frames.every((f) => f.length === 320)).toBe(true);
    // 16000 samples a second, give or take the one still in flight at a fractional step (44.1k).
    expect(Math.abs(frames.length * 320 + p.i - 16000)).toBeLessThanOrEqual(1);
    // And no drift: ten more seconds land within one sample of 176000.
    for (let s = 0; s < 10; s++) for (let i = 0; i < tone.length; i += 128) p.process([[tone.subarray(i, i + 128)]]);
    expect(Math.abs(p.port.posted.length * 320 + p.i - 176000)).toBeLessThanOrEqual(1);
    // The tone survives: peak near half scale, and 440 cycles a second -> ~8.8 per 20 ms frame.
    const all = Int16Array.from(frames.flatMap((f) => Array.from(f)));
    const peak = Math.max(...Array.from(all, Math.abs));
    expect(peak).toBeGreaterThan(0.45 * 32767);
    expect(peak).toBeLessThanOrEqual(0.5 * 32767 + 1);
    let crossings = 0;
    for (let i = 1; i < all.length; i++) if ((all[i - 1] < 0) !== (all[i] < 0)) crossings++;
    // 880 crossings a second, scaled to the samples actually posted (49 full frames at 44.1k).
    const expected = (880 * all.length) / 16000;
    expect(Math.abs(crossings - expected)).toBeLessThan(10);
  });

  it('never exceeds int16 on a clipped input', () => {
    const p = loadWorklet(16000);
    p.process([[new Float32Array(320).fill(3)]]);
    p.process([[new Float32Array(320).fill(-3)]]);
    const [hi, lo] = p.port.posted.map((b: ArrayBuffer) => new Int16Array(b));
    expect(hi[0]).toBe(32767);
    expect(lo[0]).toBe(-32768);
  });
});

describe('server audio frames', () => {
  // The layout session.Frame writes: uint32 LE turn id, then int16 LE samples.
  function frame(turn: number, samples: number[]): ArrayBuffer {
    const b = new ArrayBuffer(4 + 2 * samples.length);
    const v = new DataView(b);
    v.setUint32(0, turn, true);
    samples.forEach((s, i) => v.setInt16(4 + 2 * i, s, true));
    return b;
  }

  it('carry their turn id and samples', () => {
    const f = decodeFrame(frame(7, [0, 16384, -32768, 32767]))!;
    expect(f.turn).toBe(7);
    expect(Array.from(f.pcm)).toEqual([0, 0.5, -1, 32767 / 32768]);
  });

  it('decode from a slice that does not start at offset 0', () => {
    const f = decodeFrame(frame(4294967295, [1, -1]))!;
    expect(f.turn).toBe(4294967295);
    expect(f.pcm.length).toBe(2);
  });

  it('too short to hold a sample are refused', () => {
    expect(decodeFrame(new ArrayBuffer(4))).toBeNull();
  });
});

describe('the socket address', () => {
  it('deployed, is the page’s own host, secure when the page is', () => {
    expect(voiceRouterUrl({ protocol: 'https:', host: 'portal.example.com' }, 'production')).toBe('wss://portal.example.com/voice/ws');
    expect(voiceRouterUrl({ protocol: 'http:', host: 'portal.local' }, 'production')).toBe('ws://portal.local/voice/ws');
  });
  it('under yarn start, is the laptop router, since the dev server cannot carry a WebSocket', () => {
    expect(voiceRouterUrl({ protocol: 'http:', host: 'localhost:3100' }, 'development')).toBe('ws://127.0.0.1:8091/voice/ws');
  });
});

describe('the turn record, as the /fleet voice panel reads it', () => {
  const body = {
    summary: { turns: 4, outcomes: { ok: 2, empty: 1, cancelled: 1 }, completed: 2,
      median_s: { asr_s: 0.524357, first_audio_s: 3.0635 } },
    recent: [{ hlc: '1790467006491.000000', kind: 'ask', asr_s: 0.524357, llm_first_s: 2.5236,
      tts_s: 6.1697, words: 6, outcome: 'ok', voice: 'ljspeech' }],
  };
  it('renames the summary to the panel’s fields', () => {
    expect(toPanel(body).voiceStats).toEqual({ turns: 4, empty: 1, empty_rate: 0.25,
      asr_median_s: 0.52, first_clause_median_s: 3.06 });
  });
  it('keys each turn by its HLC stamp and rounds its timings', () => {
    const [t] = toPanel(body).voiceLog;
    expect(t).toMatchObject({ id: '1790467006491.000000', asr_s: 0.52, llm_first_s: 2.52, tts_s: 6.17, words: 6 });
  });
  it('is empty, not broken, before the router has answered', () => {
    expect(toPanel(undefined)).toEqual({ voiceStats: { turns: 0, empty: 0, empty_rate: 0,
      asr_median_s: undefined, first_clause_median_s: undefined }, voiceLog: [] });
  });
});
