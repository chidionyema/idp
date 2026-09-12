// decide.mjs — the breaker's decision, callable from node so the extension and its test agree.
//
// The logic is bin/idp-circuit-breaker's, which is merged and has a rules.yaml row. This module
// exists because a pi extension is TypeScript and the estate's gate is Python: the test drives
// this file by name, and the extension imports it, so there is one implementation and not two.
//
// Kept dependency-free on purpose. An extension that fails to load is a guard nobody has
// (LAW 28), and an import that cannot resolve is how that happens.

import { spawnSync } from "node:child_process";
import * as path from "node:path";

/**
 * Ask bin/idp-circuit-breaker whether the next action may proceed.
 *
 * The estate's breaker is the authority. This shells out to it rather than reimplementing the
 * fingerprint, so a change to the fingerprint changes both at once (LAW 43: never a second copy).
 *
 * @param {string} repoRoot  the checkout that holds bin/idp-circuit-breaker
 * @param {{observations: Array<{finding: string, target: string}>, next: {finding: string, target: string}}} input
 * @returns {{block: boolean, reason?: string, lever?: string}}
 */
export function decide(repoRoot, input) {
  const tool = path.join(repoRoot, "bin", "idp-circuit-breaker");
  const observations = input.observations || [];
  const next = input.next || {};

  // Replay the observations into a scratch store, then ask whether the next action is locked.
  // A store is used rather than in-memory state so this is a pure call: no session to leak.
  const store = path.join(
    process.env.TMPDIR || "/tmp",
    `breaker-decide-${process.pid}-${Date.now()}.jsonl`,
  );

  for (const o of observations) {
    spawnSync(tool, ["--store", store, "--finding", o.finding, "--target", o.target], {
      encoding: "utf8",
    });
  }

  const check = spawnSync(
    tool,
    ["--store", store, "--check", "--finding", next.finding || "", "--target", next.target || ""],
    { encoding: "utf8" },
  );

  if (check.status === 1) {
    let verdict = {};
    try {
      verdict = JSON.parse(check.stdout);
    } catch {
      // fall through: the exit code is the authority, the message is a courtesy
    }
    return {
      block: true,
      reason: verdict.message || "423 Locked: proven pattern. The linear action is disabled.",
      lever: verdict.lever || "find the single lever and run that",
    };
  }
  return { block: false };
}

// Runnable from the command line, which is how the test drives it.
if (import.meta.url === `file://${process.argv[1]}`) {
  const chunks = [];
  for await (const c of process.stdin) chunks.push(c);
  const input = JSON.parse(Buffer.concat(chunks).toString() || "{}");
  const root = process.env.ESTATE_ROOT || path.resolve(process.cwd());
  process.stdout.write(JSON.stringify(decide(root, input)));
}
