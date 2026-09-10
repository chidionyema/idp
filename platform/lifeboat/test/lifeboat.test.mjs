// These tests grade behaviour, never prose (R76). Every one of them asserts on a status
// code, a chosen home, a lane name or the shape of what got sent to a vendor -- nothing
// asserts that a comment or a message says a particular sentence.
//
// No network. Every outbound call is a stub, so the suite is honest on a plane and cannot
// go red because Groq is having a bad afternoon.
import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";

import worker, { handleTelegram } from "../src/index.js";
import {
  HOMES, LANES, chooseOrder, exhaust, headroom, keyMatches, resetLanes, spend, think, tryLane,
} from "../src/homes.js";

// The lane ledger is module state, so without this one test's 429 sets the running order for
// every test after it -- which is correct behaviour and useless test isolation.
beforeEach(() => resetLanes());

const SECRET = "webhook-secret-value";
const KEY = "lifeboat-bearer-value";

// A vendor that answers. Shaped like an OpenAI chat completion because every lane but
// Workers AI speaks that.
const ok = (content = "answer") => ({
  ok: true,
  status: 200,
  json: async () => ({ choices: [{ index: 0, message: { role: "assistant", content } }] }),
});
const dead = (status = 503) => ({ ok: false, status, json: async () => ({}) });

function env(over = {}) {
  return {
    LIFEBOAT_KEY: KEY,
    TELEGRAM_WEBHOOK_SECRET: SECRET,
    TELEGRAM_BOT_TOKEN: "bot-token",
    GROQ_API_KEY: "groq-key",
    GEMINI_API_KEY: "gemini-key",
    OPENROUTER_API_KEY: "openrouter-key",
    ...over,
  };
}

function tgRequest(secret = SECRET) {
  return new Request("https://lifeboat.example/webhook/telegram", {
    method: "POST",
    headers: { "x-telegram-bot-api-secret-token": secret },
  });
}
const update = (text = "how is the estate") =>
  JSON.stringify({ message: { chat: { id: 42 }, text } });

// A stub fetch that records every call and answers from a routing table keyed on hostname.
function recorder(routes) {
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url: String(url), init });
    const host = new URL(String(url)).hostname;
    const handler = routes[host];
    if (!handler) throw new Error(`no stub for ${host}`);
    return typeof handler === "function" ? handler(init) : handler;
  };
  return { calls, fetchImpl };
}

test("a wrong webhook secret is refused before the body is looked at", async () => {
  const res = await handleTelegram(tgRequest("wrong"), env(), "not even json");
  assert.equal(res.status, 401);
});

test("the constant-time compare rejects a prefix, a different length and an empty expectation", () => {
  assert.equal(keyMatches("abc", "abc"), true);
  assert.equal(keyMatches("ab", "abc"), false);
  assert.equal(keyMatches("abcd", "abc"), false);
  assert.equal(keyMatches("", ""), false); // an unset secret must never match an empty header
  assert.equal(keyMatches("abc", ""), false);
  assert.equal(keyMatches(undefined, "abc"), false);
});

test("home 1 takes the turn when the cluster answers, and no vendor is called at all", async () => {
  const { calls, fetchImpl } = recorder({ "otto.origin": { ok: true, status: 200 } });
  const res = await handleTelegram(
    tgRequest(),
    env({ ORIGIN_WEBHOOK_URL: "https://otto.origin/webhook/telegram" }),
    update(),
    fetchImpl,
  );
  assert.equal(res.status, 200);
  assert.equal((await res.json()).home, HOMES[0]);
  assert.equal(calls.length, 1); // the cluster, and nothing else
});

test("the update reaches home 1 byte for byte, with the secret header re-presented", async () => {
  const { calls, fetchImpl } = recorder({ "otto.origin": { ok: true, status: 200 } });
  const raw = update("verbatim body");
  await handleTelegram(
    tgRequest(),
    env({ ORIGIN_WEBHOOK_URL: "https://otto.origin/webhook/telegram" }),
    raw,
    fetchImpl,
  );
  assert.equal(calls[0].init.body, raw);
  assert.equal(calls[0].init.headers["x-telegram-bot-api-secret-token"], SECRET);
});

