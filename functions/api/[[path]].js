import { cloudState, json } from '../_lib/cloud-state.js';

function streamState(env) {
  const encoder = new TextEncoder();
  const state = cloudState(env);
  let timer;
  const body = new ReadableStream({
    start(controller) {
      controller.enqueue(
        encoder.encode(`event: state\ndata: ${JSON.stringify(state)}\n\n`)
      );
      timer = setInterval(() => {
        controller.enqueue(encoder.encode(': cloud projection connected\n\n'));
      }, 15_000);
    },
    cancel() {
      if (timer) clearInterval(timer);
    },
  });
  return new Response(body, {
    headers: {
      'content-type': 'text/event-stream; charset=utf-8',
      'cache-control': 'no-store',
      connection: 'keep-alive',
    },
  });
}

export async function onRequest({ request, env }) {
  const url = new URL(request.url);
  const path = url.pathname;

  if (path === '/api/brain/stream' && request.method === 'GET') {
    return streamState(env);
  }
  if (path === '/api/brain/state' && request.method === 'GET') {
    return json(cloudState(env));
  }
  if (path === '/api/state' && request.method === 'GET') {
    return json(cloudState(env));
  }
  if (path === '/api/build' && request.method === 'GET') {
    return json({
      build: String(env.CF_PAGES_COMMIT_SHA || 'cloud-preview').slice(0, 12),
    });
  }
  if (path === '/api/brain/optimus/evidence' && request.method === 'GET') {
    return json({
      writable: false,
      records: [],
      generatedAt: new Date().toISOString(),
    });
  }
  if (path === '/api/brain/heartbeat') {
    return json({
      ok: true,
      accepted: false,
      mode: 'cloud-read-only',
      surface: 'cloudflare-pages',
    });
  }
  if (path === '/api/brain/steer') {
    return json(
      {
        error:
          'This cloud founder surface is a read-only projection. Live steering is not attached here.',
        code: 'CLOUD_READ_ONLY',
      },
      409
    );
  }
  if (path === '/api/greenlane' && request.method === 'GET') {
    return json({
      ok: false,
      error: 'The cloud Greenlane replay projection is not attached in this preview.',
      next: 'Use the repository workflow state until the replay feed is promoted.',
      fetchedAt: Date.now(),
    });
  }
  if (path === '/api/brain/AGENTS.md' && request.method === 'GET') {
    return new Response('# Genesis cloud founder surface\n\nRepository is authoritative.\n', {
      headers: { 'content-type': 'text/markdown; charset=utf-8' },
    });
  }
  if (path === '/api/brain/policy' && request.method === 'GET') {
    return json({ authority: 'github-canonical', mode: 'cloud-read-only' });
  }
  if (path.startsWith('/api/brain/sessions') && request.method === 'GET') {
    return json({ sessions: [], sessionWritable: false, sessionLedgerError: null });
  }
  if (path === '/api/brain/capsule.txt' && request.method === 'GET') {
    return new Response('', {
      headers: { 'content-type': 'text/plain; charset=utf-8' },
    });
  }
  return json({ error: 'Not found', code: 'CLOUD_PROJECTION_NOT_FOUND' }, 404);
}
