// useEstateVoice — the estate's voice engine, as a hook any surface can mount.
//
// WHY THIS EXISTS AS A SHARED HOOK. Four surfaces in this app offered voice and each one reached
// for the browser's own APIs:
//
//   SpeechRecognition  -> Chrome streams the microphone to Google. When that service is
//                         unreachable `onresult` NEVER fires and no error is raised, so the
//                         control sits on "listening" for ever and looks broken. Measured
//                         2026-09-19 on the founder's machine: it did exactly that.
//   speechSynthesis    -> the OS's formant voices, audibly worse than the estate's own engine.
//
// The estate runs its own models -- faster-whisper for hearing, Kokoro/Piper for speaking -- with
// barge-in, clause streaming and 78 voices. Putting that in ONE hook is the point: a fifth voice
// surface added later gets the real engine by mounting this, rather than by remembering to avoid
// two browser APIs.
//
// ─────────────────────────────────────────────────────────────────────────────────────────────
// THE TRANSPORT MOVED ONTO THE BUS (2026-09-22). This is the change that matters here.
//
// This hook used to open `new WebSocket('ws://127.0.0.1:8899/voice/stream')` and push microphone
// PCM straight down it, with a comment justifying the hard-coded origin: "Backstage's proxy is
// HTTP-only and cannot carry an upgrade". The first half is true. The conclusion was not: the
// board's own live feed crosses that same proxy as Server-Sent Events, so the proxy was never the
// obstacle -- the WebSocket was a choice, and it bought a second transport.
//
// What that choice cost: `localhost:8899` DOES NOT EXIST IN THE CLUSTER. A portal served from
// anywhere but this one laptop had no such port, so voice could only ever work here, with a
// process someone had started by hand -- and when it was not running the board said "voice
// service not reachable on 8899", which is a sentence no deployed product can contain.
//
// So the transport splits along the seam it should always have had:
//
//   MEANING -> the estate bus. Every utterance is published as an `estate.agent.event` with
//              kind=steer (text + attributed author, which is exactly what the contract calls a
//              human correcting a session mid-flight); the finished answer is a kind=done row.
//              The board's existing `/stream` SSE carries them to the page, so what the founder
//              SAID is on the same bus, in the same schema, as what every agent is doing.
//   MEDIA   -> plain HTTP through the Backstage proxy. `POST /voice/hear` with one utterance of
//              PCM returns what was heard; `POST /voice/say` with one clause returns its audio.
//              Neither needs an upgrade, so both proxy, so both work in the cluster.
//   BRAIN   -> `POST /voice/stream`, the clause-by-clause SSE route that was ALREADY here and
//              already prompted with the same fleet state `/sessions` serves. Asking a second
//              question-answering path would have been another duplicate.
//
// Every call below therefore goes through `fetchApi.fetch('plugin://proxy/fleetview/…')` — the
// discovery middleware rewrites `proxy` to `${backend.baseUrl}/api/proxy` AND attaches the token.
// A bare `/api/proxy/…` would hit this SPA's own history fallback and get index.html with a 200;
// an `EventSource` would arrive with no credentials and get a 401 (measured 2026-09-22:
// `GET /api/proxy/fleetview/sessions` with no token is 401). Both traps are already documented in
// Fleet.tsx, which reads its stream the same way this does.
//
// WHAT IT STILL OWNS:
//   * Silero VAD in the browser, so silence costs no CPU anywhere -- nothing is sent until the
//     person actually spoke and then stopped;
//   * playback scheduled on the WebAudio clock, so clause seams are inaudible;
//   * barge-in: speaking while it talks stops playback AND aborts the in-flight turn.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { fetchApiRef, useApi } from '@backstage/core-plugin-api';

/**
 * The VAD and onnxruntime bundles, served by THIS APP at its own origin.
 *
 * The 33MB lives in `backstage/packages/app/public/voice`, and `sovereign/voice/static` is a
 * symlink to it -- still one copy on disk, pointing the other way round. It was the other way
 * round until 2026-09-22, and that broke every portal image build: the backstage image's build
 * context is `backstage/`, so a symlink out of it dangles inside the container and `yarn
 * build:all` died on `ENOENT: stat '/app/packages/app/public/voice'` (run 35683095989). The bytes
 * have to be inside the context of the image that serves them.
 *
 * The app serves them with the right MIME types -- measured 2026-09-22 on the running dev server:
 * `/voice/ort.min.js` is `application/javascript` (443678 bytes) and
 * `/voice/ort-wasm-simd-threaded.jsep.wasm` is `application/wasm`.
 *
 * WHY NOT THROUGH THE PROXY like everything else here: a `<script src>` tag and an AudioWorklet
 * cannot carry an Authorization header, and the proxy answers 401 without one. Static ML runtime
 * bundles are the app's own assets, so they belong at the app's own origin.
 *
 * WHY NOT FROM A CDN: they were, until 2026-09-19, when the page failed on the founder's machine
 * with "Cannot read properties of undefined (reading 'MicVAD')" while loading perfectly in a
 * headless test -- a browser-side block the server cannot see and therefore cannot explain. A
 * voice interface that needs jsdelivr to be reachable is not a voice interface.
 */
export const VOICE_ASSETS = '/voice/';

