/**
 * useSpeculativeVoice — client-side voice pipeline running ENTIRELY in the browser via WebGPU.
 *
 * The pipeline:
 *   1. Silero VAD v5 (2MB) — voice activity detection, cuts silence
 *   2. Whisper-tiny.en via Transformers.js — speech-to-text, emits partials every 500ms
 *   3. SmolLM2-360M-Instruct via Transformers.js — intent compiler, converts partials to JSON
 *   4. Kokoro.js q8 (86MB) — text-to-speech response
 *
 * ZERO audio/text leaves the browser until the final JSON schema is ready.
 * WebGPU primary, WASM fallback.
 * Models cached in IndexedDB after first download.
 *
 * Target hardware: M2 MacBook Air (baseline).
 *
 * 2026-09-22: Built for FleetView's edge voice architecture.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * The JSON schema for voice intent — what the speculative pipeline emits.
 * ZERO audio/text leaves the browser; only this schema does.
 */
export interface VoiceIntent {
  /** The action to take: "deploy", "status", "stop", "steer", "show", "query", etc. */
  action: string;
  /** The target of the action: "frontend", "backend", "agent #xyz", etc. */
  target?: string;
  /** The environment: "prod", "staging", etc. */
  env?: string;
  /** Confidence score from 0-1. */
  confidence: number;
  /** True while the user is still speaking (partial transcript). */
  partial: boolean;
}

export type SpeculativeVoiceState =
  | 'unloaded'      // Models not yet loaded
  | 'loading'       // Models downloading / initializing
  | 'ready'         // Loaded, mic off
  | 'listening'     // VAD active, waiting for speech
  | 'transcribing'  // Speech detected, whisper running
  | 'compiling'     // Transcript ready, intent model running
  | 'speaking'      // TTS playing response
  | 'error';        // Something broke

export interface ModelProgress {
  name: string;
  loaded: number;
  total: number;
  status: 'pending' | 'loading' | 'cached' | 'ready' | 'error';
}

export interface SpeculativeVoice {
  /** Current state of the voice pipeline. */
  state: SpeculativeVoiceState;
  /** Human-readable detail about current state. */
  detail: string;
  /** Whether all models are loaded and ready. */
  ready: boolean;
  /** Whether WebGPU is available (false = WASM fallback). */
  webgpu: boolean;
  /** Progress for each model being loaded. */
  modelProgress: Record<string, ModelProgress>;
  /** The current partial or final transcript. */
  transcript: string;
  /** The compiled intent (null until speech ends). */
  intent: VoiceIntent | null;
  /** History of intents from this session. */
  intentHistory: VoiceIntent[];
  /** Start loading models. Call once, idempotent. */
  load: () => Promise<void>;
  /** Start listening (must be loaded first). */
  start: () => Promise<void>;
  /** Stop listening and clean up. */
  stop: () => void;
  /** Speak text via Kokoro TTS. */
  speak: (text: string) => Promise<void>;
  /** Stop any playing audio. */
  silence: () => void;
  /** Performance metrics from the last turn. */
  metrics: TurnMetrics | null;
}

export interface TurnMetrics {
  vadLatencyMs: number;        // Time from speech end to VAD callback
  asrLatencyMs: number;        // Time for Whisper transcription
  intentLatencyMs: number;     // Time for SmolLM intent compilation
  totalLatencyMs: number;      // Total end-to-end
  ttsLatencyMs?: number;       // Time to first audio (if speak called)
  wordCount: number;
  partial: boolean;
}

// ---------------------------------------------------------------------------
// Model paths — HuggingFace Hub via Transformers.js
// ---------------------------------------------------------------------------

const WHISPER_MODEL = 'onnx-community/whisper-tiny.en';
const INTENT_MODEL = 'HuggingFaceTB/SmolLM2-360M-Instruct';
const KOKORO_MODEL = 'onnx-community/Kokoro-82M-ONNX';

// Local VAD assets served by the app (already in public/voice/)
const VOICE_ASSETS = '/voice/';

