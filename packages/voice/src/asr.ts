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
 * The shape of the ONE pipeline this class creates.
 *
 * transformers.js types `pipeline()`'s return as a union of every pipeline the library
 * ships, which makes any call on it unspeakable (`7348 more ...` unions, measured
 * 2026-09-22 by the first `tsc --noEmit` this package ever ran). The task is fixed at
 * creation ('automatic-speech-recognition', in init below), so the union is narrowed to
 * the shape that task is called with -- a runtime fact stated as a type, at the one
 * assignment where it is created.
 */
type ASRPipeline = (
  audio: Float32Array,
  options: {
    sampling_rate: number;
    return_timestamps: boolean;
    chunk_length_s: number;
    stride_length_s: number;
  }
) => Promise<
  | { text: string; chunks?: Array<{ text: string; timestamp: [number, number] }> }
  | Array<{ text: string; chunks?: Array<{ text: string; timestamp: [number, number] }> }>
>;

/**
 * Whisper ASR processor
 */
export class ASRProcessor {
  private transcriber: ASRPipeline | null = null;

  /**
   * Initialize the ASR model
   */
  async init(onProgress?: (progress: ModelProgress) => void): Promise<void> {
    // Use Transformers.js pipeline with progress callback. The pipeline() return type is
    // narrowed to the one shape this class calls (ASRPipeline, above) at the only line that
    // creates it -- the runtime fact, stated as a type.
    this.transcriber = (await pipeline('automatic-speech-recognition', MODEL_ID, {
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
    })) as unknown as ASRPipeline;
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
