// The estate's live state is a pure fold over events. No storage, no network, no clock of its own:
// the caller passes `now`, so the same log and the same now always give the same snapshot.
//
// The law this file enforces (docs/specs/2026-11-28-estate-live-state-spine.md): a signal that is
// missing, malformed or silent past its interval is BLIND. It is never 0, never false, never green.

export const SCHEMA = "estate-live-state.v1";
export const STATUSES = Object.freeze(["DIRECT", "ALLOCATED", "ESTIMATED", "BLIND"]);
export const DEFAULT_INTERVAL_S = 900;
export const STALE_FACTOR = 2; // a producer is stale after this many of its own declared intervals
export const FUTURE_SKEW_MS = 60_000;

const isStr = (v) => typeof v === "string" && v.length > 0;

/** Why an event cannot be trusted, or null. Presence is tested by type, never by truthiness: 0 and false are data. */
export function eventProblem(e) {
  if (e === null || typeof e !== "object" || Array.isArray(e)) return "not an object";
  if (!isStr(e.source)) return "source missing";
  if (!isStr(e.kind)) return "kind missing";
  if (!isStr(e.subject)) return "subject missing";
  if (typeof e.ts !== "number" || !Number.isFinite(e.ts)) return "ts missing";
  if (!STATUSES.includes(e.status)) return "status unknown";
  if (e.interval_s !== undefined && !(typeof e.interval_s === "number" && e.interval_s > 0 && Number.isFinite(e.interval_s))) {
    return "interval_s invalid";
  }
  if (e.status === "BLIND") {
    if (!isStr(e.reason)) return "BLIND without a reason";
    if (e.value !== undefined && e.value !== null) return "BLIND carries a value";
    return null;
  }
  if (e.value === undefined || e.value === null) return "value missing";
  if (typeof e.value === "number" && !Number.isFinite(e.value)) return "value not finite";
  return null;
}

export const keyOf = (e) => `${e.kind}:${e.subject}`;
const identifiable = (e) => e !== null && typeof e === "object" && isStr(e.kind) && isStr(e.subject);

/**
 * Fold events (each with an integer `seq`) into a snapshot at `now` (ms).
 * Last write per key wins, by seq. A repeated seq is rejected, so replaying a log is idempotent.
 */
export function fold(events, now) {
  const rejected = [];
  const seen = new Set();
  const ordered = [];
  for (const e of Array.isArray(events) ? events : []) {
    if (e === null || typeof e !== "object" || !Number.isInteger(e.seq) || e.seq < 1) {
      rejected.push({ seq: e && e.seq !== undefined ? e.seq : null, reason: "seq invalid" });
      continue;
    }
    if (seen.has(e.seq)) {
      rejected.push({ seq: e.seq, reason: "seq repeated" });
      continue;
    }
    seen.add(e.seq);
    ordered.push(e);
  }
  ordered.sort((a, b) => a.seq - b.seq);

  const subjects = {};
  let head = 0;
  for (const e of ordered) {
    head = e.seq;
    if (!identifiable(e)) {
      rejected.push({ seq: e.seq, reason: "kind or subject missing" });
      continue;
    }
    const key = keyOf(e);
    const problem = eventProblem(e);
    if (problem !== null) {
      subjects[key] = blind(e, `malformed: ${problem}`);
      continue;
    }
    subjects[key] = e.status === "BLIND" ? blind(e, e.reason) : live(e);
  }

  for (const [key, s] of Object.entries(subjects)) {
    if (s.status === "BLIND" || typeof s.ts !== "number") continue;
    const intervalMs = s.interval_s * 1000;
    if (s.ts > now + FUTURE_SKEW_MS) {
      subjects[key] = { ...blindFrom(s), reason: "future-ts" };
    } else if (now - s.ts > STALE_FACTOR * intervalMs) {
      const ageS = Math.round((now - s.ts) / 1000);
      subjects[key] = { ...blindFrom(s), reason: `stale: ${ageS}s old, interval ${s.interval_s}s` };
    }
  }

  const blindKeys = Object.keys(subjects).filter((k) => subjects[k].status === "BLIND").sort();
  return { schema: SCHEMA, seq: head, as_of: now, subjects, blind: blindKeys, rejected };
}

function live(e) {
  return {
    status: e.status,
    value: e.value,
    source: e.source,
    ts: e.ts,
    seq: e.seq,
    interval_s: e.interval_s ?? DEFAULT_INTERVAL_S,
    evidence: e.evidence ?? null,
  };
}

