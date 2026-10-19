// Contact form domain logic, kept free of Next/React so it can be tested directly.
// Everything here is deterministic and side-effect free except the rate limiter,
// which holds state in memory on purpose (see the caveat on RateLimiter).

export interface ContactInput {
  name: string;
  email: string;
  company?: string;
  message: string;
  /** Hidden field humans never fill. A bot that fills it is dropped silently. */
  website?: string;
}

export type ContactErrors = Partial<Record<"name" | "email" | "company" | "message", string>>;

export const LIMITS = {
  name: { min: 1, max: 120 },
  email: { max: 200 },
  company: { max: 200 },
  message: { min: 20, max: 5000 },
} as const;

// Deliberately not RFC 5322. It rejects the things that actually arrive in a form
// (no @, no dot, spaces, trailing dot) without rejecting plus-addressing or new TLDs.
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

/** Remove control characters a textarea or an API client can smuggle through. */
export function scrub(value: unknown): string {
  if (typeof value !== "string") return "";
  return value.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "").trim();
}

function collapse(value: string): string {
  return value.replace(/[ \t]+/g, " ").trim();
}

export interface ValidationResult {
  ok: boolean;
  errors: ContactErrors;
  value?: { name: string; email: string; company: string; message: string };
}

export function validateContact(raw: unknown): ValidationResult {
  const input: ContactInput = (raw ?? {}) as ContactInput;

  const name = collapse(scrub(input.name));
  const email = scrub(input.email).toLowerCase();
  const company = collapse(scrub(input.company));
  const message = scrub(input.message);
  const errors: ContactErrors = {};

  if (!name) errors.name = "Required";
  else if (name.length > LIMITS.name.max) errors.name = `Keep this under ${LIMITS.name.max} characters`;

  if (!email) errors.email = "Required";
  else if (email.length > LIMITS.email.max) errors.email = "That address is too long";
  else if (!EMAIL.test(email)) errors.email = "That does not look like an email address";

  if (company.length > LIMITS.company.max) errors.company = `Keep this under ${LIMITS.company.max} characters`;

  if (!message) errors.message = "Required";
  else if (message.length < LIMITS.message.min) errors.message = `Tell us a little more (at least ${LIMITS.message.min} characters)`;
  else if (message.length > LIMITS.message.max) errors.message = `That is longer than we can process (${LIMITS.message.max} characters max)`;

  if (Object.keys(errors).length > 0) return { ok: false, errors };
  return { ok: true, errors: {}, value: { name, email, company, message } };
}

/**
 * Sliding-window limiter.
 *
 * Caveat that matters in production: this holds state in one process. Behind more
 * than one instance a caller gets `limit * instances` attempts, and a restart
 * forgets everyone. That is acceptable for a form whose worst case is junk in an
 * inbox, and it is not acceptable as a general-purpose limiter. If this ever fronts
 * something billed, move the counter to Redis or the platform's edge limiter.
 */
export class RateLimiter {
  private hits = new Map<string, number[]>();
  private readonly limit: number;
  private readonly windowMs: number;
  private readonly now: () => number;

  // Fields rather than constructor parameter properties: Node's strip-only
  // TypeScript mode rejects parameter properties, and the tests run that way.
  constructor(limit = 5, windowMs = 10 * 60 * 1000, now: () => number = () => Date.now()) {
    this.limit = limit;
    this.windowMs = windowMs;
    this.now = now;
  }

  check(key: string): { allowed: boolean; remaining: number; retryAfterSeconds: number } {
    const t = this.now();
    const cutoff = t - this.windowMs;
    const recent = (this.hits.get(key) ?? []).filter((ts) => ts > cutoff);

    if (recent.length >= this.limit) {
      const retryAfterSeconds = Math.max(1, Math.ceil((recent[0] + this.windowMs - t) / 1000));
      this.hits.set(key, recent);
      return { allowed: false, remaining: 0, retryAfterSeconds };
    }

    recent.push(t);
    this.hits.set(key, recent);
    return { allowed: true, remaining: this.limit - recent.length, retryAfterSeconds: 0 };
  }

  /** Drop keys whose whole window has elapsed, so the map cannot grow forever. */
  prune(): void {
    const cutoff = this.now() - this.windowMs;
    for (const [key, stamps] of this.hits) {
      const recent = stamps.filter((ts) => ts > cutoff);
      if (recent.length === 0) this.hits.delete(key);
      else this.hits.set(key, recent);
    }
  }

