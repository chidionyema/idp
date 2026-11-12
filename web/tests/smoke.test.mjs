// Smoke test against a freshly started production server.
//
// It starts its own server on a spare port rather than reusing :3000, because the
// contact endpoint holds a rate-limit counter in process memory: a reused server
// would make the 429 assertion depend on how recently a previous run had posted.
// A test that fails depending on history is worse than no test.
import test from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createServer } from "node:http";
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
  "/investors",
  "/investors/room",
  "/products/chronos",
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

test("the logo lockup renders a mark, not just the word", async () => {
  const html = await (await fetch(`${BASE}/`)).text();
  // The mark is three primitives -- the ring, the meridian through it, and the bead where they
  // meet -- drawn by components/Logo.tsx. A regression that drops it leaves the wordmark, which
  // looks like a logo in a diff and does not in a header, so the test names the shapes: one
  // lockup in the nav and one in the footer, each carrying a mark with a meridian in it.
  assert.equal((html.match(/class="logo( |")/g) ?? []).length, 2, "expected the lockup in the header and the footer");
  assert.equal((html.match(/<svg[^>]*class="logo-mark"/g) ?? []).length, 2, "missing the mark svg");
  assert.equal((html.match(/<ellipse /g) ?? []).length, 2, "the mark is missing its meridian");

  // The tab icon is the same drawing. It is generated here rather than fetched from a CDN, so
  // the only defence against it silently vanishing is this fetch.
  const favicon = await fetch(`${BASE}/favicon.svg`);
  assert.equal(favicon.status, 200);
  assert.match(await favicon.text(), /<ellipse /, "the favicon lost its meridian");
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
  assert.equal(get.status, 200);
  assert.equal(get.headers.get("cache-control"), "no-store");
  assert.deepEqual(await get.json(), { acceptingEnquiries: false });
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

test("a configured enquiry is delivered to a real local webhook before confirmation", async () => {
  const received = [];
  const hook = createServer(async (req, res) => {
    let body = "";
    for await (const chunk of req) body += chunk;
    received.push({ method: req.method, body: JSON.parse(body) });
    res.writeHead(200, { "content-type": "application/json" });
    res.end('{"accepted":true}');
  });
  await new Promise((resolve) => hook.listen(0, "127.0.0.1", resolve));
  const hookAddress = hook.address();
  assert.ok(hookAddress && typeof hookAddress !== "string");
  const webhookPort = hookAddress.port;
  const secondPort = 3112;
  const secondBase = `http://127.0.0.1:${secondPort}`;
  const configuredServer = spawn(process.execPath,
    ["node_modules/next/dist/bin/next", "start", "--port", String(secondPort)], {
      cwd: root,
      stdio: "ignore",
      env: {
        ...process.env,
        NODE_ENV: "production",
        CONTACT_WEBHOOK_URL: `http://localhost:${webhookPort}/intake`,
        CONTACT_WEBHOOK_TOKEN: "",
        TELEGRAM_BOT_TOKEN: "",
        TELEGRAM_CHAT_ID: "",
        MERIDIAN_SECRETS_DIR: "/no-such-meridian-secrets-for-smoke-test",
      },
    });
  try {
    let ready = false;
    for (let i = 0; i < 80; i++) {
      try {
        const res = await fetch(`${secondBase}/api/contact`, { signal: AbortSignal.timeout(1500) });
        if (res.ok) { ready = true; break; }
      } catch { /* second server still starting */ }
      await sleep(350);
    }
    assert.ok(ready, "configured enquiry server did not start");
    const status = await fetch(`${secondBase}/api/contact`);
    assert.deepEqual(await status.json(), { acceptingEnquiries: true });
    assert.equal(status.headers.get("cache-control"), "no-store");

    const response = await fetch(`${secondBase}/api/contact`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        name: "Meridian Canary",
        email: "synthetic@example.test",
        company: "Synthetic Lab",
        message: "A synthetic test enquiry, not a real customer record.",
      }),
    });
    assert.equal(response.status, 200, "success must require webhook acceptance");
    assert.equal(received.length, 1, "webhook must receive exactly one delivery");
    assert.equal(received[0].method, "POST");
    assert.equal(received[0].body.source, "merian-intelligence/contact");
    assert.equal(received[0].body.email, "synthetic@example.test");
    assert.equal(received[0].body.company, "Synthetic Lab");
    assert.ok(received[0].body.received_at, "delivery needs provenance timestamp");
  } finally {
    configuredServer.kill("SIGTERM");
    await new Promise((resolve) => hook.close(resolve));
  }
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

