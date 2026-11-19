/**
 * Cloudflare Pages Functions edge adapter (`/api/*`) for `genesis-founder-surface.pages.dev`
 *
 * Enforces mission `#7760` / `gemini-sync` receiver security invariants on edge ingest:
 *   1. Fail-closed authentication (`GEMINI_SYNC_INGEST_TOKEN` Bearer / `X-Ingest-Token`)
 *   2. Max 16 MiB payload guard & valid Git bundle v2/v3 header check
 *   3. Mandatory durable R2 persistence (`INGEST_BUCKET`) — NEVER returns 200 without durable write
 *   4. Independent byte readback verification from R2 (`get()` length + SHA-256 match) before 201
 *
 * Also serves static build projections under `/api/*` with explicit
 * `isLiveState: false` and `HISTORICAL_BUILD_SNAPSHOT_NOT_LIVE` tags so historical
 * snapshots are NEVER misrepresented as live runtime state.
 */

const MAX_GEMINI_SYNC_BUNDLE_BYTES = 16 * 1024 * 1024; // 16 MiB ceiling

interface R2ObjectBodyLike {
  arrayBuffer(): Promise<ArrayBuffer>;
}

interface PagesContext {
  request: Request;
  env: {
    ASSETS?: { fetch(request: Request | string): Promise<Response> };
    INGEST_BUCKET?: {
      put(key: string, value: ArrayBuffer | ReadableStream, opts?: unknown): Promise<void>;
      get(key: string): Promise<R2ObjectBodyLike | null>;
    };
    GEMINI_SYNC_INGEST_TOKEN?: string;
    OMNIFLOW_DO_ORIGIN?: string;
  };
}

function timingSafeStrEqual(a: string, b: string): boolean {
  const te = new TextEncoder();
  const ba = te.encode(a);
  const bb = te.encode(b);
  if (ba.length === 0 || ba.length !== bb.length) return false;
  let diff = 0;
  for (let i = 0; i < ba.length; i++) {
    diff |= ba[i] ^ bb[i];
  }
  return diff === 0;
}

function jsonResponse(payload: unknown, status = 200, extraHeaders: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(payload, null, 2), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, OPTIONS',
      'Access-Control-Allow-Headers':
        'Content-Type, Authorization, X-Ingest-Token, X-Bundle-Sha256, X-Bundle-Head-Sha',
      ...extraHeaders,
    },
  });
}

