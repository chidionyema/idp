#!/usr/bin/env node
// Prints the text the Telegram board should carry. The estate's one Telegram sender (Otto's card,
// outbox #8619) delivers it; this script sends nothing and holds no bot token.
//   LIVE_STATE_URL         default https://live.meridianlabs.cloud
//   LIVE_STATE_READ_TOKEN  by name, from the vault; never printed
import { board } from "./board-lib.mjs";

const base = process.env.LIVE_STATE_URL ?? "https://live.meridianlabs.cloud";
const { code, text } = await board({ base, token: process.env.LIVE_STATE_READ_TOKEN });
console.log(text);
process.exit(code);
