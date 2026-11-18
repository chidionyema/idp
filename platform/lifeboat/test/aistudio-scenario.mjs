import { readFileSync } from "node:fs";
import { IngestError, ingest, prepare } from "../src/aistudio.js";
import { makeFetch } from "./aistudio-fakes.mjs";

function arg(name, fallback) {
  const at = process.argv.indexOf(name);
  return at === -1 ? fallback : process.argv[at + 1];
}

const mode = arg("--mode", "stream");
const payloadPath = arg("--payload");
if (!payloadPath) {
  process.stderr.write("--payload is required\n");
  process.exit(64);
}

const payload = JSON.parse(readFileSync(payloadPath, "utf8"));
const env = {
  OMNIFLOW_GH_TOKEN: "test-token",
  AI_STUDIO_INGEST_SECRET: "test-secret",
  GENESIS_REALTIME_URL: "https://genesis-founder-surface.pages.dev/realtime",
};

let existing = [];
if (mode === "dedup") {
  const prepared = await prepare(payload.files);
  existing = prepared.accepted.map((file) => ({ path: file.path, sha: file.sha }));
}

const { fetchImpl, journal } = makeFetch(existing);

try {
  const receipt = await ingest(payload, env, fetchImpl);
  process.stdout.write(JSON.stringify({ receipt, journal }));
} catch (error) {
  process.stdout.write(
    JSON.stringify({
      ok: false,
      error: error instanceof IngestError ? error.code : "INTERNAL",
      detail: error instanceof IngestError ? error.detail : String(error?.message || error),
      journal,
    }),
  );
  process.exitCode = 2;
}
