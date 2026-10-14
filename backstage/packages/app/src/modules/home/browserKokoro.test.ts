/*
 * The 54 Kokoro voices the picker now offers on a device the pod cannot speak for.
 *
 * WHY. On 2026-10-12 the founder asked for the Kokoro voices in the picker ("i want the kokoro
 * voices as options also") and there were none: the group is filled from `/voice/voices`, which
 * lists the voices FILE on the pod, and the pod has none -- and FleetReactorApp hides an empty
 * group, so nothing was even shown. The browser has the engine (kokoro-js, the same one
 * `useSpeculativeVoice` uses), so the list and the speaking both moved here.
 *
 * WHAT IS NOT TESTED HERE: `synthesiseBrowserKokoro` end to end. That downloads an 86MB model from
 * a CDN, which a unit test must not do; the hook test beside this one
 * (`useEstateVoice.kokoroSpeaker.test.tsx`) mocks it and proves the wiring, and the model id it is
 * called with is pinned against `useSpeculativeVoice`'s by
 * `tests/test_kokoro_browser_voices_match_the_model.py`.
 */
import {
  BROWSER_KOKORO_VOICES,
  deviceRunsKokoro,
  KOKORO_WEB_MODEL,
  kokoroSpeaksInTheBrowser,
  letStreamsIterate,
  pcmFromKokoro,
  rememberBrowserKokoroVoice,
  storedBrowserKokoroVoice,
} from './browserKokoro';

describe('the Kokoro voice list the browser offers', () => {
  it('is the model\'s own 54, sorted, unique, and keeps the estate\'s default', () => {
    expect(BROWSER_KOKORO_VOICES).toHaveLength(54);
    expect(new Set(BROWSER_KOKORO_VOICES).size).toBe(54);
    expect([...BROWSER_KOKORO_VOICES]).toEqual([...BROWSER_KOKORO_VOICES].sort());
    // `af_heart` is `engine.KOKORO_VOICE`, the estate's own default. A list without it would offer
    // 54 voices and not the one the servers pick.
    expect(BROWSER_KOKORO_VOICES).toContain('af_heart');
  });

  it('names each voice the way the model does', () => {
    // `af_heart`, `zm_yunyang`: two letters of language/gender, then the name. A typo like
    // `af-heart` is accepted by no engine and would be offered by the picker as a working choice.
    for (const v of BROWSER_KOKORO_VOICES) {
      expect(v).toMatch(/^[a-z]{2}_[a-z]+$/);
    }
  });

  it('pins the model the speculative pipeline already loads', () => {
    expect(KOKORO_WEB_MODEL).toBe('onnx-community/Kokoro-82M-ONNX');
  });
});

describe('who speaks Kokoro', () => {
  it('is this device when the pod reports no Kokoro voices', () => {
    // Production, measured live 2026-10-12: `"kokoro":[]`.
    expect(kokoroSpeaksInTheBrowser([])).toBe(true);
    // The catalogue route itself failing (it was a 500 on the pod until 2026-10-08) leaves the
    // list undefined, and that is the same answer: the pod is not going to speak it.
    expect(kokoroSpeaksInTheBrowser(undefined)).toBe(true);
  });

  it('is the pod when the pod has them', () => {
    // A laptop checkout: the voices file is there, so the server speaks them and the reload-safe
    // choice file it keeps is the one that should win.
    expect(kokoroSpeaksInTheBrowser(['af_heart'])).toBe(false);
  });

  it('is nobody on Safari, so the picker does not offer a voice that never speaks', () => {
    jest.spyOn(window.navigator, 'userAgent', 'get').mockReturnValue(UA.safariMac);
    expect(kokoroSpeaksInTheBrowser([])).toBe(false);
    jest.restoreAllMocks();
  });
});

// Real agent strings. The Mac Safari one is the browser measured on 2026-10-14.
const UA = {
  safariMac:
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
  safariIphone:
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
  chromeIphone:
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/118.0.5993.69 Mobile/15E148 Safari/604.1',
  chromeMac:
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
  edge:
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
  chromeAndroid:
    'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36',
  firefox: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:131.0) Gecko/20100101 Firefox/131.0',
};