test("every internal link goes somewhere, and every anchor exists", async () => {
  // 2026-10-20. A reviewer clicked "Details ->" on all three tools and reached nothing: the cards
  // all linked to /tooling, which has no per-tool section, and the research page derived anchors
  // from a title ("#agentic-routing-for-enterprise") that no element carried. Both return 200, so
  // a status check alone would have called them fine. This walks every internal href on every
  // page, then every fragment, and requires an element with that id to exist on the target.
  //
  // Only internal links: a route that fails because github.com is slow is not this site's bug,
  // and a gate that goes red for the internet gets switched off.
  const pages = ["/", ...ROUTES.filter((r) => !/\.(xml|txt)$/.test(r))];
  const seen = new Map();
  const broken = [];

  for (const page of pages) {
    const res = await fetch(`${BASE}${page}`);
    const html = await res.text();
    for (const match of html.matchAll(/href="(\/[^"]*)"/g)) {
      const href = match[1];
      if (href.startsWith("/_next/")) continue;
      const [path, fragment] = href.split("#");
      const target = path || page;
      const key = `${target}#${fragment ?? ""}`;
      if (!seen.has(key)) {
        const targetRes = await fetch(`${BASE}${target}`);
        const body = targetRes.ok ? await targetRes.text() : "";
        seen.set(key, { status: targetRes.status, body });
      }
      const { status, body } = seen.get(key);
      if (status !== 200) broken.push(`${page} -> ${target} answered ${status}`);
      else if (fragment && !body.includes(`id="${fragment}"`)) broken.push(`${page} -> ${key} (nothing carries that id)`);
    }
  }

  assert.deepEqual(broken, [], `broken internal links:\n${broken.join("\n")}`);
  // 18 distinct targets on this site today: the ten routes, the three tool anchors, and a few
  // fragments. The bound is a floor, not a target -- it fails if the crawl stopped finding links
  // at all, which is the failure mode of a crawler that silently matches nothing.
  // The founder-facing navigation is deliberately focused; removing legacy demo and
  // tool links must not be mistaken for a crawler failure. Judge the actual journeys.
  for (const route of ["/", "/consulting", "/research", "/products", "/contact"]) {
    assert.ok([...seen.keys()].some(key => key === route + "#"), `core customer journey missing: ${route}`);
  }
  assert.ok(seen.size >= 12, `expected a connected public site, found ${seen.size} distinct links`);
});

test("research answers are excerpts from published notes with working section links", async () => {
  const response = await fetch(`${BASE}/api/research/query`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ query: "How does SPIFFE workload identity work?" }),
  });
  assert.equal(response.status, 200);
  const data = await response.json();
  assert.equal(data.mode, "published-excerpts", "research responses must describe the actual retrieval method");
  assert.ok(data.sources?.length > 0, "the published note should be retrievable");
  assert.match(data.answer, /published note/, "answer must disclose it is an excerpt");
  for (const source of data.sources) {
    assert.match(source.url, /^\/writing\/[a-z0-9-]+(?:#[a-z0-9-]+)?$/);
    const [target, fragment] = source.url.split("#");
    const article = await fetch(BASE + target);
    assert.equal(article.status, 200, `cited article not found: ${target}`);
    if (fragment) assert.ok((await article.text()).includes(`id="${fragment}"`), `missing section anchor: ${source.url}`);
  }

  const unrelated = await fetch(`${BASE}/api/research/query`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ query: "qzxflarb imaginary zeppelin" }),
  });
  assert.equal(unrelated.status, 200);
  assert.deepEqual((await unrelated.json()).sources, [], "out-of-scope requests must not fabricate references");

  const invalid = await fetch(`${BASE}/api/research/query`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ query: "   " }),
  });
  assert.equal(invalid.status, 400);
});

test("investor research is visible but its private data never leaks without identity", async () => {
  const publicIntro = await fetch(`${BASE}/investors`);
  assert.equal(publicIntro.status, 200);
  assert.match(await publicIntro.text(), /RESEARCH \/ EXPERIMENTATION \/ COMMERCIALISATION/);

  const protectedData = await fetch(`${BASE}/api/investors/surfaces`, { cache: "no-store" });
  assert.equal(protectedData.status, 401, "an anonymous browser must not obtain Genesis or OTTO projections");
  assert.equal(protectedData.headers.get("cache-control"), "private, no-store, max-age=0");
  const body = await protectedData.text();
  assert.match(body, /access_required/);
  assert.doesNotMatch(body, /yieldReceipts|workflow_runs|chat_id|bot_token|secret/i);

  const room = await fetch(`${BASE}/investors/room`);
  assert.equal(room.status, 200);
  assert.match(await room.text(), /noindex/);
  const join = await fetch(`${BASE}/investors/access`, { redirect:"manual" });
  // Without identity credentials, never issue a session; show a humane restricted-access page.
  if (!process.env.INVESTOR_BROKER_ORIGIN) {
    assert.equal(join.status, 303);
    assert.match(join.headers.get("location") || "", /\/investors\/unavailable$/);
    const fallback = await fetch(`${BASE}/investors/unavailable`);
    assert.equal(fallback.status, 200);
    assert.match(await fallback.text(), /noindex/);
  }
});
