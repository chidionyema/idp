/**
 * Standalone Genesis Ingest Receiver Daemon (runnable on idp / otto.mumchimp.com host).
 * Receives AI Studio binary bundles on POST /api/ingest/bundle, verifies X-Bundle-Sha256,
 * validates the git bundle DAG, wakes an idle agent session (or spawns a new one),
 * and exposes live session telemetry on GET /api/ingest/sessions.
 */

import http from 'node:http';
import path from 'node:path';
import os from 'node:os';
import {
  createIngestReceiverState,
  handleIngestBundleRequest,
} from '../src/engine/ingestReceiver';

const RECEIVER_PORT = Number(process.env.PORT) || 8089;
const STAGING_DIR = path.join(os.tmpdir(), 'genesis-ingest-staging');
const state = createIngestReceiverState();

const server = http.createServer(async (req, res) => {
  const url = req.url ?? '/';

  if (req.method === 'GET' && url === '/api/ingest/sessions') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(
      JSON.stringify({
        acceptedCount: state.acceptedCount,
        rejectedCount: state.rejectedCount,
        activeSessions: Array.from(state.sessionsByWorkerId.values()),
        recentWakeEvents: state.wakeEvents.slice(0, 25),
      })
    );
    return;
  }

  if (req.method === 'POST' && url === '/api/ingest/bundle') {
    const chunks: Buffer[] = [];
    let totalBytes = 0;
    const MAX_BYTES = 25 * 1024 * 1024;

    req.on('data', (chunk: Buffer) => {
      totalBytes += chunk.byteLength;
      if (totalBytes <= MAX_BYTES) {
        chunks.push(chunk);
      }
    });

    req.on('end', async () => {
      if (totalBytes > MAX_BYTES) {
        res.writeHead(413, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ accepted: false, error: 'bundle_exceeds_25mb_cap' }));
        return;
      }
      const rawBody = Buffer.concat(chunks);
      const remotesHeader = String(req.headers['x-target-remotes'] ?? '');
      const result = await handleIngestBundleRequest({
        bodyBytes: rawBody,
        claimedSha256: String(req.headers['x-bundle-sha256'] ?? ''),
        sessionId: String(req.headers['x-estate-session-id'] ?? 'aistudio-default'),
        wakePolicy: String(req.headers['x-wake-policy'] ?? 'wake_idle_or_spawn_new'),
        wakeAgent: String(req.headers['x-wake-agent'] ?? 'pennyd-sync-reconciler'),
        appUrl: String(req.headers['x-app-url'] ?? 'aistudio-container'),
        targetRef: String(req.headers['x-bundle-ref'] ?? 'refs/heads/aistudio/meridian-hermes-live'),
        headSha: String(req.headers['x-bundle-head-sha'] ?? ''),
        targetRemotes: remotesHeader ? remotesHeader.split(',').map((s) => s.trim()) : undefined,
        stagingDir: STAGING_DIR,
        state,
      });

      res.writeHead(result.httpStatus, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(result));
    });
    return;
  }

  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'not_found' }));
});

server.listen(RECEIVER_PORT, '0.0.0.0', () => {
  console.log(`Genesis Ingest Receiver listening on http://0.0.0.0:${RECEIVER_PORT}`);
});