test("a dead cluster falls to home 3 when the MacBook has a door", async () => {
  const { calls, fetchImpl } = recorder({
    "otto.origin": dead(),
    "mac.ts.net": { ok: true, status: 200 },
  });
  const res = await handleTelegram(
    tgRequest(),
    env({
      ORIGIN_WEBHOOK_URL: "https://otto.origin/webhook/telegram",
      MACBOOK_WEBHOOK_URL: "https://mac.ts.net/webhook/telegram",
    }),
    update(),
    fetchImpl,
  );
  assert.equal((await res.json()).home, HOMES[2]);
  assert.equal(calls.length, 2);
});

test("with both other homes gone the edge answers on its own first lane and replies to Telegram", async () => {
  const { calls, fetchImpl } = recorder({
    "otto.origin": dead(),
    "api.groq.com": ok("I can't see the estate right now."),
    "api.telegram.org": { ok: true, status: 200 },
  });
  const res = await handleTelegram(
    tgRequest(),
    env({ ORIGIN_WEBHOOK_URL: "https://otto.origin/webhook/telegram" }),
    update(),
    fetchImpl,
  );
  const body = await res.json();
  assert.equal(res.status, 200);
  assert.equal(body.home, HOMES[1]);
  assert.equal(body.lane, "groq");
  const sent = calls.find((c) => c.url.includes("api.telegram.org"));
  assert.ok(sent, "the founder was actually spoken to");
  assert.equal(JSON.parse(sent.init.body).chat_id, 42);
});

test("a spent first vendor is stepped over silently and the next one takes the turn", async () => {
  const { fetchImpl } = recorder({
    "otto.origin": dead(),
    "api.groq.com": dead(429), // free tier exhausted, the founder's exact worry
    "generativelanguage.googleapis.com": ok(),
    "api.telegram.org": { ok: true, status: 200 },
  });
  const res = await handleTelegram(
    tgRequest(),
    env({ ORIGIN_WEBHOOK_URL: "https://otto.origin/webhook/telegram" }),
    update(),
    fetchImpl,
  );
  assert.equal((await res.json()).lane, "gemini");
});

test("a lane whose key was never set is skipped rather than failing the ladder", async () => {
  const { calls, fetchImpl } = recorder({
    "otto.origin": dead(),
    "generativelanguage.googleapis.com": ok(),
    "api.telegram.org": { ok: true, status: 200 },
  });
  const res = await handleTelegram(
    tgRequest(),
    env({ ORIGIN_WEBHOOK_URL: "https://otto.origin/webhook/telegram", GROQ_API_KEY: undefined }),
    update(),
    fetchImpl,
  );
  assert.equal((await res.json()).lane, "gemini");
  assert.ok(!calls.some((c) => c.url.includes("api.groq.com")));
});

test("Workers AI is used with no key and no fetch when the vendors ahead of it are down", async () => {
  let asked = null;
  const { calls, fetchImpl } = recorder({
    "otto.origin": dead(),
    "api.groq.com": dead(),
    "generativelanguage.googleapis.com": dead(),
    "api.telegram.org": { ok: true, status: 200 },
  });
  const res = await handleTelegram(
    tgRequest(),
    env({
      ORIGIN_WEBHOOK_URL: "https://otto.origin/webhook/telegram",
      AI: { run: async (model, input) => ((asked = { model, input }), { response: "from cf silicon" }) },
    }),
    update(),
    fetchImpl,
  );
  assert.equal((await res.json()).lane, "workers-ai");
  assert.equal(asked.model, "@cf/meta/llama-3.3-70b-instruct-fp8-fast");
  // It ran in-process: no fetch was made to any inference host for this lane.
  assert.ok(!calls.some((c) => c.url.includes("openrouter")));
});

test("every home and every lane silent still returns 200, because a non-2xx makes Telegram redeliver forever", async () => {
  const { fetchImpl } = recorder({
    "otto.origin": dead(),
    "api.groq.com": dead(),
    "generativelanguage.googleapis.com": dead(),
    "openrouter.ai": dead(),
    "api.telegram.org": { ok: true, status: 200 },
  });
  const res = await handleTelegram(
    tgRequest(),
    env({ ORIGIN_WEBHOOK_URL: "https://otto.origin/webhook/telegram" }),
    update(),
    fetchImpl,
  );
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.equal(body.lane, null);
  assert.equal(body.tried.length, LANES.length);
});

test("an update with nothing answerable in it is still 200 and calls no vendor", async () => {
  const { calls, fetchImpl } = recorder({ "otto.origin": dead() });
  const res = await handleTelegram(
    tgRequest(),
    env({ ORIGIN_WEBHOOK_URL: "https://otto.origin/webhook/telegram" }),
    JSON.stringify({ message: { chat: { id: 42 } } }), // a sticker: no text
    fetchImpl,
  );
  assert.equal(res.status, 200);
  assert.equal(calls.length, 1);
});

