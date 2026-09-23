/**
 * FleetView Voice Chrome Extension - Options Page
 *
 * Settings for webhook URL, voice config, and model management.
 */

interface Settings {
  webhookUrl: string;
  webhookTimeout: number;
  autoPunctuation: boolean;
  continuousMode: boolean;
  language: string;
}

const DEFAULT_SETTINGS: Settings = {
  webhookUrl: 'http://localhost:3000/voice/intent',
  webhookTimeout: 5000,
  autoPunctuation: true,
  continuousMode: false,
  language: 'en',
};

// DOM Elements
const webhookUrl = document.getElementById('webhook-url') as HTMLInputElement;
const webhookTimeout = document.getElementById('webhook-timeout') as HTMLInputElement;
const autoPunctuation = document.getElementById('auto-punctuation') as HTMLInputElement;
const continuousMode = document.getElementById('continuous-mode') as HTMLInputElement;
const language = document.getElementById('language') as HTMLInputElement;
const modelInfo = document.getElementById('model-info')!;
const clearModelBtn = document.getElementById('clear-model')!;
const saveBtn = document.getElementById('save-btn')!;
const testWebhookBtn = document.getElementById('test-webhook')!;
const status = document.getElementById('status')!;

// Load settings on page load
async function loadSettings() {
  const result = await chrome.storage.local.get('settings');
  const settings: Settings = result.settings || DEFAULT_SETTINGS;

  webhookUrl.value = settings.webhookUrl;
  webhookTimeout.value = settings.webhookTimeout.toString();
  autoPunctuation.checked = settings.autoPunctuation;
  continuousMode.checked = settings.continuousMode;
  language.value = settings.language;

  await loadModelInfo();
}

async function loadModelInfo() {
  const result = await chrome.storage.local.get('modelInfo');

  if (result.modelInfo) {
    const { size, downloadedAt } = result.modelInfo;
    const sizeInMB = (size / 1024 / 1024).toFixed(1);
    const date = new Date(downloadedAt).toLocaleDateString();
    modelInfo.textContent = `Whisper model: ${sizeInMB}MB, downloaded ${date}`;
  } else {
    modelInfo.textContent = 'No model downloaded';
  }
}

async function saveSettings() {
  // Validate webhook URL
  const url = webhookUrl.value.trim();
  if (!url.startsWith('http://localhost') && !url.startsWith('http://127.0.0.1')) {
    showStatus('Webhook URL must be localhost for security', 'error');
    return;
  }

  const settings: Settings = {
    webhookUrl: url,
    webhookTimeout: parseInt(webhookTimeout.value) || 5000,
    autoPunctuation: autoPunctuation.checked,
    continuousMode: continuousMode.checked,
    language: language.value.trim() || 'en',
  };

  await chrome.storage.local.set({ settings });
  showStatus('Settings saved', 'success');
}

async function testWebhook() {
  const url = webhookUrl.value.trim();

  if (!url) {
    showStatus('Please enter a webhook URL', 'error');
    return;
  }

  try {
    const testIntent = {
      type: 'voice_intent',
      action: 'test',
      target: 'webhook',
      env: 'test',
      confidence: 1.0,
      transcript: 'Test webhook connection',
      author: 'settings-test',
      timestamp: new Date().toISOString(),
    };

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(testIntent),
    });

    if (response.ok) {
      showStatus('Webhook test successful!', 'success');
    } else {
      showStatus(`Webhook returned ${response.status}`, 'error');
    }
  } catch (err) {
    showStatus('Could not connect to webhook. Is your local server running?', 'error');
  }
}

async function clearModel() {
  if (!confirm('This will clear the downloaded voice model. You will need to download it again.')) {
    return;
  }

  // Clear from IndexedDB
  try {
    const db = await openModelDB();
    const tx = db.transaction('models', 'readwrite');
    await tx.objectStore('models').clear();
    await chrome.storage.local.remove('modelInfo');
    modelInfo.textContent = 'No model downloaded';
    showStatus('Model cache cleared', 'success');
  } catch (err) {
    showStatus('Failed to clear model cache', 'error');
  }
}

function openModelDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('fleetview-voice', 1);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
  });
}

function showStatus(message: string, type: 'success' | 'error') {
  status.textContent = message;
  status.className = `status ${type}`;
  status.classList.remove('hidden');

  setTimeout(() => {
    status.classList.add('hidden');
  }, 3000);
}

// Event listeners
saveBtn.addEventListener('click', saveSettings);
testWebhookBtn.addEventListener('click', testWebhook);
clearModelBtn.addEventListener('click', clearModel);

// Initialize
loadSettings();
