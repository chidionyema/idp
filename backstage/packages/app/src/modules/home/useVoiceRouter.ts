// useVoiceRouter — the streaming voice: one WebSocket to voice-router (platform/voice-router).
//
// WHY. useEstateVoice waits for the person to stop, uploads the whole utterance to /voice/hear,
// then asks /voice/stream, then fetches /voice/say per clause: three round trips, and nothing on
// screen until the first one returns. Measured 2026-09-26: first words 3.0-3.8s after speech end.
// voice-router transcribes WHILE the person speaks (partials every 0.56s of audio), ends the
// utterance itself, streams the brain's reply phrase by phrase and synthesises each one as it
// arrives. Measured the same day against the same router: first audio median 2.26s.
//
// THE SOCKET IS SAME-ORIGIN (`/voice/ws` on the page's own host), never localhost or a port: the
// old 8899 socket existed only on one laptop, which is why tests/test_voice_on_the_bus.py refuses
// one. The ingress (cluster) or the dev proxy (laptop) routes that path to the voice-router pod,
// and voice-router checks the Origin header against its allow-list.
//
// PROTOCOL (platform/voice-router/cmd/voice-router/main.go):
//   up    binary int16 LE PCM, 16 kHz mono; text {"type":"system"|"ask"|"say"|"stop", text}
//   down  text hello{rate} partial{text} final{turn,text} phrase{turn,text} intent_result{turn,intent}
//              barge{turn} done{turn} error{turn,text}
//         binary uint32 LE turn id, then int16 LE PCM at hello.rate
// intent_result.intent is the contract in ./intentCue (an estate intent ran; its text is also spoken).
// Audio for any turn at or below the last barge is dropped: that is what makes an interruption
// silence the agent at once, even with frames still in flight.
import { useCallback, useEffect, useRef, useState } from 'react';
import type { EstateVoice, EstateVoiceState } from './useEstateVoice';
import { parseIntentResult, type IntentResult } from './intentCue';

// Where voice-router answers. Deployed, it is the page's own origin (the ingress routes /voice/).
// Under `yarn start` the page is the dev server, which cannot proxy a WebSocket, and the backend's
// proxy drops the upgrade, so the page goes to the laptop router directly: its Origin allow-list
// already admits localhost:3100. The same NODE_ENV split the sign-in module uses.
export function voiceRouterBase(
  loc: Pick<Location, 'protocol' | 'host'> = window.location,
  env: string | undefined = process.env.NODE_ENV,
): { ws: string; http: string } {
  if (env !== 'production') return { ws: 'ws://127.0.0.1:8091', http: 'http://127.0.0.1:8091' };
  const tls = loc.protocol === 'https:';
  return { ws: `${tls ? 'wss' : 'ws'}://${loc.host}`, http: `${tls ? 'https' : 'http'}://${loc.host}` };
}

export function voiceRouterUrl(
  loc: Pick<Location, 'protocol' | 'host'> = window.location,
  env: string | undefined = process.env.NODE_ENV,
): string {
  return `${voiceRouterBase(loc, env).ws}/voice/ws`;
}

/**
 * GET /voice/turns in the shape the /fleet voice panel already renders (useEstateVoice's
 * voiceStats / voiceLog): the router's turn record uses voice_turns' field names, so only the
 * summary needs renaming.
 */
export function toPanel(body: any): { voiceStats: any; voiceLog: any[] } {
  const sum = body?.summary ?? {};
  const med = sum.median_s ?? {};
  const turns = sum.turns ?? 0;
  const empty = sum.outcomes?.empty ?? 0;
  const r2 = (v: any) => (typeof v === 'number' ? Math.round(v * 100) / 100 : undefined);
  return {
    voiceStats: {
      turns,
      empty,
      empty_rate: turns ? empty / turns : 0,
      asr_median_s: r2(med.asr_s),
      first_clause_median_s: r2(med.first_audio_s),
    },
    voiceLog: (body?.recent ?? []).map((t: any) => ({
      ...t,
      id: t.hlc,
      asr_s: r2(t.asr_s),
      llm_first_s: r2(t.llm_first_s),
      tts_s: r2(t.tts_s),
    })),
  };
}

