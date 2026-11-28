#!/usr/bin/env node
// Bridge NATS JetStream messages (JSONL on stdin or --probe-nats host:port) into an
// estate-live-state.v1 endpoint (default https://live.meridianlabs.cloud).
//
// Usage:
//   cat jetstream-events.jsonl | LIVE_STATE_INGEST_TOKEN=... node scripts/nats-bridge.mjs
//   LIVE_STATE_INGEST_TOKEN=... node scripts/nats-bridge.mjs --probe-nats 127.0.0.1:4222

import net from "node:net";
import { bridgeBatch } from "./nats-bridge-lib.mjs";

const base = (process.env.LIVE_STATE_URL || "https://live.meridianlabs.cloud").replace(/\/$/, "");
const token = process.env.LIVE_STATE_INGEST_TOKEN || "";

function probeNats(hostPort, timeoutMs = 2000) {
  const [host, portStr] = hostPort.split(":");
  const port = Number(portStr || "4222");
  return new Promise((resolve) => {
    const sock = net.createConnection({ host, port });
    let done = false;
    const finish = (err) => {
      if (done) return;
      done = true;
      sock.destroy();
      resolve(err);
    };
    sock.setTimeout(timeoutMs, () => finish(`timeout after ${timeoutMs}ms`));
    sock.once("error", (e) => finish(e.message));
    sock.once("data", (buf) => {
      if (buf.toString("utf8").startsWith("INFO ")) finish(null);
      else finish("accepted connection without NATS INFO greeting");
    });
  });
}

async function readStdinLines() {
  if (process.stdin.isTTY) return [];
  const chunks = [];
  for await (const c of process.stdin) chunks.push(c);
  return Buffer.concat(chunks)
    .toString("utf8")
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean)
    .map((line) => {
      try {
        return JSON.parse(line);
      } catch {
        return { subject: "stdin", data: line };
      }
    });
}

const probeIdx = process.argv.indexOf("--probe-nats");
let result;
if (probeIdx !== -1 && process.argv[probeIdx + 1]) {
  const target = process.argv[probeIdx + 1];
  const err = await probeNats(target);
  result = err
    ? await bridgeBatch({ brokerError: `${target}: ${err}`, base, token })
    : await bridgeBatch({
        messages: [
          {
            subject: "estate.transport.nats-jetstream.probe.v1",
            data: {
              source: "nats-jetstream-bridge",
              kind: "transport",
              subject: "nats-jetstream",
              status: "DIRECT",
              value: { endpoint: target, state: "answering" },
            },
          },
        ],
        base,
        token,
      });
} else {
  const messages = await readStdinLines();
  result = await bridgeBatch({ messages, base, token });
}

for (const line of result.out) console.log(line);
for (const line of result.err) console.error(line);
process.exit(result.code);