/** The FleetView backend, through the Backstage proxy. See the header: never a bare path. */
const FLEETVIEW = 'plugin://proxy/fleetview';

const TTS_RATE = 24000;

/**
 * WHICH DEVICE IS ASKING (2026-10-04).
 *
 * Every instruction below used to name macOS: `micRefusalDetail` ended unconditionally with
 * "System Settings → Privacy & Security → Microphone → turn Chrome ON", and the site-setting
 * branch of `micBlocker` pointed at the padlock and at `chrome://settings/content/microphone`.
 * The founder reads the fleet from a PHONE, which has no macOS System Settings, no Chrome
 * settings URL and (on iOS) no padlock — so a phone-side refusal rendered a fix that cannot be
 * followed, while ASSERTING macOS as the cause. That is a guess the code was making, not a
 * measurement, and it is why "microphone blocked" survived several rounds of being "fixed".
 *
 * Chosen from the UA because it is the only thing that distinguishes the fixes; the permission
 * state cannot (all three blockers throw the same NotAllowedError). iPadOS 13+ reports itself as
 * `Macintosh`, so `maxTouchPoints > 1` is what separates an iPad from a Mac — the standard
 * check, and the reason the Mac branch cannot simply match on "Mac".
 */
export type MicPlatform = 'ios' | 'android' | 'desktop';

export function micPlatform(): MicPlatform {
  const ua = navigator.userAgent || '';
  if (/iPhone|iPod/i.test(ua)) return 'ios';
  // iPadOS 13+ masquerades as desktop Safari; a real Mac never reports touch points.
  if (/iPad/i.test(ua)) return 'ios';
  if (/Macintosh/i.test(ua) && (navigator.maxTouchPoints ?? 0) > 1) return 'ios';
  if (/Android/i.test(ua)) return 'android';
  return 'desktop';
}

/**
 * WHAT A `denied` PERMISSION STATE MEANS, AND WHY THIS NO LONGER MENTIONS A SETTING (2026-10-06).
 *
 * Measured on the founder's iPhone from live production: tapping the mic on
 * https://catalogue.mumchimp.com/fleet rendered "microphone is off for this page -- tap the mic
 * again to be asked". That string is produced by ONE branch: `permissions.query({name:'microphone'})`
 * returning `denied` in micBlocker(). So Safari is telling the page the mic is off for THIS site,
 * and the page passed that on -- but the word "off" reads as a setting to go and find, which is
 * exactly the chore the founder forbade: a voice surface asks for the microphone BY USING IT.
 *
 * THERE WAS A SETTINGS WALKTHROUGH HERE, AND IT IS GONE. For a day this branch returned
 *   'Microphone blocked. Open Settings -> Safari -> [this site] -> Microphone and choose Allow.'
 * The estate's owner rejected that twice, in his own words: "we are not going to be telling users
 * to set anything on safari", and "the instructions dont make sensse, safari should promt the
 * user". He is right, and WebKit agrees: "the user is prompted to grant website access to capture
 * devices when getUserMedia is first called" (webkit.org/blog/7763). Safari HAS a prompt. Calling
 * getUserMedia IS the request. A page that renders a Settings walkthrough instead has replaced the
 * browser's own dialog with a chore the person must do by hand.
 *
 * The reasoning that put it there is kept so it is not re-invented: on iOS a refused site is not
 * re-askable through getUserMedia, so "tap again" can be a loop, and that is still true. What was
 * wrong was the conclusion -- that the only honest reply is a menu tour. It is not. A refusal is
 * answered by naming the state and stopping, which is what `osRefusalFix` below already says, and
 * what this function now says too. The two must agree: before 2026-10-06 one said "tap the mic
 * again" and the other said "open Safari settings", in the same file, for the same refusal.
 */
export function siteSettingFix(): string {
  // One sentence, the device's words, no errand. `osRefusalFix` is the caller that ends up in
  // front of the person, so this delegates rather than keeping a second, divergent copy.
  return osRefusalFix();
}

/**
 * The refusal that reached the person, said once and in their device's words. Deliberately NOT a
 * settings walkthrough: the next tap re-asks, and a user who has decided to refuse is not helped by
 * being sent into a menu. Short enough to read on a phone at a glance.
 */
function osRefusalFix(): string {
  switch (micPlatform()) {
    case 'ios':
      return 'iOS is not letting this page use the microphone — tap the mic again to be asked';
    case 'android':
      return 'Android is not letting this page use the microphone — tap the mic again to be asked';
    default:
      return 'this computer is not letting the browser use the microphone — tap the mic again to be asked';
  }
}

/**
 * WHY THE MICROPHONE'S REFUSAL MUST BE NAMED, NOT SUMMARIZED (2026-10-03).
 *
 * The founder spent eight hours with voice dead on catalogue.mumchimp.com while the surface
 * said only "microphone blocked — allow it for this site". That sentence guesses ONE cause
 * (the site setting) and is wrong for the two that actually hold a Mac hostage:
 *
 *   Chrome has the SITE on Block   -> the browser NEVER re-prompts; retrying does nothing,
 *                                     and the fix is the padlock icon left of the URL.
 *   macOS has CHROME on Block      -> getUserMedia rejects before any prompt, the site setting
 *                                     reads "prompt" and looks innocent; the fix is System
 *                                     Settings → Privacy & Security → Microphone.
 *
 * Both throw the same NotAllowedError, so the message cannot be chosen from the exception — it
 * is chosen from the browser's own permission state, which is what this helper reads. The
 * secure-context check comes first because on an insecure origin the permission state lies
 * (mediaDevices does not even exist) and the only fix is the URL.
 *
 * Returns null when nothing is wrong; the caller proceeds with the mic.
 */
