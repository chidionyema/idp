// Vendor-neutral NATS JetStream <-> estate-live-state.v1 bridge library (ADR 0012 + live-state spine).
//
// Keeps NATS JetStream (local leaf node, Synadia NGS, OCI ARM A1, or k3s) and the edge live-state
// projector (live.meridianlabs.cloud or any compatible HTTP endpoint) decoupled behind one open
// contract. Neither transport owns the estate exclusively (R43 provider independence).
//
// Invariants:
// - A malformed, missing-value, or BLIND NATS message maps to an explicit BLIND event (never 0/green).
// - An unreachable NATS broker emits a BLIND event and exits 2 (BLIND, never an empty quiet pass).
// - An unreachable or refusing live-state target fails closed with exit 1.

import { eventProblem, STATUSES } from "../src/fold.mjs";

export const BRIDGE_SOURCE = "nats-jetstream-bridge";
export const DEFAULT_INTERVAL_S = 300;

/**
 * Convert one NATS JetStream envelope (ADR 0012 CloudEvents / ESTATE_FLEET JSON) into an
 * `estate-live-state.v1` event ready for POST /append.
 *
 * Never coerces a missing or malformed value to 0 or false: emits explicit BLIND with reason.
 */
export function natsMessageToLiveEvent(msg, { now = Date.now, defaultIntervalS = DEFAULT_INTERVAL_S } = {}) {
  const tsNow = typeof now === "function" ? now() : now;
  if (msg === null || typeof msg !== "object" || Array.isArray(msg)) {
    return {
      source: BRIDGE_SOURCE,
      kind: "nats",
      subject: "malformed",
      ts: tsNow,
      interval_s: defaultIntervalS,
      status: "BLIND",
      reason: "nats message is not an object",
    };
  }

  const rawSubject = typeof msg.subject === "string" && msg.subject.trim() ? msg.subject.trim() : "unknown";
  const seq = Number.isInteger(msg.seq) && msg.seq > 0 ? msg.seq : null;

  let payload = msg.data;
  if (typeof payload === "string") {
    try {
      payload = JSON.parse(payload);
    } catch {
      return {
        source: BRIDGE_SOURCE,
        kind: "nats",
        subject: rawSubject,
        ts: tsNow,
        interval_s: defaultIntervalS,
        status: "BLIND",
        reason: "nats payload is not valid JSON",
        evidence: seq !== null ? { nats_seq: seq, nats_subject: rawSubject } : { nats_subject: rawSubject },
      };
    }
  }

  if (payload === null || typeof payload !== "object" || Array.isArray(payload)) {
    return {
      source: BRIDGE_SOURCE,
      kind: "nats",
      subject: rawSubject,
      ts: tsNow,
      interval_s: defaultIntervalS,
      status: "BLIND",
      reason: "nats payload is not a JSON object",
      evidence: seq !== null ? { nats_seq: seq, nats_subject: rawSubject } : { nats_subject: rawSubject },
    };
  }

  const source =
    typeof payload.source === "string" && payload.source.trim()
      ? payload.source.trim()
      : typeof payload.from === "string" && payload.from.trim()
        ? payload.from.trim()
        : BRIDGE_SOURCE;
  const kind =
    typeof payload.kind === "string" && payload.kind.trim()
      ? payload.kind.trim()
      : "fleet";
  const subject =
    typeof payload.subject === "string" && payload.subject.trim()
      ? payload.subject.trim()
      : rawSubject;
  const ts =
    typeof payload.ts === "number" && Number.isFinite(payload.ts)
      ? payload.ts > 1e12
        ? payload.ts
        : Math.round(payload.ts * 1000)
      : tsNow;
  const intervalS =
    typeof payload.interval_s === "number" && Number.isFinite(payload.interval_s) && payload.interval_s > 0
      ? payload.interval_s
      : defaultIntervalS;

  const evidence = {
    transport: "nats-jetstream",
    nats_subject: rawSubject,
    ...(seq !== null ? { nats_seq: seq } : {}),
    ...(payload.id ? { envelope_id: String(payload.id) } : {}),
    ...(payload.spiffe_id ? { spiffe_id: String(payload.spiffe_id) } : {}),
  };

  if (payload.status === "BLIND") {
    return {
      source,
      kind,
      subject,
      ts,
      interval_s: intervalS,
      status: "BLIND",
      reason: typeof payload.reason === "string" && payload.reason.trim() ? payload.reason.trim() : "upstream BLIND without reason",
      evidence,
    };
  }

  const status = STATUSES.includes(payload.status) ? payload.status : "DIRECT";
  const value = payload.value !== undefined ? payload.value : payload.text !== undefined ? payload.text : payload.state;

  const candidate = {
    source,
    kind,
    subject,
    ts,
    interval_s: intervalS,
    status,
    value,
    evidence,
  };

  const problem = eventProblem(candidate);
  if (problem !== null) {
    return {
      source,
      kind,
      subject,
      ts,
      interval_s: intervalS,
      status: "BLIND",
      reason: `bridged malformed event: ${problem}`,
      evidence,
    };
  }
  return candidate;
}