function blind(e, reason) {
  return {
    status: "BLIND",
    value: null,
    reason,
    source: isStr(e.source) ? e.source : null,
    ts: typeof e.ts === "number" && Number.isFinite(e.ts) ? e.ts : null,
    seq: e.seq,
    interval_s: typeof e.interval_s === "number" && e.interval_s > 0 ? e.interval_s : DEFAULT_INTERVAL_S,
    evidence: e.evidence ?? null,
  };
}

function blindFrom(s) {
  return { ...s, status: "BLIND", value: null, last_seen_ts: s.ts };
}

/** Canonical JSON: sorted keys at every depth, so two machines hash the same state to the same bytes. */
export function canonical(v) {
  if (v === null || typeof v !== "object") return JSON.stringify(v === undefined ? null : v);
  if (Array.isArray(v)) return `[${v.map(canonical).join(",")}]`;
  return `{${Object.keys(v)
    .sort()
    .map((k) => `${JSON.stringify(k)}:${canonical(v[k])}`)
    .join(",")}}`;
}

/** sha256 over what the state says, not over when it was asked: as_of and rejected are left out. */
export async function snapshotHash(snapshot) {
  const body = canonical({ schema: snapshot.schema, seq: snapshot.seq, subjects: snapshot.subjects });
  const digest = await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(body));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** One line per subject. A BLIND subject prints the word BLIND and its reason, never a number. */
export function render(snapshot, hash) {
  const lines = [`${snapshot.schema} seq=${snapshot.seq} hash=${String(hash).slice(0, 16)} blind=${snapshot.blind.length}`];
  for (const key of Object.keys(snapshot.subjects).sort()) {
    const s = snapshot.subjects[key];
    lines.push(
      s.status === "BLIND"
        ? `${key}  BLIND  (${s.reason})`
        : `${key}  ${s.status}  ${typeof s.value === "string" ? s.value : JSON.stringify(s.value)}`,
    );
  }
  return lines.join("\n");
}

/**
 * The checker the falsifiers run. Returns violations; an empty list means no signal was coerced.
 * It judges the snapshot against the log it claims to fold, so a fold that turns a missing value
 * into 0 is caught here and nowhere else needs to trust it.
 */
export function findCoercions(events, snapshot) {
  const out = [];
  const latest = new Map();
  for (const e of events) {
    if (identifiable(e) && Number.isInteger(e.seq)) {
      const k = keyOf(e);
      if (!latest.has(k) || latest.get(k).seq < e.seq) latest.set(k, e);
    }
  }
  for (const [key, e] of latest) {
    const s = snapshot.subjects[key];
    if (s === undefined) {
      out.push(`${key}: present in the log, absent from the snapshot`);
      continue;
    }
    if (eventProblem(e) !== null && s.status !== "BLIND") out.push(`${key}: malformed event shown as ${s.status}`);
    if (e.status === "BLIND" && s.status !== "BLIND") out.push(`${key}: BLIND event shown as ${s.status}`);
    if (s.status === "BLIND" && s.value !== null) out.push(`${key}: BLIND carries value ${JSON.stringify(s.value)}`);
  }
  for (const [key, s] of Object.entries(snapshot.subjects)) {
    if (s.status !== "BLIND" && (s.value === null || s.value === undefined)) out.push(`${key}: ${s.status} with no value`);
  }
  return out;
}

/** A subject shown as live past STALE_FACTOR of its own interval at `now` is a silent producer shown as healthy. */
export function findStale(snapshot, now) {
  const out = [];
  for (const [key, s] of Object.entries(snapshot.subjects)) {
    if (s.status !== "BLIND" && now - s.ts > STALE_FACTOR * s.interval_s * 1000) {
      out.push(`${key}: ${s.status} but ${Math.round((now - s.ts) / 1000)}s old, interval ${s.interval_s}s`);
    }
  }
  return out;
}

/** Two readers fed one log must print one seq and one hash. Returns violations. */
export function parity(readers) {
  const out = [];
  const [first, ...rest] = readers;
  for (const r of rest) {
    if (r.seq !== first.seq) out.push(`${r.name}: seq ${r.seq} != ${first.name} seq ${first.seq}`);
    if (r.hash !== first.hash) out.push(`${r.name}: hash ${String(r.hash).slice(0, 12)} != ${first.name} hash ${String(first.hash).slice(0, 12)}`);
  }
  return out;
}
