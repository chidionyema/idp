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
  KOKORO_WEB_MODEL,
  kokoroSpeaksInTheBrowser,
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
