import test from "node:test";
import assert from "node:assert/strict";
import {
  RateLimiter,
  clientKey,
  deliveryPayload,
  deliveryTarget,
  scrub,
  validateContact,
} from "../lib/contact.ts";

const valid = {
  name: "Dana Whitfield",
  email: "dana@example.com",
  company: "Northwind",
  message: "We run three retrieval pipelines and the p95 latency is drifting upward.",
};

test("accepts a well-formed submission and normalises it", () => {
  const result = validateContact({ ...valid, email: "  Dana@Example.COM  ", name: "  Dana   Whitfield " });
  assert.equal(result.ok, true);
  assert.equal(result.value?.email, "dana@example.com");
  assert.equal(result.value?.name, "Dana Whitfield");
});

test("company is optional", () => {
  const { company, ...withoutCompany } = valid;
  assert.equal(company, "Northwind");
  const result = validateContact(withoutCompany);
  assert.equal(result.ok, true);
  assert.equal(result.value?.company, "");
});

test("rejects an empty submission field by field", () => {
  const result = validateContact({ name: "", email: "", message: "" });
  assert.equal(result.ok, false);
  assert.deepEqual(Object.keys(result.errors).sort(), ["email", "message", "name"]);
});

test("rejects addresses that are not addresses", () => {
  for (const email of ["dana", "dana@", "@example.com", "dana@example", "dana @example.com", "dana@example.c"]) {
    const result = validateContact({ ...valid, email });
    assert.equal(result.ok, false, `expected ${JSON.stringify(email)} to be rejected`);
    assert.equal(result.errors.email, "That does not look like an email address");
  }
});

test("accepts plus-addressing and multi-label domains", () => {
  for (const email of ["dana+projects@example.co.uk", "d.whitfield@sub.example.com"]) {
    assert.equal(validateContact({ ...valid, email }).ok, true, `expected ${email} to be accepted`);
  }
});

test("enforces the message bounds", () => {
  assert.equal(validateContact({ ...valid, message: "too short" }).ok, false);
  assert.equal(validateContact({ ...valid, message: "x".repeat(5001) }).ok, false);
  assert.equal(validateContact({ ...valid, message: "x".repeat(20) }).ok, true);
});

test("enforces the name and company bounds", () => {
  assert.equal(validateContact({ ...valid, name: "x".repeat(121) }).ok, false);
  assert.equal(validateContact({ ...valid, company: "x".repeat(201) }).ok, false);
});

test("scrub removes control characters and surrounding whitespace", () => {
  assert.equal(scrub("  hi\u0000there\u001b  "), "hithere");
  assert.equal(scrub(undefined), "");
  assert.equal(scrub(42), "");
});

test("non-object input does not throw", () => {
  for (const bad of [null, undefined, "string", 42, []]) {
    const result = validateContact(bad);
    assert.equal(result.ok, false);
  }
});

test("rate limiter allows the limit then refuses, with a retry hint", () => {
  let now = 1_000_000;
  const limiter = new RateLimiter(3, 60_000, () => now);

  for (let i = 0; i < 3; i++) {
    const gate = limiter.check("1.2.3.4");
    assert.equal(gate.allowed, true, `attempt ${i + 1} should be allowed`);
  }

  const blocked = limiter.check("1.2.3.4");
  assert.equal(blocked.allowed, false);
  assert.ok(blocked.retryAfterSeconds > 0 && blocked.retryAfterSeconds <= 60);

  // A different caller is unaffected.
  assert.equal(limiter.check("5.6.7.8").allowed, true);
});

test("rate limiter forgets callers once the window elapses", () => {
  let now = 1_000_000;
  const limiter = new RateLimiter(1, 60_000, () => now);
  assert.equal(limiter.check("k").allowed, true);
  assert.equal(limiter.check("k").allowed, false);
  now += 60_001;
  assert.equal(limiter.check("k").allowed, true);
});

test("rate limiter prune keeps live keys and drops expired ones", () => {
  let now = 1_000_000;
  const limiter = new RateLimiter(2, 60_000, () => now);
  limiter.check("old");
  now += 61_000;
  limiter.check("fresh");
  assert.equal(limiter.size, 2);
  limiter.prune();
  assert.equal(limiter.size, 1);
});

test("delivery target is absent until configured", () => {
  assert.equal(deliveryTarget({}), null);
  assert.equal(deliveryTarget({ CONTACT_WEBHOOK_URL: "   " }), null);
});

test("delivery target rejects anything that is not an https URL", () => {
  assert.equal(deliveryTarget({ CONTACT_WEBHOOK_URL: "http://insecure.example/hook" }), null);
  assert.equal(deliveryTarget({ CONTACT_WEBHOOK_URL: "not a url" }), null);
  assert.equal(deliveryTarget({ CONTACT_WEBHOOK_URL: "ftp://example.com/hook" }), null);
  assert.equal(deliveryTarget({ CONTACT_WEBHOOK_URL: "http://localhost:8080/hook" })?.url, "http://localhost:8080/hook");
});

test("delivery target carries the token when one is set", () => {
  const target = deliveryTarget({ CONTACT_WEBHOOK_URL: "https://hooks.example.com/x", CONTACT_WEBHOOK_TOKEN: "t" });
  assert.equal(target?.url, "https://hooks.example.com/x");
  assert.equal(target?.token, "t");
  assert.equal(deliveryTarget({ CONTACT_WEBHOOK_URL: "https://hooks.example.com/x" })?.token, undefined);
});

test("client key prefers the first forwarded address", () => {
  assert.equal(clientKey(new Headers({ "x-forwarded-for": "9.9.9.9, 10.0.0.1" })), "9.9.9.9");
  assert.equal(clientKey(new Headers({ "x-real-ip": "8.8.8.8" })), "8.8.8.8");
  assert.equal(clientKey(new Headers()), "unidentified");
});

test("delivery payload is the validated value plus provenance", () => {
  const payload = deliveryPayload({ name: "A", email: "a@b.co", company: "", message: "hello there friend" }, "2026-01-01T00:00:00.000Z");
  assert.deepEqual(payload, {
    source: "meridian.ai/contact",
    received_at: "2026-01-01T00:00:00.000Z",
    name: "A",
    email: "a@b.co",
    company: "",
    message: "hello there friend",
  });
});
