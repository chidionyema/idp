/**
 * breaker — enforcement for the circuit breaker, in the one place an agent cannot walk past.
 *
 * Founder, 2026-09-12: "throw the 423 Locked exception at N=3" and, on the estate's habit of
 * writing guards nothing runs, "everything needs enforcement".
 *
 * The logic is bin/idp-circuit-breaker, which has a rules.yaml row and two fixtures. This file is
 * the wiring: it watches the agent's own tool calls, records what each one found, and returns
 * { block, reason } the moment a third target carries the same finding. That is the same event
 * pi-governance already hooks, so a session gets the refusal before the call runs, not after.
 *
 * WHY HERE AND NOT IN CI. A rules.yaml row proves the breaker's logic but runs in CI, hours after
 * the mistake and on a different machine. The behaviour it exists to stop -- checking a ninth
 * target after the third proved the cause -- happens in the session, in seconds. Measured
 * 2026-09-12: nine pull requests, one cause, and five checks spent proving it. Enforcement that
 * arrives after the session has ended is a report.
 *
 * WHAT IT DOES NOT DO. It does not decide whether a finding is real, or whether a target's failure
 * matters. It counts and fingerprints. A different finding on a locked target is allowed, and nine
 * findings across nine targets never lock -- a guard that refuses correct work is an outage (R38).
 */

import * as fs from "node:fs";
import * as path from "node:path";
import { spawnSync } from "node:child_process";
import { decide } from "./decide.mjs";
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

/** Where the record lives, so a reviewer can read what was proved and when. */
const STATE =
  process.env.ESTATE_BREAKER_STATE ||
  path.join(process.env.HOME || "~", ".estate", "breaker-observations.jsonl");

/** The checkout that holds bin/idp-circuit-breaker. */
const ROOT =
  process.env.ESTATE_ROOT ||
  path.join(process.env.HOME || "~", "dev", "code", "idp");

/** Findings about a target, pulled out of a tool's result.
 *
 *  THE MISFIRE OF 2026-09-13, AND WHY THIS DELEGATES INSTEAD OF DECIDING.
 *
 *  Two copies of "what counts as a finding" is how this broke. The library in
 *  bin/idp-circuit-breaker already knew the rule; this file reimplemented it as "return the tool's
 *  raw output", so `echo hello` and `cat .git/HEAD` registered as findings, three repeated
 *  commands tripped N=3, and the guard locked bash and read -- the two tools a session needs to
 *  investigate or fix anything. It locked a working session for hours and could not be cleared
 *  from inside, because every clearing command was itself a bash call. R38: a guard that refuses
 *  correct work is an outage.
 *
 *  So there is now ONE rule, in the library, and this asks it. The library returns null when a
 *  result carries no finding -- a successful command, a shell builtin echoing its input, an empty
 *  result -- and a fingerprint when it does, and that single answer decides everything here.
 */
function findingsFrom(toolName: string, input: unknown, output: unknown): string[] {
  // Only reads and queries produce findings worth counting. A write is a change, not a diagnosis,
  // and counting those would lock the tool an agent needs to fix the thing.
  if (toolName !== "bash" && toolName !== "read") return [];
  const text = typeof output === "string" ? output : JSON.stringify(output ?? "");
  if (!text) return [];
  const fp = fingerprintVia(text);
  return fp ? [fp] : [];
}

/** Ask bin/idp-circuit-breaker for the fingerprint of this text.
 *
 *  Shelled out rather than reimplemented: the extension cannot import the Python module, and a
 *  second copy of the rule is exactly the defect being fixed. The call is O(1) and only runs for
 *  a read/query that produced output at all.
 */
function fingerprintVia(text: string): string | null {
  try {
    const r = spawnSync("python3", [path.join(ROOT, "bin", "idp-circuit-breaker"), "--fingerprint"], {
      input: text,
      encoding: "utf-8",
      timeout: 5000,
    });
    if (r.status !== 0) return null;
    const out = (r.stdout || "").trim();
    if (!out || out === "null") return null; // no finding: cannot lock, whatever the bytes
    return out;
  } catch {
    // A guard that cannot ask must not become a guard that blocks. Nothing observed.
    return null;
  }
}

function append(row: Record<string, unknown>): void {
  try {
    fs.mkdirSync(path.dirname(STATE), { recursive: true });
    fs.appendFileSync(STATE, JSON.stringify(row) + "\n");
  } catch {
    // A guard that cannot record must not become a guard that blocks. The block decision below
    // reads the same file, so a write failure degrades to "nothing observed".
  }
}

function replay(): Array<{ finding: string; target: string }> {
  try {
    return fs
      .readFileSync(STATE, "utf-8")
      .split("\n")
      .filter((l) => l.trim())
      .map((l) => {
        try {
          return JSON.parse(l);
        } catch {
          return null;
        }
      })
      .filter(Boolean) as Array<{ finding: string; target: string }>;
  } catch {
    return [];
  }
}

export default function (pi: ExtensionAPI) {
  // Record a finding after a read/query completes, naming the tool call as the target. The target
  // is what the finding was about -- for a pull request check that is the PR, and a session that
  // checks nine PRs produces nine targets. One target checked twice is one target, which
  // decide() already handles.
  pi.on("tool_result", async (event, _ctx) => {
    const findings = findingsFrom(event.toolName, event.input, event.output);
    if (!findings.length) return; // no finding -> no observation -> cannot lock. The bug, fixed.
    const target =
      (event.input as { command?: string })?.command?.slice(0, 120) ??
      (event.input as { path?: string })?.path ??
      event.toolName;
    const at = new Date().toISOString();
    append(findings.map((finding) => ({ finding, target, at, tool: event.toolName })));
  });

  // THE HARD GATE. Before a read/query runs, ask whether its pattern is already proved. If it is,
  // the call is refused with the same 423 the CLI returns, and the lever is named -- a wall with
  // no door is an outage.
  pi.on("tool_call", async (event, _ctx) => {
    if (event.toolName !== "bash" && event.toolName !== "read") return undefined;
    const observations = replay();
    if (observations.length < 3) return undefined; // nothing can be proved yet

    const pending =
      (event.input as { command?: string })?.command ??
      (event.input as { path?: string })?.path ??
      event.toolName;

    // Ask the estate's breaker with the last observation as the candidate finding: the question is
    // "is this pattern proved", and the pattern is whatever the recent targets had in common.
    const v = decide(ROOT, {
      observations: observations.slice(-3),
      next: { finding: observations[observations.length - 1].finding, target: pending },
    });
    if (!v.block) return undefined;
    return {
      block: true,
      reason: `${v.reason}\n\nInstead: ${v.lever}`,
    };
  });
}
