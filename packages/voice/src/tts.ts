/**
 * Kokoro TTS (Text-to-Speech) via kokoro-js
 *
 * Generates speech from text using Kokoro TTS model.
 * Runs entirely client-side via WebGPU/WASM through kokoro-js.
 *
 * Target: 300ms time-to-first-audio on M2 Air
 */

import type { TTSOptions, ModelProgress } from './types';

/** TTS model configuration */
const SAMPLE_RATE = 24000;
const MODEL_ID = 'onnx-community/Kokoro-82M-ONNX';

/** Available voices - Kokoro voice IDs */
export const VOICES = {
  // American English
  af_heart: 'af_heart',     // American Female - Heart (warm, default)
  af_bella: 'af_bella',     // American Female - Bella
  af_nicole: 'af_nicole',   // American Female - Nicole
  af_sarah: 'af_sarah',     // American Female - Sarah
  af_sky: 'af_sky',         // American Female - Sky
  am_adam: 'am_adam',       // American Male - Adam
  am_michael: 'am_michael', // American Male - Michael
  // British English
  bf_emma: 'bf_emma',       // British Female - Emma
  bf_isabella: 'bf_isabella', // British Female - Isabella
  bm_george: 'bm_george',   // British Male - George
  bm_lewis: 'bm_lewis',     // British Male - Lewis
  // Aliases
  default: 'af_heart',
  af: 'af_heart',
  am: 'am_adam',
  bf: 'bf_emma',
  bm: 'bm_george',
} as const;

export type VoiceId = keyof typeof VOICES;

// Lazy-loaded kokoro-js instance
let kokoroInstance: any = null;
let kokoroLoading: Promise<any> | null = null;

/**
 * Load Kokoro TTS model (lazy, cached)
 */
async function loadKokoro(onProgress?: (progress: ModelProgress) => void): Promise<any> {
  if (kokoroInstance) {
    return kokoroInstance;
  }

  if (kokoroLoading) {
    return kokoroLoading;
  }

  kokoroLoading = (async () => {
    // Dynamic import to avoid bundling if not used
    const { KokoroTTS } = await import('kokoro-js');

    // Report initial progress
    onProgress?.({
      model: 'tts',
      progress: 0,
      loaded: 0,
      total: 86_000_000, // ~86MB for q8 model
    });

    // Load with q8 quantization for speed/size balance. kokoro-js has no "auto" device:
    // it wants the device named, or null for its own default (which is WebGPU when the
    // browser has it, WASM otherwise) -- so the option is left unset rather than guessed.
    kokoroInstance = await KokoroTTS.from_pretrained(MODEL_ID, {
      dtype: 'q8',
      progress_callback: (progress: { status: string; progress?: number; loaded?: number; total?: number }) => {
        if (progress.status === 'progress' && onProgress) {
          onProgress({
            model: 'tts',
            progress: (progress.progress ?? 0) / 100,
            loaded: progress.loaded ?? 0,
            total: progress.total ?? 86_000_000,
          });
        }
      },
    });

    onProgress?.({
      model: 'tts',
      progress: 1,
      loaded: 86_000_000,
      total: 86_000_000,
    });

    return kokoroInstance;
  })();

  return kokoroLoading;
}

/**
 * Kokoro TTS processor - browser-native speech synthesis
 */
export class TTSProcessor {
  private kokoro: any = null;
  private audioContext: AudioContext | null = null;
  private currentSource: AudioBufferSourceNode | null = null;

  /**
   * Initialize the TTS model
   */
  async init(onProgress?: (progress: ModelProgress) => void): Promise<void> {
    this.kokoro = await loadKokoro(onProgress);
    this.audioContext = new AudioContext({ sampleRate: SAMPLE_RATE });
  }

  /**
   * Synthesize speech from text
   * @returns Float32Array of audio samples at 24kHz
   */
  async synthesize(text: string, options: TTSOptions = {}): Promise<Float32Array> {
    if (!this.kokoro) {
      throw new Error('TTS not initialized');
    }

    const voice = VOICES[(options.voice as VoiceId) ?? 'default'] ?? VOICES.default;
    const speed = options.speed ?? 1.0;

    // Generate audio
    const result = await this.kokoro.generate(text, {
      voice,
      speed,
    });

    // Result is already Float32Array at 24kHz
    return result.audio;
  }

