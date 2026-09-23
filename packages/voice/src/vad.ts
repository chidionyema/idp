/**
 * Silero VAD (Voice Activity Detection) wrapper
 *
 * Detects speech in audio streams using the Silero VAD model.
 * Runs entirely client-side via ONNX Runtime Web.
 */

import * as ort from 'onnxruntime-web';
import { loadModel } from './models';
import type { VADState, ModelProgress } from './types';

/** VAD model configuration */
const SAMPLE_RATE = 16000;
const WINDOW_SIZE = 512;  // 32ms at 16kHz

/**
 * Silero VAD processor
 */
export class VADProcessor {
  private session: ort.InferenceSession | null = null;
  private state: ort.Tensor | null = null;
  private sr: ort.Tensor | null = null;
  private context: ort.Tensor | null = null;
  private sensitivity: number;

  constructor(sensitivity = 0.5) {
    this.sensitivity = sensitivity;
  }

  /**
   * Initialize the VAD model
   */
  async init(onProgress?: (progress: ModelProgress) => void): Promise<void> {
    const modelData = await loadModel('vad', onProgress);

    this.session = await ort.InferenceSession.create(modelData, {
      executionProviders: ['wasm'],
      graphOptimizationLevel: 'all',
    });

    // Initialize state tensors
    this.resetState();
  }

  /**
   * Reset internal state (call between utterances)
   */
  resetState(): void {
    // Silero VAD state: [2, 1, 128] for LSTM hidden/cell states
    this.state = new ort.Tensor(
      'float32',
      new Float32Array(2 * 1 * 128).fill(0),
      [2, 1, 128]
    );

    // Sample rate tensor
    this.sr = new ort.Tensor('int64', BigInt64Array.from([BigInt(SAMPLE_RATE)]), []);

    // Context for streaming (64 samples)
    this.context = new ort.Tensor(
      'float32',
      new Float32Array(64).fill(0),
      [1, 64]
    );
  }

  /**
   * Process audio chunk and return VAD state
   * @param audio Float32Array of audio samples at 16kHz
   */
  async process(audio: Float32Array): Promise<VADState> {
    if (!this.session || !this.state || !this.sr || !this.context) {
      throw new Error('VAD not initialized');
    }

    // Ensure audio is correct length
    if (audio.length !== WINDOW_SIZE) {
      throw new Error(`Expected ${WINDOW_SIZE} samples, got ${audio.length}`);
    }

    // Create input tensor [1, window_size]
    const input = new ort.Tensor('float32', audio, [1, WINDOW_SIZE]);

    // Run inference
    const feeds = {
      input: input,
      state: this.state,
      sr: this.sr,
      context: this.context,
    };

    const results = await this.session.run(feeds);

    // Update state for next call
    this.state = results.stateN as ort.Tensor;
    this.context = results.contextN as ort.Tensor;

    // Get probability
    const output = results.output as ort.Tensor;
    const probability = (output.data as Float32Array)[0];

    // Apply sensitivity threshold
    const speaking = probability > (1 - this.sensitivity);

    return { speaking, probability };
  }

  /**
   * Set VAD sensitivity
   */
  setSensitivity(sensitivity: number): void {
    this.sensitivity = Math.max(0, Math.min(1, sensitivity));
  }

  /**
   * Clean up resources
   */
  async dispose(): Promise<void> {
    if (this.session) {
      await this.session.release();
      this.session = null;
    }
    this.state = null;
    this.sr = null;
    this.context = null;
  }
}

/**
 * Create a VAD processor from audio stream
 */
export async function createVADStream(
  stream: MediaStream,
  onVAD: (state: VADState) => void,
  sensitivity = 0.5,
  onProgress?: (progress: ModelProgress) => void
): Promise<{ vad: VADProcessor; stop: () => void }> {
  const vad = new VADProcessor(sensitivity);
  await vad.init(onProgress);

  // Create audio context
  const audioContext = new AudioContext({ sampleRate: SAMPLE_RATE });
  const source = audioContext.createMediaStreamSource(stream);

  // Create script processor for real-time processing
  const processor = audioContext.createScriptProcessor(WINDOW_SIZE, 1, 1);

  processor.onaudioprocess = async (event) => {
    const inputData = event.inputBuffer.getChannelData(0);
    const state = await vad.process(new Float32Array(inputData));
    onVAD(state);
  };

  source.connect(processor);
  processor.connect(audioContext.destination);

  const stop = () => {
    processor.disconnect();
    source.disconnect();
    audioContext.close();
    vad.dispose();
  };

  return { vad, stop };
}
