/**
 * Ready-to-Deploy Cloudflare Worker + Durable Object Edge Adapter (`https://estate-bus.mumchimp.com`)
 *
 * IMPORTANT ARCHITECTURAL ROLE:
 *   This Durable Object is strictly an **ADAPTER / EDGE RELAY to canonical OMNIFLOW**,
 *   NOT a competing authority. When `OMNIFLOW_CANONICAL_ORIGIN` is configured, mutating
 *   register / publish / lease requests forward to canonical OMNIFLOW first so monotonic
 *   fencing and custody remain single-authority. If canonical upstream is temporarily
 *   unreachable, messages are quarantined in adapter buffer (`PENDING_CANONICAL_RECONCILE`)
 *   instead of silently claiming canonical truth.
 *
 * Optional bindings:
 *   - `OMNIFLOW_CANONICAL_ORIGIN`: URL of canonical OMNIFLOW authority
 *   - `OMNIFLOW_SHARED_TOKEN`: Bearer / X-Omniflow-Token secret (recommended)
 */

interface DoStorage {
  get<T>(key: string): Promise<T | undefined>;
  put<T>(key: string, value: T): Promise<void>;
}

interface DoState {
  storage: DoStorage;
  acceptWebSocket(ws: WebSocket): void;
  getWebSockets(): WebSocket[];
}

export interface CloudflareBusEnv {
  ESTATE_BUS: {
    idFromName(name: string): unknown;
    get(id: unknown): { fetch(request: Request): Promise<Response> };
  };
  OMNIFLOW_CANONICAL_ORIGIN?: string;
  OMNIFLOW_SHARED_TOKEN?: string;
}

interface StoredEnvelope {
  seq: number;
  envelopeId: string;
  correlationId: string;
  idempotencyKey: string;
  fromAgent: string;
  target: string;
  verb: string;
  body: string;
  requiresClaim: boolean;
  custodyStage: string;
  holderAgentId: string | null;
  fencingToken: number | null;
  verifierId: string | null;
  adapterSyncState: 'SYNCED_WITH_CANONICAL_OMNIFLOW' | 'PENDING_CANONICAL_RECONCILE';
  createdAtUtc: string;
  updatedAtUtc: string;
}

interface StoredParticipant {
  agentId: string;
  surfaceClass: string;
  capabilities: string[];
  lastHeartbeatMs: number;
  ttlMs: number;
}

function authorized(request: Request, env: CloudflareBusEnv): boolean {
  const configured = (env.OMNIFLOW_SHARED_TOKEN ?? '').trim();
  if (!configured) return false; // Fail-closed: require configured shared token outside /health
  const auth = request.headers.get('authorization') ?? '';
  const bearer = auth.startsWith('Bearer ') ? auth.slice(7).trim() : '';
  const headerToken = (request.headers.get('x-omniflow-token') ?? '').trim();
  return bearer === configured || headerToken === configured;
}

function corsHeaders(): Record<string, string> {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Omniflow-Token',
  };
}

export class EstateOmniflowBusDO {
  private state: DoState;
  private env: CloudflareBusEnv;
  private sseControllers: Set<ReadableStreamDefaultController<Uint8Array>> = new Set();

  constructor(state: DoState, env: CloudflareBusEnv) {
    this.state = state;
    this.env = env;
  }

  private getCanonicalBase(): string | null {
    const raw = (this.env?.OMNIFLOW_CANONICAL_ORIGIN ?? '').trim().replace(/\/+$/, '');
    return raw ? raw : null;
  }

  private async forwardToCanonical(
    canonicalPath: string,
    method: string,
    body?: unknown
  ): Promise<{ relayed: boolean; status: number | null; payload: unknown }> {
    const base = this.getCanonicalBase();
    if (!base) {
      return { relayed: false, status: null, payload: null };
    }
    try {
      const res = await fetch(`${base}${canonicalPath}`, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'X-Omniflow-Adapter': 'cloudflare-estate-bus-do',
        },
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
      const json = await res.json().catch(() => null);
      return { relayed: res.ok, status: res.status, payload: json };
    } catch {
      return { relayed: false, status: null, payload: null };
    }
  }

