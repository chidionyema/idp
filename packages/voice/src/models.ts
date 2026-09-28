/**
 * Model loading and caching
 *
 * Handles downloading, caching, and loading ONNX models for:
 * - Silero VAD (voice activity detection)
 * - Whisper (speech recognition)
 * - SmolLM2 (intent classification)
 * - Kokoro (text-to-speech)
 */

import type { ModelInfo, ModelProgress } from './types';

/** Model registry with CDN URLs */
const MODEL_REGISTRY: Record<string, ModelInfo> = {
  vad: {
    id: 'vad',
    name: 'Silero VAD',
    size: 1_800_000,  // ~1.8MB
    cached: false,
    url: 'https://cdn.fleetview.ai/models/silero-vad-v4.onnx',
  },
  asr: {
    id: 'asr',
    name: 'Whisper Tiny',
    size: 39_000_000,  // ~39MB
    cached: false,
    url: 'https://cdn.fleetview.ai/models/whisper-tiny-en.onnx',
  },
  intent: {
    id: 'intent',
    name: 'SmolLM2 Intent',
    size: 135_000_000,  // ~135MB
    cached: false,
    url: 'https://cdn.fleetview.ai/models/smollm2-intent-q4.onnx',
  },
  tts: {
    id: 'tts',
    name: 'Kokoro',
    size: 82_000_000,  // ~82MB
    cached: false,
    url: 'https://cdn.fleetview.ai/models/kokoro-v0.19.onnx',
  },
};

/** IndexedDB database name for model cache */
const DB_NAME = 'fleetview-voice-models';
const DB_VERSION = 1;
const STORE_NAME = 'models';

/**
 * Open IndexedDB for model caching
 */
async function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'id' });
      }
    };
  });
}

/**
 * Check if a model is cached
 */
async function isCached(modelId: string): Promise<boolean> {
  try {
    const db = await openDB();
    return new Promise((resolve) => {
      const transaction = db.transaction(STORE_NAME, 'readonly');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.get(modelId);

      request.onsuccess = () => resolve(!!request.result);
      request.onerror = () => resolve(false);
    });
  } catch {
    return false;
  }
}

/**
 * Get cached model data
 */
async function getCached(modelId: string): Promise<ArrayBuffer | null> {
  try {
    const db = await openDB();
    return new Promise((resolve) => {
      const transaction = db.transaction(STORE_NAME, 'readonly');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.get(modelId);

      request.onsuccess = () => {
        const result = request.result;
        resolve(result ? result.data : null);
      };
      request.onerror = () => resolve(null);
    });
  } catch {
    return null;
  }
}

/**
 * Cache model data
 */
async function cacheModel(modelId: string, data: ArrayBuffer): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, 'readwrite');
    const store = transaction.objectStore(STORE_NAME);
    const request = store.put({ id: modelId, data, timestamp: Date.now() });

    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

/**
 * Download a model with progress reporting
 */
async function downloadModel(
  modelId: string,
  onProgress?: (progress: ModelProgress) => void
): Promise<ArrayBuffer> {
  const info = MODEL_REGISTRY[modelId];
  if (!info) {
    throw new Error(`Unknown model: ${modelId}`);
  }

  const response = await fetch(info.url);
  if (!response.ok) {
    throw new Error(`Failed to download ${info.name}: ${response.status}`);
  }

  const contentLength = parseInt(response.headers.get('content-length') || '0', 10);
  const total = contentLength || info.size;

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('Failed to get response reader');
  }

  const chunks: Uint8Array[] = [];
  let loaded = 0;

  while (true) {
    const { done, value } = await reader.read();

    if (done) break;

    chunks.push(value);
    loaded += value.length;

    onProgress?.({
      model: modelId as ModelProgress['model'],
      progress: loaded / total,
      loaded,
      total,
    });
  }

  // Combine chunks into single ArrayBuffer
  const combined = new Uint8Array(loaded);
  let offset = 0;
  for (const chunk of chunks) {
    combined.set(chunk, offset);
    offset += chunk.length;
  }

  return combined.buffer;
}

/**
 * Load a model, downloading if necessary
 */
export async function loadModel(
  modelId: string,
  onProgress?: (progress: ModelProgress) => void
): Promise<ArrayBuffer> {
  // Check cache first
  const cached = await getCached(modelId);
  if (cached) {
    onProgress?.({
      model: modelId as ModelProgress['model'],
      progress: 1,
      loaded: cached.byteLength,
      total: cached.byteLength,
    });
    return cached;
  }

  // Download and cache
  const data = await downloadModel(modelId, onProgress);
  await cacheModel(modelId, data);

  return data;
}

/**
 * Get model info
 */
export function getModelInfo(modelId: string): ModelInfo | undefined {
  return MODEL_REGISTRY[modelId];
}

/**
 * Check cache status for all models
 */
export async function checkCacheStatus(): Promise<Record<string, boolean>> {
  const status: Record<string, boolean> = {};

  for (const modelId of Object.keys(MODEL_REGISTRY)) {
    status[modelId] = await isCached(modelId);
  }

  return status;
}

/**
 * Clear model cache
 */
export async function clearCache(): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, 'readwrite');
    const store = transaction.objectStore(STORE_NAME);
    const request = store.clear();

    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

/**
 * Preload all models
 */
export async function preloadAllModels(
  onProgress?: (progress: ModelProgress) => void
): Promise<void> {
  for (const modelId of ['vad', 'asr', 'intent', 'tts']) {
    await loadModel(modelId, onProgress);
  }
}
