import { SCHEMA } from "./fold.mjs";
import { EstateLiveStateDO } from "./live-state-do.mjs";

export { EstateLiveStateDO };

const json = (body, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

/** Compare two secrets without leaking where they differ: hash both, then compare the digests. */
async function sameSecret(given, wanted) {
  const enc = new TextEncoder();
  const [a, b] = await Promise.all([
    crypto.subtle.digest("SHA-256", enc.encode(given)),
    crypto.subtle.digest("SHA-256", enc.encode(wanted)),
  ]);
  const x = new Uint8Array(a);
  const y = new Uint8Array(b);
  let diff = 0;
  for (let i = 0; i < x.length; i++) diff |= x[i] ^ y[i];
  return diff === 0;
}

/** Fail closed: a missing secret refuses every caller, it never lets them in. */
async function authorize(request, secret) {
  if (typeof secret !== "string" || secret.length === 0) return { ok: false, status: 503, error: "secret not provisioned" };
  const header = request.headers.get("authorization") ?? "";
  const given = header.startsWith("Bearer ") ? header.slice(7) : "";
  if (given.length === 0 || !(await sameSecret(given, secret))) return { ok: false, status: 401, error: "unauthorized" };
  return { ok: true };
}

export default {
  async fetch(request, env) {
    const { pathname } = new URL(request.url);

    if (pathname === "/health" && request.method === "GET") {
      return json({ ok: true, schema: SCHEMA, zone: env.DEPLOYMENT_ZONE ?? null, commit_sha: env.COMMIT_SHA ?? null });
    }

    const stub = env.LIVE_STATE.get(env.LIVE_STATE.idFromName("estate"));

    if (pathname === "/append" && request.method === "POST") {
      const auth = await authorize(request, env.LIVE_STATE_INGEST_TOKEN);
      return auth.ok ? stub.fetch(request) : json({ error: auth.error }, auth.status);
    }
    if ((pathname === "/snapshot" && request.method === "GET") || pathname === "/ws") {
      const auth = await authorize(request, env.LIVE_STATE_READ_TOKEN);
      return auth.ok ? stub.fetch(request) : json({ error: auth.error }, auth.status);
    }
    return json({ error: "not found" }, 404);
  },
};
