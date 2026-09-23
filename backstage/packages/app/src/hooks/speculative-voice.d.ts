/**
 * Type declarations for dynamic imports in useSpeculativeVoice.
 */

declare module 'kokoro-js' {
  export interface KokoroTTSOptions {
    dtype?: 'fp32' | 'fp16' | 'q8' | 'q4' | 'q4f16';
    progress_callback?: (progress: { progress?: number; status?: string }) => void;
  }

  export interface GenerateOptions {
    voice?: string;
  }

  export interface AudioResult {
    audio: Float32Array;
    sampling_rate: number;
  }

  export class KokoroTTS {
    static from_pretrained(
      model: string,
      options?: KokoroTTSOptions
    ): Promise<KokoroTTS>;

    generate(text: string, options?: GenerateOptions): Promise<AudioResult>;
  }
}

// Augment global window for VAD libraries
declare global {
  interface Window {
    ort?: {
      env?: {
        wasm?: {
          wasmPaths?: string;
        };
      };
    };
    vad?: {
      MicVAD: {
        new: (options: {
          positiveSpeechThreshold?: number;
          negativeSpeechThreshold?: number;
          minSpeechFrames?: number;
          preSpeechPadFrames?: number;
          baseAssetPath?: string;
          onnxWASMBasePath?: string;
          onSpeechStart?: () => void;
          onFrameProcessed?: (probs: { isSpeech: number }, frame: Float32Array) => void;
          onSpeechEnd?: (audio: Float32Array) => void;
        }) => Promise<{
          start: () => Promise<void>;
          destroy: () => void;
        }>;
      };
    };
  }
}

export {};
