/**
 * FleetView Voice Chrome Extension - Local Webhook Dispatch
 *
 * Parses voice transcripts into intents and sends them to localhost.
 */

export interface VoiceIntent {
  type: 'voice_intent';
  action: string;
  target: string;
  env: string;
  confidence: number;
  transcript: string;
  author: string;
  timestamp: string;
}

interface Settings {
  webhookUrl: string;
  webhookTimeout: number;
}

const DEFAULT_WEBHOOK_URL = 'http://localhost:3000/voice/intent';
const DEFAULT_TIMEOUT = 5000;

// Action patterns for intent parsing
const ACTION_PATTERNS: Record<string, RegExp[]> = {
  deploy: [
    /deploy\s+(\w+)\s+to\s+(\w+)/i,
    /push\s+(\w+)\s+to\s+(\w+)/i,
    /release\s+(\w+)\s+to\s+(\w+)/i,
  ],
  rollback: [
    /rollback\s+(\w+)\s+(?:in|on|to)?\s*(\w+)?/i,
    /revert\s+(\w+)\s+(?:in|on|to)?\s*(\w+)?/i,
  ],
  scale: [
    /scale\s+(\w+)\s+to\s+(\d+)/i,
    /set\s+(\w+)\s+replicas?\s+to\s+(\d+)/i,
  ],
  restart: [
    /restart\s+(\w+)\s*(?:in|on)?\s*(\w+)?/i,
    /bounce\s+(\w+)\s*(?:in|on)?\s*(\w+)?/i,
  ],
  status: [
    /(?:what(?:'s|is)\s+the\s+)?status\s+(?:of\s+)?(\w+)\s*(?:in|on)?\s*(\w+)?/i,
    /(?:how(?:'s|is)\s+)?(\w+)\s+doing\s*(?:in|on)?\s*(\w+)?/i,
    /check\s+(\w+)\s*(?:in|on)?\s*(\w+)?/i,
  ],
  logs: [
    /(?:show|get)\s+logs?\s+(?:for\s+)?(\w+)\s*(?:in|on)?\s*(\w+)?/i,
    /(\w+)\s+logs?\s*(?:in|on)?\s*(\w+)?/i,
  ],
  stop: [
    /stop\s+(\w+)\s*(?:in|on)?\s*(\w+)?/i,
    /shutdown\s+(\w+)\s*(?:in|on)?\s*(\w+)?/i,
  ],
  start: [
    /start\s+(\w+)\s*(?:in|on)?\s*(\w+)?/i,
    /launch\s+(\w+)\s*(?:in|on)?\s*(\w+)?/i,
  ],
};

// Environment aliases
const ENV_ALIASES: Record<string, string> = {
  production: 'prod',
  prod: 'prod',
  staging: 'staging',
  stage: 'staging',
  development: 'dev',
  dev: 'dev',
  local: 'local',
};

/**
 * Parse a voice transcript into a structured intent.
 */
export function parseIntent(transcript: string, author: string): VoiceIntent {
  const normalizedTranscript = transcript.toLowerCase().trim();

  let action = 'unknown';
  let target = 'unknown';
  let env = 'unknown';
  let confidence = 0.5;

  // Try to match action patterns
  for (const [actionName, patterns] of Object.entries(ACTION_PATTERNS)) {
    for (const pattern of patterns) {
      const match = normalizedTranscript.match(pattern);
      if (match) {
        action = actionName;
        target = match[1] || 'unknown';
        env = normalizeEnv(match[2]) || 'unknown';
        confidence = 0.95;
        break;
      }
    }
    if (action !== 'unknown') break;
  }

  // If no pattern matched, try keyword extraction
  if (action === 'unknown') {
    const result = extractKeywords(normalizedTranscript);
    action = result.action;
    target = result.target;
    env = result.env;
    confidence = result.confidence;
  }

  return {
    type: 'voice_intent',
    action,
    target,
    env,
    confidence,
    transcript,
    author,
    timestamp: new Date().toISOString(),
  };
}

/**
 * Normalize environment name using aliases.
 */
function normalizeEnv(env: string | undefined): string {
  if (!env) return '';
  const normalized = env.toLowerCase().trim();
  return ENV_ALIASES[normalized] || normalized;
}

/**
 * Extract keywords when no pattern matches.
 */
function extractKeywords(transcript: string): {
  action: string;
  target: string;
  env: string;
  confidence: number;
} {
  const words = transcript.split(/\s+/);

  // Known action words
  const actionWords = ['deploy', 'rollback', 'scale', 'restart', 'status', 'logs', 'stop', 'start', 'check'];
  const envWords = Object.keys(ENV_ALIASES);

  let action = 'unknown';
  let target = 'unknown';
  let env = 'unknown';

  for (let i = 0; i < words.length; i++) {
    const word = words[i];

    // Check for action
    if (actionWords.includes(word) && action === 'unknown') {
      action = word === 'check' ? 'status' : word;
      // Next word might be target
      if (i + 1 < words.length && !actionWords.includes(words[i + 1]) && !envWords.includes(words[i + 1])) {
        target = words[i + 1];
      }
    }

    // Check for environment
    if (envWords.includes(word)) {
      env = normalizeEnv(word);
    }
  }

  return {
    action,
    target,
    env,
    confidence: action !== 'unknown' ? 0.7 : 0.3,
  };
}

/**
 * Get webhook settings from storage.
 */
async function getSettings(): Promise<Settings> {
  const result = await chrome.storage.local.get('settings');
  return {
    webhookUrl: result.settings?.webhookUrl || DEFAULT_WEBHOOK_URL,
    webhookTimeout: result.settings?.webhookTimeout || DEFAULT_TIMEOUT,
  };
}

/**
 * Send intent to the local webhook.
 */
export async function sendToWebhook(intent: VoiceIntent): Promise<Response> {
  const { webhookUrl, webhookTimeout } = await getSettings();

  // Validate URL is localhost
  if (!webhookUrl.startsWith('http://localhost') && !webhookUrl.startsWith('http://127.0.0.1')) {
    throw new Error('Webhook URL must be localhost for security');
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), webhookTimeout);

  try {
    const response = await fetch(webhookUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(intent),
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`Webhook returned ${response.status}`);
    }

    return response;
  } finally {
    clearTimeout(timeoutId);
  }
}
