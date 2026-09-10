// Otto's three homes. The founder, 2026-09-10: "three homes, cloudflare, macbook".
//
// A HOME IS A FAILURE DOMAIN, NOT A MODEL. This distinction is the whole point and it is the
// one this estate got wrong first. On 2026-09-10 Otto was given five model lanes -- MiniMax,
// Groq, Gemini, OpenRouter and one more -- and they were called homes. They were not. All
// five were entries in one ConfigMap read by one sidecar in one pod on one cluster, so all
// five had exactly the same set of ways to die: the node, the CNI, the load balancer, the
// scheduler, the quota, the cluster. Five lanes in one pod is one home. The founder's words
// when he saw it: "this route is still tied to our cluster".
//
// So a home earns the name only by failing independently of the other two:
//
//   home 1  the cluster    OKE, Traefik, otto-gateway, the estate router. Full Otto: memory,
//                          tools, traces, the catalogue. Slowest to be right, richest answer.
//   home 2  this worker    Cloudflare's global network. No node of ours, no DNS of ours, no
//                          network of ours. It is up when our cluster is a smoking hole, and
//                          it is the only home Telegram can always reach.
//   home 3  the founder's  Reached over the tailnet, which is a WireGuard mesh and not our
//           MacBook        cluster's network. Answers when every cloud vendor has spent its
//                          free tier and the internet is the thing that is broken.
//
// The ORDER is fixed and is a statement about quality, not a load balance: home 1 is tried
// first every time because it is the only one that remembers the conversation. Homes 2 and 3
// are what "Otto answered at all" looks like on a bad day.
export const HOMES = ["cluster", "cloudflare-edge", "founder-macbook"];

// The lanes home 2 can think with, in order. Every one is FREE, and every one is a different
// vendor, because the founder's question -- "free with limits? what if limit is reached? need
// otto to live forever" -- is answered by another vendor, never by a bigger promise.
//
// Measured from inside the estate on 2026-09-10, on these very keys:
//   groq openai/gpt-oss-120b     200 in 0.48s, tool calls work
//   gemini-2.5-flash-lite        200 in 0.82s, tool calls work
//   openrouter nemotron-3.5      200 in 8.68s, no tool call
export const LANES = [
  {
    name: "groq",
    // Measured on 2026-09-10 by reading the vendor's own x-ratelimit-limit-requests header,
    // not by trusting a pricing page.
    budget: { requests: 1000, window: "day" },
    secret: "GROQ_API_KEY",
    url: "https://api.groq.com/openai/v1/chat/completions",
    model: "openai/gpt-oss-120b",
  },
  {
    name: "gemini",
    budget: { requests: 1500, window: "day" },   // published free tier, flash-lite
    secret: "GEMINI_API_KEY",
    url: "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
    // -lite and not plain flash: asked for a tool call on 2026-09-10, gemini-2.5-flash
    // answered in prose and made none, and -lite made the call.
    model: "gemini-2.5-flash-lite",
  },
  {
    // Workers AI runs INSIDE this worker, on Cloudflare's own silicon, over no network at
    // all -- env.AI.run is an in-process call, not a fetch. It cannot be partitioned away
    // from the thing calling it, cannot 429 on someone else's quota and cannot have its slug
    // churned out from under us. It sits third because it is the weakest model of the four,
    // and no lower because being unreachable is the one failure it cannot have.
    //
    // This lane is also why platform/vendors/consoles.yaml:387 no longer holds. That note
    // refuses Workers AI as a vendor row because its REST endpoint needs an account id and
    // "no file in the estate holds one". Two things have changed. The binding below needs no
    // account id and no key at all -- the binding IS the credential. And the estate does in
    // fact derive the account id already: bin/idp-bootstrap-cloudflare:155 reads it straight
    // off the zone record, `ACCOUNT_ID=$(jq -r .account.id <<<"$zone")`.
    name: "workers-ai",
    binding: "AI",
    model: "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
  },
  {
    name: "openrouter",
    budget: { requests: 50, window: "day" },     // published free tier, no credit balance
    secret: "OPENROUTER_API_KEY",
    url: "https://openrouter.ai/api/v1/chat/completions",
    // Last, and never counted on. Of four free models asked in one run on 2026-09-10, one
    // timed out at 45s, one returned 403, one returned 429, and this one answered in 8.68s.
    // It is here because something beats silence.
    model: "nvidia/nemotron-3.5-lightning:free",
  },
];

