import { fold, snapshotHash, eventProblem, keyOf } from "./fold.mjs";

const HEAD = "head";
const PREFIX = "k:";
const MAX_BATCH = 100;
const TICK_MS = 30_000; // a hibernating object still tells its readers when a producer has gone silent

const json = (body, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

/**
 * One object holds the estate's live state. Storage keeps the latest event per key plus a head
 * counter: folding that is equal to folding the whole log, a fact test/fold.test.mjs asserts, so
 * the append-only log never has to grow without bound.
 */
export class EstateLiveStateDO {
  constructor(state, env) {
    this.state = state;
    this.env = env;
  }

  async fetch(request) {
    const { pathname } = new URL(request.url);
    if (pathname === "/append" && request.method === "POST") return this.append(request);
    if (pathname === "/snapshot" && request.method === "GET") return json(await this.snapshot());
    if (pathname === "/ws") return this.upgrade(request);
    return json({ error: "not found" }, 404);
  }

  async snapshot(now = Date.now()) {
    const stored = await this.state.storage.list({ prefix: PREFIX });
    const snap = fold([...stored.values()], now);
    return { ...snap, hash: await snapshotHash(snap) };
  }

  async append(request) {
    let body;
    try {
      body = await request.json();
    } catch {
      return json({ error: "body is not JSON" }, 400);
    }
    const events = Array.isArray(body) ? body : [body];
    if (events.length === 0 || events.length > MAX_BATCH) return json({ error: `send 1 to ${MAX_BATCH} events` }, 400);
    const now = Date.now();
    const staged = events.map((e) => (e && typeof e === "object" && e.ts === undefined ? { ...e, ts: now } : e));
    const refused = staged.map((e, i) => ({ i, problem: eventProblem(e) })).filter((r) => r.problem !== null);
    // All or nothing: a producer that sends one bad event learns it, and none of the batch half-lands.
    if (refused.length > 0) return json({ error: "events refused", refused }, 422);

    let head = 0;
    await this.state.storage.transaction(async (txn) => {
      head = (await txn.get(HEAD)) ?? 0;
      for (const e of staged) {
        head += 1;
        await txn.put(`${PREFIX}${keyOf(e)}`, { ...e, seq: head });
      }
      await txn.put(HEAD, head);
    });
    await this.broadcast("event");
    return json({ accepted: staged.length, seq: head });
  }

  async upgrade(request) {
    if (request.headers.get("Upgrade") !== "websocket") return json({ error: "expected a websocket upgrade" }, 426);
    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);
    this.state.acceptWebSocket(server);
    server.send(JSON.stringify({ type: "snapshot", snapshot: await this.snapshot() }));
    await this.arm();
    return new Response(null, { status: 101, webSocket: client });
  }

  async broadcast(type) {
    const sockets = this.state.getWebSockets();
    if (sockets.length === 0) return;
    const payload = JSON.stringify({ type, snapshot: await this.snapshot() });
    for (const ws of sockets) {
      try {
        ws.send(payload);
      } catch {
        /* a dead socket costs that socket, not the broadcast */
      }
    }
    await this.arm();
  }

  async arm() {
    if (this.state.getWebSockets().length > 0 && (await this.state.storage.getAlarm()) === null) {
      await this.state.storage.setAlarm(Date.now() + TICK_MS);
    }
  }

  async alarm() {
    await this.broadcast("tick");
  }

  async webSocketMessage(ws, message) {
    if (message === "ping") ws.send("pong");
  }

  async webSocketClose(ws) {
    try {
      ws.close();
    } catch {
      /* already closed */
    }
  }
}
