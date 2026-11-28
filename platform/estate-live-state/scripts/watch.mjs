#!/usr/bin/env node
// The terminal board. One read of the worker's snapshot, printed as one line per subject, then the
// `parity` line (seq and full hash) that the Telegram and web readers must print identically.
//   LIVE_STATE_URL         default https://live.meridianlabs.cloud
//   LIVE_STATE_READ_TOKEN  by name, from the vault; never printed
import { watch } from "./watch-lib.mjs";

const base = process.env.LIVE_STATE_URL ?? "https://live.meridianlabs.cloud";
const { code, out, err } = await watch({ base, token: process.env.LIVE_STATE_READ_TOKEN });
for (const l of out) console.log(l);
for (const l of err) console.error(l);
process.exit(code);