// ---------------------------------------------------------------------------------------
// HEADROOM, NOT A CHAIN.
//
// A fallback chain walks lane 1, lane 2, lane 3 and stops at the first that answers. Which
// means lane 1 takes every single request while it is healthy, and the ladder is only ever as
// tall as lane 1 is empty. Groq's measured 1,000 a day drains by the afternoon, and from then
// until midnight UTC the estate runs a rung shorter -- while Gemini's 1,500 sat untouched all
// day and expires unspent at its own reset. Two lanes with 1,000 each are not 2,000 requests
// under a chain. They are 1,000, then a worse model.
//
// So the chooser spends the lane with the most headroom RELATIVE TO ITS OWN REFILL WINDOW.
// Not the most requests left -- the largest fraction of its own budget -- because a lane with
// 50 a day at 90% full deserves its turn against a lane with 1,500 at 20%. Under load every
// lane drains together and they all reset together, which is what "12,750 free requests a
// day" has to mean if the number is to be worth writing down.
//
// TWO HONEST LIMITS, stated because a silent estimate is worse than a known one:
//
// 1. This counter lives in the isolate. Cloudflare may run several, and each keeps its own
//    tally, so the count is a floor on what has been spent, never the truth. It is corrected
//    the moment a vendor tells us the truth -- x-ratelimit-remaining-requests is believed over
//    anything counted here -- and a 429 zeroes the lane outright until its window rolls. The
//    alternative was a Durable Object or a KV write per request, which buys exactness at the
//    price of a second thing that can be down. A lifeboat does not get a dependency.
// 2. workers-ai is not reordered. It is metered in neurons, not requests, and this code has
//    measured no neuron figure, so it keeps its declared rank rather than being sorted on an
//    invented number. It is also the one lane that cannot be partitioned away from the code
//    calling it, which is exactly why it earns a fixed place rather than a computed one.
export const WINDOW_MS = { minute: 60_000, day: 86_400_000, month: 2_592_000_000 };

// name -> { remaining, resetAt }. Exported so the tests can drive it and /health can show it.
export const LANE_STATE = new Map();

// Every lane full again. Only the tests call this: a real isolate forgets by dying.
export function resetLanes() { LANE_STATE.clear(); }

function windowEnd(lane, now) {
  return now + (WINDOW_MS[lane.budget.window] ?? WINDOW_MS.day);
}

// 1 means untouched, 0 means spent. A lane past its reset is full again by definition.
export function headroom(lane, now = Date.now()) {
  if (!lane.budget) return null;
  const s = LANE_STATE.get(lane.name);
  if (!s || now >= s.resetAt) return 1;
  return Math.max(0, s.remaining) / lane.budget.requests;
}

// One request's worth, or the vendor's own count when it sends one.
export function spend(lane, now = Date.now(), headers = null) {
  if (!lane.budget) return;
  let s = LANE_STATE.get(lane.name);
  if (!s || now >= s.resetAt) {
    s = { remaining: lane.budget.requests, resetAt: windowEnd(lane, now) };
  }
  s.remaining -= 1;
  const told = headers?.get?.("x-ratelimit-remaining-requests");
  if (told !== null && told !== undefined && told !== "" && Number.isFinite(Number(told))) {
    s.remaining = Number(told);   // the vendor is the authority, always
  }
  LANE_STATE.set(lane.name, s);
}

// A refusal is not a slow lane, it is a spent one: stop offering it until its window rolls.
export function exhaust(lane, now = Date.now(), headers = null) {
  if (!lane.budget) return;
  const retry = Number(headers?.get?.("retry-after"));
  const resetAt = Number.isFinite(retry) && retry > 0
    ? now + retry * 1000
    : windowEnd(lane, now);
  LANE_STATE.set(lane.name, { remaining: 0, resetAt });
}

// Headroom is compared in tenths, not exactly. On exact fractions one request through a
// 1,000/day lane (99.9% left) puts it behind an untouched 50/day lane, and the next request
// puts it back, so the estate alternates between its best model and its worst on every turn
// while both are nearly full. That is not load balancing, it is a coin toss with extra steps.
// A band means the declared quality order holds until a lane has genuinely fallen about a
// tenth of its own budget behind a peer, and only then does the turn move.
function band(h) { return Math.ceil(h * 10); }

// The metered lanes are sorted by headroom and put back into the slots the metered lanes
// already occupied, so an unmetered lane never moves. Ties keep the declared order, which is
// the quality order: headroom decides between equals, it does not overrule a better model.
export function chooseOrder(now = Date.now(), lanes = LANES) {
  const slots = [];
  lanes.forEach((l, i) => { if (l.budget) slots.push(i); });
  const metered = slots.map((i) => lanes[i]);
  metered.sort((a, b) => (band(headroom(b, now)) - band(headroom(a, now))) ||
                         (lanes.indexOf(a) - lanes.indexOf(b)));
  const out = lanes.slice();
  slots.forEach((slot, k) => { out[slot] = metered[k]; });
  return out;
}