  get size(): number {
    return this.hits.size;
  }
}

export interface DeliveryTarget {
  url: string;
  token?: string;
}

/**
 * Reads one named secret. Env is the laptop shape; a mounted file is the cluster shape.
 *
 * The cluster shape exists because kyverno's `secrets-not-from-env-vars` refuses a Pod that
 * takes a credential through its environment: a value in an env var is printed by every crash
 * dump, by `kubectl describe pod`, and by any library that logs its environment on start. So
 * platform/meridian/ mounts the Secret as files and this reads them; nothing about the site's
 * behaviour changes, and the value never enters a process's environment block.
 */
export type SecretReader = (name: string) => string | undefined;

/**
 * Delivery is provider-agnostic by design: the site posts JSON to whatever URL the
 * deployment supplies through CONTACT_WEBHOOK_URL (with an optional bearer token in
 * CONTACT_WEBHOOK_TOKEN). Referencing the variable by name only keeps the secret out
 * of the repo, and naming no vendor keeps this file from making a purchasing decision.
 */
export function deliveryTarget(
  env: Record<string, string | undefined>,
  readSecret?: SecretReader,
): DeliveryTarget | null {
  const url = (env.CONTACT_WEBHOOK_URL ?? readSecret?.("CONTACT_WEBHOOK_URL"))?.trim();
  if (!url) return null;
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "https:" && parsed.hostname !== "localhost") return null;
  } catch {
    return null;
  }
  const token = (env.CONTACT_WEBHOOK_TOKEN ?? readSecret?.("CONTACT_WEBHOOK_TOKEN"))?.trim();
  return { url, token: token || undefined };
}

/**
 * Telegram delivery: the same two named secrets, read the same way (env, then mounted file), for
 * a deployment whose destination is a chat rather than a webhook. `TELEGRAM_BOT_TOKEN` and
 * `TELEGRAM_CHAT_ID` are the names the vault entry's properties are mounted under. The token is
 * shape-checked before it is spliced into the API path, so a malformed value is "not configured"
 * (503) instead of a request to an attacker-shaped URL. The returned url carries the token: it is
 * never logged, and callers log a status code or error name only.
 */
export interface TelegramTarget {
  url: string;
  chatId: string;
}

export function telegramTarget(
  env: Record<string, string | undefined>,
  readSecret?: SecretReader,
): TelegramTarget | null {
  const token = (env.TELEGRAM_BOT_TOKEN ?? readSecret?.("TELEGRAM_BOT_TOKEN"))?.trim();
  const chatId = (env.TELEGRAM_CHAT_ID ?? readSecret?.("TELEGRAM_CHAT_ID"))?.trim();
  if (!token || !chatId) return null;
  if (!/^\d{5,}:[A-Za-z0-9_-]{20,}$/.test(token)) return null;
  if (!/^-?\d+$|^@[A-Za-z0-9_]{5,}$/.test(chatId)) return null;
  return { url: `https://api.telegram.org/bot${token}/sendMessage`, chatId };
}

/** Telegram refuses a message over 4096 characters; the form's own limits sit well inside it. */
const TELEGRAM_MAX = 4096;

export function telegramPayload(
  chatId: string,
  value: NonNullable<ValidationResult["value"]>,
  receivedAt: string,
) {
  const lines = [
    "New enquiry via meridian.ai/contact",
    `Name: ${value.name}`,
    `Email: ${value.email}`,
    ...(value.company ? [`Company: ${value.company}`] : []),
    `Received: ${receivedAt}`,
    "",
    value.message,
  ];
  // Plain text, no parse_mode: visitor-supplied text is never interpreted as markup.
  return {
    chat_id: chatId,
    text: lines.join("\n").slice(0, TELEGRAM_MAX),
    disable_web_page_preview: true,
  };
}

export function deliveryPayload(value: NonNullable<ValidationResult["value"]>, receivedAt: string) {
  return {
    source: "meridian.ai/contact",
    received_at: receivedAt,
    ...value,
  };
}

/** Best-effort client identity for rate limiting. `null` falls into one shared bucket. */
export function clientKey(headers: Headers): string {
  const forwarded = headers.get("x-forwarded-for");
  if (forwarded) return forwarded.split(",")[0].trim();
  return headers.get("x-real-ip")?.trim() || "unidentified";
}