async function micBlocker(): Promise<string | null> {
  // TWO DIFFERENT BLOCKERS, TWO DIFFERENT FIXES -- do not collapse them into one message.
  //
  // Measured on LIVE production 2026-10-04 with an iPhone and a Pixel user-agent: this function
  // returned "this page is not on https" while the page WAS on https (the address bar was
  // https://catalogue.mumchimp.com). The cause was `||` here: `!isSecureContext` and
  // `!mediaDevices.getUserMedia` are not the same fault, and only the first is about the URL. On a
  // phone the second is what fires -- Safari on iOS exposes `navigator.mediaDevices` as undefined
  // to a page it is not prepared to grant, which says nothing about https. The page then sent the
  // founder to fix a URL that was already correct, which is the same defect as the macOS message on
  // a phone: a fix that cannot be followed, asserting a cause that is not the cause.
  //
  // So: an insecure origin names the URL. A SECURE origin with no getUserMedia names the DEVICE,
  // and asks the platform helper for the path that device can actually follow.
  if (!window.isSecureContext) {
    return 'microphone needs a secure page — open it over https://catalogue.mumchimp.com';
  }
  // NO DEVICE NAMED, NO SETTINGS SENT: the caller now simply calls getUserMedia, which IS the
  // request. If the browser will not even expose the API there is nothing a user can reach from a
  // menu that would change it, and the honest answer is that this browser cannot.
  if (!navigator.mediaDevices?.getUserMedia) {
    return 'this browser cannot reach the microphone — open the page in Safari or Chrome';
  }
  // THE PERMISSION QUERY IS ADVISORY, NOT A VERDICT (2026-10-05). What it is asked for is whether
  // an instruction is needed BEFORE trying; it never decides that trying is pointless. Safari and
  // Firefox do not implement the `microphone` PermissionName, so query() rejects and the catch
  // below is the ordinary path on iOS -- and where it IS implemented, a stale `denied` is cleared
  // by the next request anyway. Either way the answer to "can this device be asked?" is yes, so
  // this returns null and the caller makes the real request. Reporting the state as a message was
  // the defect: it told the person their device had refused before the device had been asked.
  try {
    const p = await navigator.permissions.query({ name: 'microphone' as PermissionName });
    if (p.state === 'denied') return siteSettingFix();
    return null;
  } catch {
    // Safari and Firefox do not implement the microphone permission query; the caller falls
    // back to the refusal-time message below.
    return null;
  }
}

/**
 * The refusal-time companion to `micBlocker`: the mic WAS just refused, so if the per-site
 * state still says "prompt" the block is not the site’s — it is the OS refusing the browser
 * itself, and no amount of site-allowing will clear it.
 */
async function micRefusalDetail(): Promise<string> {
  const blocked = await micBlocker();
  if (blocked) return blocked;
  return osRefusalFix();
}

/**
 * WHAT TO SAY WHEN THE MICROPHONE WAS JUST REFUSED (2026-10-05).
 *
 * This is the one place that decides the refusal's words, so the decision is readable and testable
 * rather than a stack of ternaries inside a catch.
 *
 * WHAT IT REPLACED, AND WHY. The caller used to regex the error's ENGLISH TEXT:
 *
 *     /permission|denied|notallowed/i.test(msg) ? ... : /notfound|device/i.test(msg) ? ... : `microphone failed: ${msg}`
 *
 * Measured on LIVE production that day, iPhone user-agent, after entering as a guest: a phone whose
 * `navigator.mediaDevices` is undefined (what Safari does for a page it will not grant) threw
 * `TypeError: Cannot read properties of undefined (reading 'getUserMedia')`. Those words match
 * neither pattern, so it fell to the last branch and the founder was shown V8's own sentence where
 * a fix belonged -- `microphone failed: Cannot read properties of undefined...` read back off the
 * live page. Matching prose to guess a cause is the same defect as guessing a platform from a UA.
 *
 * So the classification reads `name`, which the browser SETS, and falls back to prose only for the
 * engines that set nothing useful. A refusal our own voice path raised already says something the
 * person can act on and is passed through untouched; `detail` is never allowed to be an exception
 * string.
 */
async function refusalDetail(e: any, msg: string): Promise<string> {
  const name = String(e?.name || '');
  // Raised by useVoiceRouter (MicRefusal), already worded for the person.
  if (name === 'MicRefusal') return msg;

  const denied = /permission|denied|notallowed|security/i.test(name) || /permission|denied|notallowed/i.test(msg);
  if (denied) return micRefusalDetail();

  const absent =
    /notfound|devicesnotfound|notreadable|trackstart/i.test(name) || /notfound|no.*device/i.test(msg);
  if (absent) {
    return 'no microphone found — check this device has one and that no other app is holding it, then tap again';
  }

  // Nothing recognisable: name the block without pasting the engine's text over the person's screen.
  return `microphone blocked: the browser would not give this page a microphone (${name || 'unknown error'}). Tap the mic again to be asked.`;
}

