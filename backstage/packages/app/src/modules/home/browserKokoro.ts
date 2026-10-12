/*
 * Kokoro IN THE BROWSER -- the 54 voices as real options on a device the pod cannot speak for.
 *
 * WHY THIS FILE EXISTS. The picker's Kokoro group is filled from `/voice/voices`, which lists the
 * voices FILE on the host that answers (sovereign/voice/catalogue.kokoro_voices reads
 * `voices-v1.0.bin`). The pod has no such file: it is a 250m CPU / 256Mi sidecar and
 * `fleetview-backend.Dockerfile` records that it never takes the local engine path. Measured live
 * 2026-10-12: `curl https://catalogue.mumchimp.com/voice/voices` answered
 * `"kokoro":[],"say":[],"piper":[]` -- and FleetReactorApp HIDES an empty group, so the founder
 * opened the picker and there was no Kokoro at all in it (2026-10-12: "i want the kokoro voices as
 * options also").
 *
 * THE ENGINE WAS ALREADY ON THE DEVICE. `kokoro-js` is a real dependency (`app/package.json`) and
 * `hooks/useSpeculativeVoice.ts` already synthesises with it -- `onnx-community/Kokoro-82M-ONNX`,
 * dtype q8, the same voice set. So the browser can BOTH list these voices and speak them: no pod
 * model, no new service, no second engine (AGENTS.md §6). What was missing was only the wiring.
 *
 * WHY LISTING IS FREE. The model is 86MB and downloads on FIRST USE only, in the browser, cached
 * by it after that -- the list below costs nothing and is present the moment the picker opens.
 *
 * THE NAMES ARE THE MODEL'S OWN. `kokoro-js` exports only KokoroTTS/TextSplitterStream/env -- it
 * does not export its VOICES map, so it cannot be asked -- and the names that matter are the
 * members of `voices-v1.0.bin`, which is exactly what the server-side lister reads. Two guards
 * keep the copies honest, both thrown rather than skipped: `browserKokoro.test.ts` holds the list
 * to the shape of that naming (54 entries, sorted, unique) and
 * `tests/test_kokoro_browser_voices_match_the_model.py` compares it to
 * `sovereign.voice.catalogue.kokoro_voices()` character for character on any host that has the
 * file, and to `useSpeculativeVoice.ts`'s model id on every host.
 */

/**
 * The model `hooks/useSpeculativeVoice.ts` already loads. The same ONNX repo, pinned here rather
 * than re-derived, so the browser picker and the speculative pipeline cannot name two models: the
 * python guard above fails if these two strings ever differ.
 */
export const KOKORO_WEB_MODEL = 'onnx-community/Kokoro-82M-ONNX';

/**
 * Every voice in Kokoro v1.0, in the order `voices-v1.0.bin` stores them.
 *
 * Frozen here because the browser cannot read the archive (it is a 28MB zip served by nothing) and
 * because `kokoro-js` does not export the map. `af_heart` first-class: it is the estate's own
 * default (`engine.KOKORO_VOICE`).
 */
export const BROWSER_KOKORO_VOICES: readonly string[] = [
  'af_alloy',
  'af_aoede',
  'af_bella',
  'af_heart',
  'af_jessica',
  'af_kore',
  'af_nicole',
  'af_nova',
  'af_river',
  'af_sarah',
  'af_sky',
  'am_adam',
  'am_echo',
  'am_eric',
  'am_fenrir',
  'am_liam',
  'am_michael',
  'am_onyx',
  'am_puck',
  'am_santa',
  'bf_alice',
  'bf_emma',
  'bf_isabella',
  'bf_lily',
  'bm_daniel',
  'bm_fable',
  'bm_george',
  'bm_lewis',
  'ef_dora',
  'em_alex',
  'em_santa',
  'ff_siwis',
  'hf_alpha',
  'hf_beta',
  'hm_omega',
  'hm_psi',
  'if_sara',
  'im_nicola',
  'jf_alpha',
  'jf_gongitsune',
  'jf_nezumi',
  'jf_tebukuro',
  'jm_kumo',
  'pf_dora',
  'pm_alex',
  'pm_santa',
  'zf_xiaobei',
  'zf_xiaoni',
  'zf_xiaoxiao',
  'zf_xiaoyi',
  'zm_yunjian',
  'zm_yunxi',
  'zm_yunxia',
  'zm_yunyang',
];

