/*
 * The pod's cloud voice is chosen and the pod cannot speak: this device's Kokoro speaks instead.
 *
 * WHY THIS TEST EXISTS. Measured 2026-10-13 on the live pod: Orpheus's 100 requests a day were
 * spent, `/voice/say` answered 502 after ~5s, and every clause before that had loaded the Kokoro
 * model only for it to refuse the name "hannah". So the founder waited ~5s a clause and then heard
 * the OS voice. Checked here on the real hook:
 *
 *   1. a working pod is asked first and the browser model is never touched for a cloud voice;
 *   2. a pod that fails hands the clause to this device's Kokoro, in `af_heart`;
 *   3. the next clause does not ask the failed pod again.
 */
import { act, renderHook } from '@testing-library/react';

const calls: string[] = [];
const podSamples = new Float32Array([0.1, 0.2]);
const kokoroSamples = new Float32Array([0.25, -0.25, 0.5]);
const synthesised: Array<{ text: string; voice: string }> = [];
let sayStatus = 200;

jest.mock('./browserKokoro', () => {
  const actual = jest.requireActual('./browserKokoro');
  return {
    ...actual,
    synthesiseBrowserKokoro: jest.fn(async (text: string, voice: string) => {
      synthesised.push({ text, voice });
      return kokoroSamples.slice().buffer;
    }),
  };
});

const fetchApi = {
  fetch: jest.fn(async (url: string) => {
    calls.push(url);
    if (url.endsWith('/voice/voices')) {
      return {
        ok: true,
        // The pod, measured live 2026-10-12: local engines empty, cloud voices present.
        json: async () => ({
          cloud: ['hannah', 'troy'],
          say: [],
          kokoro: [],
          piper: [],
          engine: 'cloud',
          current: { engine: 'cloud', cloud: 'hannah' },
        }),
      };
    }
    if (url.endsWith('/voice/say')) {
      return {
        ok: sayStatus < 400,
        status: sayStatus,
        arrayBuffer: async () => podSamples.slice().buffer,
      };
    }
    return { ok: true, arrayBuffer: async () => new ArrayBuffer(0), json: async () => ({}) };
  }),
};

jest.mock('@backstage/core-plugin-api', () => ({
  fetchApiRef: { $$type: 'fetchApi' },
  useApi: () => fetchApi,
}));

class FakeBuffer {
  samples: Float32Array;
  constructor(len: number) {
    this.samples = new Float32Array(len);
  }
  get duration() {
    return this.samples.length / 24000;
  }
  copyToChannel(f32: Float32Array) {
    this.samples.set(f32);
  }
}

const played: Float32Array[] = [];

class FakeAudioContext {
  sampleRate = 24000;
  currentTime = 0;
  destination = {};
  createBuffer(_channels: number, len: number) {
    return new FakeBuffer(len) as unknown as AudioBuffer;
  }
  createBufferSource() {
    const src: any = {
      buffer: null,
      connect() {},
      start() {
        if (src.buffer) played.push((src.buffer as unknown as FakeBuffer).samples);
      },
    };
    return src;
  }
  resume() {
    return Promise.resolve();
  }
  close() {
    return Promise.resolve();
  }
}

// eslint-disable-next-line import/first
import { useEstateVoice } from './useEstateVoice';
import { applyLoudness } from './faceAudio';

const flush = () => new Promise(resolve => setTimeout(resolve, 0));
const says = () => calls.filter(u => u.endsWith('/voice/say')).length;

describe("the pod's cloud voice, chosen on a device with its own Kokoro", () => {
  beforeEach(() => {
    calls.length = 0;
    synthesised.length = 0;
    played.length = 0;
    sayStatus = 200;
    window.localStorage.clear();
    (window as any).AudioContext = FakeAudioContext;
    fetchApi.fetch.mockClear();
  });

  it('is spoken by a working pod, and the browser model is not loaded for it', async () => {
    const { result } = renderHook(() => useEstateVoice());
    await act(flush);
    expect(result.current.current).toEqual({ engine: 'cloud', voice: 'hannah' });

    await act(async () => {
      result.current.speak('hello there');
      await flush();
    });

    expect(says()).toBe(1);
    expect(synthesised).toEqual([]);
    expect(played).toHaveLength(1);
    // The pod's own samples reach the clock -- raised to the founder's level by faceAudio, which is
    // the only change the stage makes (same shape, scaled), so the expectation is the same clause
    // run through it.
    expect([...played[0]]).toEqual([...applyLoudness(podSamples)]);
  });

  it("is spoken by this device's Kokoro when the pod cannot, and the pod is then left alone", async () => {
    sayStatus = 502;
    const { result } = renderHook(() => useEstateVoice());
    await act(flush);

    await act(async () => {
      result.current.speak('first clause');
      await flush();
    });
    expect(says()).toBe(1);
    expect(synthesised).toEqual([{ text: 'first clause', voice: 'af_heart' }]);
    expect([...played[0]]).toEqual([...applyLoudness(kokoroSamples)]);

    await act(async () => {
      result.current.speak('second clause');
      await flush();
    });
    expect(says()).toBe(1);
    expect(synthesised[1]).toEqual({ text: 'second clause', voice: 'af_heart' });
    expect(played).toHaveLength(2);
  });
});
