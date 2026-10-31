// pi-founder-governance: the founder's prompt reaches the CANONICAL intake, stamped with the
// source it came from.
//
// The rule this pins: a pi prompt is recorded as source=pi, with the pi session id, through
// bin/estate-founder-intake -- the one door every surface stamps through. If the extension
// called the intake without --source, a pi prompt would enter the ledger looking like a chat
// prompt, and the plan-link reader could not tell them apart.
//
// The intake is stubbed by a real executable that records its argv and stdin, so the test
// measures the CALL, not the source text.
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync, readFileSync, chmodSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

const FAKE = `#!/usr/bin/env python3
import json, os, sys
with open(os.environ["RECORD"], "w", encoding="utf-8") as fh:
    json.dump({"argv": sys.argv[1:], "stdin": sys.stdin.read()}, fh)
print(json.dumps({"fingerprint": "abc123", "repeat_of": None, "sentences": []}))
`;

function stubIntake(): { bin: string; record: () => any } {
  const dir = mkdtempSync(path.join(tmpdir(), "pi-intake-"));
  const bin = path.join(dir, "estate-founder-intake");
  writeFileSync(bin, FAKE, "utf-8");
  chmodSync(bin, 0o755);
  const recordFile = path.join(dir, "record.json");
  process.env.RECORD = recordFile;
  return {
    bin: dir,
    record: () => JSON.parse(readFileSync(recordFile, "utf-8")),
  };
}

test("the pi prompt is stamped through the canonical intake, with its source", async () => {
  const stub = stubIntake();
  process.env.ESTATE_FOUNDER_GOVERNANCE_BIN = stub.bin;
  const mod = await import("./index.ts");
  const handlers: Record<string, (event: any, ctx: any) => any> = {};
  const pi: any = {
    on: (name: string, fn: any) => {
      handlers[name] = fn;
    },
    getActiveTools: () => [],
    setActiveTools: () => {},
  };
  mod.default(pi);
  assert.ok(handlers["before_agent_start"], "the extension must hook before_agent_start");

  const prompt = "Land the plan links and show me the exit status.";
  await handlers["before_agent_start"](
    { prompt },
    { sessionManager: { getSessionId: () => "pi-test-session-1" } },
  );

  const record = stub.record();
  assert.deepEqual(record.argv, [
    "--stdin",
    "--session",
    "pi-test-session-1",
    "--source",
    "pi",
    "--json",
  ]);
  assert.equal(record.stdin, prompt);
});
