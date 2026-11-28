#!/usr/bin/env node
// Runs every Optimus metric once and appends one event per metric to the live-state worker.
//   node scripts/sweep.mjs [--dry-run] [--catalog catalog/optimus-metrics.json]
//   LIVE_STATE_URL           default https://live.meridianlabs.cloud
//   LIVE_STATE_INGEST_TOKEN  by name, from the vault; never printed, and stripped from the measures' env
// Exit: 0 every event posted (a BLIND metric is data, not a failure) or --dry-run, 1 a read or post
// failure, 2 BLIND: measured, but there was no ingest token, so nothing was sent.
// Runs where the repo is checked out, from the repo root (CI), not on the laptop.
import { readFileSync } from "node:fs";
import { metricsOf, post, runMeasure, sweep, tally } from "./sweep-lib.mjs";

const args = process.argv.slice(2);
const dry = args.includes("--dry-run");
const at = args.indexOf("--catalog");
const catalogPath = at >= 0 ? args[at + 1] : "catalog/optimus-metrics.json";
const base = process.env.LIVE_STATE_URL ?? "https://live.meridianlabs.cloud";

let metrics;
try {
  metrics = metricsOf(JSON.parse(readFileSync(catalogPath, "utf8")));
} catch (e) {
  console.error(`SWEEP FAIL  ${catalogPath}: ${e.message}`);
  process.exit(1);
}
const events = await sweep({ metrics, run: (argv) => runMeasure(argv, { cwd: process.cwd() }), now: Date.now });
console.log(tally(events));
for (const e of events) console.log(e.status === "BLIND" ? `${e.subject}  BLIND  (${e.reason})` : `${e.subject}  DIRECT  ${e.value}`);
if (dry) process.exit(0);
const { code, out, err } = await post({ base, token: process.env.LIVE_STATE_INGEST_TOKEN, events });
for (const l of out) console.log(l);
for (const l of err) console.error(l);
process.exit(code);
