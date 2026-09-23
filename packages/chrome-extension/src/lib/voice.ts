/**
 * FleetView Voice Chrome Extension - WebGPU Whisper Voice Recognition
 *
 * Handles model downloading, caching in IndexedDB, and voice transcription.
 * Uses Transformers.js with WebGPU backend for local inference.
 */

// Model configuration
const MODEL_ID = 'Xenova/whisper-tiny.en';
const MODEL_CACHE_KEY = 'whisper-model';
const DB_NAME = 'fleetview-voice';
const DB_VERSION = 1;
const STORE_NAME = 'models';

// State
let mediaRecorder: MediaRecorder | null = null;
let audioChunks: Blob[] = [];
let transcriptionCallback: ((text: string) => void) | null = null;

// Transformers.js pipeline (loaded lazily)
let pipeline: any = null;

/**
 * Open IndexedDB for model caching.
 */
function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
    };
  });
}

/**
 * Check if model is already downloaded and cached.
 */
export async function isModelLoaded(): Promise<boolean> {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);

    return new Promise((resolve) => {
      const request = store.get(MODEL_CACHE_KEY);
      request.onsuccess = () => resolve(!!request.result);
      request.onerror = () => resolve(false);
    });
  } catch {
    return false;
  }
}

/**
 * Download the Whisper model with progress callback.
 * Caches the model in IndexedDB for offline use.
 */
export async function downloadModel(
  onProgress?: (progress: number) => void
): Promise<void> {
  // Dynamic import to avoid loading transformers.js until needed
  const { pipeline: createPipeline, env } = await import('@xenova/transformers');

  // Configure for WebGPU if available
  env.backends.onnx.wasm.numThreads = 4;

  let lastProgress = 0;

  // Create pipeline with progress tracking
  pipeline = await createPipeline('automatic-speech-recognition', MODEL_ID, {
    progress_callback: (progress: any) => {
      if (progress.status === 'progress' && progress.progress) {
        const progressValue = progress.progress / 100;
        if (progressValue > lastProgress) {
          lastProgress = progressValue;
          onProgress?.(progressValue);
        }
      }
    },
  });

  // Mark as cached
  const db = await openDB();
  const tx = db.transaction(STORE_NAME, 'readwrite');
  const store = tx.objectStore(STORE_NAME);

  await new Promise<void>((resolve, reject) => {
    const request = store.put({ downloaded: true, timestamp: Date.now() }, MODEL_CACHE_KEY);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });

  // Save model info
  await chrome.storage.local.set({
    modelInfo: {
      size: 40 * 1024 * 1024, // ~40MB
      downloadedAt: Date.now(),
    },
  });
}

/**
 * Get current download progress (0-1).
 */
export function getDownloadProgress(): number {
  // Progress is reported via callback
  return 0;
}

/**
 * Initialize voice recognition.
 */
export async function initVoice(): Promise<void> {
  if (!pipeline) {
    const { pipeline: createPipeline } = await import('@xenova/transformers');
    pipeline = await createPipeline('automatic-speech-recognition', MODEL_ID);
  }
}

/**
 * Start listening for voice input.
 */
export async function startListening(
  onTranscript: (text: string) => void
): Promise<void> {
  transcriptionCallback = onTranscript;
  audioChunks = [];

  // Request microphone access
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

  mediaRecorder = new MediaRecorder(stream, {
    mimeType: 'audio/webm;codecs=opus',
  });

  mediaRecorder.ondataavailable = (event) => {
    if (event.data.size > 0) {
      audioChunks.push(event.data);
    }
  };

  mediaRecorder.onstop = async () => {
    // Stop all tracks
    stream.getTracks().forEach((track) => track.stop());

    // Process audio
    if (audioChunks.length > 0) {
      await processAudio();
    }
  };

  // Start recording
  mediaRecorder.start(100); // Collect data every 100ms
}

/**
 * Stop listening and process the audio.
 */
export async function stopListening(): Promise<void> {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
}

/**
 * Process recorded audio and transcribe.
 */
async function processAudio(): Promise<void> {
  if (!pipeline) {
    await initVoice();
  }

  // Combine audio chunks
  const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });

  // Convert to ArrayBuffer
  const arrayBuffer = await audioBlob.arrayBuffer();

  // Decode audio
  const audioContext = new AudioContext({ sampleRate: 16000 });
  const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

  // Get audio data as Float32Array
  const audioData = audioBuffer.getChannelData(0);

  // Transcribe
  const result = await pipeline(audioData, {
    chunk_length_s: 30,
    stride_length_s: 5,
    language: 'english',
    task: 'transcribe',
  });

  // Call callback with transcript
  if (transcriptionCallback && result.text) {
    transcriptionCallback(result.text.trim());
  }
}
