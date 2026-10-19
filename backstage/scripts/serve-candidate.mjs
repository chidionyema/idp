#!/usr/bin/env node
/*
 * serve-candidate.mjs — the phone e2e grades THE CANDIDATE, not production.
 *
 * WHY. portal-app.yml's phone step used to run Playwright against
 * PLAYWRIGHT_URL=https://catalogue.mumchimp.com — the DEPLOYED app. A lane that changes
 * backstage/ was therefore graded by the app that does not contain the change yet: the
 * gate could only pass on yesterday's code, and the face-voice defect (idp#6577) made
 * every portal-touching lane red forever (measured 2026-10-19: b3186..b3208, lanes
 * agent-attribution, face-csp-worker-media and safari-csp-mic all red on the same
 * production-only failure). A candidate is served here instead: this process serves the
 * freshly built dist/ and forwards the backend doors (/api, /voice) to the live estate,
 * so the phone drives the code under test with the real backend behind it.
 *
 * Node stdlib only: this runs on the CI runner with no extra install.
 *
 *   UPSTREAM=https://catalogue.mumchimp.com PORT=4173 DIST=packages/app/dist node scripts/serve-candidate.mjs
 */
import http from 'node:http';
import https from 'node:https';
import { readFile, stat } from 'node:fs/promises';
import { extname, join, normalize, resolve } from 'node:path';

const PORT = Number(process.env.PORT ?? 4173);
const DIST = resolve(process.env.DIST ?? 'packages/app/dist');
const UPSTREAM = process.env.UPSTREAM ?? 'https://catalogue.mumchimp.com';
const up = new URL(UPSTREAM);

// The SPA pages (/fleet, /face) have no file on disk; everything with an extension does.
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.glb': 'model/gltf-binary',
  '.mjs': 'text/javascript',
  '.wasm': 'application/wasm',
  '.map': 'application/json',
  '.woff2': 'font/woff2',
  '.mp3': 'audio/mpeg',
};

async function serveStatic(req, res) {
  let path = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  path = normalize(path).replace(/^(\.\.[/\\])+/, '');
  let file = join(DIST, path);
  try {
    const st = await stat(file);
    if (st.isDirectory()) file = join(file, 'index.html');
    await stat(file);
  } catch {
    if (extname(path)) {
      res.writeHead(404).end('not found');
      return;
    }
    file = join(DIST, 'index.html'); // SPA fallback: /fleet, /face, /...
  }
  try {
    const body = await readFile(file);
    res.writeHead(200, {
      'content-type': MIME[extname(file)] ?? 'application/octet-stream',
      'cache-control': 'no-store',
    });
    res.end(body);
  } catch {
    res.writeHead(404).end('not found');
  }
}

// /api and /voice are the backend doors. The candidate's frontend must meet the real
// backend, or "a spoken question is heard and answered" proves nothing. Forward the
// request untouched (method, headers, streaming body) and stream the answer back,
// cookies included, so the guest sign-in flow works on this origin.
const PROXIED = /^\/(api|voice)\//;

function forward(req, res) {
  const options = {
    protocol: up.protocol,
    hostname: up.hostname,
    port: up.port || (up.protocol === 'https:' ? 443 : 80),
    path: req.url,
    method: req.method,
    headers: { ...req.headers, host: up.host },
  };
  const lib = up.protocol === 'https:' ? https : http;
  const ureq = lib.request(options, ures => {
    res.writeHead(ures.statusCode ?? 502, ures.headers);
    ures.pipe(res);
  });
  ureq.on('error', () => {
    res.writeHead(502).end('upstream unreachable');
  });
  req.pipe(ureq);
}

const server = http.createServer((req, res) =>
  PROXIED.test(req.url ?? '') ? forward(req, res) : serveStatic(req, res),
);

// The voice router opens /voice/ws. Pipe the upgrade both ways; without it the page
// still runs its HTTP turn flow, but a dead socket on load is noise the tests read.
server.on('upgrade', (req, socket, head) => {
  const lib = up.protocol === 'https:' ? https : http;
  const ureq = lib.request({
    hostname: up.hostname,
    port: up.port || (up.protocol === 'https:' ? 443 : 80),
    path: req.url,
    method: req.method,
    headers: { ...req.headers, host: up.host },
  });
  ureq.on('upgrade', (ures, usocket, uhead) => {
    const lines = [`HTTP/1.1 101 Switching Protocols`];
    for (const [k, v] of Object.entries(ures.headers)) lines.push(`${k}: ${v}`);
    socket.write(lines.join('\r\n') + '\r\n\r\n');
    if (uhead?.length) usocket.unshift(uhead);
    usocket.pipe(socket);
    socket.pipe(usocket);
  });
  ureq.on('response', ures => {
    // upstream refused the upgrade: answer and close, the page retries on its own
    const lines = [`HTTP/1.1 ${ures.statusCode} ${ures.statusMessage}`];
    for (const [k, v] of Object.entries(ures.headers)) lines.push(`${k}: ${v}`);
    socket.end(lines.join('\r\n') + '\r\n\r\n');
  });
  ureq.on('error', () => socket.destroy());
  ureq.end();
});

server.listen(PORT, () => {
  console.log(`candidate served on http://localhost:${PORT} (dist=${DIST}, upstream=${UPSTREAM})`);
});
