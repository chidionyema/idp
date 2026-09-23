/**
 * FleetView Voice Chrome Extension - Popup UI
 *
 * Handles login, model download, and voice control UI.
 */

import { getAuthToken, getUserInfo, logout, isAuthenticated } from '../lib/auth';
import { initVoice, startListening, stopListening, isModelLoaded, downloadModel, getDownloadProgress } from '../lib/voice';
import { sendToWebhook, parseIntent } from '../lib/webhook';

// DOM Elements
const loginSection = document.getElementById('login-section')!;
const modelSection = document.getElementById('model-section')!;
const voiceSection = document.getElementById('voice-section')!;
const userInfo = document.getElementById('user-info')!;
const userEmail = document.getElementById('user-email')!;
const googleLoginBtn = document.getElementById('google-login')!;
const logoutBtn = document.getElementById('logout-btn')!;
const modelStatusText = document.getElementById('model-status-text')!;
const progressContainer = document.getElementById('progress-container')!;
const progressBar = document.getElementById('progress-bar')! as HTMLDivElement;
const progressText = document.getElementById('progress-text')!;
const downloadModelBtn = document.getElementById('download-model')!;
const listenBtn = document.getElementById('listen-btn')!;
const listenText = document.getElementById('listen-text')!;
const transcriptContainer = document.getElementById('transcript-container')!;
const transcript = document.getElementById('transcript')!;
const intentContainer = document.getElementById('intent-container')!;
const intent = document.getElementById('intent')!;
const webhookStatus = document.getElementById('webhook-status')!;
const webhookStatusText = document.getElementById('webhook-status-text')!;
const optionsLink = document.getElementById('options-link')!;

let isListening = false;
let currentUser: { email: string } | null = null;

// Initialize popup
async function init() {
  // Check authentication
  const authenticated = await isAuthenticated();

  if (authenticated) {
    currentUser = await getUserInfo();
    showAuthenticatedUI();
    await checkModelStatus();
  } else {
    showLoginUI();
  }

  setupEventListeners();
}

function showLoginUI() {
  loginSection.classList.remove('hidden');
  modelSection.classList.add('hidden');
  voiceSection.classList.add('hidden');
  userInfo.classList.add('hidden');
}

function showAuthenticatedUI() {
  loginSection.classList.add('hidden');
  userInfo.classList.remove('hidden');
  userEmail.textContent = currentUser?.email || 'User';
}

async function checkModelStatus() {
  modelSection.classList.remove('hidden');

  const loaded = await isModelLoaded();

  if (loaded) {
    modelStatusText.textContent = 'Voice model ready';
    modelStatusText.style.color = 'var(--success)';
    downloadModelBtn.classList.add('hidden');
    voiceSection.classList.remove('hidden');
  } else {
    modelStatusText.textContent = 'Voice model not downloaded';
    downloadModelBtn.classList.remove('hidden');
    voiceSection.classList.add('hidden');
  }
}

function setupEventListeners() {
  // Google login
  googleLoginBtn.addEventListener('click', async () => {
    try {
      googleLoginBtn.textContent = 'Signing in...';
      await getAuthToken();
      currentUser = await getUserInfo();
      showAuthenticatedUI();
      await checkModelStatus();
    } catch (err) {
      console.error('Login failed:', err);
      googleLoginBtn.textContent = 'Sign in with Google';
      alert('Login failed. Please try again.');
    }
  });

  // Logout
  logoutBtn.addEventListener('click', async () => {
    await logout();
    currentUser = null;
    showLoginUI();
  });

  // Download model
  downloadModelBtn.addEventListener('click', async () => {
    downloadModelBtn.classList.add('hidden');
    progressContainer.classList.remove('hidden');
    progressText.classList.remove('hidden');
    modelStatusText.textContent = 'Downloading voice model...';

    try {
      await downloadModel((progress) => {
        const percent = Math.round(progress * 100);
        progressBar.style.width = `${percent}%`;
        progressText.textContent = `${percent}%`;
      });

      modelStatusText.textContent = 'Voice model ready';
      modelStatusText.style.color = 'var(--success)';
      progressContainer.classList.add('hidden');
      progressText.classList.add('hidden');
      voiceSection.classList.remove('hidden');
    } catch (err) {
      console.error('Model download failed:', err);
      modelStatusText.textContent = 'Download failed';
      modelStatusText.style.color = 'var(--error)';
      downloadModelBtn.classList.remove('hidden');
      progressContainer.classList.add('hidden');
      progressText.classList.add('hidden');
    }
  });

  // Listen button
  listenBtn.addEventListener('click', async () => {
    if (isListening) {
      await stopRecording();
    } else {
      await startRecording();
    }
  });

  // Options link
  optionsLink.addEventListener('click', (e) => {
    e.preventDefault();
    chrome.runtime.openOptionsPage();
  });
}

async function startRecording() {
  isListening = true;
  listenBtn.classList.add('listening');
  listenText.textContent = 'Listening...';
  transcriptContainer.classList.add('hidden');
  intentContainer.classList.add('hidden');
  webhookStatus.classList.add('hidden');

  try {
    await startListening(async (text) => {
      // Got transcript
      transcript.textContent = text;
      transcriptContainer.classList.remove('hidden');

      // Parse intent
      const intentData = parseIntent(text, currentUser?.email || 'unknown');
      intent.textContent = JSON.stringify(intentData, null, 2);
      intentContainer.classList.remove('hidden');

      // Send to webhook
      try {
        await sendToWebhook(intentData);
        webhookStatus.classList.remove('hidden', 'error');
        webhookStatus.classList.add('success');
        webhookStatusText.textContent = 'Sent to local agent';
      } catch (err) {
        webhookStatus.classList.remove('hidden', 'success');
        webhookStatus.classList.add('error');
        webhookStatusText.textContent = 'Webhook failed - check settings';
      }

      // Stop listening after getting transcript
      await stopRecording();
    });
  } catch (err) {
    console.error('Recording failed:', err);
    await stopRecording();
    alert('Could not access microphone. Please check permissions.');
  }
}

async function stopRecording() {
  isListening = false;
  listenBtn.classList.remove('listening');
  listenText.textContent = 'Start Listening';
  await stopListening();
}

// Start
init();
