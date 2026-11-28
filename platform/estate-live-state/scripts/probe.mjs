#!/usr/bin/env node
// Asks the deployed worker the questions only a working one can answer. Exit 0 only on proof.
//   /health   -> schema and commit_sha         (no secret needed)
//   /snapshot -> a fresh seq, hash and age     (needs LIVE_STATE_READ_TOKEN, by name, from the vault)
import { probe } from "./probe-lib.mjs";

const base = process.env.LIVE_STATE_URL ?? "https://live.meridianlabs.cloud";
const { code, out, err } = await probe({ base, token: process.env.LIVE_STATE_READ_TOKEN });
for (const l of out) console.log(l);
for (const l of err) console.error(l);
process.exit(code);