  /**
   * Synthesize and stream audio for low latency (clause-by-clause)
   * Yields audio chunks as they're generated
   */
  async *synthesizeStream(text: string, options: TTSOptions = {}): AsyncGenerator<Float32Array> {
    if (!this.kokoro) {
      throw new Error('TTS not initialized');
    }

    const voice = VOICES[(options.voice as VoiceId) ?? 'default'] ?? VOICES.default;
    const speed = options.speed ?? 1.0;

    // Stream generation if supported
    if (this.kokoro.generate_stream) {
      for await (const chunk of this.kokoro.generate_stream(text, { voice, speed })) {
        yield chunk.audio;
      }
    } else {
      // Fallback to full generation
      const result = await this.kokoro.generate(text, { voice, speed });
      yield result.audio;
    }
  }

  /**
   * Speak text (synthesize and play)
   */
  async speak(text: string, options: TTSOptions = {}): Promise<void> {
    if (!this.audioContext) {
      this.audioContext = new AudioContext({ sampleRate: SAMPLE_RATE });
    }

    // Resume context if suspended (browser autoplay policy)
    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume();
    }

    const audio = await this.synthesize(text, options);

    // Create audio buffer
    const buffer = this.audioContext.createBuffer(1, audio.length, SAMPLE_RATE);
    buffer.getChannelData(0).set(audio);

    // Stop any currently playing audio
    this.stopSpeaking();

    // Play buffer
    return new Promise((resolve) => {
      this.currentSource = this.audioContext!.createBufferSource();
      this.currentSource.buffer = buffer;
      this.currentSource.connect(this.audioContext!.destination);
      this.currentSource.onended = () => {
        this.currentSource = null;
        resolve();
      };
      this.currentSource.start();
    });
  }

  /**
   * Speak with streaming for lower latency
   * Starts playing audio before full synthesis is complete
   */
  async speakStream(text: string, options: TTSOptions = {}): Promise<void> {
    if (!this.audioContext) {
      this.audioContext = new AudioContext({ sampleRate: SAMPLE_RATE });
    }

    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume();
    }

    this.stopSpeaking();

    const chunks: Float32Array[] = [];
    let totalLength = 0;

    // Collect all chunks
    for await (const chunk of this.synthesizeStream(text, options)) {
      chunks.push(chunk);
      totalLength += chunk.length;
    }

    if (totalLength === 0) return;

    // Combine into single buffer
    const combined = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of chunks) {
      combined.set(chunk, offset);
      offset += chunk.length;
    }

    const buffer = this.audioContext.createBuffer(1, combined.length, SAMPLE_RATE);
    buffer.getChannelData(0).set(combined);

    return new Promise((resolve) => {
      this.currentSource = this.audioContext!.createBufferSource();
      this.currentSource.buffer = buffer;
      this.currentSource.connect(this.audioContext!.destination);
      this.currentSource.onended = () => {
        this.currentSource = null;
        resolve();
      };
      this.currentSource.start();
    });
  }

  /**
   * Stop any currently playing speech
   */
  stopSpeaking(): void {
    if (this.currentSource) {
      try {
        this.currentSource.stop();
      } catch {
        // Already stopped
      }
      this.currentSource = null;
    }
  }

  /**
   * Check if currently speaking
   */
  isSpeaking(): boolean {
    return this.currentSource !== null;
  }

  /**
   * Get audio data as WAV blob
   */
  toWavBlob(audio: Float32Array): Blob {
    const buffer = new ArrayBuffer(44 + audio.length * 2);
    const view = new DataView(buffer);

    // WAV header
    const writeString = (offset: number, str: string) => {
      for (let i = 0; i < str.length; i++) {
        view.setUint8(offset + i, str.charCodeAt(i));
      }
    };

    writeString(0, 'RIFF');
    view.setUint32(4, 36 + audio.length * 2, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);  // Subchunk size
    view.setUint16(20, 1, true);   // PCM format
    view.setUint16(22, 1, true);   // Mono
    view.setUint32(24, SAMPLE_RATE, true);
    view.setUint32(28, SAMPLE_RATE * 2, true);  // Byte rate
    view.setUint16(32, 2, true);   // Block align
    view.setUint16(34, 16, true);  // Bits per sample
    writeString(36, 'data');
    view.setUint32(40, audio.length * 2, true);

    // Write samples
    let offset = 44;
    for (let i = 0; i < audio.length; i++) {
      const sample = Math.max(-1, Math.min(1, audio[i]));
      view.setInt16(offset, sample * 0x7FFF, true);
      offset += 2;
    }

    return new Blob([buffer], { type: 'audio/wav' });
  }

  /**
   * List available voices
   */
  getVoices(): string[] {
    return Object.keys(VOICES).filter(k => !['default', 'af', 'am', 'bf', 'bm'].includes(k));
  }

  /**
   * Clean up resources
   */
  async dispose(): Promise<void> {
    this.stopSpeaking();
    if (this.audioContext) {
      await this.audioContext.close();
      this.audioContext = null;
    }
    this.kokoro = null;
  }
}
