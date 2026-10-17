// Smoke test against a freshly started production server.
//
// It starts its own server on a spare port rather than reusing :3000, because the
// contact endpoint holds a rate-limit counter in process memory: a reused server
// would make the 429 assertion depend on how recently a previous run had posted.
// A test that fails depending on history is worse than no test.
import test from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const PORT = 3111;
const BASE = `http://127.0.0.1:${PORT}`;

const ROUTES = [
  "/",
  "/case-studies",
  "/consulting",
  "/contact",
  "/demo",
  "/research",
  "/tooling",
  "/writing",
  "/tools/cost-calculator",
  "/tools/trace-explorer",
  "/sitemap.xml",
  "/robots.txt",
];

let server;

async function waitForServer(deadlineMs = 40_000) {
  const started = Date.now();
  while (Date.now() - started < deadlineMs) {
    try {
      const res = await fetch(`${BASE}/`, { signal: AbortSignal.timeout(2000) });
      if (res.ok) return;
    } catch {
      /* not up yet */
    }
    await sleep(400);
  }
  throw new Error(`server did not become ready on ${BASE} within ${deadlineMs}ms`);
}

test.before(async () => {
  assert.ok(existsSync(path.join(root, ".next", "BUILD_ID")), "run `npm run build` before the smoke test");
  server = spawn(process.execPath, ["node_modules/next/dist/bin/next", "start", "--port", String(PORT)], {
    cwd: root,
    stdio: "ignore",
    env: { ...process.env, NODE_ENV: "production", CONTACT_WEBHOOK_URL: "" },
  });
  await waitForServer();
});

test.after(() => {
  server?.kill("SIGTERM");
});

test("every public route responds 200", async () => {
  for (const route of ROUTES) {
    const res = await fetch(`${BASE}${route}`);
    assert.equal(res.status, 200, `${route} returned ${res.status}`);
  }
});

test("the article route renders a real post", async () => {
  const sitemap = await (await fetch(`${BASE}/sitemap.xml`)).text();
  const match = sitemap.match(/<loc>[^<]*\/(writing\/[a-z0-9-]+)<\/loc>/);
  assert.ok(match, "expected at least one article in the sitemap");
  const res = await fetch(`${BASE}/${match[1]}`);
  assert.equal(res.status, 200);
  assert.match(await res.text(), /<h1/);
});

test("security headers are present on every route", async () => {
  const required = [
    "content-security-policy",
    "strict-transport-security",
    "x-content-type-options",
    "x-frame-options",
    "referrer-policy",
    "permissions-policy",
  ];
  const res = await fetch(`${BASE}/`);
  for (const header of required) {
    assert.ok(res.headers.get(header), `missing ${header}`);
  }
  assert.equal(res.headers.get("x-powered-by"), null, "x-powered-by should not be advertised");
});

test("content is readable without JavaScript", async () => {
  const html = await (await fetch(`${BASE}/`)).text();
  // The reveal animation starts at opacity 0; without scripting it must be undone.
  assert.match(html, /<noscript><style>[^<]*data-reveal[^<]*opacity:1/, "missing noscript override for the reveal animation");
  assert.match(html, /skip-link/, "missing skip link");
  assert.match(html, /id="main"/, "main landmark needs an id for the skip link");
});

test("contact endpoint refuses malformed requests", async () => {
  const wrongType = await fetch(`${BASE}/api/contact`, { method: "POST", body: "not json", headers: { "content-type": "text/plain" } });
  assert.equal(wrongType.status, 415);

  const badJson = await fetch(`${BASE}/api/contact`, { method: "POST", body: "{", headers: { "content-type": "application/json" } });
  assert.equal(badJson.status, 400);

  const invalid = await fetch(`${BASE}/api/contact`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ name: "", email: "nope", message: "x" }),
  });
  assert.equal(invalid.status, 400);
  const body = await invalid.json();
  assert.equal(body.error, "invalid_input");
  assert.ok(body.errors.email && body.errors.name && body.errors.message);

  const get = await fetch(`${BASE}/api/contact`);
  assert.equal(get.status, 405);
});

test("a honeypot submission is accepted silently", async () => {
  const res = await fetch(`${BASE}/api/contact`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      name: "Bot",
      email: "bot@example.com",
      message: "buy cheap things from our website today",
      website: "http://spam.example",
    }),
  });
  assert.equal(res.status, 200);
});

test("a valid submission with no delivery path configured fails loudly", async () => {
  const res = await fetch(`${BASE}/api/contact`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      name: "Dana Whitfield",
      email: "dana@example.com",
      message: "We run three retrieval pipelines and p95 is drifting upward.",
    }),
  });
  // 503, not 200: an unconfigured deployment must not look like a successful one.
  assert.equal(res.status, 503);
  assert.equal((await res.json()).error, "delivery_not_configured");
});

test("the endpoint rate-limits a caller that keeps posting", async () => {
  const payload = JSON.stringify({
    name: "Dana Whitfield",
    email: "dana@example.com",
    message: "We run three retrieval pipelines and p95 is drifting upward.",
  });
  let saw429 = false;
  for (let i = 0; i < 8 && !saw429; i++) {
    const res = await fetch(`${BASE}/api/contact`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: payload,
    });
    if (res.status === 429) {
      saw429 = true;
      assert.ok(Number(res.headers.get("retry-after")) > 0, "429 should carry a Retry-After");
    }
  }
  assert.ok(saw429, "expected the limiter to engage within 8 attempts");
});
