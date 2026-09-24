/**
 * VoiceClient - Main entry point for FleetView Voice SDK
 *
 * Provides a unified API for voice input/output:
 * - Listens for speech using VAD + ASR
 * - Parses intents from transcripts
 * - Synthesizes speech output
 */

import { VADProcessor } from './vad';
import { ASRProcessor, audioBufferToFloat32 } from './asr';
import { IntentProcessor } from './intent';
import { TTSProcessor } from './tts';
import { createConversation, type Conversation } from './conversation';
import type {
  VoiceClientConfig,
  VoiceClientState,
  Intent,
  VADState,
  ModelProgress,
  TTSOptions,
} from './types';

/** Default configuration values */
const DEFAULTS: Required<Omit<VoiceClientConfig, 'token' | 'onIntent' | 'onPartialTranscript' | 'onClarificationNeeded' | 'onSpeaking' | 'onError' | 'onModelProgress'>> = {
  vadSensitivity: 0.5,
  minSpeechDuration: 300,
  silenceDuration: 500,
  modelCacheDir: '',
  speculativeStreaming: true,
  partialInterval: 500,
  debug: false,
};

/**
 * FleetView Voice Client
 *
 * @example
 * ```typescript
 * const client = new VoiceClient({
 *   onIntent: (intent) => console.log(intent),
 *   onSpeaking: (speaking) => updateUI(speaking),
 * });
 *
 * await client.start();
 *
 * // Later:
 * await client.speak("Deployment complete");
 * client.stop();
 * ```
 */
export class VoiceClient {
  private config: VoiceClientConfig;
  private state: VoiceClientState = 'idle';

  // Processors
  private vad: VADProcessor | null = null;
  private asr: ASRProcessor | null = null;
  private intent: IntentProcessor | null = null;
  private tts: TTSProcessor | null = null;

  // Audio capture
  private mediaStream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private processor: ScriptProcessorNode | null = null;

  // Speech detection state
  private isSpeaking = false;
  private speechBuffer: Float32Array[] = [];
  private speechStartTime = 0;
  private silenceStartTime = 0;

  // Speculative streaming state
  private lastPartialTime = 0;
  private partialProcessing = false;
  private lastPartialTranscript = '';
  private partialSequence = 0;

  // Conversation memory + barge-in. The edge leg of the same conversation the server records,
  // so "it" and "that one" resolve across whichever side answered the last turn.
  private conversation: Conversation = createConversation();

  constructor(config: VoiceClientConfig = {}) {
    this.config = { ...DEFAULTS, ...config };
  }

  /**
   * Get current client state
   */
  getState(): VoiceClientState {
    return this.state;
  }

