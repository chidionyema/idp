import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("../app/contact/page.tsx", import.meta.url), "utf8");

test("enquiry form renders only when readiness is explicitly available", () => {
  assert.match(source, /availability !== "available" && availability !== "checking" \? \(/);
  assert.match(source, /availability === "checking" \? \(/);
  assert.match(source, /setAvailability\("unknown"\)/);
  assert.doesNotMatch(source, /availability === "unavailable" \? \(/);
});

test("submission is blocked unless readiness is available", () => {
  assert.match(source, /if \(status === "sending" \|\| availability !== "available"\) return;/);
});

test("malformed or failed readiness never grants availability", () => {
  assert.match(source, /typeof data\.acceptingEnquiries !== "boolean"/);
  assert.match(source, /setAvailability\(data\.acceptingEnquiries \? "available" : "unavailable"\)/);
});
