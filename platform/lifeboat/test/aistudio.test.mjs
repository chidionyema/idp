import { test } from "node:test";
import assert from "node:assert/strict";

import {
  DRIVE_PATH,
  INTAKE_RULE,
  IngestError,
  handleIngest,
  ingest,
  prepare,
} from "../src/aistudio.js";
import { SOURCE_FILES, encodeFiles, makeFetch } from "./aistudio-fakes.mjs";

const ENV = {
  OMNIFLOW_GH_TOKEN: "test-token",
  AI_STUDIO_INGEST_SECRET: "test-secret",
  GENESIS_REALTIME_URL: "https://genesis-founder-surface.pages.dev/realtime",
};

const posts = (journal, suffix) =>
  journal.filter((entry) => entry.method === "POST" && entry.path.endsWith(suffix));

test("prepare sanitizes mock fixtures and hashes the landed bytes", async () => {
  const files = await encodeFiles(SOURCE_FILES);
  const prepared = await prepare(files);
  assert.deepEqual(
    prepared.accepted.map((file) => file.path),
    ["src/engine/routerCore.ts"],
  );
  assert.equal(prepared.sanitized[0].reason, "MOCK_FIXTURE");
  assert.match(prepared.accepted[0].sha, /^[0-9a-f]{64}$/);
});

test("prepare refuses a digest that disagrees with the bytes (59effb8f4)", async () => {
  const files = await encodeFiles(SOURCE_FILES);
  files[0].sha256 = "0".repeat(64);
  const prepared = await prepare(files);
  assert.equal(prepared.rejected[0].reason, "PARTIAL_FLUSH_DIGEST");
  assert.equal(prepared.accepted.length, 0);
});

test("a finished stream turn becomes one sanitized commit and wakes the fleet", async () => {
  const { fetchImpl, journal } = makeFetch();
  const payload = { source: "stream", files: await encodeFiles(SOURCE_FILES) };
  const receipt = await ingest(payload, ENV, fetchImpl);

  assert.equal(receipt.ok, true);
  assert.equal(receipt.deduped, false);
  assert.equal(receipt.intake_rule, INTAKE_RULE);
  assert.deepEqual(
    receipt.files.map((file) => file.path),
    ["src/engine/routerCore.ts"],
  );
  assert.equal(receipt.sanitized.length, 1);
  assert.equal(posts(journal, "/git/commits").length, 1);
  assert.equal(posts(journal, "/issues/8133/comments").length, 1);
  assert.equal(posts(journal, "/greenlane.yml/dispatches").length, 1);
  assert.equal(posts(journal, "/realtime").length, 1);

  const assignment = posts(journal, "/issues/8133/comments")[0].body.body;
  assert.match(assignment, /OMNIFLOW-EVENT\/v1/);
  assert.match(assignment, /aistudio-auto-land/);
  assert.match(assignment, /lane\/aistudio-auto-intake/);
});

test("the Drive channel dedupes into the stream channel's commit", async () => {
  const files = await encodeFiles(SOURCE_FILES);
  const prepared = await prepare(files);
  const existing = prepared.accepted.map((file) => ({ path: file.path, sha: file.sha }));
  const { fetchImpl, journal } = makeFetch(existing);

  const receipt = await ingest({ source: "drive", files }, ENV, fetchImpl);

  assert.equal(receipt.deduped, true);
  assert.equal(posts(journal, "/git/commits").length, 0);
  assert.equal(posts(journal, "/issues/8133/comments").length, 1);
  assert.equal(posts(journal, "/greenlane.yml/dispatches").length, 1);
});

test("a partial flush never reaches a commit", async () => {
  const files = await encodeFiles(SOURCE_FILES);
  files[0].bytes = files[0].bytes - 1;
  const { fetchImpl, journal } = makeFetch();

  await assert.rejects(
    () => ingest({ source: "stream", files }, ENV, fetchImpl),
    (error) => error instanceof IngestError && error.status === 409,
  );
  assert.equal(posts(journal, "/git/commits").length, 0);
});

test("the ingest door fails closed without its secret and accepts the Drive sync handshake", async () => {
  const { fetchImpl, journal } = makeFetch();
  const body = JSON.stringify({ source: "drive", files: [] });

  const noSecret = await handleIngest(
    new Request("https://edge/api/ingest/drive-webhook", { method: "POST", body }),
    {},
    fetchImpl,
  );
  assert.equal(noSecret.status, 503);

  const wrong = await handleIngest(
    new Request("https://edge/api/ingest/drive-webhook", {
      method: "POST",
      body,
      headers: { "x-genesis-ingest-token": "nope" },
    }),
    ENV,
    fetchImpl,
  );
  assert.equal(wrong.status, 401);

  const sync = await handleIngest(
    new Request(`https://edge${DRIVE_PATH}`, {
      method: "POST",
      body,
      headers: {
        "x-genesis-ingest-token": ENV.AI_STUDIO_INGEST_SECRET,
        "x-goog-resource-state": "sync",
      },
    }),
    ENV,
    fetchImpl,
  );
  assert.deepEqual(await sync.json(), { ok: true, sync: true });
  assert.equal(journal.length, 0);
});