// ---------------------------------------------------------------------------
// Intent compilation prompt
// ---------------------------------------------------------------------------

const INTENT_SYSTEM_PROMPT = `You are an intent parser for a voice-controlled fleet management system.
Given a voice transcript, extract the intent as JSON. Output ONLY valid JSON, no explanation.

Schema:
{
  "action": string,    // "deploy", "status", "stop", "steer", "show", "query", "rollback", "scale", "logs", "restart"
  "target": string?,   // service/agent name if mentioned
  "env": string?,      // "prod", "staging", "dev" if mentioned
  "confidence": number // 0-1, how confident you are
}

Examples:
"stop the frontend" -> {"action":"stop","target":"frontend","confidence":0.95}
"what's stuck" -> {"action":"query","target":"stuck","confidence":0.9}
"deploy backend to prod" -> {"action":"deploy","target":"backend","env":"prod","confidence":0.95}
"show me agent xyz" -> {"action":"show","target":"agent xyz","confidence":0.9}
"how's production doing" -> {"action":"status","env":"prod","confidence":0.85}`;

// ---------------------------------------------------------------------------
// WebGPU detection
// ---------------------------------------------------------------------------

async function hasWebGPU(): Promise<boolean> {
  if (typeof navigator === 'undefined') return false;
  if (!('gpu' in navigator)) return false;
  try {
    const gpu = (navigator as any).gpu;
    const adapter = await gpu.requestAdapter();
    return adapter !== null;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// Dynamic imports — Transformers.js and Kokoro are loaded at runtime
// ---------------------------------------------------------------------------

type TransformersModule = typeof import('@huggingface/transformers');
type KokoroModule = typeof import('kokoro-js');

let transformersPromise: Promise<TransformersModule> | null = null;
let kokoroPromise: Promise<KokoroModule> | null = null;

async function loadTransformers(): Promise<TransformersModule> {
  if (!transformersPromise) {
    transformersPromise = import('@huggingface/transformers');
  }
  return transformersPromise;
}

async function loadKokoro(): Promise<KokoroModule> {
  if (!kokoroPromise) {
    kokoroPromise = import('kokoro-js');
  }
  return kokoroPromise;
}

// ---------------------------------------------------------------------------
// VAD loader — uses the estate's existing Silero assets
// ---------------------------------------------------------------------------

let vadLibsPromise: Promise<{ ok: boolean; missing: string[] }> | null = null;

function loadVadScript(src: string): Promise<boolean> {
  return new Promise((resolve) => {
    const existing = document.querySelector(`script[src="${src}"]`);
    if (existing) {
      resolve(true);
      return;
    }
    const s = document.createElement('script');
    s.src = src;
    s.onload = () => resolve(true);
    s.onerror = () => resolve(false);
    document.head.appendChild(s);
  });
}

async function ensureVadLibs(): Promise<{ ok: boolean; missing: string[] }> {
  if (vadLibsPromise) return vadLibsPromise;
  vadLibsPromise = (async () => {
    const missing: string[] = [];
    const w = window as any;

    // Load ONNX Runtime first
    if (typeof w.ort === 'undefined') {
      if (!(await loadVadScript(`${VOICE_ASSETS}ort.min.js`))) {
        missing.push('ort');
      }
    }

    // Load VAD bundle after ORT (it depends on window.ort)
    if (missing.length === 0 && (typeof w.vad === 'undefined' || !w.vad.MicVAD)) {
      await loadVadScript(`${VOICE_ASSETS}vad.bundle.min.js?t=${Date.now()}`);
    }

    if (typeof w.ort === 'undefined') missing.push('ort');
    if (typeof w.vad === 'undefined' || !w.vad.MicVAD) missing.push('vad');

    const ok = missing.length === 0;
    if (!ok) vadLibsPromise = null; // Allow retry on failure
    return { ok, missing };
  })();
  return vadLibsPromise;
}

// ---------------------------------------------------------------------------
// Hook implementation
// ---------------------------------------------------------------------------

interface PipelineContext {
  audio: AudioContext;
  vad: any;
  whisper: any;
  intentPipeline: any;
  tts: any;
  playing: AudioBufferSourceNode[];
  nextPlayStart: number;
  abortController: AbortController | null;
}

export function useSpeculativeVoice(): SpeculativeVoice {
  const [state, setState] = useState<SpeculativeVoiceState>('unloaded');
  const [detail, setDetail] = useState('Models not loaded');
  const [webgpu, setWebgpu] = useState(false);
  const [modelProgress, setModelProgress] = useState<Record<string, ModelProgress>>({});
  const [transcript, setTranscript] = useState('');
  const [intent, setIntent] = useState<VoiceIntent | null>(null);
  const [intentHistory, setIntentHistory] = useState<VoiceIntent[]>([]);
  const [metrics, setMetrics] = useState<TurnMetrics | null>(null);

  const ctxRef = useRef<PipelineContext | null>(null);
  const loadingRef = useRef(false);

  // Partial transcript accumulator for streaming ASR
  const partialBufferRef = useRef<Float32Array[]>([]);
  const lastPartialTimeRef = useRef(0);

  const ready = state === 'ready' || state === 'listening' || state === 'transcribing' ||
                state === 'compiling' || state === 'speaking';

  // Update model progress helper
  const updateProgress = useCallback((name: string, update: Partial<ModelProgress>) => {
    setModelProgress((prev) => ({
      ...prev,
      [name]: { ...prev[name], name, ...update } as ModelProgress,
    }));
  }, []);

  // ---------------------------------------------------------------------------
  // load() — download and initialize all models
  // ---------------------------------------------------------------------------
  const load = useCallback(async () => {
    if (loadingRef.current || state !== 'unloaded') return;
    loadingRef.current = true;
    setState('loading');
    setDetail('Checking WebGPU support...');

    try {
      // Check WebGPU
      const hasGPU = await hasWebGPU();
      setWebgpu(hasGPU);
      const device = hasGPU ? 'webgpu' : 'wasm';
      setDetail(`Using ${hasGPU ? 'WebGPU' : 'WASM'} backend`);

      // Initialize progress tracking
      const models = ['vad', 'whisper', 'intent', 'tts'];
      models.forEach((m) => updateProgress(m, { loaded: 0, total: 100, status: 'pending' }));

      // Load VAD libs (local assets)
      setDetail('Loading voice activity detection...');
      updateProgress('vad', { status: 'loading' });
      const vadResult = await ensureVadLibs();
      if (!vadResult.ok) {
        throw new Error(`VAD libraries missing: ${vadResult.missing.join(', ')}`);
      }
      updateProgress('vad', { loaded: 100, status: 'ready' });

      // Tell ONNX Runtime where WASM files are
      const w = window as any;
      if (w.ort?.env?.wasm) {
        w.ort.env.wasm.wasmPaths = VOICE_ASSETS;
      }

      // Load Transformers.js
      setDetail('Loading Transformers.js...');
      const { pipeline, env } = await loadTransformers();

      // Configure Transformers.js for browser
      env.allowLocalModels = false;
      env.useBrowserCache = true;

      // Load Whisper
      setDetail('Loading Whisper ASR model...');
      updateProgress('whisper', { status: 'loading' });
      const whisper = await pipeline('automatic-speech-recognition', WHISPER_MODEL, {
        device,
        dtype: 'q8',
        progress_callback: (p: any) => {
          if (p.progress !== undefined) {
            updateProgress('whisper', { loaded: Math.round(p.progress), total: 100 });
          }
        },
      });
      updateProgress('whisper', { loaded: 100, status: 'ready' });

      // Load SmolLM for intent
      setDetail('Loading intent compiler model...');
      updateProgress('intent', { status: 'loading' });
      const intentPipeline = await pipeline('text-generation', INTENT_MODEL, {
        device,
        dtype: 'q4',
        progress_callback: (p: any) => {
          if (p.progress !== undefined) {
            updateProgress('intent', { loaded: Math.round(p.progress), total: 100 });
          }
        },
      });
      updateProgress('intent', { loaded: 100, status: 'ready' });

      // Load Kokoro TTS
      setDetail('Loading TTS model...');
      updateProgress('tts', { status: 'loading' });
      const { KokoroTTS } = await loadKokoro();
      const tts = await KokoroTTS.from_pretrained(KOKORO_MODEL, {
        dtype: 'q8',
        progress_callback: (p: any) => {
          if (p.progress !== undefined) {
            updateProgress('tts', { loaded: Math.round(p.progress), total: 100 });
          }
        },
      });
      updateProgress('tts', { loaded: 100, status: 'ready' });

      // Create AudioContext
      const audio = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: 24000, // Kokoro output rate
      });

      // Store context
      ctxRef.current = {
        audio,
        vad: null, // Created on start()
        whisper,
        intentPipeline,
        tts,
        playing: [],
        nextPlayStart: 0,
        abortController: null,
      };

      setState('ready');
      setDetail('All models loaded. Ready to listen.');

    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setState('error');
      setDetail(`Load failed: ${msg}`);
      loadingRef.current = false;
    }
  }, [state, updateProgress]);

  // ---------------------------------------------------------------------------
  // Compile intent from transcript
  // ---------------------------------------------------------------------------
  const compileIntent = useCallback(async (text: string, partial: boolean): Promise<VoiceIntent> => {
    const ctx = ctxRef.current;
    if (!ctx?.intentPipeline) {
      return { action: 'unknown', confidence: 0, partial };
    }

    try {
      const prompt = `${INTENT_SYSTEM_PROMPT}\n\nTranscript: "${text}"\nJSON:`;

      const result = await ctx.intentPipeline(prompt, {
        max_new_tokens: 100,
        temperature: 0.1,
        do_sample: false,
      });

      // Extract JSON from response
      const output = result[0]?.generated_text || '';
      const jsonMatch = output.match(/\{[^}]+\}/);

      if (jsonMatch) {
        const parsed = JSON.parse(jsonMatch[0]);
        return {
          action: parsed.action || 'unknown',
          target: parsed.target,
          env: parsed.env,
          confidence: typeof parsed.confidence === 'number' ? parsed.confidence : 0.5,
          partial,
        };
      }
    } catch (err) {
      console.warn('Intent compilation failed:', err);
    }

    // Fallback: simple keyword matching
    const lower = text.toLowerCase();
    let action = 'query';
    let target: string | undefined;
    let confidence = 0.5;

    if (/^stop\s+/.test(lower)) {
      action = 'stop';
      target = text.replace(/^stop\s+/i, '').trim();
      confidence = 0.9;
    } else if (/^deploy\s+/.test(lower)) {
      action = 'deploy';
      target = text.replace(/^deploy\s+/i, '').split(/\s+to\s+/)[0].trim();
      confidence = 0.85;
    } else if (/^show\s+/.test(lower) || /^what('s| is)\s+/.test(lower)) {
      action = 'show';
      confidence = 0.7;
    } else if (/stuck|waiting|error|failed/.test(lower)) {
      action = 'query';
      target = 'stuck';
      confidence = 0.8;
    }

    return { action, target, confidence, partial };
  }, []);

  // ---------------------------------------------------------------------------
  // Process speech buffer — run ASR and intent
  // ---------------------------------------------------------------------------
  const processSpeech = useCallback(async (audioBuffer: Float32Array, isFinal: boolean) => {
    const ctx = ctxRef.current;
    if (!ctx) return;

    const turnStart = performance.now();
    let vadLatency = 0;
    let asrLatency = 0;
    let intentLatency = 0;

    try {
      setState('transcribing');
      setDetail('Transcribing speech...');

      // Run Whisper ASR
      const asrStart = performance.now();
      const asrResult = await ctx.whisper(audioBuffer, {
        language: 'en',
        task: 'transcribe',
        return_timestamps: false,
      });
      asrLatency = performance.now() - asrStart;

      const text = asrResult?.text?.trim() || '';
      if (!text) {
        setState('listening');
        setDetail('No speech detected');
        return;
      }

      setTranscript(text);

      // Compile intent
      setState('compiling');
      setDetail('Compiling intent...');

      const intentStart = performance.now();
      const compiledIntent = await compileIntent(text, !isFinal);
      intentLatency = performance.now() - intentStart;

      setIntent(compiledIntent);

      if (isFinal) {
        setIntentHistory((prev) => [compiledIntent, ...prev].slice(0, 20));
      }

      const totalLatency = performance.now() - turnStart;

      setMetrics({
        vadLatencyMs: vadLatency,
        asrLatencyMs: asrLatency,
        intentLatencyMs: intentLatency,
        totalLatencyMs: totalLatency,
        wordCount: text.split(/\s+/).length,
        partial: !isFinal,
      });

      setState('ready');
      setDetail(`Intent: ${compiledIntent.action} (${Math.round(compiledIntent.confidence * 100)}% confidence) in ${Math.round(totalLatency)}ms`);

    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error('Speech processing error:', err);
      setState('error');
      setDetail(`Processing failed: ${msg}`);
    }
  }, [compileIntent]);

  // ---------------------------------------------------------------------------
  // start() — begin listening
  // ---------------------------------------------------------------------------
  const start = useCallback(async () => {
    const ctx = ctxRef.current;
    if (!ctx) {
      setDetail('Models not loaded. Call load() first.');
      return;
    }

    if (state === 'listening' || state === 'transcribing' || state === 'compiling') {
      return; // Already active
    }

    setState('listening');
    setDetail('Initializing microphone...');
    setTranscript('');
    setIntent(null);
    partialBufferRef.current = [];

    try {
      // Resume AudioContext if suspended (browser autoplay policy)
      if (ctx.audio.state === 'suspended') {
        await ctx.audio.resume();
      }

      const w = window as any;

      // Create VAD instance
      const vad = await w.vad.MicVAD.new({
        positiveSpeechThreshold: 0.8, // Higher threshold to avoid false positives
        negativeSpeechThreshold: 0.5,
        minSpeechFrames: 3,
        preSpeechPadFrames: 5,
        baseAssetPath: VOICE_ASSETS,
        onnxWASMBasePath: VOICE_ASSETS,

        onSpeechStart: () => {
          setDetail('Speech detected...');
          partialBufferRef.current = [];
          lastPartialTimeRef.current = performance.now();
        },

        onFrameProcessed: (probs: { isSpeech: number }, frame: Float32Array) => {
          // Accumulate audio frames during speech
          if (probs.isSpeech > 0.5) {
            partialBufferRef.current.push(new Float32Array(frame));

            // Emit partial transcript every 500ms
            const now = performance.now();
            if (now - lastPartialTimeRef.current > 500 && partialBufferRef.current.length > 0) {
              lastPartialTimeRef.current = now;
              // Concatenate buffers
              const totalLength = partialBufferRef.current.reduce((sum, buf) => sum + buf.length, 0);
              const combined = new Float32Array(totalLength);
              let offset = 0;
              for (const buf of partialBufferRef.current) {
                combined.set(buf, offset);
                offset += buf.length;
              }
              // Run partial ASR (don't wait)
              void processSpeech(combined, false);
            }
          }
        },

        onSpeechEnd: (audio: Float32Array) => {
          // Final transcript
          void processSpeech(audio, true);
        },
      });

      ctx.vad = vad;
      await vad.start();

      setDetail('Listening — speak any time');

    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setState('error');
      if (/permission|denied|notallowed/i.test(msg)) {
        setDetail('Microphone blocked — allow it for this site');
      } else {
        setDetail(`Microphone failed: ${msg}`);
      }
    }
  }, [state, processSpeech]);

  // ---------------------------------------------------------------------------
  // stop() — stop listening and clean up
  // ---------------------------------------------------------------------------
  const stop = useCallback(() => {
    const ctx = ctxRef.current;
    if (!ctx) return;

    // Stop VAD
    try {
      ctx.vad?.destroy?.();
      ctx.vad = null;
    } catch {
      // Already destroyed
    }

    // Stop any in-flight processing
    try {
      ctx.abortController?.abort();
      ctx.abortController = null;
    } catch {
      // Nothing in flight
    }

    // Stop playback
    ctx.playing.forEach((node) => {
      try {
        node.stop();
      } catch {
        // Already stopped
      }
    });
    ctx.playing = [];
    ctx.nextPlayStart = 0;

    setState('ready');
    setDetail('Stopped listening');
  }, []);

  // ---------------------------------------------------------------------------
  // silence() — stop any playing audio
  // ---------------------------------------------------------------------------
  const silence = useCallback(() => {
    const ctx = ctxRef.current;
    if (!ctx) return;

    ctx.playing.forEach((node) => {
      try {
        node.stop();
      } catch {
        // Already stopped
      }
    });
    ctx.playing = [];
    ctx.nextPlayStart = 0;

    if (state === 'speaking') {
      setState('ready');
      setDetail('Audio stopped');
    }
  }, [state]);

  // ---------------------------------------------------------------------------
  // speak() — synthesize and play text via Kokoro
  // ---------------------------------------------------------------------------
  const speak = useCallback(async (text: string) => {
    const ctx = ctxRef.current;
    if (!ctx?.tts || !ctx.audio) {
      setDetail('TTS not loaded');
      return;
    }

    if (!text.trim()) return;

    const ttsStart = performance.now();
    setState('speaking');
    setDetail('Generating speech...');

    try {
      // Generate audio with Kokoro
      const result = await ctx.tts.generate(text, {
        voice: 'af_sky', // Fast, clear voice
      });

      const ttsLatency = performance.now() - ttsStart;
      setMetrics((prev) => prev ? { ...prev, ttsLatencyMs: ttsLatency } : null);
      setDetail(`Speaking (TTS: ${Math.round(ttsLatency)}ms)`);

      // Get audio data — Kokoro returns { audio: Float32Array, sampling_rate: number }
      const audioData = result.audio || result;
      const sampleRate = result.sampling_rate || 24000;

      // Create buffer and play
      const buffer = ctx.audio.createBuffer(1, audioData.length, sampleRate);
      buffer.copyToChannel(audioData, 0);

      const source = ctx.audio.createBufferSource();
      source.buffer = buffer;
      source.connect(ctx.audio.destination);

      // Queue playback
      if (ctx.nextPlayStart < ctx.audio.currentTime + 0.02) {
        ctx.nextPlayStart = ctx.audio.currentTime + 0.02;
      }
      source.start(ctx.nextPlayStart);
      ctx.nextPlayStart += buffer.duration;

      ctx.playing.push(source);
      source.onended = () => {
        ctx.playing = ctx.playing.filter((s) => s !== source);
        if (ctx.playing.length === 0) {
          setState('ready');
          setDetail('Ready');
        }
      };

    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setState('error');
      setDetail(`TTS failed: ${msg}`);
    }
  }, []);

  // ---------------------------------------------------------------------------
  // Cleanup on unmount
  // ---------------------------------------------------------------------------
  useEffect(() => {
    return () => {
      const ctx = ctxRef.current;
      if (ctx) {
        try {
          ctx.vad?.destroy?.();
        } catch {}
        try {
          ctx.audio?.close();
        } catch {}
        ctx.playing.forEach((s) => {
          try {
            s.stop();
          } catch {}
        });
      }
      ctxRef.current = null;
    };
  }, []);

  return useMemo(() => ({
    state,
    detail,
    ready,
    webgpu,
    modelProgress,
    transcript,
    intent,
    intentHistory,
    load,
    start,
    stop,
    speak,
    silence,
    metrics,
  }), [
    state,
    detail,
    ready,
    webgpu,
    modelProgress,
    transcript,
    intent,
    intentHistory,
    load,
    start,
    stop,
    speak,
    silence,
    metrics,
  ]);
}
