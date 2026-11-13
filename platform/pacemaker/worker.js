// estate pacemaker, Cloudflare home (idp#8026; ADR 0037: three homes, two providers).
//
// GitHub's scheduler delivered 13 of ~176 expected idp cron runs on 2026-11-12/13 (7%), while
// workflow_dispatch always started. This Worker's cron is a second, independent clock: every tick it
// asks GitHub to run .github/workflows/estate-pacemaker.yml with home=cloudflare. The judgement
// (which clock missed, which home is silent) lives once, in bin/estate-pacemaker; this file only
// knocks. It holds a GitHub App key as a Worker secret and mints a one-hour token per tick, scoped
// by the App's installation, never stored.
//
// GET /healthz answers "ok <last tick ISO> <last status>" so any home can see this one is alive.

const GH = "https://api.github.com";
const UA = "estate-pacemaker-cloudflare";

function b64url(bytes) {
  let s = "";
  const arr = new Uint8Array(bytes);
  for (let i = 0; i < arr.length; i++) s += String.fromCharCode(arr[i]);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function pemToPkcs8(pem) {
  const body = pem.replace(/-----[^-]+-----/g, "").replace(/\s+/g, "");
  const raw = atob(body);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out.buffer;
}

export async function appJwt(appId, pkcs8Pem, nowSec) {
  const enc = new TextEncoder();
  const header = b64url(enc.encode(JSON.stringify({ alg: "RS256", typ: "JWT" })));
  const payload = b64url(enc.encode(JSON.stringify({ iat: nowSec - 60, exp: nowSec + 540, iss: String(appId) })));
  const key = await crypto.subtle.importKey(
    "pkcs8", pemToPkcs8(pkcs8Pem), { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", key, enc.encode(`${header}.${payload}`));
  return `${header}.${payload}.${b64url(sig)}`;
}

async function gh(path, token, init = {}) {
  const r = await fetch(GH + path, {
    ...init,
    headers: { Authorization: `Bearer ${token}`, Accept: "application/vnd.github+json", "User-Agent": UA,
               "X-GitHub-Api-Version": "2022-11-28", ...(init.headers || {}) },
  });
  return r;
}

export async function knock(env, nowSec) {
  const [owner, repo] = env.REPO.split("/");
  const jwt = await appJwt(env.APP_ID, env.APP_PEM_PKCS8, nowSec);
  const inst = await gh(`/repos/${owner}/${repo}/installation`, jwt);
  if (!inst.ok) return `FAIL installation ${inst.status}`;
  const { id } = await inst.json();
  const tok = await gh(`/app/installations/${id}/access_tokens`, jwt, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repositories: [repo], permissions: { actions: "write" } }),
  });
  if (!tok.ok) return `FAIL token ${tok.status}`;
  const { token } = await tok.json();
  const d = await gh(`/repos/${owner}/${repo}/actions/workflows/estate-pacemaker.yml/dispatches`, token, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ref: "main", inputs: { home: "cloudflare" } }),
  });
  return d.status === 204 ? "ok dispatched" : `FAIL dispatch ${d.status}`;
}

let last = { at: null, status: "no tick yet" };

export default {
  async scheduled(_event, env, ctx) {
    const now = Math.floor(Date.now() / 1000);
    const status = await knock(env, now).catch((e) => `FAIL ${String(e).slice(0, 120)}`);
    last = { at: new Date(now * 1000).toISOString(), status };
    if (env.STATE) ctx.waitUntil(env.STATE.put("last", JSON.stringify(last)));
  },
  async fetch(req, env) {
    const url = new URL(req.url);
    if (url.pathname !== "/healthz") return new Response("estate pacemaker\n", { status: 404 });
    const stored = env.STATE ? await env.STATE.get("last") : null;
    const l = stored ? JSON.parse(stored) : last;
    return new Response(`ok ${l.at || "-"} ${l.status}\n`, { headers: { "content-type": "text/plain" } });
  },
};
