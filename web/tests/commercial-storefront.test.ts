import test from "node:test";
import assert from "node:assert/strict";
import { verifiedGumroadProductUrl } from "../lib/commercialStorefront.ts";

test("no merchant account produces no pretend checkout", () => {
  for (const raw of [undefined, null, "", "  ", "not a url"]) {
    assert.equal(verifiedGumroadProductUrl(raw), null);
  }
});

test("only actual HTTPS Gumroad product paths become storefront links", () => {
  assert.equal(verifiedGumroadProductUrl("https://gumroad.com/l/fromprompt"), "https://gumroad.com/l/fromprompt");
  assert.equal(verifiedGumroadProductUrl("https://merdian.gumroad.com/l/fieldbook01"), "https://merdian.gumroad.com/l/fieldbook01");
  assert.equal(verifiedGumroadProductUrl(" https://merdian.gumroad.com/l/guide-a?campaign=foo#bar "),
    "https://merdian.gumroad.com/l/guide-a");
});

test("invalid merchants, URLs and private credentials cannot enter the public buy CTA", () => {
  for (const raw of [
    "http://gumroad.com/l/book",
    "https://gumroad.com.evil.example/l/book",
    "https://evilgumroad.com/l/book",
    "https://gumroad.com/user",
    "https://gumroad.com/l/",
    "https://user:pass@gumroad.com/l/book",
    "https://gumroad.com:444/l/book",
    "javascript:alert(1)",
    "https://gumroad.com/l/book/../../unsafe",
  ]) {
    assert.equal(verifiedGumroadProductUrl(raw), null, raw);
  }
});