async function sha256Hex(buf: ArrayBuffer): Promise<string> {
  const hashBuf = await crypto.subtle.digest('SHA-256', buf);
  return Array.from(new Uint8Array(hashBuf))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

async function tryStaticProjection(
  context: PagesContext,
  pathname: string
): Promise<Response | null> {
  if (!context.env?.ASSETS) return null;
  const assetUrl = new URL(pathname, context.request.url);
  const res = await context.env.ASSETS.fetch(assetUrl.toString());
  const ct = res.headers.get('content-type') ?? '';
  if (res.ok && ct.includes('application/json')) {
    const raw = (await res.json()) as Record<string, unknown>;
    const tagged: Record<string, unknown> = {
      ...raw,
      isLiveState: false,
      telemetryFreshness: 'HISTORICAL_BUILD_SNAPSHOT_NOT_LIVE',
      liveStateWarning:
        'HISTORICAL STATIC SNAPSHOT ONLY — NOT LIVE RUNTIME TELEMETRY. Operational settlement remains withheld.',
    };
    return jsonResponse(tagged, 200, {
      'X-Projection-Source': 'cloudflare-pages-static-snapshot',
      'X-Telemetry-Freshness': 'HISTORICAL_BUILD_SNAPSHOT_NOT_LIVE',
    });
  }
  return null;
}

export async function onRequest(context: PagesContext): Promise<Response> {
  const { request } = context;
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, OPTIONS',
        'Access-Control-Allow-Headers':
          'Content-Type, Authorization, X-Ingest-Token, X-Bundle-Sha256, X-Bundle-Head-Sha',
      },
    });
  }

  const url = new URL(request.url);
  const pathname = url.pathname.replace(/\/+$/, '') || '/';

  // 1. Authenticated, durable, readback-verified bundle ingest (#7760 / gemini-sync parity)
  if (pathname === '/api/ingest/bundle') {
    const tokenConfigured = Boolean((context.env?.GEMINI_SYNC_INGEST_TOKEN ?? '').trim());
    const durableConfigured = Boolean(context.env?.INGEST_BUCKET);

    if (request.method === 'GET') {
      return jsonResponse({
        ok: true,
        missionRef: '#7760',
        canonicalReceiverRepo: 'chidionyema/gemini-sync',
        maxBundleBytes: MAX_GEMINI_SYNC_BUNDLE_BYTES,
        authConfigured: tokenConfigured,
        durableStorageConfigured: durableConfigured,
        requiresIndependentByteReadback: true,
        readyForProductionIngest: tokenConfigured && durableConfigured,
        isLiveState: true,
        timestampUtc: new Date().toISOString(),
      });
    }

    // Enforce fail-closed authentication BEFORE touching storage or digest
    const expectedToken = (context.env?.GEMINI_SYNC_INGEST_TOKEN ?? '').trim();
    if (!expectedToken) {
      return jsonResponse(
        {
          ok: false,
          accepted: false,
          error: 'INGEST_AUTH_TOKEN_NOT_CONFIGURED',
          missionRef: '#7760',
        },
        503
      );
    }

    const authHeader = request.headers.get('authorization') ?? '';
    const bearerToken = authHeader.startsWith('Bearer ') ? authHeader.slice(7).trim() : '';
    const headerToken = (request.headers.get('x-ingest-token') ?? '').trim();
    const presented = bearerToken || headerToken;
    if (!timingSafeStrEqual(presented, expectedToken)) {
      return jsonResponse(
        {
          ok: false,
          accepted: false,
          error: 'UNAUTHORIZED_INVALID_OR_MISSING_INGEST_TOKEN',
          missionRef: '#7760',
        },
        401
      );
    }

    // Enforce mandatory durable R2 storage BEFORE accepting
    if (!context.env?.INGEST_BUCKET) {
      return jsonResponse(
        {
          ok: false,
          accepted: false,
          error: 'DURABLE_STORAGE_NOT_CONFIGURED_FAIL_CLOSED',
          note: 'SHA-256 alone without durable storage & independent readback cannot be accepted.',
        },
        503
      );
    }

    const digest = (request.headers.get('x-bundle-sha256') ?? '').trim();
    const headSha = (request.headers.get('x-bundle-head-sha') ?? '').trim();
    if (!digest || !headSha) {
      return jsonResponse(
        { ok: false, accepted: false, error: 'MISSING_REQUIRED_DIGEST_OR_HEAD_SHA_HEADER' },
        400
      );
    }

    const buf = await request.arrayBuffer();
    if (buf.byteLength === 0) {
      return jsonResponse({ ok: false, accepted: false, error: 'EMPTY_BUNDLE_PAYLOAD' }, 400);
    }
    if (buf.byteLength > MAX_GEMINI_SYNC_BUNDLE_BYTES) {
      return jsonResponse(
        {
          ok: false,
          accepted: false,
          error: 'BUNDLE_EXCEEDS_16_MIB_LIMIT',
          bundleBytes: buf.byteLength,
          maxBundleBytes: MAX_GEMINI_SYNC_BUNDLE_BYTES,
        },
        413
      );
    }

    // Verify Git bundle header magic (# v2 git bundle or # v3 git bundle)
    const headPrefix = new TextDecoder().decode(buf.slice(0, 32));
    if (!headPrefix.startsWith('# v2 git bundle') && !headPrefix.startsWith('# v3 git bundle')) {
      return jsonResponse({ ok: false, accepted: false, error: 'INVALID_GIT_BUNDLE_MAGIC_HEADER' }, 400);
    }

    const computedSha = await sha256Hex(buf);
    if (!timingSafeStrEqual(digest.toLowerCase(), computedSha.toLowerCase())) {
      return jsonResponse(
        {
          ok: false,
          accepted: false,
          error: 'BUNDLE_SHA256_MISMATCH',
          expected: digest,
          computed: computedSha,
        },
        422
      );
    }

    // Replay / duplicate detection + durable R2 write + mandatory independent byte readback
    const objectKey = `bundles/${computedSha}.bundle`;
    const existingObj = await context.env.INGEST_BUCKET.get(objectKey);
    if (existingObj) {
      const existingBuf = await existingObj.arrayBuffer();
      const existingSha = await sha256Hex(existingBuf);
      if (existingBuf.byteLength !== buf.byteLength || !timingSafeStrEqual(existingSha, computedSha)) {
        return jsonResponse(
          {
            ok: false,
            accepted: false,
            error: 'CORRUPTED_EXISTING_STORAGE_DETECTED',
            objectKey,
          },
          500
        );
      }
      return jsonResponse({
        ok: true,
        accepted: true,
        duplicateReplay: true,
        durableStoredInR2: true,
        independentReadbackVerified: true,
        objectKey,
        bundleSha256: computedSha,
        bundleBytes: existingBuf.byteLength,
        headSha,
        receivedAtUtc: new Date().toISOString(),
      });
    }

    await context.env.INGEST_BUCKET.put(objectKey, buf, {
      customMetadata: { headSha, receivedAtUtc: new Date().toISOString(), missionRef: '7760' },
    });

    // Mandatory independent byte readback from durable storage
    const readbackObj = await context.env.INGEST_BUCKET.get(objectKey);
    if (!readbackObj) {
      return jsonResponse(
        { ok: false, accepted: false, error: 'DURABLE_READBACK_OBJECT_MISSING', objectKey },
        500
      );
    }
    const readbackBuf = await readbackObj.arrayBuffer();
    const readbackSha = await sha256Hex(readbackBuf);
    if (readbackBuf.byteLength !== buf.byteLength || !timingSafeStrEqual(readbackSha, computedSha)) {
      return jsonResponse(
        {
          ok: false,
          accepted: false,
          error: 'CORRUPTED_STORAGE_READBACK_DETECTED',
          expectedBytes: buf.byteLength,
          readbackBytes: readbackBuf.byteLength,
        },
        500
      );
    }

    return jsonResponse(
      {
        ok: true,
        accepted: true,
        duplicateReplay: false,
        durableStoredInR2: true,
        independentReadbackVerified: true,
        objectKey,
        bundleSha256: computedSha,
        bundleBytes: readbackBuf.byteLength,
        headSha,
        receivedAtUtc: new Date().toISOString(),
      },
      201
    );
  }

  // 2. Canonical OMNIFLOW origin proxy (when configured), else explicitly tagged static snapshot (isLiveState: false)
  const projectionPaths = new Set([
    '/api/health',
    '/api/karma/settlement',
    '/api/passkey/health',
    '/api/resilience/matrix',
    '/api/audit/all-seeing-eye',
    '/api/omniflow/universal-settlement',
    '/api/omniflow/state',
    '/api/omniflow/mathematical-proof',
    '/api/export/auto-sync',
    '/api/export/manifest',
  ]);

  if (projectionPaths.has(pathname)) {
    const doOrigin = (context.env?.OMNIFLOW_DO_ORIGIN ?? '').trim().replace(/\/+$/, '');
    if (doOrigin && pathname.startsWith('/api/omniflow/')) {
      try {
        const upstream = await fetch(`${doOrigin}${pathname}`, {
          method: request.method,
          headers: request.headers,
        });
        if (upstream.ok) return upstream;
      } catch {
        // Fall through cleanly to explicitly marked non-live static snapshot
      }
    }

    const staticRes = await tryStaticProjection(context, pathname);
    if (staticRes) return staticRes;
  }

  if (pathname === '/api/health') {
    return jsonResponse({
      ok: true,
      service: 'genesis-founder-surface-pages-fallback',
      isLiveState: false,
      telemetryFreshness: 'HISTORICAL_BUILD_SNAPSHOT_NOT_LIVE',
      liveStateWarning: 'Static fallback only; deploy dist/ & backend/DO adapter for live state.',
      certificationWithheld: true,
      neverShowFalseGreen: true,
      historicalBaselineFailedRuns: 359,
      liveFailedWorkflowRunsCount: null,
      externalRepositoriesAudited: 6,
      timestampUtc: new Date().toISOString(),
    });
  }

  if (pathname === '/api/passkey/health') {
    return jsonResponse({
      ok: true,
      host: 'passkey.mumchimp.com',
      isLiveState: false,
      telemetryFreshness: 'HISTORICAL_BUILD_SNAPSHOT_NOT_LIVE',
      externalHttpReachable: null,
      externalPasskeyVerifyScriptRun: false,
      verdict: 'HISTORICAL_SNAPSHOT_ONLY_UNMEASURED_IN_STATIC_FALLBACK',
      timestampUtc: new Date().toISOString(),
    });
  }

  return jsonResponse(
    {
      ok: false,
      error: 'API_ROUTE_NOT_PROVISIONED_ON_STATIC_EDGE',
      path: pathname,
      timestampUtc: new Date().toISOString(),
    },
    404
  );
}