describe('which browsers can run the model', () => {
  // Measured in real Safari 16.6, 2026-10-14: ~2 minutes to download, ~70s to start, then ~1GB of
  // JavaScript heap and a page that stopped answering before the first sample.
  it('is not WebKit -- Safari, or any browser on an iPhone', () => {
    expect(deviceRunsKokoro(UA.safariMac)).toBe(false);
    expect(deviceRunsKokoro(UA.safariIphone)).toBe(false);
    expect(deviceRunsKokoro(UA.chromeIphone)).toBe(false);
  });

  it('is every other browser, unchanged', () => {
    expect(deviceRunsKokoro(UA.chromeMac)).toBe(true);
    expect(deviceRunsKokoro(UA.edge)).toBe(true);
    expect(deviceRunsKokoro(UA.chromeAndroid)).toBe(true);
    expect(deviceRunsKokoro(UA.firefox)).toBe(true);
  });

  it('includes the test runner, so the other tests here exercise the browser path', () => {
    expect(deviceRunsKokoro()).toBe(true);
  });
});

describe('Kokoro samples to the bytes the audio clock reads', () => {
  it('copies the samples rather than reinterpreting the backing store', () => {
    const buf = pcmFromKokoro(new Float32Array([0.5, -0.5, 0]));
    expect(buf.byteLength).toBe(12);
    expect([...new Float32Array(buf)]).toEqual([0.5, -0.5, 0]);
  });

  it('sends only the view\'s own samples', () => {
    // `RawAudio.audio` can be a VIEW onto a larger buffer. Handing `.buffer` straight to the audio
    // clock would queue the whole store -- the clause plus whatever else is behind it.
    const backing = new Float32Array([1, 2, 3, 4, 5, 6]);
    const view = backing.subarray(2, 4);
    expect([...new Float32Array(pcmFromKokoro(view))]).toEqual([3, 4]);
  });

  it('accepts a plain array too', () => {
    expect([...new Float32Array(pcmFromKokoro([0.25]))]).toEqual([0.25]);
  });
});

describe('the remembered device voice', () => {
  afterEach(() => window.localStorage.clear());

  it('round-trips a voice the model actually has', () => {
    rememberBrowserKokoroVoice('af_bella');
    expect(storedBrowserKokoroVoice()).toBe('af_bella');
  });

  it('refuses a stale name, so a reload cannot restore a voice the engine would reject', () => {
    window.localStorage.setItem('estate.voice.browserKokoro', 'af_not_a_voice');
    expect(storedBrowserKokoroVoice()).toBeNull();
  });

  it('is null when nothing was ever chosen', () => {
    expect(storedBrowserKokoroVoice()).toBeNull();
  });
});

