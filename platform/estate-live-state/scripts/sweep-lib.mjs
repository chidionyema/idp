// The Optimus sweep: one producer for the live-state spine. For each metric in
// catalog/optimus-metrics.json it runs the metric's own `measure` command and turns the answer into
// one event. The catalogue's contract: a measure prints exactly `optimus.<name>=<number>`.
//   a number printed on a zero exit  -> DIRECT with that number
//   anything else                    -> BLIND with the reason (timeout, exit code, the measure's own
//                                       "BLIND: ..." line, an unparsable or mismatched line)
// A failed measure is never 0. Commands and the network are injected so the tests run neither.
import { execFile } from "node:child_process";

export const SOURCE = "optimus-sweep";
export const BATCH = 100; // the worker's per-request cap
export const MEASURE_TIMEOUT_MS = 40_000;
export const CONCURRENCY = 6;

const NUMBER = "-?\\d+(?:\\.\\d+)?";
const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** The one number a measure printed for `name`, or null when the output has none or has two. */
export function parseMeasure(name, stdout) {
  const re = new RegExp(`^optimus\\.${escapeRe(name)}=(${NUMBER})\\s*$`, "gm");
  const found = [...String(stdout).matchAll(re)];
  if (found.length !== 1) return null;
  const n = Number(found[0][1]);
  return Number.isFinite(n) ? n : null;
}

const firstLine = (s) => String(s ?? "").split("\n").map((l) => l.trim()).find((l) => l.length > 0) ?? "";
const clip = (s, n = 200) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);

/** One metric and what running it returned, as the event the object will store. */
export function eventFor(metric, res, now, intervalS) {
  const base = { source: SOURCE, kind: "optimus", subject: metric.name, ts: now, interval_s: intervalS };
  const evidence = { unit: metric.unit, better: metric.better, owner: metric.owner, exit: res.code, ms: res.ms };
  const blind = (reason) => ({ ...base, status: "BLIND", reason: clip(reason), evidence });
  if (res.timedOut) return blind(`timeout after ${Math.round(MEASURE_TIMEOUT_MS / 1000)}s`);
  if (res.code !== 0) {
    const said = firstLine(res.stderr) || firstLine(String(res.stdout).split("\n").filter((l) => !l.startsWith("optimus.")).join("\n"));
    return blind(said || `exit ${res.code}`);
  }
  const value = parseMeasure(metric.name, res.stdout);
  if (value === null) return blind(`no single optimus.${metric.name}=<number> line on stdout`);
  return { ...base, status: "DIRECT", value, evidence };
}

/** Default runner. The live-state tokens are stripped so no catalogue command can read them. */
export function runMeasure(argv, { cwd, env = process.env, timeoutMs = MEASURE_TIMEOUT_MS } = {}) {
  const clean = { ...env };
  for (const k of Object.keys(clean)) if (k.startsWith("LIVE_STATE_")) delete clean[k];
  const t0 = Date.now();
  return new Promise((resolve) => {
    execFile(argv[0], argv.slice(1), { cwd, env: clean, timeout: timeoutMs, maxBuffer: 1 << 20 }, (error, stdout, stderr) => {
      const timedOut = Boolean(error && (error.killed || error.signal === "SIGTERM") && Date.now() - t0 >= timeoutMs - 50);
      const code = error ? (typeof error.code === "number" ? error.code : 1) : 0;
      resolve({ code, stdout: String(stdout), stderr: String(stderr || (error && !timedOut ? error.message : "")), timedOut, ms: Date.now() - t0 });
    });
  });
}

/** Run every metric, `concurrency` at a time, and return the events in catalogue order. */
export async function sweep({ metrics, run, now, intervalS = 3600, concurrency = CONCURRENCY }) {
  const events = new Array(metrics.length);
  let next = 0;
  const worker = async () => {
    for (let i = next++; i < metrics.length; i = next++) {
      const m = metrics[i];
      let res;
      try {
        res = await run(m.measure);
      } catch (e) {
        res = { code: 1, stdout: "", stderr: `could not run: ${e.message}`, timedOut: false, ms: 0 };
      }
      events[i] = eventFor(m, res, now(), intervalS);
    }
  };
  await Promise.all(Array.from({ length: Math.max(1, Math.min(concurrency, metrics.length)) }, worker));
  return events;
}

/** The catalogue's metrics, or throws with a reason. A catalogue that cannot be read is not an empty sweep. */
export function metricsOf(catalog) {
  if (catalog === null || typeof catalog !== "object" || !Array.isArray(catalog.metrics) || catalog.metrics.length === 0) {
    throw new Error("catalogue has no metrics list");
  }
  const seen = new Set();
  for (const m of catalog.metrics) {
    if (typeof m?.name !== "string" || !Array.isArray(m.measure) || m.measure.length === 0 || !m.measure.every((a) => typeof a === "string")) {
      throw new Error(`metric ${JSON.stringify(m?.name)} has no measure argv`);
    }
    if (seen.has(m.name)) throw new Error(`metric ${m.name} is listed twice`);
    seen.add(m.name);
  }
  return catalog.metrics;
}

/** POST the events in batches of BATCH. Returns {code, out, err}; 0 only when every batch was accepted whole. */
export async function post({ base, token, events, fetchImpl = fetch }) {
  const out = [];
  const err = [];
  if (typeof token !== "string" || token.length === 0) {
    out.push(`BLIND  not posted  LIVE_STATE_INGEST_TOKEN is not set, so ${events.length} events were measured and sent nowhere`);
    return { code: 2, out, err };
  }
  let accepted = 0;
  for (let i = 0; i < events.length; i += BATCH) {
    const batch = events.slice(i, i + BATCH);
    let res;
    try {
      res = await fetchImpl(`${base}/append`, {
        method: "POST",
        headers: { authorization: `Bearer ${token}`, "content-type": "application/json" },
        body: JSON.stringify(batch),
        signal: AbortSignal.timeout(15_000),
      });
    } catch (e) {
      err.push(`SWEEP FAIL  ${base}/append unreachable: ${e.message}`);
      return { code: 1, out, err };
    }
    if (!res.ok) {
      err.push(`SWEEP FAIL  ${base}/append HTTP ${res.status} after ${accepted} of ${events.length} events`);
      return { code: 1, out, err };
    }
    const body = await res.json().catch(() => null);
    if (body === null || body.accepted !== batch.length) {
      err.push(`SWEEP FAIL  ${base}/append accepted ${body === null ? "?" : body.accepted} of ${batch.length}`);
      return { code: 1, out, err };
    }
    accepted += body.accepted;
    out.push(`ok  /append  accepted=${accepted}/${events.length}  seq=${body.seq}`);
  }
  return { code: 0, out, err };
}

export const tally = (events) => {
  const blind = events.filter((e) => e.status === "BLIND").length;
  return `sweep  metrics=${events.length}  direct=${events.length - blind}  blind=${blind}`;
};
