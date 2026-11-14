// brain-hub -- the One-Brain's cloud home: live state and realtime stream, off the Mac.
//
// WHY (founder, 2026-11-14: "need to get it off Mac urgent"; chose Cloudflare + GitHub).
// Every founder panel fed by /api/brain/* read files that exist only on the MacBook
// (~/.estate/estate.db, ~/.estate/state/one-brain/*, an in-memory event log), so with the Mac
// asleep the cockpit was empty. This Worker + one SQLite-backed Durable Object (Workers free
// tier) holds that state at brain.<estate zone>, and an hourly snapshot goes to R2 as the audit copy.
//
// Contract (same paths and shapes as argon server.ts, so the cockpit only changes its origin):
//   GET  /healthz                         "ok"
//   GET  /api/brain/state                 snapshot; ledgers are null until first import (never "0")
//   GET  /api/brain/stream                SSE: snapshot, or replay from Last-Event-ID / ?since=, or a gap
//   POST /api/brain/heartbeat             a surface says it is alive (expires after 90s)
//   POST /api/brain/steer                 [admin] founder directive
//   POST /api/brain/lifeboat-toggle       [admin]
//   POST /api/brain/import                [admin] idempotent bulk import of the Mac ledgers (by id)
//   POST /api/brain/record/<kind>         [admin] append one instruction | yield | policy | session | arr record
// Admin = "Authorization: Bearer <BRAIN_ADMIN_KEY>" (Worker secret). No key configured -> every write
// is refused (fail closed); reads stay open, as on the Mac hub. No credentials are stored here.

const KINDS = {
  instruction: { table: 'instructions', id: r => r.instructionId, at: r => r.initiatedAtMs ?? r.initiated_at_ms ?? 0 },
  yield: { table: 'yields', id: r => r.receiptId ?? r.yieldId ?? r.id, at: r => r.recordedAtMs ?? r.recorded_at_ms ?? 0 },
  policy: { table: 'policy', id: r => r.decisionId ?? r.id, at: r => r.recordedAtMs ?? r.recorded_at_ms ?? 0 },
  session: { table: 'sessions', id: r => r.sessionId ?? r.id, at: r => Date.parse(r.updatedAt ?? r.startedAt ?? '') || 0 },
  arr: { table: 'arr', id: r => r.ticketId ?? r.id, at: r => Date.parse(r.createdAt ?? '') || 0 },
};
const IMPORT_KEYS = { instructions: 'instruction', yieldReceipts: 'yield', policyDecisions: 'policy', sessions: 'session', arrTickets: 'arr' };
const RETAIN = 2000;            // events kept for replay
const SURFACE_TTL_MS = 90_000;  // same as server.ts
const STREAM_MAX_MS = 280_000;  // a stream ends before the platform cuts it; clients resume by id

