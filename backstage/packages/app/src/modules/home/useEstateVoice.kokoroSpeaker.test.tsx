/*
 * A Kokoro voice chosen on this device is spoken BY this device, and the pod is not asked.
 *
 * WHY THIS TEST EXISTS. The picker offering 54 voices means nothing if choosing one is refused or
 * silently ignored. The pod cannot synthesise Kokoro -- `/voice/select` validates the name against
 * the voices file on that host (`sovereign/voice/catalogue.select`), and it has none -- so the two
 * things that had to be true are, and are checked here on the real hook:
 *
 *   1. `selectVoice('kokoro', <a voice>)` does NOT post to `/voice/select` (which would answer 400)
 *      and does report the choice.
 *   2. the clause that then reaches the audio clock is the one the BROWSER synthesised: no
 *      `/voice/say` request, and the samples played are the browser's.
 *
 * The audio device is a fake -- jsdom has no AudioContext, which is why the page tests mock
 * this hook outright instead of running it. The fake is deliberately thin: it records what was
 * handed to `createBuffer`, so the assertion is about the audio that would be HEARD.
 */
import { act, renderHook } from '@testing-library/react';

const calls: string[] = [];
const samples = new Float32Array([0.25, -0.25, 0.5]);
const synthesised: Array<{ text: string; voice: string }> = [];

jest.mock('./browserKokoro', () => {
  const actual = jest.requireActual('./browserKokoro');
  return {
    ...actual,
    synthesiseBrowserKokoro: jest.fn(async (text: string, voice: string) => {
      synthesised.push({ text, voice });
      return samples.slice().buffer;
    }),
  };
});

// `useEstateVoice` reaches the backend only through `useApi(fetchApiRef)`, so the ref can be a
// token and the hook can be the fake.
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

describe('a Kokoro voice chosen on a device the pod cannot speak for', () => {
  beforeEach(() => {
    calls.length = 0;
    synthesised.length = 0;
    played.length = 0;
    window.localStorage.clear();
    (window as any).AudioContext = FakeAudioContext;
    fetchApi.fetch.mockClear();
  });

  it('is accepted without asking the pod to select it', async () => {
    const { result } = renderHook(() => useEstateVoice());
    await act(flush);

    let said = '';
    await act(async () => {
      said = await result.current.selectVoice('kokoro', 'af_bella');
    });

    expect(calls.some(u => u.endsWith('/voice/select'))).toBe(false);
    expect(said).toContain('af_bella');
    expect(result.current.current).toEqual({ engine: 'kokoro', voice: 'af_bella' });
  });

  it('is spoken by the browser: no /voice/say, and its own samples reach the audio clock', async () => {
    const { result } = renderHook(() => useEstateVoice());
    await act(flush);
    await act(async () => {
      await result.current.selectVoice('kokoro', 'af_bella');
    });

    await act(async () => {
      result.current.speak('hello there');
      await flush();
    });

    expect(synthesised).toEqual([{ text: 'hello there', voice: 'af_bella' }]);
    expect(calls.some(u => u.endsWith('/voice/say'))).toBe(false);
    expect(played).toHaveLength(1);
    // Its own samples reach the clock, raised to the founder's level (faceAudio, idp#6784).
    expect([...played[0]]).toEqual([...applyLoudness(samples)]);
  });

  it('survives a reload: the choice is remembered, not replaced by the pod\'s cloud voice', async () => {
    const first = renderHook(() => useEstateVoice());
    await act(flush);
    await act(async () => {
      await first.result.current.selectVoice('kokoro', 'af_sky');
    });

    // A reload: the same page, the catalogue answered again with `kokoro: []`.
    const second = renderHook(() => useEstateVoice());
    await act(flush);

    expect(second.result.current.current).toEqual({ engine: 'kokoro', voice: 'af_sky' });
  });
});
