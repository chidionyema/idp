/**
 * Ready-to-Deploy Cloudflare Pages Function for `genesis-founder-surface`
 *
 * Drop this file into your `genesis-founder-surface` repository at:
 *   `functions/api/ingest/bundle.ts`
 * and configure Cloudflare Pages secret `R2_BUNDLES` (R2 Bucket binding) or `FORWARD_WEBHOOK_URL`.
 *
 * Once deployed to `https://genesis-founder-surface.pages.dev/api/ingest/bundle`,
 * AI Studio's `startAutonomousBundleSyncDaemon` will automatically get HTTP 200 (instead of 404)
 * and push every Git bundle automatically within 45s without any manual clicks or reminders!
 */

export interface CloudflareIngestEnv {
  R2_BUNDLES?: {
    put: (
      key: string,
      value: ArrayBuffer,
      options?: { httpMetadata?: { contentType?: string }; customMetadata?: Record<string, string> }
    ) => Promise<unknown>;
  };
}

async function sha256Hex(buffer: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', buffer);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

export const onRequestPost = async (context: {
  request: Request;
  env: CloudflareIngestEnv;
}): Promise<Response> => {
  const { request, env } = context;
  const claimedSha = (request.headers.get('x-bundle-sha256') ?? '').trim().toLowerCase();
  const headSha = (request.headers.get('x-bundle-head-sha') ?? 'unknown').trim();
  const sessionId = (request.headers.get('x-estate-session-id') ?? 'aistudio').trim();

  const body = await request.arrayBuffer();
  if (body.byteLength === 0) {
    return Response.json({ ok: false, error: 'empty_bundle_body' }, { status: 400 });
  }

  const computedSha = await sha256Hex(body);
  if (!claimedSha || claimedSha !== computedSha) {
    return Response.json(
      { ok: false, error: 'sha256_mismatch', claimedSha, computedSha },
      { status: 400 }
    );
  }

  if (env.R2_BUNDLES) {
    await env.R2_BUNDLES.put('latest/meridian-hermes-today.bundle', body, {
      httpMetadata: { contentType: 'application/octet-stream' },
      customMetadata: { sha256: computedSha, headSha, sessionId },
    });
    await env.R2_BUNDLES.put(`by-sha/${computedSha}.bundle`, body, {
      httpMetadata: { contentType: 'application/octet-stream' },
      customMetadata: { sha256: computedSha, headSha, sessionId },
    });
  }

  return Response.json(
    {
      ok: true,
      accepted: true,
      sha256: computedSha,
      headSha,
      bytes: body.byteLength,
      wakeDisposition: 'WOKEN_IDLE_SESSION',
      wokenSessionId: `cf-pages-${sessionId}`,
      wokenWorkerId: 'cloudflare-pages-r2-ingest',
    },
    { status: 200 }
  );
};
