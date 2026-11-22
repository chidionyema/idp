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
  assert.equal(posts(journal, "/greenlane.yml/dispatches").length, 0);
  assert.equal(receipt.custody.gate_verified, false);
  assert.equal(receipt.custody.greenlane_landed, false);
  assert.equal(receipt.custody.operational_yield, false);
  assert.equal(receipt.dispatch.promotion, "NOT_OBSERVED");
  assert.equal(posts(journal, "/realtime").length, 1);

  const assignment = posts(journal, "/issues/8133/comments")[0].body.body;
  assert.match(assignment, /OMNIFLOW-EVENT\/v1/);
  assert.match(assignment, /aistudio-preseal/);
  assert.match(assignment, /submit\/aistudio-auto-intake/);
});

test("the Drive channel dedupes into the stream channel's commit", async () => {
  const files = await encodeFiles(SOURCE_FILES);
  const prepared = await prepare(files);
  const existing = prepared.accepted.map((file) => ({ path: file.path, sha: file.git_blob_sha }));
  const { fetchImpl, journal } = makeFetch(existing);

  const receipt = await ingest({ source: "drive", files }, ENV, fetchImpl);

  assert.equal(receipt.deduped, true);
  assert.equal(posts(journal, "/git/commits").length, 0);
  assert.equal(posts(journal, "/issues/8133/comments").length, 1);
  assert.equal(posts(journal, "/greenlane.yml/dispatches").length, 0);
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


test("protected paths refuse before any GitHub access, including in nested sources", async () => {
  const blocked = await encodeFiles([
    { path: ".github/workflows/ci.yml", content: "on: push\n" },
    { path: "src/.env.production", content: "API_KEY=abc\n" },
    { path: "src/nested/../../etc/passwd", content: "x" },
  ]);
  for (const file of blocked) {
    const { fetchImpl, journal } = makeFetch();
    await assert.rejects(
      () => ingest({ source: "stream", files: [file] }, ENV, fetchImpl),
      (error) => error instanceof IngestError && error.status === 409,
    );
    assert.equal(journal.length, 0, "invalid path reached GitHub");
  }
});

test("first submit commit extends main and never becomes an orphan", async () => {
  const { fetchImpl, journal } = makeFetch();
  const files = await encodeFiles([SOURCE_FILES[0]]);
  const receipt = await ingest({ source: "stream", files }, ENV, fetchImpl);
  const post = posts(journal, "/git/commits")[0];
  assert.deepEqual(post.body.parents, ["a".repeat(40)]);
  assert.equal(receipt.lane, "submit/aistudio-auto-intake");
  assert.equal(receipt.custody.phase, "SUBMIT_SOURCE_ONLY");
});

test("real Git blob digest controls idempotence, not SHA256", async () => {
  const files = await encodeFiles([SOURCE_FILES[0]]);
  const prepared = await prepare(files);
  const { fetchImpl, journal } = makeFetch([
    { path: SOURCE_FILES[0].path, sha: prepared.accepted[0].git_blob_sha },
  ]);
  const receipt = await ingest({ source: "stream", files }, ENV, fetchImpl);
  assert.equal(receipt.deduped, true);
  assert.equal(posts(journal, "/git/blobs").length, 0);
  assert.equal(posts(journal, "/git/commits").length, 0);
});

test("100755 original stays executable in candidate tree", async () => {
  const files = await encodeFiles([{ path: "src/engine/exec.sh", content: "#!/bin/sh\nexit 0\n" }]);
  const { fetchImpl, journal } = makeFetch([
    { path: "src/engine/exec.sh", sha: "0".repeat(40), mode: "100755" },
  ]);
  await ingest({ source: "stream", files }, ENV, fetchImpl);
  const tree = posts(journal, "/git/trees")[0].body.tree;
  assert.equal(tree[0].mode, "100755");
});

test("symlink source cannot trigger even a GitHub blob POST", async () => {
  const files = await encodeFiles([{ path: "src/external.ts", content: "export const n = 1;\n" }]);
  const { fetchImpl, journal } = makeFetch([
    { path: "src/external.ts", sha: "0".repeat(40), mode: "120000" },
  ]);
  await assert.rejects(
    () => ingest({ source: "stream", files }, ENV, fetchImpl),
    /EXISTING_FILE_MODE_REFUSED/,
  );
  assert.equal(journal.filter((x) => x.method === "POST").length, 0);
});

test("missing declared digest and byte length refuse source", async () => {
  const files = await encodeFiles([SOURCE_FILES[0]]);
  const { fetchImpl, journal } = makeFetch();
  const noDigest = [{ ...files[0], sha256: undefined }];
  await assert.rejects(() => ingest({ source: "stream", files: noDigest }, ENV, fetchImpl));
  const noBytes = [{ ...files[0], bytes: undefined }];
  await assert.rejects(() => ingest({ source: "stream", files: noBytes }, ENV, fetchImpl));
  assert.equal(journal.length, 0);
});

test("configured relay cannot bypass the trusted submit gate", async () => {
  const files = await encodeFiles([SOURCE_FILES[0]]);
  const { fetchImpl, journal } = makeFetch();
  const env = { ...ENV, OMNIFLOW_RELAY_URL: "https://relay.example/execute" };
  const receipt = await ingest({ source: "stream", files }, env, fetchImpl);
  assert.equal(receipt.dispatch.promotion, "NOT_OBSERVED");
  assert.equal(journal.some((x) => x.path === "/execute"), false);
  assert.equal(posts(journal, "/greenlane.yml/dispatches").length, 0);
});
