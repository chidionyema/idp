// The laptop terminal reader's logic, with fetch injected so the tests need no server and no child
// process. It holds no state of its own: it asks the worker for the snapshot, recomputes the hash
// itself, and prints the same lines every other reader prints (render in src/fold.mjs).
// Returns {code, out, err}: 0 = the snapshot was read and its hash matches what this reader computed,
// 1 = a failure (unreachable, refused, malformed, or a hash this reader cannot reproduce),
// 2 = BLIND, it could not look (no read token), and it printed no state at all.
import { render, snapshotHash, findStale } from "../src/fold.mjs";

export async function watch({ base, token, fetchImpl = fetch, now = Date.now }) {
  const out = [];
  const err = [];
  const fail = (why) => {
    err.push(`WATCH FAIL  ${base}  ${why}`);
    return { code: 1, out: [], err };
  };
  if (typeof token !== "string" || token.length === 0) {
    out.push("BLIND  snapshot  LIVE_STATE_READ_TOKEN is not set, so no state was read");
    return { code: 2, out, err };
  }
  let res;
  try {
    res = await fetchImpl(`${base}/snapshot`, {
      headers: { authorization: `Bearer ${token}` },
      signal: AbortSignal.timeout(15_000),
    });
  } catch (e) {
    return fail(`unreachable: ${e.message}`);
  }
  if (!res.ok) return fail(`HTTP ${res.status}`);
  let snap;
  try {
    snap = await res.json();
  } catch {
    return fail("body is not JSON");
  }
  if (snap === null || typeof snap !== "object" || snap.schema !== "estate-live-state.v1") return fail("not estate-live-state.v1");
  if (typeof snap.hash !== "string" || snap.subjects === null || typeof snap.subjects !== "object" || !Array.isArray(snap.blind)) {
    return fail("snapshot is missing hash, subjects or blind");
  }
  const mine = await snapshotHash(snap);
  if (mine !== snap.hash) return fail(`hash ${snap.hash.slice(0, 12)} is not what this reader computes (${mine.slice(0, 12)})`);
  const stale = findStale(snap, now());
  if (stale.length > 0) return fail(`shown as live but silent past its interval: ${stale.join("; ")}`);
  out.push(...render(snap, snap.hash).split("\n"));
  out.push(`parity  seq=${snap.seq}  hash=${snap.hash}`);
  return { code: 0, out, err };
}