const json = (body, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', 'x-content-type-options': 'nosniff' } });

function safeEqual(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}

export function admin(request, env) {
  const key = typeof env.BRAIN_ADMIN_KEY === 'string' ? env.BRAIN_ADMIN_KEY : '';
  if (key.length < 24) return { ok: false, status: 503, error: 'writes disabled: no admin key configured' };
  const got = (request.headers.get('authorization') || '').replace(/^Bearer\s+/i, '');
  return safeEqual(got, key) ? { ok: true } : { ok: false, status: 401, error: 'unauthorized' };
}

export function frame(id, event, payload) {
  return `id: ${id}\nevent: ${event}\ndata: ${JSON.stringify(payload)}\n\n`;
}

export function parseCursor(raw) {
  if (raw === null || raw === undefined || raw === '') return null;
  const n = Number(raw);
  return Number.isSafeInteger(n) && n >= 0 ? n : null;
}

/** The Durable Object: one instance ("estate") owns all state; SQLite storage, strong consistency. */
export class BrainHub {
  constructor(ctx, env) {
    this.ctx = ctx;
    this.env = env;
    this.sql = ctx.storage.sql;
    this.clients = new Set();
    this.sql.exec(`CREATE TABLE IF NOT EXISTS records(kind TEXT NOT NULL, id TEXT NOT NULL, at INTEGER NOT NULL, body TEXT NOT NULL, PRIMARY KEY(kind,id))`);
    this.sql.exec(`CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, event TEXT NOT NULL, payload TEXT NOT NULL, at INTEGER NOT NULL)`);
    this.sql.exec(`CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, v TEXT NOT NULL)`);
  }

  get(k, fallback = null) { const r = this.sql.exec('SELECT v FROM kv WHERE k=?', k).toArray()[0]; return r ? JSON.parse(r.v) : fallback; }
  set(k, v) { this.sql.exec('INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v', k, JSON.stringify(v)); }
  latestId() { return this.sql.exec('SELECT COALESCE(MAX(id),0) AS n FROM events').toArray()[0].n; }
  list(kind) { return this.sql.exec('SELECT body FROM records WHERE kind=? ORDER BY at DESC, id', kind).toArray().map(r => JSON.parse(r.body)); }

  upsert(kind, rec) {
    const spec = KINDS[kind];
    const id = spec && spec.id(rec);
    if (!spec || typeof id !== 'string' || !id) return false;
    this.sql.exec('INSERT INTO records(kind,id,at,body) VALUES(?,?,?,?) ON CONFLICT(kind,id) DO UPDATE SET at=excluded.at, body=excluded.body',
      kind, id, Number(spec.at(rec)) || 0, JSON.stringify(rec));
    return true;
  }

  surfaces(now) {
    const live = this.get('surfaces', {});
    for (const [name, s] of Object.entries(live)) if (now - Date.parse(s.lastSeen) > SURFACE_TTL_MS) delete live[name];
    return Object.values(live);
  }

  state(now = Date.now()) {
    const imported = this.get('importedAt');
    const led = kind => (imported ? this.list(kind) : null); // never report an empty ledger as "0" before data arrived
    const directives = this.get('directives', []);
    return {
      protocol: 'GEN-NET-006', status: 'cloud-hub', authority: 'github-canonical',
      alwaysOnHome: 'cloudflare-durable-object', laptopMayBeRequired: false, primaryInteraction: 'voice-first-remote',
      commit: this.env.HUB_BUILD || null, branch: 'main', origin: 'brain-hub',
      models: { primary: 'minimax/MiniMax-M3.1-Flash', secondary: 'deepseek/deepseek-v4-flash',
        subscription: 'gemini/manual-subscription-only', router: 'direct-provider-only' },
      lifeboatMode: this.get('lifeboatMode', false), labFlags: this.get('labFlags', null),
      directive: directives.at(-1) || null, directives,
      surfaces: this.surfaces(now), motions: this.get('motions', []),
      arrWritable: this.writable(), arrTickets: led('arr'), sessions: led('session'),
      streamSequence: this.latestId(), sessionLedgerError: null, sessionWritable: this.writable(),
      provenanceWritable: this.writable(), instructions: led('instruction'), yieldReceipts: led('yield'),
      policyDecisions: led('policy'), syncVerification: null, runtimeVerification: null, sync: {},
      importedAt: imported, ledgersSource: imported ? 'cloud-hub' : 'awaiting-first-import-from-mac',
      generatedAt: new Date(now).toISOString(),
    };
  }

  writable() { return typeof this.env.BRAIN_ADMIN_KEY === 'string' && this.env.BRAIN_ADMIN_KEY.length >= 24; }

  append(event, payload, now = Date.now()) {
    const id = this.latestId() + 1;
    this.sql.exec('INSERT INTO events(id,event,payload,at) VALUES(?,?,?,?)', id, event, JSON.stringify(payload), now);
    this.sql.exec('DELETE FROM events WHERE id <= ?', id - RETAIN);
    const f = frame(id, event, payload);
    for (const w of this.clients) w.write(f).catch(() => this.clients.delete(w));
    return id;
  }

  async fetch(request) {
    const url = new URL(request.url);
    const p = url.pathname;
    const now = Date.now();
    if (request.method === 'GET' && p === '/api/brain/state') return json(this.state(now));
    if (request.method === 'GET' && p === '/api/brain/stream') return this.stream(request, url, now);
    if (request.method !== 'POST') return json({ error: 'not found' }, 404);
    let body;
    try { body = await request.json(); } catch { return json({ error: 'body must be JSON' }, 400); }
    if (!body || typeof body !== 'object') return json({ error: 'body must be an object' }, 400);

    if (p === '/api/brain/heartbeat') {
      const name = typeof body.name === 'string' ? body.name.slice(0, 80) : '';
      if (!/^[\w .:@-]+$/.test(name)) return json({ error: 'name required' }, 400);
      const live = this.get('surfaces', {});
      live[name] = { name, kind: String(body.kind || 'surface').slice(0, 40), lastSeen: new Date(now).toISOString() };
      this.set('surfaces', live);
      this.append('surface', live[name], now);
      return json({ ok: true });
    }
    const auth = admin(request, this.env);
    if (!auth.ok) return json({ error: auth.error }, auth.status);

    if (p === '/api/brain/steer') {
      const text = typeof body.directive === 'string' ? body.directive.trim().slice(0, 2000) : '';
      if (!text) return json({ error: 'directive required' }, 400);
      const d = { directive: text, by: String(body.by || 'founder').slice(0, 60), at: new Date(now).toISOString() };
      const all = this.get('directives', []); all.push(d); this.set('directives', all.slice(-50));
      return json({ ok: true, id: this.append('directive', d, now) });
    }
    if (p === '/api/brain/lifeboat-toggle') {
      const on = Boolean(body.enabled);
      this.set('lifeboatMode', on);
      return json({ ok: true, lifeboatMode: on, id: this.append('lifeboat', { enabled: on }, now) });
    }
    if (p === '/api/brain/import') {
      const counts = {};
      for (const [field, kind] of Object.entries(IMPORT_KEYS)) {
        if (!Array.isArray(body[field])) continue;
        counts[field] = 0;
        for (const rec of body[field]) if (rec && typeof rec === 'object' && this.upsert(kind, rec)) counts[field] += 1;
      }
      if (body.labFlags && typeof body.labFlags === 'object') this.set('labFlags', body.labFlags);
      if (!Object.keys(counts).length) return json({ error: 'nothing to import' }, 400);
      this.set('importedAt', new Date(now).toISOString());
      return json({ ok: true, imported: counts, id: this.append('import', { counts, source: String(body.source || 'mac').slice(0, 60) }, now) });
    }
    const m = p.match(/^\/api\/brain\/record\/(instruction|yield|policy|session|arr)$/);
    if (m) {
      if (!this.upsert(m[1], body)) return json({ error: 'record has no id for kind ' + m[1] }, 400);
      if (!this.get('importedAt')) this.set('importedAt', new Date(now).toISOString());
      return json({ ok: true, id: this.append('record', { kind: m[1], record: body }, now) });
    }
    return json({ error: 'not found' }, 404);
  }

  stream(request, url, now) {
    const cursor = parseCursor(request.headers.get('last-event-id') ?? url.searchParams.get('since') ?? url.searchParams.get('cursor'));
    const { readable, writable } = new TransformStream();
    const w = writable.getWriter();
    const enc = new TextEncoder();
    const writer = { write: s => w.write(enc.encode(s)) };
    const latest = this.latestId();
    const first = [];
    if (cursor === null) first.push(frame(latest, 'state', this.state(now)));
    else {
      const oldest = this.sql.exec('SELECT COALESCE(MIN(id),0) AS n FROM events').toArray()[0].n;
      if (cursor < oldest - 1 || cursor > latest) {
        first.push(`event: gap\ndata: ${JSON.stringify({ from: cursor, to: latest, reason: cursor > latest ? 'cursor-ahead' : 'evicted', latest })}\n\n`);
        first.push(frame(latest, 'state', this.state(now)));
      } else {
        for (const e of this.sql.exec('SELECT id,event,payload FROM events WHERE id > ? ORDER BY id', cursor).toArray())
          first.push(frame(e.id, e.event, JSON.parse(e.payload)));
      }
    }
    first.unshift('retry: 3000\n\n');
    (async () => { for (const f of first) await writer.write(f); })().catch(() => {});
    this.clients.add(writer);
    const ping = setInterval(() => writer.write(': ping\n\n').catch(() => {}), 25_000);
    setTimeout(() => { clearInterval(ping); this.clients.delete(writer); w.close().catch(() => {}); }, STREAM_MAX_MS);
    return new Response(readable, { headers: { 'content-type': 'text/event-stream', 'cache-control': 'no-cache, no-transform', 'x-content-type-options': 'nosniff' } });
  }

  async snapshot() {
    if (!this.env.SNAPSHOTS) return null;
    const body = JSON.stringify(this.state());
    const key = 'brain/' + new Date().toISOString().slice(0, 13) + '.json';
    await this.env.SNAPSHOTS.put(key, body, { httpMetadata: { contentType: 'application/json' } });
    await this.env.SNAPSHOTS.put('brain/latest.json', body, { httpMetadata: { contentType: 'application/json' } });
    return key;
  }
}

const hub = env => env.HUB.get(env.HUB.idFromName('estate'));

// Read-only cross-origin access for the founder's surfaces (GET only; writes are server-to-server
// with the admin key and never need CORS). Exact origins, plus this account's Vercel previews.
const ALLOWED_ORIGINS = new Set(['https://genesis-founder-surface.pages.dev', 'http://127.0.0.1:3000', 'http://localhost:3000']);
export function allowedOrigin(origin) {
  if (!origin) return false;
  if (ALLOWED_ORIGINS.has(origin)) return true;
  return /^https:\/\/otto-private-office(-[a-z0-9-]+)?-chidionyemas-projects\.vercel\.app$/.test(origin)
    || origin === 'https://otto-private-office.vercel.app';
}
function withCors(response, request) {
  const origin = request.headers.get('origin');
  if (request.method !== 'GET' || !allowedOrigin(origin)) return response;
  const h = new Headers(response.headers);
  h.set('access-control-allow-origin', origin);
  h.set('vary', 'origin');
  h.set('access-control-expose-headers', 'content-type');
  return new Response(response.body, { status: response.status, headers: h });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/healthz') return new Response('ok', { headers: { 'content-type': 'text/plain', 'cache-control': 'no-store' } });
    if (!url.pathname.startsWith('/api/brain/')) return json({ error: 'not found' }, 404);
    if (request.method === 'OPTIONS') {
      const origin = request.headers.get('origin');
      if (!allowedOrigin(origin)) return new Response(null, { status: 403 });
      return new Response(null, { status: 204, headers: { 'access-control-allow-origin': origin,
        'access-control-allow-methods': 'GET', 'access-control-allow-headers': 'last-event-id, accept, cache-control', 'access-control-max-age': '600', vary: 'origin' } });
    }
    return withCors(await hub(env).fetch(request), request);
  },
  async scheduled(_event, env) {
    // hourly audit copy to R2; the hub itself is the live store
    await hub(env).fetch(new Request('https://hub.internal/__snapshot', { method: 'PUT' })).catch(() => {});
  },
};

// The snapshot route is internal only (never reachable from the edge: the front door above only forwards /api/brain/*).
const _fetch = BrainHub.prototype.fetch;
BrainHub.prototype.fetch = async function (request) {
  if (request.method === 'PUT' && new URL(request.url).pathname === '/__snapshot') return json({ key: await this.snapshot() });
  return _fetch.call(this, request);
};