// A lane gets this long before the next one is tried. Deliberately mean: a lane that stalls
// spends the NEXT lane's turn, and every measurement above is under a second bar one. The
// founder on the old behaviour, 2026-09-08: "we wait for a model to finish and then switch
// which fails all the time."
export const LANE_TIMEOUT_MS = 20_000;

// How long home 1 gets to prove it is alive before home 2 stops waiting for it. Short,
// because this budget is spent while the founder is watching a "typing" indicator, and
// because the failure it is built for -- a dead cluster -- shows up as a connect timeout or
// a 5xx well inside it. A cluster that needs longer than this to say hello is not going to
// produce a good answer at the end of it either.
export const ORIGIN_TIMEOUT_MS = 8_000;

// Compare without leaking how much of the key was right. A lifeboat is on the public
// internet by definition -- that is the entire point of it -- so its front door is the one
// place in this code that gets to be careful.
export function keyMatches(presented, expected) {
  if (typeof presented !== "string" || typeof expected !== "string") return false;
  if (presented.length === 0 || expected.length === 0) return false;
  if (presented.length !== expected.length) return false;
  let diff = 0;
  for (let i = 0; i < presented.length; i++) {
    diff |= presented.charCodeAt(i) ^ expected.charCodeAt(i);
  }
  return diff === 0;
}

// One lane, one attempt, no retry. Retries belong to the caller; doing them here only delays
// the hop to a lane that can answer. A lane that cannot answer returns null rather than
// throwing, because "next" is the only thing this code ever wants to do about it.
export async function tryLane(lane, env, body, fetchImpl = fetch) {
  const messages = body.messages;

  if (lane.binding) {
    const ai = env[lane.binding];
    if (!ai) return null; // binding absent in this deployment: skip, do not fail
    const out = await ai.run(lane.model, {
      messages,
      max_tokens: body.max_tokens ?? 1024,
    });
    const text = out?.response ?? out?.result?.response;
    if (!text) return null;
    return {
      id: `lifeboat-${crypto.randomUUID()}`,
      object: "chat.completion",
      created: Math.floor(Date.now() / 1000),
      model: lane.model,
      choices: [
        { index: 0, message: { role: "assistant", content: text }, finish_reason: "stop" },
      ],
      usage: {},
    };
  }

  const key = env[lane.secret];
  if (!key) return null; // a lane whose key was never set is skipped, not an error

  const res = await fetchImpl(lane.url, {
    method: "POST",
    headers: {
      authorization: `Bearer ${key}`,
      "content-type": "application/json",
      // api.groq.com answered 403 in 0.05s to a call with no user agent on 2026-09-10, and
      // 200 to the identical call with this header. One line, whole lane.
      "user-agent": "estate-lifeboat/1",
    },
    body: JSON.stringify({
      model: lane.model,
      messages,
      ...(body.max_tokens ? { max_tokens: body.max_tokens } : {}),
      ...(body.temperature !== undefined ? { temperature: body.temperature } : {}),
      ...(body.tools ? { tools: body.tools } : {}),
      ...(body.tool_choice ? { tool_choice: body.tool_choice } : {}),
    }),
    signal: AbortSignal.timeout(LANE_TIMEOUT_MS),
  });
  // 429 spent, 404 slug churned, 5xx vendor down: every one of them means "try the next lane".
  // They do not all mean the same thing to the ledger, though -- a 429 is the vendor saying the
  // window is gone, and believing it is the difference between skipping a dead lane for an hour
  // and rediscovering it is dead on every single request.
  if (res.status === 429) { exhaust(lane, Date.now(), res.headers); return null; }
  if (!res.ok) return null;
  spend(lane, Date.now(), res.headers);
  const out = await res.json();
  if (!out?.choices?.length) return null;
  return out;
}

// Walk the lanes until one answers, most headroom first. Returns { out, lane } or { tried }
// with nobody home.
export async function think(env, body, fetchImpl = fetch) {
  const tried = [];
  for (const lane of chooseOrder(Date.now())) {
    try {
      const out = await tryLane(lane, env, body, fetchImpl);
      if (out) return { out, lane: lane.name, tried };
      tried.push(lane.name);
    } catch (e) {
      tried.push(`${lane.name}(${e?.name || "error"})`);
    }
  }
  return { tried };
}
