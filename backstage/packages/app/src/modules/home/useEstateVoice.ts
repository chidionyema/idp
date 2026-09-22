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
 * `backstage/packages/app/public/voice` is a symlink to `sovereign/voice/static`, so there is one
 * copy of the 33MB on disk and the app serves it with the right MIME types -- measured 2026-09-22
 * on the running dev server: `/voice/ort.min.js` is `application/javascript` (443678 bytes) and
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
  catalogue: { say: string[]; kokoro: string[]; piper: string[] };
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
      // BARGE-IN, SERVER SIDE: whatever was still being said for the last utterance is abandoned
      // before this one starts. The socket sent a "barge_in" frame for this; an AbortController
      // does it without a channel, because each request is its own.
      c.turn?.abort();
      const turn = new AbortController();
      c.turn = turn;
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
        setState('listening');
        setDetail('did not catch that — say it again');
        return;
      }

      const question: string = hearBody.text;
      setHeard(question);
      setReply('');
      setState('thinking');
      setDetail(`heard in ${hearBody.asr_seconds}s`);

      let firstClauseAt: number | null = null;
      let ttsSeconds = 0;
      let clauses = 0;
      const spoken: string[] = [];

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
              const ttsStarted = performance.now();
              try {
                await sayClause(payload.text, turn.signal);
              } catch {
                /* one clause that could not be spoken must not end the conversation */
              }
              ttsSeconds += (performance.now() - ttsStarted) / 1000;
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

      const totalSeconds = (performance.now() - startedAt) / 1000;
      const firstClauseSeconds =
        firstClauseAt === null ? null : (firstClauseAt - startedAt) / 1000;

      historyRef.current = [
        ...historyRef.current,
        { role: 'user', content: question },
        { role: 'assistant', content: spoken.join(' ') },
      ].slice(-8);

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
    [current.engine, current.voice, fetchApi, sayClause, sessionId],
  );

  const start = useCallback(async () => {
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
          // BARGE-IN, both halves and in this order: silence the browser immediately so the
          // person hears themselves rather than the machine, then abandon the turn in flight so
          // the rest of the reply is never fetched. Without the second half the answer talks over
          // the interruption, which is the most robotic thing a voice interface can do.
          silence();
          setState('listening');
          ctx.turn?.abort();
        },
        onSpeechEnd: (buf: Float32Array) => {
          setState('thinking');
          void runTurn(buf.buffer as ArrayBuffer);
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
