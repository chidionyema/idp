import { json } from '../_lib/cloud-state.js';

export async function onRequest({ request, env }) {
  const url = new URL(request.url);
  if (url.pathname === '/omega/api/state') {
    return json({
      build: String(env.CF_PAGES_COMMIT_SHA || 'cloud-preview').slice(0, 12),
      demos: [],
      blocks: [],
      mode: 'cloud-read-only',
    });
  }
  return new Response('', { status: 204 });
}