/**
 * Where a spoken clause goes when a face is on screen. The estate face (faceEngine.ts) plays the
 * clause itself so its lips move to the exact audio; without one, `play()` below schedules it on
 * the voice's own context as before. One sink at a time: the face that mounted last owns it.
 */
export interface ClauseSink {
  speak(pcm: ArrayBuffer, text: string): void;
  stop(): void;
}
let clauseSink: ClauseSink | null = null;
export function setClauseSink(sink: ClauseSink | null): void {
  clauseSink = sink;
}

/**
 * Who is speaking. The event contract's `steer` object REQUIRES an author, because "the estate
 * never runs a steer with no attributed author" -- and `/voice/hear` refuses a request without
 * one rather than inventing a default. The same name Fleet.tsx sends with a nudge or a stop.
 */
const AUTHOR = 'founder';

/**
 * Load the VAD and onnxruntime bundles.
 *
 * Idempotent and awaited: a second call while the first is in flight returns the same promise, and
 * a failure is reported rather than thrown so the caller can name it.
 */
let libsPromise: Promise<{ ok: boolean; missing: string[] }> | null = null;

function loadScript(src: string): Promise<boolean> {
  return new Promise((resolve) => {
    const s = document.createElement('script');
    s.src = src;
    s.onload = () => resolve(true);
    s.onerror = () => resolve(false);
    document.head.appendChild(s);
  });
}

export function ensureVoiceLibs(): Promise<{ ok: boolean; missing: string[] }> {
  if (libsPromise) return libsPromise;
  libsPromise = (async () => {
    const missing: string[] = [];
    const w = window as any;
    if (typeof w.ort === 'undefined') {
      if (!(await loadScript(`${VOICE_ASSETS}ort.min.js`))) missing.push('ort');
    }
    // The VAD bundle reads `self.ort` as it executes, so it must load AFTER ort exists -- and it
    // must not be attempted at all if ort failed, or the error names the wrong library.
    if (missing.length === 0 && (typeof w.vad === 'undefined' || !w.vad.MicVAD)) {
      await loadScript(`${VOICE_ASSETS}vad.bundle.min.js?retry=${Date.now()}`);
    }
    if (typeof w.ort === 'undefined') missing.push('ort');
    if (typeof w.vad === 'undefined' || !w.vad.MicVAD) missing.push('vad');
    const ok = missing.length === 0;
    // A FAILED LOAD IS NOT CACHED FOR EVER.
    //
    // `libsPromise` was assigned once and never reset, so a single transient failure to fetch the
    // two bundles left voice PERMANENTLY broken for the life of the page, with the same message
    // on every click and no way back. Retrying is cheap and the alternative is a feature that one
    // bad moment disables until a full reload.
    if (!ok) libsPromise = null;
    return { ok, missing };
  })();
  return libsPromise;
}

export type EstateVoiceState = 'off' | 'listening' | 'thinking' | 'speaking' | 'error';

export interface EstateVoice {
  state: EstateVoiceState;
  /** What the person was heard to say, as transcribed by whisper. */
  heard: string;
  /** The reply so far, clause by clause. */
  reply: string;
  /** A short status line: timings, refusals, the reason for anything that did not work. */
  detail: string;
  /** Whether the engine is usable at all on this host. */
  available: boolean;
  start: () => Promise<void>;
  stop: () => void;
  /** Make the engine speak one sentence, outside a conversation. Used for spoken replies. */
  speak: (text: string) => void;
  /** Stop whatever is sounding, now. */
  silence: () => void;
  /** The last N voice turns, newest first -- latency and friction, for the panel. */
  voiceLog: any[];
  /** The friction summary: empty rate, medians, per-voice speed. */
  voiceStats: any;
  /** The catalogue, for a picker. */
  catalogue: { cloud: string[]; say: string[]; kokoro: string[]; piper: string[] };
  /** The live engine and voice. */
  current: { engine: string; voice: string };
  selectVoice: (engine: string, voice: string) => Promise<string>;
}

interface Ctx {
  audio: AudioContext;
  vad: any;
  nextStart: number;
  playing: AudioBufferSourceNode[];
  /** Aborts the turn in flight: the SSE read and any clause still being synthesised. */
  turn: AbortController | null;
}

