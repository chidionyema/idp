// Otto's second home: a door and a brain on Cloudflare's network, in a failure domain that
// shares nothing with the cluster.
//
// The founder's spec, 2026-09-09, verbatim: "You built a distributed, multi-agent workforce,
// but you accidentally gave them a single brain stem ... You must give them a Lifeboat -- a
// secondary gateway that lives in a completely different failure domain ... hosted outside
// your Oracle cluster entirely ... It has no database, no SigNoz tracing, and no complex
// configuration. It is a dumb, bulletproof proxy."
//
// It does two jobs, and the second one is the one that was missing.
//
//   THE BRAIN  /v1/chat/completions, OpenAI-shaped, so no agent's code changes: an agent
//              that can talk to litellm.llm.svc can talk to this by changing one base URL.
//              This is the half the spec described, and it serves the whole crew.
//
//   THE DOOR   /webhook/telegram. Otto's door was a single hostname on our load balancer --
//              platform/otto-gateway/registration-reconciler.yaml says "# The one door" in
//              so many words. A brain with five lanes behind a door with one hostname is
//              still a system with one way to die, and that is what the founder saw:
//              "this route is still tied to our cluster". Telegram allows exactly one
//              webhook URL per bot, so multi-homing the door is not a matter of listing
//              three; it is a matter of pointing the one at the home that cannot be
//              partitioned from Telegram, and having THAT home fan out to the others.
//              Cloudflare's anycast network is that home.
//
// WHAT IT DELIBERATELY IS NOT. Not a second estate router. It keeps no ledger, spends
// against no budget, writes no trace, remembers nothing, and has no database. Every one of
// those absences is load-bearing: a spent key, a lost Postgres or a bad telemetry config
// cannot stop it answering. That last one is not hypothetical -- on 2026-09-09 a single
// telemetry misconfiguration paralysed the estate.
//
// WHY NOT CLOUDFLARE AI GATEWAY, WHICH DOES FALLBACK NATIVELY. It was the first thing
// considered and the founder's spec names it. It is one more service that can be having a
// bad day, and a lifeboat whose failover is performed by a dependency has precisely the
// dependency it exists to remove. The lane list here is not a reimplementation of a
// platform -- it is an ordered list in the platform's own language. The heavy lifting, the
// global network, the runtime, the secret store, the TLS, the routing, the inference
// silicon, is all Cloudflare's.

import { HOMES, ORIGIN_TIMEOUT_MS, keyMatches, think } from "./homes.js";

function json(body, status = 200, extra = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", ...extra },
  });
}

function bearer(request) {
  const h = request.headers.get("authorization") || "";
  return h.startsWith("Bearer ") ? h.slice(7) : "";
}

// Forward a Telegram update, byte for byte, to a home that runs the real Otto. The body is
// passed through untouched and the secret header is re-presented, because the thing on the
// other end is the same Otto with the same verification -- this worker is a road, not a
// translator. True means that home took the update and owns answering it.
async function forwardTo(url, rawBody, secretHeader, fetchImpl = fetch) {
  if (!url) return false;
  try {
    const res = await fetchImpl(url, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        ...(secretHeader ? { "x-telegram-bot-api-secret-token": secretHeader } : {}),
      },
      body: rawBody,
      signal: AbortSignal.timeout(ORIGIN_TIMEOUT_MS),
    });
    return res.ok;
  } catch {
    return false; // connect refused, DNS gone, TLS dead, timed out: all the same answer
  }
}

