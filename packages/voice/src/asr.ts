/**
 * Whisper ASR (Automatic Speech Recognition) wrapper
 *
 * Transcribes audio to text using Whisper Tiny model.
 * Runs entirely client-side via ONNX Runtime Web or Transformers.js.
 */

import { pipeline, env } from '@xenova/transformers';
import type { ASRResult, ModelProgress } from './types';

// Disable local model loading attempts
env.allowLocalModels = false;

/** ASR model configuration */
const MODEL_ID = 'Xenova/whisper-tiny.en';
const SAMPLE_RATE = 16000;

/**
 * Whisper ASR processor
 */
export class ASRProcessor {
  private transcriber: Awaited<ReturnType<typeof pipeline>> | null = null;

  /**
   * Initialize the ASR model
   */
  async init(onProgress?: (progress: ModelProgress) => void): Promise<void> {
    // Use Transformers.js pipeline with progress callback
    this.transcriber = await pipeline('automatic-speech-recognition', MODEL_ID, {
      progress_callback: (data: { status: string; progress?: number; loaded?: number; total?: number }) => {
        if (data.status === 'progress' && onProgress && data.progress !== undefined) {
          onProgress({
            model: 'asr',
            progress: data.progress / 100,
            loaded: data.loaded || 0,
            total: data.total || 0,
          });
        }
      },
    });
  }

  /**
   * Transcribe audio to text
   * @param audio Float32Array of audio samples at 16kHz
   */
  async transcribe(audio: Float32Array): Promise<ASRResult> {
    if (!this.transcriber) {
      throw new Error('ASR not initialized');
    }

    // Run transcription
    const result = await this.transcriber(audio, {
      sampling_rate: SAMPLE_RATE,
      return_timestamps: true,
      chunk_length_s: 30,
      stride_length_s: 5,
    });

    // Handle result format
    if (Array.isArray(result)) {
      const first = result[0];
      return {
        text: first.text.trim(),
        confidence: 1.0,  // Whisper doesn't provide confidence
        segments: first.chunks?.map((chunk: { text: string; timestamp: [number, number] }) => ({
          text: chunk.text,
          start: chunk.timestamp[0],
          end: chunk.timestamp[1],
        })),
      };
    }

    return {
      text: (result as { text: string }).text.trim(),
      confidence: 1.0,
    };
  }

  /**
   * Clean up resources
   */
  async dispose(): Promise<void> {
    this.transcriber = null;
  }
}

/**
 * Resample audio to 16kHz if necessary
 */
export function resampleTo16kHz(
  audio: Float32Array,
  originalSampleRate: number
): Float32Array {
  if (originalSampleRate === SAMPLE_RATE) {
    return audio;
  }

  const ratio = SAMPLE_RATE / originalSampleRate;
  const newLength = Math.round(audio.length * ratio);
  const resampled = new Float32Array(newLength);

  for (let i = 0; i < newLength; i++) {
    const srcIndex = i / ratio;
    const srcIndexFloor = Math.floor(srcIndex);
    const srcIndexCeil = Math.min(srcIndexFloor + 1, audio.length - 1);
    const t = srcIndex - srcIndexFloor;

    // Linear interpolation
    resampled[i] = audio[srcIndexFloor] * (1 - t) + audio[srcIndexCeil] * t;
  }

  return resampled;
}

/**
 * Convert AudioBuffer to Float32Array at 16kHz
 */
export function audioBufferToFloat32(buffer: AudioBuffer): Float32Array {
  // Get first channel (mono)
  const channelData = buffer.getChannelData(0);

  // Resample if necessary
  return resampleTo16kHz(channelData, buffer.sampleRate);
}