/**
 * Push a batch of bridged NATS JetStream messages to any `estate-live-state.v1` HTTP endpoint.
 *
 * Returns {code, accepted, seq, events, out, err}:
 * - 0: bridged and accepted by target (or broker explicitly reported BLIND and target recorded it)
 * - 1: target refused, unreachable, or returned malformed response (fail closed)
 * - 2: BLIND (missing ingest token or unreachable NATS broker when no fallback target accepted BLIND)
 */
export async function bridgeBatch({
  messages,
  brokerError = null,
  base,
  token,
  fetchImpl = fetch,
  now = Date.now,
}) {
  const out = [];
  const err = [];
  if (typeof token !== "string" || token.length === 0) {
    out.push("BLIND  nats-bridge  LIVE_STATE_INGEST_TOKEN is not set; nothing forwarded");
    return { code: 2, accepted: 0, seq: null, events: [], out, err };
  }

  let events;
  if (brokerError) {
    events = [
      {
        source: BRIDGE_SOURCE,
        kind: "transport",
        subject: "nats-jetstream",
        ts: now(),
        interval_s: DEFAULT_INTERVAL_S,
        status: "BLIND",
        reason: `nats broker unreachable: ${brokerError}`,
        evidence: { transport: "nats-jetstream" },
      },
    ];
  } else {
    const list = Array.isArray(messages) ? messages : [];
    if (list.length === 0) {
      out.push("BRIDGE OK  0 messages to forward");
      return { code: 0, accepted: 0, seq: null, events: [], out, err };
    }
    events = list.map((m) => natsMessageToLiveEvent(m, { now }));
  }

  let res;
  try {
    res = await fetchImpl(`${base}/append`, {
      method: "POST",
      headers: {
        authorization: `Bearer ${token}`,
        "content-type": "application/json",
      },
      body: JSON.stringify(events),
      signal: AbortSignal.timeout(15_000),
    });
  } catch (e) {
    err.push(`BRIDGE FAIL  ${base}/append  unreachable: ${e.message}`);
    return { code: 1, accepted: 0, seq: null, events, out, err };
  }

  if (!res.ok) {
    err.push(`BRIDGE FAIL  ${base}/append  HTTP ${res.status}`);
    return { code: 1, accepted: 0, seq: null, events, out, err };
  }

  let body;
  try {
    body = await res.json();
  } catch {
    err.push(`BRIDGE FAIL  ${base}/append  response is not JSON`);
    return { code: 1, accepted: 0, seq: null, events, out, err };
  }

  if (typeof body?.accepted !== "number" || typeof body?.seq !== "number") {
    err.push(`BRIDGE FAIL  ${base}/append  response missing accepted/seq`);
    return { code: 1, accepted: 0, seq: null, events, out, err };
  }

  if (brokerError) {
    out.push(`BLIND  nats-jetstream  recorded on ${base} seq=${body.seq}`);
    return { code: 2, accepted: body.accepted, seq: body.seq, events, out, err };
  }
  out.push(`BRIDGE OK  forwarded=${body.accepted}  seq=${body.seq}`);
  return { code: 0, accepted: body.accepted, seq: body.seq, events, out, err };
}
