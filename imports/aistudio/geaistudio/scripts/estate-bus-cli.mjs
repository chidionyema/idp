#!/usr/bin/env node
/**
 * Zero-Dependency Meridian OMNIFLOW Console & Agent Bridge CLI
 * Works in any terminal (Mac, Linux, GitHub Actions, OpenCode/Argon/GLM consoles).
 *
 * Usage:
 *   node scripts/estate-bus-cli.mjs probe --url https://estate-bus.mumchimp.com/health
 *   node scripts/estate-bus-cli.mjs listen --bus http://localhost:3000 --agent glm-console-01 --caps code:patch,idp
 *   node scripts/estate-bus-cli.mjs send --bus http://localhost:3000 --from glm-console-01 --to @all --verb ASK --text "Need KARMA review"
 *   node scripts/estate-bus-cli.mjs claim --bus http://localhost:3000 --agent glm-console-01 --envelope MSG-0002
 *   node scripts/estate-bus-cli.mjs verify --bus http://localhost:3000 --agent karma-verifier --envelope MSG-0002 --note "200 OK verified"
 */

const args = process.argv.slice(2);
const command = args[0] || 'help';

function flag(name, fallback = '') {
  const idx = args.indexOf(`--${name}`);
  if (idx !== -1 && args[idx + 1] && !args[idx + 1].startsWith('--')) {
    return args[idx + 1];
  }
  return fallback;
}

const busUrl = flag('bus', 'http://localhost:3000').replace(/\/+$/, '');
const token = flag('token', '');
const prefix = busUrl.includes('estate-bus.') ? '/v1/bus' : '/api/omniflow';

function headers() {
  const h = { 'Content-Type': 'application/json' };
  if (token) h['X-Omniflow-Token'] = token;
  return h;
}

async function runProbe() {
  const url = flag('url', 'https://estate-bus.mumchimp.com/health');
  const res = await fetch(`${busUrl}/api/omniflow/probe-external`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ url }),
  }).catch(() => null);
  if (res && res.ok) {
    console.log(JSON.stringify(await res.json(), null, 2));
    return;
  }
  const direct = await fetch(url, { signal: AbortSignal.timeout(5000) });
  console.log(JSON.stringify({ url, httpStatus: direct.status, ok: direct.ok }, null, 2));
}

async function runSend() {
  const fromAgent = flag('from', 'console-cli-worker');
  const target = flag('to', '@all');
  const verb = flag('verb', 'ASK');
  const body = flag('text', '');
  if (!body) {
    console.error('Missing --text "..."');
    process.exit(1);
  }
  const res = await fetch(`${busUrl}${prefix}/publish`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({
      fromAgent,
      fromSurface: 'CONSOLE_CLI',
      target,
      verb,
      body,
      requiresClaim: verb === 'ASK' || verb === 'OFFER',
    }),
  });
  console.log(JSON.stringify(await res.json(), null, 2));
}

async function runClaim() {
  const agent = flag('agent', 'console-cli-worker');
  const envelopeId = flag('envelope', '');
  const res = await fetch(`${busUrl}${prefix}/lease`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ action: 'CLAIM', envelopeId, workerId: agent }),
  });
  console.log(JSON.stringify(await res.json(), null, 2));
}

async function runVerify() {
  const agent = flag('agent', 'karma-cli-verifier');
  const envelopeId = flag('envelope', '');
  const note = flag('note', 'Verified externally via estate-bus-cli');
  const res = await fetch(`${busUrl}${prefix}/lease`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({
      action: 'VERIFY_EFFECT',
      envelopeId,
      verifierId: agent,
      evidenceNote: note,
    }),
  });
  console.log(JSON.stringify(await res.json(), null, 2));
}

async function runListen() {
  const agentId = flag('agent', `cli-${process.pid}`);
  const caps = flag('caps', 'code:patch,idp')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);

  await fetch(`${busUrl}${prefix}/register`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({
      agentId,
      displayName: `${agentId} (Console Bridge)`,
      surfaceClass: 'CONSOLE_CLI',
      transport: 'CLI_BRIDGE',
      capabilities: caps,
      ttlMs: 30_000,
    }),
  });
  console.error(`[omniflow] Registered ${agentId} on ${busUrl}; streaming live SSE...`);

  const hb = setInterval(() => {
    fetch(`${busUrl}${prefix}/heartbeat`, {
      method: 'POST',
      headers: headers(),
      body: JSON.stringify({ agentId }),
    }).catch(() => {});
  }, 15_000);

  const shutdown = async () => {
    clearInterval(hb);
    await fetch(`${busUrl}${prefix}/disconnect`, {
      method: 'POST',
      headers: headers(),
      body: JSON.stringify({ agentId }),
    }).catch(() => {});
    process.exit(0);
  };
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);

  const res = await fetch(`${busUrl}${prefix}/stream`, { headers: headers() });
  if (!res.ok || !res.body) {
    console.error(`[omniflow] Failed to open SSE stream: HTTP ${res.status}`);
    process.exit(1);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  let lastSeenSeq = 0;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const frames = buf.split('\n\n');
    buf = frames.pop() ?? '';
    for (const frame of frames) {
      const dataLine = frame
        .split('\n')
        .find((l) => l.startsWith('data: '));
      if (!dataLine) continue;
      try {
        const snap = JSON.parse(dataLine.slice(6));
        const msgs = Array.isArray(snap.messages) ? snap.messages : [snap];
        for (const m of [...msgs].reverse()) {
          if (m.seq && m.seq > lastSeenSeq) {
            lastSeenSeq = m.seq;
            console.log(
              `[${m.envelopeId}] ${m.fromAgent} -> ${m.target} (${m.verb} | ${m.custodyStage}${
                m.fencingToken ? ` f_${m.fencingToken}` : ''
              }): ${m.body}`
            );
          }
        }
      } catch {
        // Ignore keepalive frames
      }
    }
  }
}

async function runValidate() {
  const rawFiles = flag('files', '');
  const files = rawFiles
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
  const res = await fetch(`${busUrl}/api/omniflow/validate-manifest`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({ proposedFiles: files }),
  });
  const json = await res.json();
  console.log(JSON.stringify(json, null, 2));
  if (!res.ok || !json.boundaryValid) {
    process.exit(2);
  }
}

if (command === 'probe') await runProbe();
else if (command === 'send') await runSend();
else if (command === 'claim') await runClaim();
else if (command === 'verify') await runVerify();
else if (command === 'validate') await runValidate();
else if (command === 'listen') await runListen();
else {
  console.log('Commands: probe | validate | listen | send | claim | verify');
}