// Speak to the founder directly, from the edge, using Telegram's own API. This is the line
// that makes home 2 a home rather than a proxy: when no home that runs the real Otto can be
// reached, this worker still holds a conversation with him.
async function tell(env, chatId, text, fetchImpl = fetch) {
  const token = env.TELEGRAM_BOT_TOKEN;
  if (!token || !chatId) return false;
  try {
    const res = await fetchImpl(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ chat_id: chatId, text, disable_web_page_preview: true }),
      signal: AbortSignal.timeout(ORIGIN_TIMEOUT_MS),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function handleTelegram(request, env, rawBody, fetchImpl = fetch) {
  // Telegram presents this on every call and nobody else knows it. Checked before a single
  // byte of the body is trusted, and compared without leaking its length.
  const presented = request.headers.get("x-telegram-bot-api-secret-token") || "";
  if (!keyMatches(presented, env.TELEGRAM_WEBHOOK_SECRET || "")) {
    return json({ ok: false, error: "bad webhook secret" }, 401);
  }

  let update;
  try {
    update = JSON.parse(rawBody);
  } catch {
    return json({ ok: false, error: "body is not JSON" }, 400);
  }

  // Home 1 first, every time. It is the only home that remembers the conversation, holds the
  // tools and can reach the estate, so a degraded answer from anywhere else is strictly
  // worse and is never preferred while home 1 can be had.
  if (await forwardTo(env.ORIGIN_WEBHOOK_URL, rawBody, presented, fetchImpl)) {
    return json({ ok: true, home: HOMES[0] });
  }

  // Home 3, the founder's MacBook, when it has been given a public door of its own. It is
  // tried ahead of answering here because it runs the real Otto with the real memory, and
  // because it is his machine: an answer from it costs no vendor quota at all.
  if (await forwardTo(env.MACBOOK_WEBHOOK_URL, rawBody, presented, fetchImpl)) {
    return json({ ok: true, home: HOMES[2] });
  }

  // Home 2 answers for itself. Degraded on purpose and honest about it.
  const msg = update?.message || update?.edited_message;
  const chatId = msg?.chat?.id;
  const text = msg?.text;
  if (!chatId || !text) {
    // An update with nothing to answer -- a join, a sticker, a reaction. Both homes that
    // could have handled it richly are down, and there is nothing for this one to say. 200
    // regardless: a non-2xx makes Telegram redeliver it every few seconds, forever.
    return json({ ok: true, home: HOMES[1], note: "no answerable text" });
  }

  const { out, lane, tried } = await think(
    env,
    {
      messages: [
        {
          role: "system",
          content:
            "You are Otto, the founder's assistant. His estate's cluster is unreachable, so " +
            "you are answering from an emergency gateway with no memory of earlier messages, " +
            "no tools and no access to the estate. Answer what you can from general knowledge. " +
            "If the question needs live estate state, say plainly that you cannot see it right now.",
        },
        { role: "user", content: text },
      ],
      max_tokens: 800,
    },
    fetchImpl,
  );

  // He is told which home answered, every time, in the first line. An assistant that
  // silently degrades teaches its owner to trust a quality it is no longer delivering --
  // and this one degrading is itself the alert that the cluster is down.
  const reply = out
    ? `[lifeboat: the cluster is unreachable, answering from the Cloudflare edge via ${lane}. ` +
      `No memory of earlier messages and no estate access.]\n\n` +
      (out.choices?.[0]?.message?.content ?? "")
    : `[lifeboat] The cluster is unreachable and every emergency lane is silent too ` +
      `(${tried.join(", ")}). I cannot answer this one.`;

  await tell(env, chatId, reply, fetchImpl);
  // Always 200 once the update has been dealt with, answered or not. Telegram redelivers on
  // anything else, and a redelivery storm during an outage is the last thing that helps.
  return json({ ok: true, home: HOMES[1], lane: lane ?? null, tried });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Reads no secret and touches no vendor, so no vendor and no key can ever take it red.
    // It answers the only question worth asking of a lifeboat -- is the lifeboat there --
    // and /v1/chat/completions answers the different question of whether a lane can think.
    if (url.pathname === "/health") {
      return json({
        status: "afloat",
        homes: HOMES,
        // Which roads out of here are configured. Not whether they are up: proving that
        // would mean calling them, and a health check that calls four vendors is a health
        // check that fails when a vendor does.
        origin: Boolean(env.ORIGIN_WEBHOOK_URL),
        macbook: Boolean(env.MACBOOK_WEBHOOK_URL),
        door: Boolean(env.TELEGRAM_WEBHOOK_SECRET && env.TELEGRAM_BOT_TOKEN),
      });
    }

    if (url.pathname === "/webhook/telegram" && request.method === "POST") {
      // Read once: a Request body is a stream and is gone after the first read, and this
      // one has to survive being forwarded to two homes in turn.
      const rawBody = await request.text();
      return handleTelegram(request, env, rawBody);
    }

    // Everything below is the brain, and the brain is behind a key.
    if (!keyMatches(bearer(request), env.LIFEBOAT_KEY || "")) {
      return json({ error: { message: "Unauthorized", type: "invalid_request_error" } }, 401);
    }

    // Callers list models before they use them. Lane names are returned rather than the
    // model ids behind them, because which model is behind a lane is this worker's business
    // and it changes when a vendor churns a slug -- which both Groq and OpenRouter did
    // inside one week in September 2026.
    if (url.pathname === "/v1/models") {
      const { LANES } = await import("./homes.js");
      return json({
        object: "list",
        data: LANES.map((l) => ({ id: l.name, object: "model", owned_by: "estate-lifeboat" })),
      });
    }

    if (url.pathname !== "/v1/chat/completions" || request.method !== "POST") {
      return json({ error: { message: "Not found", type: "invalid_request_error" } }, 404);
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return json({ error: { message: "Body is not JSON", type: "invalid_request_error" } }, 400);
    }
    if (!Array.isArray(body?.messages) || body.messages.length === 0) {
      return json(
        { error: { message: "messages is required", type: "invalid_request_error" } },
        400,
      );
    }

    // The caller's `model` is deliberately ignored. It asked for a lane the estate router
    // knows -- `minimax`, `judgment`, `cheap` -- and this is not that router and has none of
    // them. It is a lifeboat: it answers with whatever is still floating. Honouring the
    // requested model would mean refusing the call at precisely the moment refusing is fatal.
    const { out, lane, tried } = await think(env, body);
    if (out) {
      return json({ ...out, _lifeboat_lane: lane }, 200, { "x-lifeboat-lane": lane });
    }

    // Every lane at every vendor silent. Say which were tried, because the next thing that
    // happens is a human reading this line at a bad moment.
    return json(
      {
        error: {
          message: `every lifeboat lane is silent: ${tried.join(", ")}`,
          type: "service_unavailable",
        },
      },
      503,
    );
  },
};
