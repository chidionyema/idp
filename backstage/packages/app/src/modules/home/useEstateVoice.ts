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
// Meanwhile `sovereign/voice/server.py` runs the estate's own models -- faster-whisper for
// hearing, Kokoro for speaking -- supports barge-in, streams clauses, and offers 78 voices. The
// app was using none of it.
//
// Putting that in ONE hook is the point: a fifth voice surface added later gets the real engine by
// mounting this, rather than by remembering to avoid two browser APIs.
//
// WHAT IT OWNS:
//   * the WebSocket to the voice service (NOT proxied -- Backstage's proxy is HTTP-only and
//     cannot carry an upgrade, so this dials port 8899 directly; the server allows the localhost
//     origins by CORS);
//   * Silero VAD in the browser, so silence costs no CPU anywhere -- nothing is sent until the
//     person actually spoke and then stopped;
//   * playback scheduled on the WebAudio clock, so clause seams are inaudible;
//   * barge-in: speaking while it talks stops playback AND tells the server to stop generating.
import { useCallback, useEffect, useRef, useState } from 'react';

/** Where the voice service lives. A constant, because a WebSocket cannot go through the proxy. */
export const VOICE_ORIGIN = 'http://127.0.0.1:8899';
const TTS_RATE = 24000;

/**
 * Load the VAD and onnxruntime bundles FROM THE VOICE SERVICE, not from this app's origin.
 *
 * WHY. Measured 2026-09-20 in the Fleet page: the voice bar failed with "voice libraries not
 * loaded", because Backstage serves its SPA for any unknown path -- so a request to
 * /static/ort.min.js on port 3100 returns **index.html with content-type text/html**, a 200 that
 * is not the library. A `<script src="/static/...">` in this app therefore loads a page as
 * JavaScript and defines nothing.
 *
 * The files exist, correctly typed, on the voice service, which already serves them for its own
 * client page. Loading them from there means ONE copy of a 450KB and a 16KB bundle, one place to
 * version them, and no second static mount inside Backstage.
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
      if (!(await loadScript(`${VOICE_ORIGIN}/static/ort.min.js`))) missing.push('ort');
    }
    // The VAD bundle reads `self.ort` as it executes, so it must load AFTER ort exists -- and it
    // silently assigns nothing when it runs too early, which is the race documented in the voice
    // service's own client page. Waiting on ort here removes that ordering hazard entirely.
    if (missing.length === 0 && (typeof w.vad === 'undefined' || !w.vad.MicVAD)) {
      if (!(await loadScript(`${VOICE_ORIGIN}/static/vad.bundle.min.js`))) missing.push('vad');
    }
    // Re-inject once if it loaded but did not attach, for the same reason.
    if (missing.length === 0 && (typeof w.vad === 'undefined' || !w.vad.MicVAD)) {
      await loadScript(`${VOICE_ORIGIN}/static/vad.bundle.min.js?retry=${Date.now()}`);
    }
    if (typeof w.ort === 'undefined') missing.push('ort');
    if (typeof w.vad === 'undefined' || !w.vad.MicVAD) missing.push('vad');
    const ok = missing.length === 0;
    // A FAILED LOAD IS NOT CACHED FOR EVER.
    //
    // `libsPromise` was assigned once and never reset, so a single transient failure to fetch the
    // two bundles -- the voice service starting a second late, a blocked request, a flaky network
    // -- left voice PERMANENTLY broken for the life of the page, with the same "is it on 8899?"
    // message on every click and no way back. Retrying is cheap and the alternative is a feature
    // that one bad moment disables until a full reload.
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
  catalogue: { say: string[]; kokoro: string[]; piper: string[] };
  /** The live engine and voice. */
  current: { engine: string; voice: string };
  selectVoice: (engine: string, voice: string) => Promise<string>;
}

interface Ctx {
  ws: WebSocket;
  audio: AudioContext;
  vad: any;
  nextStart: number;
  playing: AudioBufferSourceNode[];
}