test("a cluster that hangs does not hang the turn: a thrown fetch is just the next home", async () => {
  const fetchImpl = async (url) => {
    if (String(url).includes("otto.origin")) throw Object.assign(new Error("timed out"), { name: "TimeoutError" });
    if (String(url).includes("api.groq.com")) return ok();
    return { ok: true, status: 200 };
  };
  const res = await handleTelegram(
    tgRequest(),
    env({ ORIGIN_WEBHOOK_URL: "https://otto.origin/webhook/telegram" }),
    update(),
    fetchImpl,
  );
  assert.equal((await res.json()).lane, "groq");
});

test("the brain refuses a caller with no key and serves one with the right key", async () => {
  const e = env();
  const unauth = await worker.fetch(
    new Request("https://lifeboat.example/v1/chat/completions", {
      method: "POST",
      body: JSON.stringify({ messages: [{ role: "user", content: "hi" }] }),
    }),
    e,
  );
  assert.equal(unauth.status, 401);
});

test("health touches no vendor, reads no key, and names the three homes", async () => {
  const res = await worker.fetch(new Request("https://lifeboat.example/health"), {});
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.deepEqual(body.homes, HOMES);
  assert.equal(body.homes.length, 3);
});

test("the ladder is four lanes at four different vendors, so one vendor's limit cannot end it", async () => {
  const hosts = LANES.filter((l) => l.url).map((l) => new URL(l.url).hostname);
  assert.equal(new Set(hosts).size, hosts.length);
  assert.ok(LANES.some((l) => l.binding), "one lane runs in-process with no network");
});

test("a vendor's non-2xx never leaks upward as a lane answer", async () => {
  const out = await tryLane(LANES[0], env(), { messages: [{ role: "user", content: "x" }] }, async () => dead(500));
  assert.equal(out, null);
});

test("a vendor answering 200 with no choices is treated as no answer", async () => {
  const out = await tryLane(
    LANES[0],
    env(),
    { messages: [{ role: "user", content: "x" }] },
    async () => ({ ok: true, status: 200, json: async () => ({ choices: [] }) }),
  );
  assert.equal(out, null);
});

test("tools and temperature reach the vendor when the caller sent them", async () => {
  let seen = null;
  await tryLane(
    LANES[0],
    env(),
    { messages: [{ role: "user", content: "x" }], tools: [{ type: "function" }], temperature: 0.2 },
    async (_u, init) => ((seen = JSON.parse(init.body)), ok()),
  );
  assert.equal(seen.temperature, 0.2);
  assert.equal(seen.tools.length, 1);
});

test("every vendor call carries a user agent, because Groq answers 403 without one", async () => {
  let headers = null;
  await tryLane(LANES[0], env(), { messages: [{ role: "user", content: "x" }] }, async (_u, init) => {
    headers = init.headers;
    return ok();
  });
  assert.ok(headers["user-agent"]);
});

test("think reports which lanes it tried when none of them answered", async () => {
  const { tried, out } = await think(env({ AI: undefined }), { messages: [{ role: "user", content: "x" }] }, async () => dead());
  assert.equal(out, undefined);
  assert.equal(tried.length, LANES.length);
});


// --- the chooser --------------------------------------------------------------------------

test("with every lane untouched the declared quality order is what runs", () => {
  assert.deepEqual(chooseOrder(Date.now()).map((l) => l.name),
                   ["groq", "gemini", "workers-ai", "kaggle", "openrouter"]);
});

test("a 429 takes a lane out of the running until its window rolls, it does not just skip it once", async () => {
  const { fetchImpl } = recorder({ "api.groq.com": dead(429) });
  await tryLane(LANES[0], env(), { messages: [] }, fetchImpl);
  assert.equal(headroom(LANES[0]), 0);
  assert.equal(chooseOrder(Date.now())[0].name, "gemini");
  // and it comes back on its own once the day has rolled, with nothing to reset it by hand
  assert.equal(chooseOrder(Date.now() + 86_400_001)[0].name, "groq");
});

