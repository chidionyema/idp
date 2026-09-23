/**
 * FleetView Voice Chrome Extension - Background Service Worker
 *
 * Manages extension lifecycle, OAuth tokens, and model loading state.
 */

// Extension installation
chrome.runtime.onInstalled.addListener(async (details) => {
  if (details.reason === 'install') {
    console.log('FleetView Voice extension installed');

    // Set default settings
    await chrome.storage.local.set({
      settings: {
        webhookUrl: 'http://localhost:3000/voice/intent',
        webhookTimeout: 5000,
        autoPunctuation: true,
        continuousMode: false,
        language: 'en',
      },
    });
  }
});

// Handle messages from popup/content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'GET_AUTH_STATUS') {
    chrome.identity.getAuthToken({ interactive: false }, (token) => {
      sendResponse({ authenticated: !!token && !chrome.runtime.lastError });
    });
    return true; // Keep channel open for async response
  }

  if (message.type === 'GET_MODEL_STATUS') {
    // Check IndexedDB for model
    checkModelCached().then((cached) => {
      sendResponse({ cached });
    });
    return true;
  }

  if (message.type === 'SEND_INTENT') {
    // Forward intent to webhook
    sendIntentToWebhook(message.intent).then((result) => {
      sendResponse(result);
    });
    return true;
  }
});

/**
 * Check if model is cached in IndexedDB.
 */
async function checkModelCached(): Promise<boolean> {
  return new Promise((resolve) => {
    const request = indexedDB.open('fleetview-voice', 1);

    request.onerror = () => resolve(false);

    request.onsuccess = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains('models')) {
        resolve(false);
        return;
      }

      const tx = db.transaction('models', 'readonly');
      const store = tx.objectStore('models');
      const getRequest = store.get('whisper-model');

      getRequest.onsuccess = () => resolve(!!getRequest.result);
      getRequest.onerror = () => resolve(false);
    };

    request.onupgradeneeded = () => {
      // DB doesn't exist or needs upgrade
      resolve(false);
    };
  });
}

/**
 * Send intent to configured webhook.
 */
async function sendIntentToWebhook(intent: any): Promise<{ success: boolean; error?: string }> {
  try {
    const result = await chrome.storage.local.get('settings');
    const webhookUrl = result.settings?.webhookUrl || 'http://localhost:3000/voice/intent';
    const timeout = result.settings?.webhookTimeout || 5000;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    const response = await fetch(webhookUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(intent),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      return { success: false, error: `HTTP ${response.status}` };
    }

    return { success: true };
  } catch (err: any) {
    return { success: false, error: err.message };
  }
}

// Keep service worker alive during voice operations
let keepAliveInterval: ReturnType<typeof setInterval> | null = null;

chrome.runtime.onConnect.addListener((port) => {
  if (port.name === 'voice-session') {
    // Start keep-alive ping
    keepAliveInterval = setInterval(() => {
      port.postMessage({ type: 'ping' });
    }, 20000);

    port.onDisconnect.addListener(() => {
      if (keepAliveInterval) {
        clearInterval(keepAliveInterval);
        keepAliveInterval = null;
      }
    });
  }
});

console.log('FleetView Voice service worker started');