export function useEstateVoice(): EstateVoice {
  const [state, setState] = useState<EstateVoiceState>('off');
  const [heard, setHeard] = useState('');
  const [reply, setReply] = useState('');
  const [detail, setDetail] = useState('');
  const [available, setAvailable] = useState(false);
  // `piper` WAS MISSING FROM THIS SHAPE, and the picker renders from it -- so the three Piper
  // voices the service reports were dropped on arrival and the group showed "0 voices" while the
  // engine was IN FACT RUNNING PIPER. A type that does not match what the server sends is not a
  // type error; it is a silent truncation, and only the picker's optgroup label revealed it.
  const [catalogue, setCatalogue] = useState<{ say: string[]; kokoro: string[]; piper: string[] }>({
    say: [],
    kokoro: [],
    piper: [],
  });
  const [current, setCurrent] = useState({ engine: 'kokoro', voice: 'af_heart' });
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
      try {
        c.ws.close();
      } catch {
        /* already closed */
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
    setHeard('');
    setReply('');
    setDetail('');
  }, [silence]);

  /**
   * Speak a sentence outside a conversation.
   *
   * This is what replaces `speechSynthesis` at every call site that only needed a reply read
   * aloud. It uses the SAME engine and the chosen voice, so a spoken reply and a spoken answer
   * sound like the same product -- which they did not when one came from Kokoro and the other
   * from the operating system.
   */
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
          ws: null as unknown as WebSocket,
          audio: speakCtxRef.current,
          vad: null,
          nextStart: 0,
          playing: [],
        };
        borrowedRef.current = true;
      }
      fetch(`${VOICE_ORIGIN}/voice/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ engine: current.engine, voice: current.voice, text }),
      })
        .then((r) => (r.ok ? r.arrayBuffer() : null))
        .then((buf) => {
          if (!buf) {
            setDetail('could not speak that — voice service refused');
            return;
          }
          play(buf);
        })
        .catch((e) => setDetail(`could not speak: ${e.message || e}`));
    },
    [current.engine, current.voice, play],
  );

  const start = useCallback(async () => {
    setDetail('loading voice libraries…');
    // FETCH THEM FROM THE VOICE SERVICE FIRST. Backstage answers /static/* with its own SPA, so
    // the libraries have to come from the origin that actually has them; see ensureVoiceLibs.
    const libs = await ensureVoiceLibs();
    if (!libs.ok) {
      setState('error');
      setDetail(
        `voice libraries missing (${libs.missing.join(', ')}) — is the voice service on 8899?`,
      );
      return;
    }
    if (typeof (window as any).ort !== 'undefined') {
      // Tell onnxruntime where ITS wasm files are: the voice service, for the same reason as the
      // VAD assets below. Left unset it resolves them against this origin, where Backstage
      // answers with HTML.
      (window as any).ort.env.wasm.wasmPaths = `${VOICE_ORIGIN}/static/`;
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

    const ws = new WebSocket(`${VOICE_ORIGIN.replace(/^http/, 'ws')}/voice/stream`);
    ws.binaryType = 'arraybuffer';
    const ctx: Ctx = { ws, audio, vad: null, nextStart: 0, playing: [] };
    ctxRef.current = ctx;

    ws.onmessage = (ev) => {
      if (ev.data instanceof ArrayBuffer) {
        play(ev.data);
        return;
      }
      let m: any;
      try {
        m = JSON.parse(ev.data as string);
      } catch {
        return;
      }
      if (m.type === 'transcript') {
        setHeard(m.text);
        setReply('');
        setDetail(`heard in ${m.asr_seconds}s`);
        setState('thinking');
      } else if (m.type === 'clause') {
        setReply((p) => (p ? `${p} ${m.text}` : m.text));
      } else if (m.type === 'interrupted') {
        setDetail('— interrupted');
        setState('listening');
      } else if (m.type === 'done') {
        setDetail(`first audio ${m.first_audio}s · reply ${m.total}s`);
        setState('listening');
      } else if (m.type === 'error') {
        setState('error');
        setDetail(m.error || 'error');
      } else if (m.type === 'empty') {
        setState('listening');
      }
    };
    ws.onerror = () => {
      setState('error');
      setDetail('voice service unreachable — is it running on 8899?');
    };
    ws.onclose = () => setState((s) => (s === 'error' ? s : 'off'));

    ws.onopen = async () => {
      try {
        const vad = await (window as any).vad.MicVAD.new({
          // 0.8 rather than the 0.5 default: on a laptop microphone the lower threshold fires on
          // keyboard and fan noise, and every false positive is a wasted transcription.
          positiveSpeechThreshold: 0.8,
          negativeSpeechThreshold: 0.5,
          minSpeechFrames: 3,
          preSpeechPadFrames: 5,
          // THE VAD'S OWN ASSETS LIVE ON THE VOICE SERVICE, not here. Its worklet and the silero
          // weights are fetched relative to these paths, and Backstage answers any unknown path
          // with its SPA -- so `/static/` here would resolve to an HTML page and the worklet
          // would fail to load with a MIME error rather than a 404.
          baseAssetPath: `${VOICE_ORIGIN}/static/`,
          onnxWASMBasePath: `${VOICE_ORIGIN}/static/`,
          onSpeechStart: () => {
            // BARGE-IN, both halves and in this order: silence the browser immediately so the
            // person hears themselves rather than the machine, then tell the server to stop
            // generating. Without the second half the reply talks over the interruption, which is
            // the most robotic thing a voice interface can do.
            silence();
            setState('listening');
            if (ws.readyState === WebSocket.OPEN) ws.send('barge_in');
          },
          onSpeechEnd: (buf: Float32Array) => {
            setState('thinking');
            if (ws.readyState === WebSocket.OPEN) ws.send(buf.buffer);
          },
        });
        ctx.vad = vad;
        vad.start();
        setState('listening');
        setDetail('listening — speak any time');
      } catch (e: any) {
        setState('error');
        const msg = String(e?.message || e);
        // NAME THE REAL CAUSE. A microphone the browser declined is the common one here and is
        // fixed by granting permission, not by reloading or by editing code.
        setDetail(
          /permission|denied|notallowed/i.test(msg)
            ? 'microphone blocked — allow it for this site, then try again'
            : `microphone failed: ${msg}`,
        );
      }
    };
  }, [play, silence]);

  // The log, on a 10s cadence -- fast enough to see a problem appear, slow enough not to add to
  // the load the log exists to measure.
  useEffect(() => {
    let cancelled = false;
    const pull = async () => {
      try {
        const [l, s2] = await Promise.all([
          fetch(`${VOICE_ORIGIN}/log?limit=40`).then((r) => (r.ok ? r.json() : null)).catch(() => null),
          fetch(`${VOICE_ORIGIN}/log/summary`).then((r) => (r.ok ? r.json() : null)).catch(() => null),
        ]);
        if (cancelled) return;
        if (l) setVoiceLog(l.turns || []);
        if (s2) setVoiceStats(s2);
      } catch { /* the log is an instrument; its absence must not break the engine */ }
    };
    const t = setInterval(pull, 10000);
    pull();
    return () => { cancelled = true; clearInterval(t); };
  }, []);

  // Load the catalogue once so a picker is populated before it opens, and mark availability from
  // what the service reports rather than from what the browser claims to support.
  useEffect(() => {
    let cancelled = false;
    fetch(`${VOICE_ORIGIN}/voices`)
      .then((r) => r.json())
      .then((d) => {
        if (cancelled) return;
        setCatalogue({ say: d.say || [], kokoro: d.kokoro || [], piper: d.piper || [] });
        setAvailable(true);
        setCurrent({
          engine: d.current?.engine || 'kokoro',
          voice: d.current?.[d.current?.engine] || 'af_heart',
        });
      })
      .catch(() => {
        if (!cancelled) {
          setAvailable(false);
          setDetail('voice service not reachable on 8899');
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const selectVoice = useCallback(async (engine: string, voice: string) => {
    try {
      const r = await fetch(`${VOICE_ORIGIN}/voice/select`, {
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
  }, []);

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