  private async broadcast(eventName: string, payload: unknown): Promise<void> {
    const json = JSON.stringify(payload);
    const sseFrame = new TextEncoder().encode(`event: ${eventName}\ndata: ${json}\n\n`);
    for (const ctrl of this.sseControllers) {
      try {
        ctrl.enqueue(sseFrame);
      } catch {
        this.sseControllers.delete(ctrl);
      }
    }
    const wsFrame = JSON.stringify({ event: eventName, data: payload });
    for (const ws of this.state.getWebSockets()) {
      try {
        ws.send(wsFrame);
      } catch {
        // Ignore closed socket
      }
    }
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    const canonicalBase = this.getCanonicalBase();
    const messages = (await this.state.storage.get<StoredEnvelope[]>('messages')) ?? [];
    const participants =
      (await this.state.storage.get<Record<string, StoredParticipant>>('participants')) ?? {};
    let nextSeq = (await this.state.storage.get<number>('nextSeq')) ?? 1;
    let fenceEpoch = (await this.state.storage.get<number>('fenceEpoch')) ?? 500;

    // Sweep stale heartbeats locally in adapter cache
    const nowMs = Date.now();
    let recovered = false;
    for (const [id, p] of Object.entries(participants)) {
      if (nowMs - p.lastHeartbeatMs > p.ttlMs) {
        delete participants[id];
        for (const msg of messages) {
          if (msg.holderAgentId === id && msg.custodyStage === 'LEASED') {
            msg.custodyStage = 'LEASE_EXPIRED_RECOVERING';
            msg.holderAgentId = null;
            msg.updatedAtUtc = new Date(nowMs).toISOString();
            recovered = true;
          }
        }
      }
    }
    if (recovered) {
      await this.state.storage.put('messages', messages);
      await this.state.storage.put('participants', participants);
    }

    if (url.pathname === '/health') {
      return Response.json(
        {
          ok: true,
          service: 'meridian-estate-bus-do-adapter',
          authorityMode: 'CANONICAL_OMNIFLOW_EDGE_ADAPTER',
          competingAuthority: false,
          canonicalOriginConfigured: Boolean(canonicalBase),
          bufferedPendingCanonicalCount: messages.filter(
            (m) => m.adapterSyncState === 'PENDING_CANONICAL_RECONCILE'
          ).length,
          participantsCount: Object.keys(participants).length,
          messagesCount: messages.length,
          timestampUtc: new Date(nowMs).toISOString(),
        },
        { headers: corsHeaders() }
      );
    }

    if (url.pathname === '/v1/bus/state' && request.method === 'GET') {
      const upstream = await this.forwardToCanonical('/api/omniflow/state', 'GET');
      if (upstream.relayed && upstream.payload) {
        return Response.json(
          {
            ok: true,
            authorityMode: 'CANONICAL_OMNIFLOW_EDGE_ADAPTER',
            canonicalRelayed: true,
            snapshot: upstream.payload,
          },
          { headers: corsHeaders() }
        );
      }
      return Response.json(
        {
          ok: true,
          authorityMode: 'CANONICAL_OMNIFLOW_EDGE_ADAPTER',
          canonicalRelayed: false,
          adapterNote: 'Canonical origin unreachable or unconfigured; returning edge adapter buffer only.',
          fenceEpoch,
          participants: Object.values(participants),
          messages,
        },
        { headers: corsHeaders() }
      );
    }

    if (url.pathname === '/v1/bus/ws' && request.headers.get('Upgrade') === 'websocket') {
      const pair = new (globalThis as unknown as { WebSocketPair: new () => [WebSocket, WebSocket] }).WebSocketPair();
      const [client, server] = [pair[0], pair[1]];
      this.state.acceptWebSocket(server);
      server.send(
        JSON.stringify({
          event: 'bus_init',
          data: {
            authorityMode: 'CANONICAL_OMNIFLOW_EDGE_ADAPTER',
            fenceEpoch,
            messages,
            participants: Object.values(participants),
          },
        })
      );
      return new Response(null, { status: 101, webSocket: client } as ResponseInit & { webSocket: WebSocket });
    }

    if (url.pathname === '/v1/bus/stream' && request.method === 'GET') {
      let controllerRef: ReadableStreamDefaultController<Uint8Array> | null = null;
      const stream = new ReadableStream<Uint8Array>({
        start: (controller) => {
          controllerRef = controller;
          this.sseControllers.add(controller);
          const init = `event: bus_init\ndata: ${JSON.stringify({
            authorityMode: 'CANONICAL_OMNIFLOW_EDGE_ADAPTER',
            fenceEpoch,
            messages,
            participants: Object.values(participants),
          })}\n\n`;
          controller.enqueue(new TextEncoder().encode(init));
        },
        cancel: () => {
          if (controllerRef) this.sseControllers.delete(controllerRef);
        },
      });
      return new Response(stream, {
        headers: {
          ...corsHeaders(),
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
        },
      });
    }

    if (url.pathname === '/v1/bus/register' && request.method === 'POST') {
      const body = (await request.json()) as {
        agentId: string;
        surfaceClass?: string;
        capabilities?: string[];
        ttlMs?: number;
      };
      if (!body.agentId) {
        return Response.json({ ok: false, error: 'agentId_required' }, { status: 400, headers: corsHeaders() });
      }
      const upstream = await this.forwardToCanonical('/api/omniflow/register', 'POST', body);
      participants[body.agentId] = {
        agentId: body.agentId,
        surfaceClass: body.surfaceClass ?? 'CONSOLE_CLI',
        capabilities: body.capabilities ?? [],
        lastHeartbeatMs: nowMs,
        ttlMs: Math.max(10_000, Math.min(300_000, body.ttlMs ?? 60_000)),
      };
      await this.state.storage.put('participants', participants);
      await this.broadcast('presence', Object.values(participants));
      return Response.json(
        {
          ok: true,
          authorityMode: 'CANONICAL_OMNIFLOW_EDGE_ADAPTER',
          canonicalRelayed: upstream.relayed,
          participant: participants[body.agentId],
        },
        { headers: corsHeaders() }
      );
    }

    if (url.pathname === '/v1/bus/publish' && request.method === 'POST') {
      const body = (await request.json()) as {
        fromAgent: string;
        target?: string;
        verb?: string;
        body: string;
        correlationId?: string;
        idempotencyKey?: string;
        requiresClaim?: boolean;
      };
      const upstream = await this.forwardToCanonical('/api/omniflow/publish', 'POST', body);
      const idemKey = body.idempotencyKey ?? `idem-${nowMs}-${nextSeq}`;
      const existing = messages.find((m) => m.idempotencyKey === idemKey);
      if (existing) {
        return Response.json(
          {
            ok: true,
            authorityMode: 'CANONICAL_OMNIFLOW_EDGE_ADAPTER',
            canonicalRelayed: upstream.relayed,
            deduplicated: true,
            message: existing,
          },
          { headers: corsHeaders() }
        );
      }
      const seq = nextSeq++;
      const envelopeId = `MSG-${String(seq).padStart(4, '0')}`;
      const record: StoredEnvelope = {
        seq,
        envelopeId,
        correlationId: body.correlationId ?? `corr-${envelopeId.toLowerCase()}`,
        idempotencyKey: idemKey,
        fromAgent: body.fromAgent || 'unknown',
        target: body.target || '@all',
        verb: body.verb || 'ASK',
        body: String(body.body || '').slice(0, 4000),
        requiresClaim: Boolean(body.requiresClaim ?? true),
        custodyStage: body.requiresClaim ?? true ? 'DELIVERED' : 'PUBLISHED',
        holderAgentId: null,
        fencingToken: null,
        verifierId: null,
        adapterSyncState: upstream.relayed
          ? 'SYNCED_WITH_CANONICAL_OMNIFLOW'
          : 'PENDING_CANONICAL_RECONCILE',
        createdAtUtc: new Date(nowMs).toISOString(),
        updatedAtUtc: new Date(nowMs).toISOString(),
      };
      messages.unshift(record);
      if (messages.length > 200) messages.length = 200;
      await this.state.storage.put('nextSeq', nextSeq);
      await this.state.storage.put('messages', messages);
      await this.broadcast('bus_message', record);
      return Response.json(
        {
          ok: true,
          authorityMode: 'CANONICAL_OMNIFLOW_EDGE_ADAPTER',
          canonicalRelayed: upstream.relayed,
          deduplicated: false,
          message: record,
        },
        { status: upstream.relayed ? 201 : 202, headers: corsHeaders() }
      );
    }

    if (url.pathname === '/v1/bus/lease' && request.method === 'POST') {
      const body = (await request.json()) as {
        action: 'CLAIM' | 'VERIFY_EFFECT';
        envelopeId: string;
        actorId: string;
      };
      // Refuse lease grants cleanly unless canonical OMNIFLOW approves them (prevents split-brain competing authority!)
      const upstream = await this.forwardToCanonical('/api/omniflow/lease', 'POST', {
        action: body.action,
        envelopeId: body.envelopeId,
        workerId: body.actorId,
        verifierId: body.actorId,
      });
      if (!canonicalBase || !upstream.relayed) {
        return Response.json(
          {
            ok: false,
            error: 'CANONICAL_OMNIFLOW_AUTHORITY_UNREACHABLE_FOR_FENCED_LEASE',
            authorityMode: 'CANONICAL_OMNIFLOW_EDGE_ADAPTER',
            competingAuthorityRefused: true,
          },
          { status: 503, headers: corsHeaders() }
        );
      }
      const target = messages.find((m) => m.envelopeId === body.envelopeId);
      if (target) {
        if (body.action === 'CLAIM') {
          fenceEpoch += 1;
          target.fencingToken = fenceEpoch;
          target.holderAgentId = body.actorId;
          target.custodyStage = 'LEASED';
        } else {
          target.verifierId = body.actorId;
          target.custodyStage = 'VERIFIED_EFFECT';
        }
        target.adapterSyncState = 'SYNCED_WITH_CANONICAL_OMNIFLOW';
        target.updatedAtUtc = new Date(nowMs).toISOString();
        await this.state.storage.put('fenceEpoch', fenceEpoch);
        await this.state.storage.put('messages', messages);
        await this.broadcast('bus_lease', target);
      }
      return Response.json(
        {
          ok: true,
          authorityMode: 'CANONICAL_OMNIFLOW_EDGE_ADAPTER',
          canonicalPayload: upstream.payload,
        },
        { headers: corsHeaders() }
      );
    }

    return Response.json({ ok: false, error: 'not_found' }, { status: 404, headers: corsHeaders() });
  }
}

export default {
  async fetch(request: Request, env: CloudflareBusEnv): Promise<Response> {
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }
    const url = new URL(request.url);
    if (url.pathname !== '/health' && !authorized(request, env)) {
      return Response.json(
        { ok: false, error: 'unauthorized_missing_or_unconfigured_omniflow_token' },
        { status: 401, headers: corsHeaders() }
      );
    }
    const stub = env.ESTATE_BUS.get(env.ESTATE_BUS.idFromName('global-estate-bus-adapter-v1'));
    return stub.fetch(request);
  },
};