describe('a clause never waits for the model', () => {
  // The founder, 2026-10-14: "i get text response right away but voice is lagging and mostly
  // does not work". Every clause used to await the 86MB model load, and a failed load was
  // forgotten at once, so on a browser where the model never loads each clause paid for the
  // attempt again before the pod could speak it.
  const generate = jest.fn(async () => ({ audio: new Float32Array([0.1, 0.2]) }));
  let load: jest.Mock;
  let synth: typeof import('./browserKokoro').synthesiseBrowserKokoro;
  let retryMs: number;

  const settle = () => new Promise(r => setTimeout(r, 0));

  beforeEach(() => {
    jest.resetModules();
    generate.mockClear();
    load = jest.fn();
    jest.doMock('kokoro-js', () => ({ KokoroTTS: { from_pretrained: load } }));
    jest.isolateModules(() => {
      const m = require('./browserKokoro');
      synth = m.synthesiseBrowserKokoro;
      retryMs = m.KOKORO_RETRY_MS;
    });
  });

  afterEach(() => {
    jest.dontMock('kokoro-js');
    jest.restoreAllMocks();
  });

  it('answers null at once while the model loads, then speaks once it has', async () => {
    let finish: (tts: unknown) => void = () => undefined;
    load.mockReturnValue(new Promise(r => (finish = r)));

    // The load has not finished: the clause goes to the next speaker now, not after it.
    await expect(synth('Hello there.', 'af_heart')).resolves.toBeNull();
    await expect(synth('And again.', 'af_heart')).resolves.toBeNull();
    expect(load).toHaveBeenCalledTimes(1);

    finish({ generate });
    await settle();
    const pcm = await synth('Now in Kokoro.', 'af_heart');
    expect(pcm).not.toBeNull();
    expect(generate).toHaveBeenCalledWith('Now in Kokoro.', { voice: 'af_heart' });
  });

  it('believes a failed load for a while instead of retrying it on every clause', async () => {
    const now = jest.spyOn(Date, 'now').mockReturnValue(1_000_000);
    load.mockRejectedValue(new TypeError('undefined is not a function'));

    await expect(synth('One.', 'af_heart')).resolves.toBeNull();
    await settle();
    for (const clause of ['Two.', 'Three.', 'Four.']) {
      await expect(synth(clause, 'af_heart')).resolves.toBeNull();
    }
    expect(load).toHaveBeenCalledTimes(1);

    // After the rest, a connection that has since recovered is given its chance.
    now.mockReturnValue(1_000_000 + retryMs);
    await synth('Five.', 'af_heart');
    await settle();
    expect(load).toHaveBeenCalledTimes(2);
  });

  it('never starts the download on Safari', async () => {
    jest.spyOn(window.navigator, 'userAgent', 'get').mockReturnValue(UA.safariMac);
    load.mockResolvedValue({ generate });

    for (const clause of ['One.', 'Two.', 'Three.']) {
      await expect(synth(clause, 'af_heart')).resolves.toBeNull();
    }
    await settle();
    expect(load).not.toHaveBeenCalled();
  });
});

describe('a stream kokoro-js can read on Safari', () => {
  // Measured in real Safari 16.6, 2026-10-14: kokoro-js's phonemizer reads its dictionary with
  // `for await (const chunk of stream)`, Safari's ReadableStream cannot be iterated that way, and
  // importing kokoro-js threw "undefined is not a function near '...r of ...a'".
  const real = (globalThis as { ReadableStream?: unknown }).ReadableStream;

  // Safari's shape: a reader, and no async iterator.
  class SafariStream {
    released = false;
    constructor(private chunks: string[]) {}
    getReader() {
      return {
        read: async () =>
          this.chunks.length
            ? { done: false, value: this.chunks.shift() }
            : { done: true, value: undefined },
        releaseLock: () => {
          this.released = true;
        },
      };
    }
  }

  afterEach(() => {
    (globalThis as { ReadableStream?: unknown }).ReadableStream = real;
  });

  it('is iterable with for-await once the gap is filled, and lets go of its reader', async () => {
    (globalThis as { ReadableStream?: unknown }).ReadableStream = SafariStream;
    letStreamsIterate();
    const stream = new SafariStream(['a', 'b', 'c']);
    const seen: string[] = [];
    for await (const chunk of stream as unknown as AsyncIterable<string>) seen.push(chunk);
    expect(seen).toEqual(['a', 'b', 'c']);
    expect(stream.released).toBe(true);
  });

  it("leaves a browser's own iterator alone", () => {
    const own = async function* own() {};
    class ModernStream {}
    Object.defineProperty(ModernStream.prototype, Symbol.asyncIterator, { value: own });
    (globalThis as { ReadableStream?: unknown }).ReadableStream = ModernStream;
    letStreamsIterate();
    expect(ModernStream.prototype[Symbol.asyncIterator as keyof ModernStream]).toBe(own);
  });

  it('does nothing where there is no ReadableStream at all', () => {
    (globalThis as { ReadableStream?: unknown }).ReadableStream = undefined;
    expect(() => letStreamsIterate()).not.toThrow();
  });
});