test("the lane with the most headroom relative to its OWN budget takes the turn", () => {
  // groq is down to 100 of its 1,000 and gemini to 150 of its 1,500 -- a tenth each. The
  // untouched lane is openrouter, which has 50 requests left in total, half of what groq has.
  // It goes first anyway, and that is the whole idea: absolute headroom would keep draining
  // the big lane until it was empty and leave the small one to expire unspent.
  spend(LANES[0], Date.now(), { get: () => "100" });
  spend(LANES[1], Date.now(), { get: () => "150" });
  const order = chooseOrder(Date.now()).map((l) => l.name);
  assert.equal(order[0], "openrouter");
  assert.ok(order.indexOf("openrouter") < order.indexOf("groq"));
});

test("one request through a big lane does not hand the turn to a small one", () => {
  spend(LANES[0]);   // 999 of 1,000 left
  assert.equal(chooseOrder(Date.now())[0].name, "groq");
});

test("the vendor's own count is believed over anything counted here", () => {
  spend(LANES[0], Date.now(), { get: (h) => (h === "x-ratelimit-remaining-requests" ? "7" : null) });
  assert.equal(headroom(LANES[0]), 7 / 1000);
});

test("the unmetered in-process lane keeps its declared rank however the others are sorted", () => {
  exhaust(LANES[0]);
  exhaust(LANES[1]);
  assert.equal(chooseOrder(Date.now()).findIndex((l) => l.name === "workers-ai"), 2);
});

test("a spent lane is skipped and a live one answers, without the spent lane being fetched", async () => {
  exhaust(LANES[0]);
  const { calls, fetchImpl } = recorder({ "generativelanguage.googleapis.com": ok("from gemini") });
  const { lane } = await think(env({ AI: undefined }), { messages: [] }, fetchImpl);
  assert.equal(lane, "gemini");
  assert.ok(!calls.some((c) => c.url.includes("groq")));
});

// --------------------------------------------------------------------------------------
// The GPU lane nobody bills for.

test("a lane whose address lives in the environment is fetched at that address", async () => {
  const kaggle = LANES.find((l) => l.name === "kaggle");
  let asked = null;
  const out = await tryLane(
    kaggle,
    { KAGGLE_LANE_KEY: "k", KAGGLE_LANE_URL: "https://gpu.example/v1/chat/completions" },
    { messages: [{ role: "user", content: "hi" }] },
    async (url) => {
      asked = url;
      return { ok: true, status: 200, headers: new Headers(), json: async () => ({ choices: [{ message: { content: "yes" } }] }) };
    },
  );
  assert.equal(asked, "https://gpu.example/v1/chat/completions");
  assert.equal(out.choices[0].message.content, "yes");
});

test("the same lane with a key but no address is skipped, not fetched against undefined", async () => {
  const kaggle = LANES.find((l) => l.name === "kaggle");
  let fetched = false;
  const out = await tryLane(
    kaggle,
    { KAGGLE_LANE_KEY: "k" },
    { messages: [{ role: "user", content: "hi" }] },
    async () => { fetched = true; throw new Error("must not be reached"); },
  );
  assert.equal(out, null);
  assert.equal(fetched, false, "a lane with no address must cost no request");
});

test("a notebook that is not running costs one lane, not the turn", async () => {
  // No session up: the hostname does not answer and fetch throws. think() must count it and
  // carry on, because a down GPU is the normal state of a 30-hour-a-week lane.
  const order = [];
  const res = await think(
    { KAGGLE_LANE_KEY: "k", KAGGLE_LANE_URL: "https://gpu.example/v1", OPENROUTER_API_KEY: "o" },
    { messages: [{ role: "user", content: "hi" }] },
    async (url) => {
      order.push(url);
      if (url.startsWith("https://gpu.example")) throw new Error("connect ECONNREFUSED");
      return { ok: true, status: 200, headers: new Headers(), json: async () => ({ choices: [{ message: { content: "fallback" } }] }) };
    },
  );
  assert.equal(res.out.choices[0].message.content, "fallback");
  assert.ok(res.tried.some((t) => t.startsWith("kaggle(")), `kaggle should be tried and named: ${res.tried}`);
});

test("the GPU lane is never reordered by headroom, because nothing counted its hours", () => {
  const kaggle = LANES.find((l) => l.name === "kaggle");
  assert.equal(kaggle.budget, undefined, "a lane with no measured budget must declare none");
  const at = LANES.indexOf(kaggle);
  for (const l of LANES) if (l.budget) exhaust(l, Date.now(), null);
  assert.equal(chooseOrder(Date.now())[at].name, "kaggle");
});
