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
    secret: "GROQ_API_KEY",
    url: "https://api.groq.com/openai/v1/chat/completions",
    model: "openai/gpt-oss-120b",
  },
  {
    name: "gemini",
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
    secret: "OPENROUTER_API_KEY",
    url: "https://openrouter.ai/api/v1/chat/completions",
    // Last, and never counted on. Of four free models asked in one run on 2026-09-10, one
    // timed out at 45s, one returned 403, one returned 429, and this one answered in 8.68s.
    // It is here because something beats silence.
    model: "nvidia/nemotron-3.5-lightning:free",
  },
];

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
  // 429 spent, 404 slug churned, 5xx vendor down: every one of them means the same thing here.
  if (!res.ok) return null;
  const out = await res.json();
  if (!out?.choices?.length) return null;
  return out;
}

// Walk the lanes until one answers. Returns { out, lane } or { tried } with nobody home.
export async function think(env, body, fetchImpl = fetch) {
  const tried = [];
  for (const lane of LANES) {
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