// The capture worklet: downsample whatever rate the hardware runs at to 16 kHz by averaging, and
// post 20 ms frames of int16. An AudioWorklet runs off the main thread, so a busy page cannot drop
// microphone audio the way the deprecated ScriptProcessor does. Loaded from a Blob so it needs no
// static asset and no auth header.
export const CAPTURE_WORKLET = `
class Capture extends AudioWorkletProcessor {
  constructor() { super(); this.step = sampleRate / 16000; this.acc = 0; this.n = 0; this.pos = 0;
    this.out = new Int16Array(320); this.i = 0; }
  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (!ch) return true;
    for (let k = 0; k < ch.length; k++) {
      this.acc += ch[k]; this.n++; this.pos++;
      if (this.pos >= this.step) {
        this.pos -= this.step;
        const v = Math.max(-1, Math.min(1, this.acc / this.n));
        this.out[this.i++] = v < 0 ? v * 32768 : v * 32767;
        this.acc = 0; this.n = 0;
        if (this.i === this.out.length) { this.port.postMessage(this.out.buffer, [this.out.buffer]);
          this.out = new Int16Array(320); this.i = 0; }
      }
    }
    return true;
  }
}
registerProcessor('voice-capture', Capture);
`;

/** Split a server audio frame into its turn id and samples; null for a frame too short to hold both. */
export function decodeFrame(data: ArrayBuffer): { turn: number; pcm: Float32Array } | null {
  if (data.byteLength < 6) return null;
  const turn = new DataView(data).getUint32(0, true);
  const n = (data.byteLength - 4) >> 1;
  const view = new DataView(data, 4);
  const pcm = new Float32Array(n);
  for (let i = 0; i < n; i++) pcm[i] = view.getInt16(2 * i, true) / 32768;
  return { turn, pcm };
}

interface Live {
  ws: WebSocket;
  audio: AudioContext;
  mic: MediaStream;
  node: AudioWorkletNode;
  rate: number;
  nextStart: number;
  playing: AudioBufferSourceNode[];
  barged: number;
}

export interface VoiceRouter extends EstateVoice {
  /** The words so far, while the person is still speaking. */
  partial: string;
  /** The router answered its last turns read; false until it has, and after it stops. */
  reachable: boolean;
}

export interface VoiceRouterOptions {
  /** An utterance ran an estate intent: its result, for the visual cue. */
  onIntentResult?: (r: IntentResult) => void;
}

/**
 * `system` is the context the brain answers from -- the live fleet, so it never invents counts.
 * It is re-sent whenever it changes.
 */
