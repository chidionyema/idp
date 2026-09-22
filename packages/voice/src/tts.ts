/**
 * Kokoro TTS (Text-to-Speech) wrapper
 *
 * Generates speech from text using Kokoro TTS model.
 * Runs entirely client-side via ONNX Runtime Web.
 */

import * as ort from 'onnxruntime-web';
import { loadModel } from './models';
import type { TTSOptions, ModelProgress } from './types';

/** TTS model configuration */
const SAMPLE_RATE = 24000;

/** Available voices */
export const VOICES = {
  default: 'af',       // American Female
  af: 'af',            // American Female
  am: 'am',            // American Male
  bf: 'bf',            // British Female
  bm: 'bm',            // British Male
} as const;

export type VoiceId = keyof typeof VOICES;

/**
 * Kokoro TTS processor
 */
export class TTSProcessor {
  private session: ort.InferenceSession | null = null;
  private audioContext: AudioContext | null = null;

  /**
   * Initialize the TTS model
   */
  async init(onProgress?: (progress: ModelProgress) => void): Promise<void> {
    const modelData = await loadModel('tts', onProgress);

    this.session = await ort.InferenceSession.create(modelData, {
      executionProviders: ['wasm'],
      graphOptimizationLevel: 'all',
    });

    // Create audio context for playback
    this.audioContext = new AudioContext({ sampleRate: SAMPLE_RATE });
  }

  /**
   * Convert text to phonemes (simplified)
   * In production, this would use a proper G2P model
   */
  private textToPhonemes(text: string): number[] {
    // Simplified phoneme mapping
    // Real implementation would use a G2P library
    const charToPhoneme: Record<string, number> = {
      ' ': 0, 'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5,
      'f': 6, 'g': 7, 'h': 8, 'i': 9, 'j': 10, 'k': 11,
      'l': 12, 'm': 13, 'n': 14, 'o': 15, 'p': 16, 'q': 17,
      'r': 18, 's': 19, 't': 20, 'u': 21, 'v': 22, 'w': 23,
      'x': 24, 'y': 25, 'z': 26, '.': 27, ',': 28, '!': 29,
      '?': 30, "'": 31,
    };

    return text
      .toLowerCase()
      .split('')
      .map(c => charToPhoneme[c] ?? 0);
  }

  /**
   * Synthesize speech from text
   * @returns Float32Array of audio samples at 24kHz
   */
  async synthesize(text: string, options: TTSOptions = {}): Promise<Float32Array> {
    if (!this.session) {
      throw new Error('TTS not initialized');
    }

    const { voice = 'default', speed = 1.0, pitch = 0 } = options;

    // Convert text to phoneme sequence
    const phonemes = this.textToPhonemes(text);

    // Create input tensors
    const phonemesTensor = new ort.Tensor(
      'int64',
      BigInt64Array.from(phonemes.map(BigInt)),
      [1, phonemes.length]
    );

    const speedTensor = new ort.Tensor('float32', [speed], [1]);
    const pitchTensor = new ort.Tensor('float32', [pitch], [1]);

    // Voice embedding (placeholder - real implementation loads voice vectors)
    const voiceEmbedding = new ort.Tensor(
      'float32',
      new Float32Array(256).fill(VOICES[voice as VoiceId] === 'am' || VOICES[voice as VoiceId] === 'bm' ? -0.5 : 0.5),
      [1, 256]
    );

    // Run inference
    const feeds = {
      phonemes: phonemesTensor,
      speed: speedTensor,
      pitch: pitchTensor,
      voice: voiceEmbedding,
    };

    const results = await this.session.run(feeds);

    // Extract audio output
    const audio = results.audio as ort.Tensor;
    return audio.data as Float32Array;
  }

  /**
   * Speak text (synthesize and play)
   */
  async speak(text: string, options: TTSOptions = {}): Promise<void> {
    if (!this.audioContext) {
      this.audioContext = new AudioContext({ sampleRate: SAMPLE_RATE });
    }

    const audio = await this.synthesize(text, options);

    // Create audio buffer
    const buffer = this.audioContext.createBuffer(1, audio.length, SAMPLE_RATE);
    buffer.getChannelData(0).set(audio);

    // Play buffer
    return new Promise((resolve) => {
      const source = this.audioContext!.createBufferSource();
      source.buffer = buffer;
      source.connect(this.audioContext!.destination);
      source.onended = () => resolve();
      source.start();
    });
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
   * Clean up resources
   */
  async dispose(): Promise<void> {
    if (this.session) {
      await this.session.release();
      this.session = null;
    }
    if (this.audioContext) {
      await this.audioContext.close();
      this.audioContext = null;
    }
  }
}
