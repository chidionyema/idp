import test from "node:test";
import assert from "node:assert/strict";
import { mailjetAccepted, mailjetPayload, mailjetTarget } from "../lib/mailjet.ts";

const values: Record<string, string> = {
  MAILJET_API_KEY: "test-key",
  MAILJET_SECRET_KEY: "test-secret",
  MERDIAN_ENQUIRIES_FROM: "verified@example.com",
  MERDIAN_ENQUIRIES_TO: "inbox@example.net",
};

test("Mailjet is unavailable without all credentials and addresses", () => {
  assert.equal(mailjetTarget({}), null);
  assert.equal(mailjetTarget({ MAILJET_API_KEY: "test-key" }), null);
  assert.equal(mailjetTarget({ ...values, MERDIAN_ENQUIRIES_FROM: "fake" }), null);
  assert.equal(mailjetTarget({ ...values, MERDIAN_ENQUIRIES_TO: "fake" }), null);
  assert.deepEqual(mailjetTarget(values), {
    apiKey: "test-key", secretKey: "test-secret",
    senderEmail: "verified@example.com", recipientEmail: "inbox@example.net",
  });
});

test("Mailjet reads the same mounted secrets as existing delivery paths", () => {
  assert.deepEqual(mailjetTarget({}, (name) => values[name]), mailjetTarget(values));
});

test("Mailjet payload uses verified sender and customer reply-to, never customer From", () => {
  const target = mailjetTarget(values);
  assert.ok(target);
  const payload = mailjetPayload(target!, {
    name: "Dana Whitfield", email: "dana@client.com", company: "Northwind",
    message: "We need technical consultancy for our retrieval architecture.",
  }, "2026-11-10T00:00:00.000Z");
  const message = payload.Messages[0];
  assert.equal(message.From.Email, "verified@example.com");
  assert.equal(message.From.Name, "Meridian Intelligence");
  assert.equal(message.To[0].Email, "inbox@example.net");
  assert.deepEqual(message.ReplyTo, { Email: "dana@client.com", Name: "Dana Whitfield" });
  assert.match(message.TextPart, /retrieval architecture/);
  assert.equal(message.TrackOpens, "disabled");
  assert.equal(message.TrackClicks, "disabled");
});

test("Mailjet per-message rejection and malformed responses fail closed", () => {
  assert.equal(mailjetAccepted({ Messages: [{ Status: "success" }] }), true);
  assert.equal(mailjetAccepted({ Messages: [{ Status: "error" }] }), false);
  assert.equal(mailjetAccepted({ Messages: [] }), false);
  assert.equal(mailjetAccepted({ Messages: [{ Status: "success" }, { Status: "error" }] }), false);
  assert.equal(mailjetAccepted({ error: "failed" }), false);
  assert.equal(mailjetAccepted(null), false);
});