export function useVoiceRouter(system = '', opts: VoiceRouterOptions = {}): VoiceRouter {
  const [state, setState] = useState<EstateVoiceState>('off');
  const [partial, setPartial] = useState('');
  const [heard, setHeard] = useState('');
  const [reply, setReply] = useState('');
  const [detail, setDetail] = useState('');
  const liveRef = useRef<Live | null>(null);
  const systemRef = useRef(system);
  const onIntentRef = useRef(opts.onIntentResult);
  onIntentRef.current = opts.onIntentResult;
  const finalAt = useRef(0);
  const [reachable, setReachable] = useState(false);
  const [panel, setPanel] = useState<{ voiceStats: any; voiceLog: any[] }>({ voiceStats: {}, voiceLog: [] });

  // The turn record, every 3s: the panel's metrics, and the proof the router is there at all.
  useEffect(() => {
    let live = true;
    const read = async () => {
      try {
        const r = await fetch(`${voiceRouterBase().http}/voice/turns`);
        if (!r.ok) throw new Error(String(r.status));
        const p = toPanel(await r.json());
        if (live) {
          setPanel(p);
          setReachable(true);
        }
      } catch {
        if (live) setReachable(false);
      }
    };
    void read();
    const t = setInterval(read, 3000);
    return () => {
      live = false;
      clearInterval(t);
    };
  }, []);

  const silence = useCallback(() => {
    const l = liveRef.current;
    if (!l) return;
    l.playing.forEach((s) => {
      try {
        s.stop();
      } catch {
        /* already ended */
      }
    });
    l.playing = [];
    l.nextStart = 0;
  }, []);

  const play = useCallback((data: ArrayBuffer) => {
    const l = liveRef.current;
    const f = l && decodeFrame(data);
    if (!l || !f || f.turn <= l.barged) return;
    const buf = l.audio.createBuffer(1, f.pcm.length, l.rate);
    buf.copyToChannel(f.pcm, 0);
    const src = l.audio.createBufferSource();
    src.buffer = buf;
    src.connect(l.audio.destination);
    // Queued on the audio hardware clock, so the seams between phrases are inaudible.
    if (l.nextStart < l.audio.currentTime + 0.02) {
      if (finalAt.current) {
        setDetail(`first audio ${Math.round(performance.now() - finalAt.current)}ms after the words were final`);
        finalAt.current = 0;
      }
      l.nextStart = l.audio.currentTime + 0.02;
    }
    src.start(l.nextStart);
    l.nextStart += buf.duration;
    l.playing.push(src);
    src.onended = () => {
      l.playing = l.playing.filter((s) => s !== src);
      if (l.playing.length === 0) setState((s) => (s === 'speaking' ? 'listening' : s));
    };
    setState('speaking');
  }, []);

  const stop = useCallback(() => {
    const l = liveRef.current;
    liveRef.current = null;
    if (!l) return;
    l.playing.forEach((s) => {
      try {
        s.stop();
      } catch {
        /* already ended */
      }
    });
    l.node.port.onmessage = null;
    l.mic.getTracks().forEach((t) => t.stop());
    l.ws.onclose = null;
    l.ws.close();
    void l.audio.close();
    setState('off');
    setPartial('');
  }, []);

  const start = useCallback(async () => {
    if (liveRef.current) return;
    setDetail('');
    let audio: AudioContext | null = null;
    let mic: MediaStream | null = null;
    try {
      mic = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
      });
      audio = new AudioContext();
      const url = URL.createObjectURL(new Blob([CAPTURE_WORKLET], { type: 'application/javascript' }));
      await audio.audioWorklet.addModule(url);
      URL.revokeObjectURL(url);
      const node = new AudioWorkletNode(audio, 'voice-capture');
      audio.createMediaStreamSource(mic).connect(node);
      const ws = new WebSocket(voiceRouterUrl());
      ws.binaryType = 'arraybuffer';
      await new Promise<void>((resolve, reject) => {
        ws.onopen = () => resolve();
        ws.onerror = () => reject(new Error('voice-router is not reachable at /voice/ws'));
      });
      const l: Live = { ws, audio, mic, node, rate: 22050, nextStart: 0, playing: [], barged: 0 };
      liveRef.current = l;
      node.port.onmessage = (e) => {
        if (ws.readyState === WebSocket.OPEN) ws.send(e.data as ArrayBuffer);
      };
      if (systemRef.current) ws.send(JSON.stringify({ type: 'system', text: systemRef.current }));
      ws.onmessage = (e) => {
        if (typeof e.data !== 'string') {
          play(e.data as ArrayBuffer);
          return;
        }
        const m = JSON.parse(e.data);
        switch (m.type) {
          case 'hello':
            l.rate = m.rate;
            setState('listening');
            break;
          case 'partial':
            setPartial(m.text);
            break;
          case 'final':
            finalAt.current = performance.now();
            setPartial('');
            setHeard(m.text);
            setReply('');
            setState('thinking');
            break;
          case 'phrase':
            setReply((r) => (r ? `${r} ${m.text}` : m.text));
            break;
          case 'intent_result': {
            const r = parseIntentResult(m.intent);
            if (r) onIntentRef.current?.(r);
            break;
          }
          case 'barge':
            l.barged = Math.max(l.barged, m.turn);
            silence();
            setState('listening');
            break;
          case 'error':
            setDetail(m.text);
            setState('listening');
            break;
          default:
        }
      };
      ws.onclose = () => {
        if (liveRef.current === l) {
          stop();
          setState('error');
          setDetail('voice-router closed the connection');
        }
      };
    } catch (err: any) {
      mic?.getTracks().forEach((t) => t.stop());
      void audio?.close();
      liveRef.current = null;
      setState('error');
      setDetail(String(err?.message ?? err));
      throw err;
    }
  }, [play, silence, stop]);

  // Reads text aloud as given (an agent's reply on /fleet), as useEstateVoice.speak does. `say`,
  // not `ask`: an ask would hand the words to the brain, which would answer them.
  const speak = useCallback((text: string) => {
    const l = liveRef.current;
    if (l && text.trim() && l.ws.readyState === WebSocket.OPEN) l.ws.send(JSON.stringify({ type: 'say', text }));
  }, []);

  const interrupt = useCallback(() => {
    silence();
    const l = liveRef.current;
    if (l && l.ws.readyState === WebSocket.OPEN) l.ws.send(JSON.stringify({ type: 'stop' }));
  }, [silence]);

  useEffect(() => {
    systemRef.current = system;
    const l = liveRef.current;
    if (l && system && l.ws.readyState === WebSocket.OPEN) l.ws.send(JSON.stringify({ type: 'system', text: system }));
  }, [system]);

  useEffect(() => stop, [stop]);

  return {
    state,
    partial,
    heard,
    reply,
    detail,
    available: typeof window !== 'undefined' && 'AudioWorkletNode' in window,
    reachable,
    start,
    stop,
    speak,
    silence: interrupt,
    voiceLog: panel.voiceLog,
    voiceStats: panel.voiceStats,
    catalogue: { cloud: [], say: [], kokoro: [], piper: ['ljspeech-medium'] },
    current: { engine: 'voice-router', voice: 'ljspeech-medium' },
    selectVoice: async () => 'voice-router has one voice; set VOICE_TTS on the pod to change it',
  };
}