  /**
   * Initialize and start listening
   * Downloads models if necessary
   */
  async start(): Promise<void> {
    if (this.state !== 'idle' && this.state !== 'error') {
      throw new Error(`Cannot start from state: ${this.state}`);
    }

    try {
      this.state = 'loading';
      this.log('Loading models...');

      // Initialize all processors in parallel
      await Promise.all([
        this.initVAD(),
        this.initASR(),
        this.initIntent(),
        this.initTTS(),
      ]);

      this.state = 'ready';
      this.log('Models loaded');

      // Request microphone access
      this.log('Requesting microphone access...');
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000,
        },
      });

      // Start audio processing
      await this.startAudioProcessing();

      this.state = 'listening';
      this.log('Listening for speech');

    } catch (error) {
      this.state = 'error';
      this.handleError(error as Error);
      throw error;
    }
  }

  /**
   * Stop listening and clean up
   */
  async stop(): Promise<void> {
    this.log('Stopping...');

    // Stop audio capture
    if (this.processor) {
      this.processor.disconnect();
      this.processor = null;
    }

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
      this.mediaStream = null;
    }

    if (this.audioContext) {
      await this.audioContext.close();
      this.audioContext = null;
    }

    // Dispose processors
    await Promise.all([
      this.vad?.dispose(),
      this.asr?.dispose(),
      this.intent?.dispose(),
      this.tts?.dispose(),
    ]);

    this.vad = null;
    this.asr = null;
    this.intent = null;
    this.tts = null;

    this.state = 'idle';
    this.log('Stopped');
  }

  /**
   * Speak text using TTS
   */
  async speak(text: string, options?: TTSOptions): Promise<void> {
    if (!this.tts) {
      throw new Error('TTS not initialized');
    }

    // A new utterance is a barge-in on whatever was being spoken: the person who speaks first
    // wins, and the previous sentence stops rather than stacking a second voice over it.
    this.conversation.bargeIn();
    this.tts.stopSpeaking();
    this.conversation.clearBargeIn();

    const previousState = this.state;
    this.state = 'speaking';
    this.log(`Speaking: "${text}"`);

    try {
      await this.tts.speak(text, options);
      this.conversation.remember('agent', text);
    } finally {
      this.state = previousState === 'listening' ? 'listening' : 'ready';
    }
  }

  /**
   * Stop speaking immediately (barge-in), without ending the conversation.
   * The current TTS is cancelled; the remembered turns are left intact.
   */
  bargeIn(): void {
    this.conversation.bargeIn();
    this.tts?.stopSpeaking();
    this.conversation.clearBargeIn();
  }

  /**
   * The remembered turns, oldest-first. This is the memory the next answer is prompted with.
   */
  history(): ReturnType<Conversation['history']> {
    return this.conversation.history();
  }

  /**
   * Forget the conversation (keep the models and the microphone running).
   */
  resetConversation(): void {
    this.conversation.reset();
  }

  /**
   * Synthesize text to audio (returns Float32Array)
   */
  async synthesize(text: string, options?: TTSOptions): Promise<Float32Array> {
    if (!this.tts) {
      throw new Error('TTS not initialized');
    }

    return this.tts.synthesize(text, options);
  }

  // --- Private methods ---

  private async initVAD(): Promise<void> {
    this.vad = new VADProcessor(this.config.vadSensitivity);
    await this.vad.init(this.handleModelProgress.bind(this));
  }

  private async initASR(): Promise<void> {
    this.asr = new ASRProcessor();
    await this.asr.init(this.handleModelProgress.bind(this));
  }

  private async initIntent(): Promise<void> {
    this.intent = new IntentProcessor();
    await this.intent.init(this.handleModelProgress.bind(this));
  }

  private async initTTS(): Promise<void> {
    this.tts = new TTSProcessor();
    await this.tts.init(this.handleModelProgress.bind(this));
  }

  private async startAudioProcessing(): Promise<void> {
    if (!this.mediaStream) {
      throw new Error('No media stream');
    }

    // Create audio context
    this.audioContext = new AudioContext({ sampleRate: 16000 });
    const source = this.audioContext.createMediaStreamSource(this.mediaStream);

    // Create script processor for real-time processing
    // Note: ScriptProcessorNode is deprecated but still works everywhere
    // Web Audio Worklet would be better for production
    this.processor = this.audioContext.createScriptProcessor(512, 1, 1);

    this.processor.onaudioprocess = (event) => {
      this.processAudioChunk(event.inputBuffer.getChannelData(0));
    };

    source.connect(this.processor);
    // Connect to destination to keep processing (but muted)
    const gain = this.audioContext.createGain();
    gain.gain.value = 0;
    this.processor.connect(gain);
    gain.connect(this.audioContext.destination);
  }

  private async processAudioChunk(audio: Float32Array): Promise<void> {
    if (!this.vad || this.state !== 'listening') {
      return;
    }

    try {
      // Run VAD
      const vadState = await this.vad.process(new Float32Array(audio));

      const now = Date.now();

      if (vadState.speaking) {
        // Speech detected
        if (!this.isSpeaking) {
          // Speech started
          this.isSpeaking = true;
          this.speechStartTime = now;
          this.speechBuffer = [];
          this.lastPartialTime = now;
          this.lastPartialTranscript = '';
          this.partialSequence = 0;
          this.config.onSpeaking?.(true);
          this.log('Speech started');
        }

        // Accumulate audio
        this.speechBuffer.push(new Float32Array(audio));
        this.silenceStartTime = 0;

        // Speculative streaming: emit partial transcripts every partialInterval ms
        if (this.config.speculativeStreaming && !this.partialProcessing) {
          const timeSinceLastPartial = now - this.lastPartialTime;
          if (timeSinceLastPartial >= this.config.partialInterval!) {
            this.processPartial();
          }
        }

      } else if (this.isSpeaking) {
        // Silence while in speech
        if (this.silenceStartTime === 0) {
          this.silenceStartTime = now;
        }

        // Still accumulate in case speech resumes
        this.speechBuffer.push(new Float32Array(audio));

        // Check if silence is long enough to end utterance
        const silenceDuration = now - this.silenceStartTime;
        const speechDuration = now - this.speechStartTime;

        if (silenceDuration >= this.config.silenceDuration!) {
          // End of utterance
          this.isSpeaking = false;
          this.config.onSpeaking?.(false);
          this.log(`Speech ended (${speechDuration}ms)`);

          // Process if long enough
          if (speechDuration >= this.config.minSpeechDuration!) {
            await this.processUtterance();
          } else {
            this.log('Speech too short, ignoring');
          }

          this.speechBuffer = [];
          this.vad.resetState();
        }
      }
    } catch (error) {
      this.handleError(error as Error);
    }
  }

  /**
   * Process partial audio for speculative streaming.
   * Runs in parallel with speech accumulation.
   */
  private async processPartial(): Promise<void> {
    if (!this.asr || !this.intent || this.speechBuffer.length === 0) {
      return;
    }

    // Guard against concurrent partial processing
    if (this.partialProcessing) {
      return;
    }

    this.partialProcessing = true;
    this.lastPartialTime = Date.now();
    this.partialSequence++;
    const currentSequence = this.partialSequence;

    try {
      // Snapshot the current buffer (don't block accumulation)
      const bufferSnapshot = [...this.speechBuffer];
      const totalLength = bufferSnapshot.reduce((sum, buf) => sum + buf.length, 0);

      // Need minimum audio for meaningful transcription (~200ms at 16kHz = 3200 samples)
      if (totalLength < 3200) {
        return;
      }

      const combined = new Float32Array(totalLength);
      let offset = 0;
      for (const buf of bufferSnapshot) {
        combined.set(buf, offset);
        offset += buf.length;
      }

      // Transcribe partial audio
      this.log(`Partial transcription (seq=${currentSequence})...`);
      const asrResult = await this.asr.transcribe(combined);

      // Skip if speech has ended or a newer partial is being processed
      if (!this.isSpeaking || currentSequence !== this.partialSequence) {
        this.log(`Partial ${currentSequence} stale, discarding`);
        return;
      }

      const transcript = asrResult.text.trim();

      // Only process if transcript has changed
      if (transcript && transcript !== this.lastPartialTranscript) {
        this.lastPartialTranscript = transcript;
        this.log(`Partial transcript: "${transcript}"`);

        // Notify about partial transcript
        this.config.onPartialTranscript?.(transcript);

        // Parse speculative intent
        this.log('Parsing partial intent...');
        const parsedIntent = await this.intent.parse(transcript);

        // Skip if speech has ended or a newer partial is being processed
        if (!this.isSpeaking || currentSequence !== this.partialSequence) {
          this.log(`Partial intent ${currentSequence} stale, discarding`);
          return;
        }

        this.log(`Partial intent: ${parsedIntent.category}/${parsedIntent.action}`);

        // Emit partial intent with partial flag
        this.config.onIntent?.({
          ...parsedIntent,
          partial: true,
        });
      }
    } catch (error) {
      // Log but don't propagate partial processing errors
      this.log('Partial processing error:', error);
    } finally {
      this.partialProcessing = false;
    }
  }

  private async processUtterance(): Promise<void> {
    if (!this.asr || !this.intent || this.speechBuffer.length === 0) {
      return;
    }

    this.state = 'processing';

    try {
      // Combine speech buffer
      const totalLength = this.speechBuffer.reduce((sum, buf) => sum + buf.length, 0);
      const combined = new Float32Array(totalLength);
      let offset = 0;
      for (const buf of this.speechBuffer) {
        combined.set(buf, offset);
        offset += buf.length;
      }

      // Transcribe
      this.log('Transcribing final...');
      const asrResult = await this.asr.transcribe(combined);
      this.log(`Final transcript: "${asrResult.text}"`);

      if (asrResult.text.trim()) {
        // Remember what the person said BEFORE parsing, so the conversation carries it even if
        // intent parsing falls back to keyword matching or fails entirely.
        this.conversation.remember('person', asrResult.text);

        // Parse intent
        this.log('Parsing final intent...');
        const parsedIntent = await this.intent.parse(asrResult.text);
        this.log(`Final intent: ${parsedIntent.category}/${parsedIntent.action}`);

        const finalIntent = {
          ...parsedIntent,
          partial: false,
        };

        // Emit final intent
        this.config.onIntent?.(finalIntent);

        // The 2100 clarification handshake: a final intent whose confidence is below the
        // floor (0.90) is not shipped to the bus -- the consumer is expected to ask the user
        // one targeted question and feed the answer back as the next utterance. This is the
        // floor the spec calls out: "If confidence < 90%, the agent mesh triggers a
        // clarification flow instead of executing."
        //
        // Partials never trigger this -- a partial by definition has not finished, and the
        // next partial is the actual answer.
        if (this.config.onClarificationNeeded && finalIntent.confidence < 0.90) {
          this.log(`Clarification needed (confidence=${finalIntent.confidence.toFixed(2)})`);
          this.config.onClarificationNeeded(finalIntent);
        }
      }
    } catch (error) {
      this.handleError(error as Error);
    } finally {
      this.state = 'listening';
    }
  }

  private handleModelProgress(progress: ModelProgress): void {
    this.config.onModelProgress?.(progress);
  }

  private handleError(error: Error): void {
    console.error('[VoiceClient]', error);
    this.config.onError?.(error);
  }

  private log(...args: unknown[]): void {
    if (this.config.debug) {
      console.log('[VoiceClient]', ...args);
    }
  }
}
