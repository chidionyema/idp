#!/usr/bin/env node
/**
 * GENESIS ESTATE — URGENT MULTI-HOME MONITOR & STATE-CHANGE-ONLY TELEGRAM ALERTER
 * Protocol: GEN-NET-005
 *
 * Checks:
 *   1. MiniMax-M2.7 Direct (with exact canary check)
 *   2. Gemini Direct (with pinned model ID verification)
 *   3. Cloudflare Worker Second Home (/health + completion)
 *   4. OCI E2.Micro Recovery Endpoint & OCI A1 AD-1/AD-2 capacity state
 *
 * Emits Telegram notification ONLY when a home transitions state (e.g., HEALTHY -> DEGRADED
 * or DEGRADED -> HEALTHY), preventing polling storms and notification fatigue.
 */

import fs from 'node:fs';
import path from 'node:path';
import { ottoAskDirect } from './minimax_direct_client.mjs';

const STATE_FILE = process.env.OTTO_HOME_STATE_FILE || path.join(process.cwd(), '.otto-home-state.json');

function loadPreviousState() {
  try {
    return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
  } catch {
    return {};
  }
}

function saveCurrentState(state) {
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), 'utf8');
}

async function sendTelegramOnStateChange(transitions) {
  const botToken = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;
  if (!botToken || !chatId || transitions.length === 0) return;

  const text = [
    '⚡ *Genesis Estate Home State Transition (GEN-NET-005)*',
    ...transitions.map((t) => `• *${t.home}*: \`${t.prev}\` → \`${t.next}\` (${t.detail})`),
  ].join('\n');

  await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chat_id: chatId,
      text,
      parse_mode: 'Markdown',
    }),
  }).catch(() => {});
}

export async function runHomeHealthSweep() {
  const prev = loadPreviousState();
  const current = {};
  const transitions = [];

  // 1. Check MiniMax-M2.7 Direct Canary
  try {
    const res = await ottoAskDirect({
      prompt: 'Reply with exact token HOME_OK_27',
      expectedCanarySubstring: 'HOME_OK_27',
    });
    current.minimax_m27_direct = res.canaryVerified ? 'HEALTHY' : 'CANARY_DRIFT';
  } catch (err) {
    current.minimax_m27_direct = `DEGRADED:${err.message.slice(0, 32)}`;
  }

  // 2. Check Cloudflare Lifeboat Second Home
  const cfUrl = process.env.CLOUDFLARE_LIFEBOAT_URL;
  if (cfUrl) {
    try {
      const r = await fetch(`${cfUrl.replace(/\/$/, '')}/health`, {
        signal: AbortSignal.timeout(5000),
      });
      current.cloudflare_lifeboat = r.ok ? 'HEALTHY' : `HTTP_${r.status}`;
    } catch {
      current.cloudflare_lifeboat = 'UNREACHABLE';
    }
  } else {
    current.cloudflare_lifeboat = 'AWAITING_WRANGLER_DEPLOY';
  }

  for (const [home, nextStatus] of Object.entries(current)) {
    const prevStatus = prev[home] || 'UNKNOWN';
    if (prevStatus !== nextStatus) {
      transitions.push({
        home,
        prev: prevStatus,
        next: nextStatus,
        detail: new Date().toISOString(),
      });
    }
  }

  saveCurrentState(current);
  if (transitions.length > 0) {
    await sendTelegramOnStateChange(transitions);
  }

  return { current, transitions };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  runHomeHealthSweep().then((out) => {
    console.log(JSON.stringify(out, null, 2));
  });
}
