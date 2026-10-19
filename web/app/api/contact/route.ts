import { NextRequest, NextResponse } from "next/server";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import {
  RateLimiter,
  deliveryPayload,
  deliveryTarget,
  telegramPayload,
  telegramTarget,
  clientKey,
  validateContact,
  type SecretReader,
} from "@/lib/contact";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Where platform/meridian/deployment.yaml mounts the delivery Secret: one file per key.
const SECRETS_DIR = process.env.MERIDIAN_SECRETS_DIR ?? "/etc/meridian-secrets";

/** A missing directory or file is "this deployment has no destination", not an error. */
const readSecret: SecretReader = (name) => {
  try {
    return readFileSync(join(SECRETS_DIR, name), "utf8");
  } catch {
    return undefined;
  }
};

// Shared across requests in this process. See the caveat on RateLimiter.
const limiter = new RateLimiter(5, 10 * 60 * 1000);
let lastPrune = 0;

const MAX_BODY_BYTES = 16_000;

export async function POST(req: NextRequest) {
  // A JSON form post is the only thing this endpoint accepts. Anything else is a
  // client we did not write, or a probe.
  const contentType = req.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return NextResponse.json({ ok: false, error: "expected_application_json" }, { status: 415 });
  }

  const raw = await req.text();
  if (raw.length > MAX_BODY_BYTES) {
    return NextResponse.json({ ok: false, error: "payload_too_large" }, { status: 413 });
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return NextResponse.json({ ok: false, error: "invalid_json" }, { status: 400 });
  }

  const now = Date.now();
  if (now - lastPrune > 60_000) {
    limiter.prune();
    lastPrune = now;
  }

  const key = clientKey(req.headers);
  const gate = limiter.check(key);
  if (!gate.allowed) {
    return NextResponse.json(
      { ok: false, error: "rate_limited" },
      { status: 429, headers: { "Retry-After": String(gate.retryAfterSeconds) } }
    );
  }

  // Honeypot. Answer 200 so a bot learns nothing, and deliver nothing.
  const honeypot = typeof (parsed as { website?: unknown })?.website === "string"
    ? (parsed as { website: string }).website.trim()
    : "";
  if (honeypot) {
    return NextResponse.json({ ok: true });
  }

  const result = validateContact(parsed);
  if (!result.ok || !result.value) {
    return NextResponse.json({ ok: false, error: "invalid_input", errors: result.errors }, { status: 400 });
  }

  // An explicit webhook wins; otherwise Telegram. Either is "a delivery path", and with neither
  // the submission is refused rather than accepted and dropped.
  const webhook = deliveryTarget(process.env, readSecret);
  const telegram = webhook ? null : telegramTarget(process.env, readSecret);
  if (!webhook && !telegram) {
    // Refuse loudly rather than accept a lead and drop it. An unconfigured
    // deployment should look broken, not successful.
    console.error("[contact] no delivery path (CONTACT_WEBHOOK_URL or TELEGRAM_BOT_TOKEN+TELEGRAM_CHAT_ID); refusing the submission");
    return NextResponse.json({ ok: false, error: "delivery_not_configured" }, { status: 503 });
  }

  const receivedAt = new Date(now).toISOString();
  const request = webhook
    ? {
        url: webhook.url,
        headers: {
          "content-type": "application/json",
          ...(webhook.token ? { authorization: `Bearer ${webhook.token}` } : {}),
        },
        body: JSON.stringify(deliveryPayload(result.value, receivedAt)),
      }
    : {
        url: telegram!.url,
        headers: { "content-type": "application/json" },
        body: JSON.stringify(telegramPayload(telegram!.chatId, result.value, receivedAt)),
      };

  try {
    const res = await fetch(request.url, {
      method: "POST",
      headers: request.headers,
      body: request.body,
      signal: AbortSignal.timeout(8000),
    });

    if (!res.ok) {
      console.error(`[contact] delivery failed: upstream returned ${res.status}`);
      return NextResponse.json({ ok: false, error: "delivery_failed" }, { status: 502 });
    }
  } catch (err) {
    console.error(`[contact] delivery threw: ${(err as Error).name}`);
    return NextResponse.json({ ok: false, error: "delivery_failed" }, { status: 502 });
  }

  return NextResponse.json({ ok: true });
}

export async function GET() {
  return NextResponse.json({ ok: false, error: "method_not_allowed" }, { status: 405 });
}