/**
 * WHOSE KOKORO IS THIS -- the pod's, or this device's?
 *
 * One question, asked in two places (the picker, which decides what to list, and the voice hook,
 * which decides who synthesises), so it lives in one function: the pod speaks Kokoro exactly when
 * it can list it, because both come from the same voices file on that host. An empty list is
 * therefore not "no Kokoro" but "not this host's Kokoro" -- and the browser takes it from there.
 */
export function kokoroSpeaksInTheBrowser(podKokoroVoices: readonly string[] | undefined): boolean {
  return !podKokoroVoices || podKokoroVoices.length === 0;
}

/**
 * Kokoro's float32 samples as the bytes `play()` reads: 24kHz mono float32, which is what the pod
 * returns from `/voice/say` too (`TTS_RATE = 24000`), so the caller needs no branch on format.
 *
 * COPIED, NOT REINTERPRETED. `RawAudio.audio` is a Float32Array that may be a VIEW onto a larger
 * backing store; handing `.buffer` straight on would send the whole store to the audio clock.
 * `slice()` is the copy that makes the byte length the sample length.
 */
export function pcmFromKokoro(audio: Float32Array | number[]): ArrayBuffer {
  const f32 = audio instanceof Float32Array ? audio : Float32Array.from(audio);
  return f32.slice().buffer;
}

let _loading: Promise<import('kokoro-js').KokoroTTS> | null = null;

/**
 * The model, loaded once per page and shared by every clause.
 *
 * Imported HERE, lazily, so opening a page never pays for it: the transform
 * `useSpeculativeVoice.ts` uses is the same one, but a static import here would put it in the
 * first paint of every surface that mounts the voice hook. Downloads only when a Kokoro voice is
 * actually chosen.
 */
function loadKokoro(): Promise<import('kokoro-js').KokoroTTS> {
  if (!_loading) {
    _loading = import('kokoro-js')
      .then(({ KokoroTTS }) => KokoroTTS.from_pretrained(KOKORO_WEB_MODEL, { dtype: 'q8' }))
      .catch(err => {
        // A failed load must not be cached as the answer for ever: the next clause, on a
        // connection that works, should be allowed to try.
        _loading = null;
        throw err;
      });
  }
  return _loading;
}

/**
 * One clause of text to playable PCM, or null -- and null is the product, not an error.
 *
 * The caller falls back to the pod's `/voice/say` and then to the device voice when this returns
 * null, so an offline phone, a browser without WebGPU, or a model that fails to download all end
 * in speech rather than in silence. Slow is acceptable here and silence is not.
 */
export async function synthesiseBrowserKokoro(
  text: string,
  voice: string,
): Promise<ArrayBuffer | null> {
  const clause = (text || '').trim();
  if (!clause) return null;
  try {
    const tts = await loadKokoro();
    const result = await tts.generate(clause, { voice: voice as never });
    const audio = (result as { audio?: Float32Array }).audio;
    if (!audio || !audio.length) return null;
    return pcmFromKokoro(audio);
  } catch {
    return null;
  }
}

/**
 * The chosen Kokoro voice, kept on THIS device.
 *
 * The pod cannot persist this choice: `voice_media._save_choice` writes to the pod's home, which
 * no volume backs (its own comment records that every deploy forgets the founder's pick), and it
 * cannot name a Kokoro voice at all. localStorage is the only store here that outlives a reload,
 * and per-device is correct rather than incidental -- this voice is spoken by the device that
 * chose it.
 */
const PREF_KEY = 'estate.voice.browserKokoro';

export function rememberBrowserKokoroVoice(voice: string): void {
  try {
    window.localStorage.setItem(PREF_KEY, voice);
  } catch {
    /* private mode, or storage full: the choice still holds for this page */
  }
}

/**
 * The remembered voice, or null -- including for a name no longer in the model, so a stale entry
 * cannot put the picker into a voice the engine would refuse.
 */
export function storedBrowserKokoroVoice(): string | null {
  try {
    const v = window.localStorage.getItem(PREF_KEY);
    return v && BROWSER_KOKORO_VOICES.includes(v) ? v : null;
  } catch {
    return null;
  }
}
