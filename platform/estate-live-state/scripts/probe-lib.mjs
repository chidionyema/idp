// The probe's logic, with fetch injected so the tests need no server and no child process.
// Returns {code, out, err}: code 0 only on proof, 1 on any failure, 2 when it could not look (BLIND).
export async function probe({ base, token, fetchImpl = fetch, now = Date.now }) {
  const out = [];
  const err = [];
  const fail = (why) => {
    err.push(`PROBE FAIL  ${base}  ${why}`);
    return { code: 1, out, err };
  };
  const get = (path, headers) => fetchImpl(`${base}${path}`, { headers, signal: AbortSignal.timeout(15_000) });

  const t0 = now();
  let health;
  try {
    health = await get("/health");
  } catch (e) {
    return fail(`/health unreachable: ${e.message}`);
  }
  if (!health.ok) return fail(`/health HTTP ${health.status}`);
  const h = await health.json();
  if (h.schema !== "estate-live-state.v1") return fail(`/health schema ${JSON.stringify(h.schema)}`);
  if (!h.commit_sha || h.commit_sha === "dev-local") return fail(`/health commit_sha ${JSON.stringify(h.commit_sha)} is not a deployed sha`);
  out.push(`ok  /health  commit_sha=${h.commit_sha}  zone=${h.zone}  ${now() - t0}ms`);

  if (!token) {
    out.push("BLIND  /snapshot  LIVE_STATE_READ_TOKEN not set, so the snapshot was not read");
    return { code: 2, out, err };
  }
  const t1 = now();
  let res;
  try {
    res = await get("/snapshot", { authorization: `Bearer ${token}` });
  } catch (e) {
    return fail(`/snapshot unreachable: ${e.message}`);
  }
  if (!res.ok) return fail(`/snapshot HTTP ${res.status}`);
  const s = await res.json();
  if (s.schema !== "estate-live-state.v1" || typeof s.hash !== "string") return fail("/snapshot is not estate-live-state.v1");
  out.push(`ok  /snapshot  seq=${s.seq}  hash=${s.hash.slice(0, 16)}  subjects=${Object.keys(s.subjects).length}  blind=${s.blind.length}  ${now() - t1}ms`);
  return { code: 0, out, err };
}