export function useEstateVoice(): EstateVoice {
  const fetchApi = useApi(fetchApiRef);
  const [state, setState] = useState<EstateVoiceState>('off');
  const [heard, setHeard] = useState('');
  const [reply, setReply] = useState('');
  const [detail, setDetail] = useState('');
  const [available, setAvailable] = useState(false);
  // `piper` WAS MISSING FROM THIS SHAPE, and the picker renders from it -- so the three Piper
  // voices the service reports were dropped on arrival and the group showed "0 voices" while the
  // engine was IN FACT RUNNING PIPER. A type that does not match what the server sends is not a
  // type error; it is a silent truncation, and only the picker's optgroup label revealed it.
  const [catalogue, setCatalogue] = useState<{ cloud: string[]; say: string[]; kokoro: string[]; piper: string[] }>({
    cloud: [],
    say: [],
    kokoro: [],
    piper: [],
  });
  const [current, setCurrent] = useState({ engine: 'cloud', voice: 'troy' });
  // THE VOICE LOG. Polled slowly: a turn log changes only when a turn happens, and the board is
  // already polling four other endpoints every 2 seconds.
  const [voiceLog, setVoiceLog] = useState<any[]>([]);
  const [voiceStats, setVoiceStats] = useState<any>({});
  const ctxRef = useRef<Ctx | null>(null);
  // A context created only to read replies aloud, kept apart from a conversation's so neither can
  // orphan the other. Closed in `stop()`.
  const speakCtxRef = useRef<AudioContext | null>(null);
  // True when `ctxRef` is a borrow of `speakCtxRef` rather than a real conversation.
  const borrowedRef = useRef(false);
  // The last few exchanges, so a follow-up question ("and the other one?") has something to refer
  // to. Held in a ref rather than state: the answer loop reads it mid-turn and a re-render on
  // every clause would be a re-render per word.
  const historyRef = useRef<{ role: string; content: string }[]>([]);

  /**
   * THIS CONVERSATION'S SESSION ID, minted once per mounted hook.
   *
   * It is what the bus rows are keyed by (`estate.agent.sovereign.<this>.steer`), so a voice
   * conversation appears on the board as a session in its own right -- which is the honest
   * description: it IS a session, with a person on one end.
   */
  const sessionId = useMemo(
    () => `voice-${Math.random().toString(16).slice(2, 10)}`,
    [],
  );

  /** Stop everything sounding, now. Called on barge-in and on teardown. */
  const silence = useCallback(() => {
    const c = ctxRef.current;
    if (!c) return;
    c.playing.forEach((s) => {
      try {
        s.stop();
      } catch {
        /* already ended */
      }
    });
    c.playing = [];
    c.nextStart = 0;
    clauseSink?.stop();
  }, []);

  /**
   * Schedule one clause of audio.
   *
   * `currentTime` is the AUDIO HARDWARE clock, and queueing against it is what removes the click
   * between clauses -- a `setTimeout` queue drifts by however long the main thread was busy, and
   * the seam becomes audible.
   */
  const play = useCallback((pcm: ArrayBuffer) => {
    const c = ctxRef.current;
    if (!c) return;
    const f32 = new Float32Array(pcm);
    if (!f32.length) return;
    const buf = c.audio.createBuffer(1, f32.length, TTS_RATE);
    buf.copyToChannel(f32, 0);
    const src = c.audio.createBufferSource();
    src.buffer = buf;
    src.connect(c.audio.destination);
    if (c.nextStart < c.audio.currentTime + 0.02) c.nextStart = c.audio.currentTime + 0.02;
    src.start(c.nextStart);
    c.nextStart += buf.duration;
    c.playing.push(src);
    src.onended = () => {
      c.playing = c.playing.filter((s) => s !== src);
    };
    setState('speaking');
  }, []);

  const stop = useCallback(() => {
    silence();
    const c = ctxRef.current;
    if (c) {
      try {
        c.vad?.destroy?.();
      } catch {
        /* already gone */
      }
      // The turn in flight is aborted rather than left to finish into a closed context: without
      // this, stopping the mic during an answer leaves requests running and clauses arriving for
      // an AudioContext that is about to be closed.
      try {
        c.turn?.abort();
      } catch {
        /* nothing in flight */
      }
      // THE AUDIO CONTEXT IS CLOSED, and it was not.
      //
      // `start()` builds a fresh AudioContext every time, and `stop()` released only the VAD and
      // the socket -- so every mic on/off cycle leaked one. Browsers cap live contexts (Chrome
      // around 6 for AudioContext), after which `new AudioContext()` throws and voice reports
      // "AudioContext failed: ..." with no hint that toggling is what exhausted it. `close()`
      // returns a promise; it is deliberately not awaited, because the caller is a click handler
      // that must return immediately and the release does not need to block the UI.
      if (!borrowedRef.current) {
        try {
          void c.audio.close();
        } catch {
          /* already closed, or a browser that refuses */
        }
      }
    }
    // The speak-only context is closed here too, whether or not a conversation borrowed it.
    if (speakCtxRef.current) {
      try {
        void speakCtxRef.current.close();
      } catch {
        /* already closed */
      }
      speakCtxRef.current = null;
    }
    borrowedRef.current = false;
    ctxRef.current = null;
    setState('off');
  }, [silence]);

  /** One clause of text to audio, in the voice that is currently live, and play it. */
  const sayClause = useCallback(
    async (text: string, signal?: AbortSignal) => {
      const res = await fetchApi.fetch(`${FLEETVIEW}/voice/say`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
        signal,
      });
      if (!res.ok) return false;
      play(await res.arrayBuffer());
      return true;
    },
    [fetchApi, play],
  );

  const speak = useCallback(
    (text: string) => {
      // A SPEAK-ONLY CONTEXT IS TRACKED SEPARATELY FROM A CONVERSATION.
      //
      // `speak()` used to install a "dummy" context into `ctxRef.current` when no conversation was
      // running. Two faults followed: `start()` would later OVERWRITE it, orphaning its
      // AudioContext with nothing left holding a reference to close it; and `stop()` could not
      // release it either, because by then the ref held something else. A page that only reads
      // replies aloud therefore leaked exactly one context per utterance.
      //
      // The dummy is gone. A speak-only context lives in `speakCtxRef` and is reused across
      // utterances and closed by `stop()` alongside everything else.
      if (!ctxRef.current) {
        if (!speakCtxRef.current) {
          try {
            speakCtxRef.current = new (window.AudioContext ||
              (window as any).webkitAudioContext)({ sampleRate: TTS_RATE });
          } catch (e: any) {
            setDetail(`audio unavailable: ${e.message || e}`);
            return;
          }
        }
        // Borrow it for the duration of this call, so `play()` -- which reads ctxRef -- has a
        // context with a destination. `stop()` closes whichever ones exist.
        ctxRef.current = {
          audio: speakCtxRef.current,
          vad: null,
          nextStart: 0,
          playing: [],
          turn: null,
        };
        borrowedRef.current = true;
      }
      void sayClause(text).then((ok) => {
        if (!ok) setDetail('could not speak that — the voice service refused it');
      }).catch((e: any) => setDetail(`could not speak: ${e.message || e}`));
    },
    [sayClause],
  );

  /**
   * ONE TURN, END TO END: hear it, put it on the bus, ask, speak the answer, close the turn.
   *
   * This is the whole of what the WebSocket used to do, as four ordinary requests. Each one is
   * short, so a dropped connection costs one clause rather than the conversation, and every one
   * of them proxies -- which is the point of the change.
   */
  const runTurn = useCallback(
    async (pcm: ArrayBuffer) => {
      const c = ctxRef.current;
      if (!c) return;
      // BARGE-IN ONLY ON REAL WORDS (2026-09-26). This used to abort the turn in flight the moment
      // ANY sound started -- a cough, the fan, the machine's own voice through the speakers -- so a
      // reply was cancelled, a new turn started, and that one was cancelled too: the founder's "we
      // looping", three /voice/hear calls in the same second in the log. The previous turn now
      // keeps talking until this utterance comes back as non-empty text.
      const turn = new AbortController();
      const startedAt = performance.now();

      let hearBody: any;
      try {
        const res = await fetchApi.fetch(
          `${FLEETVIEW}/voice/hear?session_id=${encodeURIComponent(
            sessionId,
          )}&author=${encodeURIComponent(AUTHOR)}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/octet-stream' },
            body: pcm,
            signal: turn.signal,
          },
        );
        hearBody = await res.json();
        if (!res.ok) {
          setState('error');
          setDetail(hearBody?.error || `could not hear that (${res.status})`);
          return;
        }
      } catch (e: any) {
        if (turn.signal.aborted) return;
        setState('error');
        setDetail(`could not reach the voice service: ${e.message || e}`);
        return;
      }

      // AN EMPTY TRANSCRIPT IS NOT AN ERROR. The person spoke and nothing came back -- the thing
      // behind "I had to say it three times". The server has already counted it; the page simply
      // goes back to listening rather than showing a fault.
      if (hearBody.empty) {
        // Noise, not words: whatever was being said carries on.
        if (!c.turn) setState('listening');
        return;
      }

      // Real words: NOW the old reply stops and this turn owns the speaker.
      c.turn?.abort();
      silence();
      c.turn = turn;

      const question: string = hearBody.text;
      setHeard(question);
      setReply('');
      setState('thinking');
      setDetail(`heard in ${hearBody.asr_seconds}s`);

      let firstClauseAt: number | null = null;
      let ttsSeconds = 0;
      let clauses = 0;
      const spoken: string[] = [];
      // ALL CLAUSES SYNTHESISE AT ONCE, PLAY IN ORDER. Each clause used to wait for the previous
      // clause's audio before the stream was even read again, so a four-clause answer paid four
      // synthesis round trips back to back. Now each request starts the moment its text lands, and
      // `chain` only orders the PLAYBACK.
      let chain: Promise<void> = Promise.resolve();

      try {
        const res = await fetchApi.fetch(`${FLEETVIEW}/voice/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
          body: JSON.stringify({ question, history: historyRef.current }),
          signal: turn.signal,
        });
        if (!res.ok || !res.body) {
          setState('error');
          setDetail(`the fleet did not answer (${res.status})`);
          return;
        }
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        // eslint-disable-next-line no-constant-condition
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          // SSE frames are separated by a blank line; a partial frame stays in the buffer until
          // its terminator arrives, because a chunk boundary is not a message boundary.
          const frames = buffer.split('\n\n');
          buffer = frames.pop() ?? '';
          for (const frame of frames) {
            const event = /^event:\s*(.*)$/m.exec(frame)?.[1]?.trim();
            const dataLine = /^data:\s*(.*)$/m.exec(frame)?.[1];
            if (!event || !dataLine) continue;
            let payload: any;
            try {
              payload = JSON.parse(dataLine);
            } catch {
              continue;
            }
            if (event === 'error') {
              setState('error');
              setDetail(payload.error || 'the fleet refused the question');
              return;
            }
            if (event === 'delta' && payload.text) {
              if (firstClauseAt === null) firstClauseAt = performance.now();
              setReply((p) => (p ? `${p} ${payload.text}` : payload.text));
              spoken.push(payload.text);
              clauses += 1;
              // SPEAK EACH CLAUSE AS IT LANDS, and await it so the audio is scheduled in the
              // order it was written. Synthesis is the slow half; a clause whose audio fails is
              // still on screen, which is why a missing clause degrades to silence, not to a
              // broken turn.
              const clauseText: string = payload.text;
              const ttsStarted = performance.now();
              const audio = fetchApi
                .fetch(`${FLEETVIEW}/voice/say`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ text: payload.text }),
                  signal: turn.signal,
                })
                .then((r) => (r.ok ? r.arrayBuffer() : null))
                .catch(() => null); // one clause that cannot be spoken must not end the turn
              chain = chain.then(async () => {
                const buf = await audio;
                ttsSeconds += (performance.now() - ttsStarted) / 1000;
                if (buf && !turn.signal.aborted) {
                  if (clauses === 1 || c.playing.length === 0) setState('speaking');
                  if (clauseSink) clauseSink.speak(buf, clauseText);
                  else play(buf);
                }
              });
            }
          }
        }
      } catch (e: any) {
        if (turn.signal.aborted) {
          setDetail('— interrupted');
          setState('listening');
          return;
        }
        setState('error');
        setDetail(`the answer stopped: ${e.message || e}`);
        return;
      }

      await chain;
      if (turn.signal.aborted) return;
      const totalSeconds = (performance.now() - startedAt) / 1000;
      const firstClauseSeconds =
        firstClauseAt === null ? null : (firstClauseAt - startedAt) / 1000;

      historyRef.current = [
        ...historyRef.current,
        { role: 'user', content: question },
        { role: 'assistant', content: spoken.join(' ') },
      ].slice(-8);

      if (c.turn === turn) c.turn = null;
      setState('listening');
      setDetail(
        firstClauseSeconds === null
          ? `answered in ${totalSeconds.toFixed(1)}s`
          : `first words ${firstClauseSeconds.toFixed(1)}s · reply ${totalSeconds.toFixed(1)}s`,
      );

      // CLOSE THE TURN: the friction log gets the numbers measured HERE, at the speaker, which is
      // where the person experiences them; the bus gets a kind=done row so a reader of
      // `estate.agent.sovereign.>` can tell a turn that finished from one that was abandoned.
      try {
        await fetchApi.fetch(`${FLEETVIEW}/voice/done`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: sessionId,
            asr_seconds: hearBody.asr_seconds,
            first_clause_seconds: firstClauseSeconds,
            total_seconds: totalSeconds,
            tts_seconds: ttsSeconds,
            words: question.split(/\s+/).filter(Boolean).length,
            clauses,
            engine: current.engine,
            voice: current.voice,
            outcome: 'ok',
          }),
        });
      } catch {
        /* the log is an instrument; its absence must not break the conversation */
      }
    },
    [current.engine, current.voice, fetchApi, play, silence, sessionId],
  );

  const start = useCallback(async () => {
    // NO PRE-FLIGHT GATE. Measured 2026-10-04, and the founder's own words: "there is absolutely no
    // difference... we are not going to be telling users to set anything on safari". This function
    // used to call `micBlocker()` here and RETURN before opening the device whenever it had an
    // opinion -- which is what put a settings instruction on screen instead of a working mic. A
    // voice product asks for the microphone by USING it: the getUserMedia call made by the VAD
    // below IS the permission prompt, and on iOS and Android the next tap re-prompts once the
    // person allows it. Nothing on this path requires a user to open Settings.
    setDetail('loading voice libraries…');
    const libs = await ensureVoiceLibs();
    if (!libs.ok) {
      setState('error');
      setDetail(
        `voice libraries missing (${libs.missing.join(', ')}) — ${VOICE_ASSETS} is not serving them`,
      );
      return;
    }
    if (typeof (window as any).ort !== 'undefined') {
      // Tell onnxruntime where ITS wasm files are. Left unset it resolves them against the page's
      // path rather than the app root, and a route like /fleet/room would look for them there.
      (window as any).ort.env.wasm.wasmPaths = VOICE_ASSETS;
    }
    let audio: AudioContext;
    try {
      audio = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: TTS_RATE,
      });
      if (audio.state === 'suspended') await audio.resume();
    } catch (e: any) {
      setState('error');
      setDetail(`AudioContext failed: ${e.message || e}`);
      return;
    }

    const ctx: Ctx = { audio, vad: null, nextStart: 0, playing: [], turn: null };
    ctxRef.current = ctx;

    try {
      const vad = await (window as any).vad.MicVAD.new({
        // 0.8 rather than the 0.5 default: on a laptop microphone the lower threshold fires on
        // keyboard and fan noise, and every false positive is a wasted transcription.
        positiveSpeechThreshold: 0.8,
        negativeSpeechThreshold: 0.5,
        minSpeechFrames: 3,
        preSpeechPadFrames: 5,
        baseAssetPath: VOICE_ASSETS,
        onnxWASMBasePath: VOICE_ASSETS,
        onSpeechStart: () => {
          // A SOUND IS NOT YET AN INTERRUPTION. Barge-in happens in runTurn once the sound comes
          // back as words; cancelling here is what made the machine cut itself off (see runTurn).
          if (!ctx.turn) setState('listening');
        },
        onSpeechEnd: (buf: Float32Array) => {
          // HEARD, SAID OUT LOUD, AT ONCE. A soft 70ms tone the instant the person stops, before
          // any network: "am I being heard?" is answered in milliseconds, not after transcription.
          try {
            const o = audio.createOscillator();
            const g = audio.createGain();
            o.frequency.value = 880;
            g.gain.setValueAtTime(0.0001, audio.currentTime);
            g.gain.exponentialRampToValueAtTime(0.08, audio.currentTime + 0.01);
            g.gain.exponentialRampToValueAtTime(0.0001, audio.currentTime + 0.07);
            o.connect(g).connect(audio.destination);
            o.start();
            o.stop(audio.currentTime + 0.08);
          } catch { /* the tone is a courtesy; the turn does not depend on it */ }
          setState('thinking');
          setDetail('heard you — working…');
          void runTurn(buf.buffer as ArrayBuffer);
        },
        onVADMisfire: () => {
          // Too short to be speech. Nothing is sent, nothing is cancelled.
          if (!ctx.turn) setState('listening');
        },
      });
      ctx.vad = vad;
      vad.start();
      setState('listening');
      setDetail('listening — speak any time');
    } catch (e: any) {
      setState('error');
      const msg = String(e?.message || e);
      // WHAT HAPPENED, IN ONE LINE, AND NOTHING TO GO CHANGE. A refusal used to end in a settings
      // walkthrough chosen from the user-agent; the founder read that and refused it ("we are not
      // going to be telling users to set anything on safari"). The page now says what happened and
      // invites the retry that actually re-prompts, which is the only fix a person can act on from
      // the page itself. The cause is still named, because a blank refusal is the defect this file
      // was written to end.
      //
      // CLASSIFIED BY IDENTITY, NOT BY PROSE (2026-10-05). This used to regex the error's ENGLISH
      // TEXT to decide what to say. Measured on LIVE production this turn (iPhone UA, after entering
      // as a guest), a phone whose `navigator.mediaDevices` is undefined threw
      // `TypeError: Cannot read properties of undefined (reading 'getUserMedia')`, whose words match
      // neither /permission|denied|notallowed/ nor /notfound|device/ -- so it fell to the last branch
      // and the founder was shown V8's own sentence where a fix belonged. Reading a message to guess
      // a cause is the same defect as guessing a platform from a UA.
      //
      // The error's `name` is a fact the browser set; the message is prose we were pattern-matching.
      // A refusal raised by our own voice path (`MicRefusal` from useVoiceRouter, whose message is
      // already worded for the person) is passed through untouched.
      setDetail(await refusalDetail(e, msg));
    }
  }, [runTurn, silence]);

  // The log, on a 10s cadence -- fast enough to see a problem appear, slow enough not to add to
  // the load the log exists to measure.
  useEffect(() => {
    let cancelled = false;
    const pull = async () => {
      try {
        const [l, s2] = await Promise.all([
          fetchApi
            .fetch(`${FLEETVIEW}/voice/log?limit=40`)
            .then((r) => (r.ok ? r.json() : null))
            .catch(() => null),
          fetchApi
            .fetch(`${FLEETVIEW}/voice/log/summary`)
            .then((r) => (r.ok ? r.json() : null))
            .catch(() => null),
        ]);
        if (cancelled) return;
        if (l) setVoiceLog(l.turns || []);
        if (s2) setVoiceStats(s2);
      } catch {
        /* the log is an instrument; its absence must not break the engine */
      }
    };
    const t = setInterval(pull, 10000);
    pull();
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, [fetchApi]);

  // Load the catalogue once so a picker is populated before it opens, and mark availability from
  // what the service reports rather than from what the browser claims to support.
  useEffect(() => {
    let cancelled = false;
    fetchApi
      .fetch(`${FLEETVIEW}/voice/voices`)
      .then((r) => r.json())
      .then((d) => {
        if (cancelled) return;
        setCatalogue({ cloud: d.cloud || [], say: d.say || [], kokoro: d.kokoro || [], piper: d.piper || [] });
        setAvailable(true);
        setCurrent({
          engine: d.current?.engine || 'cloud',
          voice: d.current?.[d.current?.engine] || 'troy',
        });
      })
      .catch(() => {
        if (!cancelled) {
          setAvailable(false);
          // NAMES THE SERVICE, NOT A PORT. The old text was "voice service not reachable on 8899",
          // which was only ever true on one laptop and told a cluster user to look for something
          // that does not exist there.
          setDetail('the FleetView backend is not answering for voice');
        }
      });
    return () => {
      cancelled = true;
    };
  }, [fetchApi]);

  const selectVoice = useCallback(
    async (engine: string, voice: string) => {
      try {
        const r = await fetchApi.fetch(`${FLEETVIEW}/voice/select`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ engine, voice }),
        });
        const j = await r.json();
        if (!r.ok) return `refused: ${j.error || r.status}`;
        setCurrent({ engine: j.engine, voice: j.voice });
        return `now speaking with ${j.voice}`;
      } catch (e: any) {
        return `failed: ${e.message || e}`;
      }
    },
    [fetchApi],
  );

  // Leave nothing running when the surface unmounts.
  useEffect(() => () => stop(), [stop]);

  return {
    state,
    heard,
    reply,
    detail,
    available,
    start,
    stop,
    speak,
    silence,
    catalogue,
    voiceLog,
    voiceStats,
    current,
    selectVoice,
  };
}
