// The off-host seal: grade behaviour, not prose. Every assertion is a status code or a
// signature check -- if the signing is wrong, these fail; if the door is open, these fail.
import { test } from "node:test";
import assert from "node:assert/strict";
import { generateKeyPairSync, verify } from "node:crypto";

import worker from "../src/index.js";
import { handleSeal, sealPayload } from "../src/seal.js";

function keypairPem() {
  const { privateKey, publicKey } = generateKeyPairSync("ed25519");
  return {
    priv: privateKey.export({ type: "pkcs8", format: "pem" }),
    pub: publicKey,
  };
}

function req(body, token, path = "/seal") {
  return new Request(`https://lifeboat.example${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
}

const HEAD = "be30ca508195f8fff9116257db03004e40d5ffc3";

test("an unauthenticated seal request is refused", async () => {
  const { priv } = keypairPem();
  const res = await handleSeal(req({ reason: "x", paths: ["bin/a"], head: HEAD }, ""),
    { FOUNDER_SEAL_KEY_PEM: priv, FOUNDER_SEAL_TOKEN: "tok" });
  assert.equal(res.status, 401);
});

test("a wrong bearer token is refused", async () => {
  const { priv } = keypairPem();
  const res = await handleSeal(req({ reason: "x", paths: ["bin/a"], head: HEAD }, "nope"),
    { FOUNDER_SEAL_KEY_PEM: priv, FOUNDER_SEAL_TOKEN: "tok" });
  assert.equal(res.status, 401);
});

test("an authorised request returns a trailer that verifies against the public key", async () => {
  const { priv, pub } = keypairPem();
  const res = await handleSeal(
    req({ reason: "strip advisory", paths: ["bin/a", "bin/b"], head: HEAD }, "tok"),
    { FOUNDER_SEAL_KEY_PEM: priv, FOUNDER_SEAL_TOKEN: "tok" },
  );
  assert.equal(res.status, 200);
  const body = await res.json();

  const lines = body.trailer.split("\n");
  const get = (name) => (lines.find((l) => l.startsWith(`${name}: `)) || "").slice(name.length + 2);
  const sig = Buffer.from(get("X-Idp-Auth"), "base64");
  const payload = sealPayload({
    ts: get("X-Idp-Auth-Timestamp"),
    head: HEAD,
    reason: get("X-Idp-Auth-Reason"),
    paths: get("X-Idp-Auth-Paths").split(","),
  });
  assert.equal(verify(null, Buffer.from(payload), pub, sig), true, "signature must verify");
});

test("a malformed head is refused before any signing", async () => {
  const { priv } = keypairPem();
  const res = await handleSeal(req({ reason: "x", paths: ["bin/a"], head: "short" }, "tok"),
    { FOUNDER_SEAL_KEY_PEM: priv, FOUNDER_SEAL_TOKEN: "tok" });
  assert.equal(res.status, 400);
});

test("the worker refuses when the signing key is absent rather than signing nothing", async () => {
  const res = await handleSeal(req({ reason: "x", paths: ["bin/a"], head: HEAD }, "tok"),
    { FOUNDER_SEAL_TOKEN: "tok" });
  assert.equal(res.status, 501);
});

test("the route is reachable through the worker's own fetch", async () => {
  const { priv } = keypairPem();
  const res = await worker.fetch(req({ reason: "r", paths: ["bin/a"], head: HEAD }, "tok"), {
    FOUNDER_SEAL_KEY_PEM: priv, FOUNDER_SEAL_TOKEN: "tok",
  });
  assert.equal(res.status, 200);
});

test("OPTIONS answers 204 for the portal", async () => {
  const { priv } = keypairPem();
  const res = await worker.fetch(
    new Request("https://lifeboat.example/seal", { method: "OPTIONS" }),
    { FOUNDER_SEAL_KEY_PEM: priv, FOUNDER_SEAL_TOKEN: "tok" },
  );
  assert.equal(res.status, 204);
});
