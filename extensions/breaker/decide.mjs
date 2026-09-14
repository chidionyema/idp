// decide.mjs — the breaker's decision, callable from node so the extension and its test agree.
//
// The logic is bin/idp-circuit-breaker's, which is merged and has a rules.yaml row. This module
// exists because a pi extension is TypeScript and the estate's gate is Python: the test drives
// this file by name, and the extension imports it, so there is one implementation and not two.
//
// Kept dependency-free on purpose. An extension that fails to load is a guard nobody has
// (LAW 28), and an import that cannot resolve is how that happens.

import { spawnSync } from "node:child_process";
import * as fs from "node:fs";
import * as path from "node:path";

/**
 * Find bin/idp-circuit-breaker, wherever the checkout actually is.
 *
 * A checkout is often a git worktree, and the primary clone is frequently on another branch (this
 * estate runs one session per worktree and switches the primary). Assuming `repoRoot/bin` therefore
 * finds nothing exactly when a session is working in a worktree, which is the normal case here.
 *
 * Candidates, in order: the path given, then any worktree of the same repository, then the estate's
 * home checkout. The first one that holds the tool wins. Nothing is guessed: a miss returns null and
 * the caller reports BLIND.
 *
 * A root the caller NAMED but which does not exist is not a candidate at all, and it stops the
 * search -- it is not a checkout, so no other checkout may answer for it. Measured 2026-09-13:
 * passing '/nonexistent-root' fell through to the home checkout, found the tool there, replayed the
 * observations and returned 423 Locked, so a caller asking about a root that is not there was
 * answered with a DIFFERENT root's verdict. Silence is not the only way to lie about a missing
 * tool; answering from somewhere else is the same defect wearing a result.
 */
function findTool(repoRoot) {
  const rel = path.join("bin", "idp-circuit-breaker");
  const seen = new Set();
  // A named root that is not on disk ends the search: BLIND, and never another checkout's answer.
  if (repoRoot && !fs.existsSync(repoRoot)) return null;
  const roots = [repoRoot, process.env.ESTATE_ROOT, path.join(process.env.HOME || "~", "dev", "code", "idp")];
  for (const r of roots) {
    if (r) seen.add(path.resolve(r));
  }
  // Every worktree of the supplied checkout, which `git worktree list` names by absolute path.
  if (repoRoot) {
    const wt = spawnSync("git", ["-C", repoRoot, "worktree", "list", "--porcelain"], {
      encoding: "utf8",
    });
    for (const line of (wt.stdout || "").split("\n")) {
      if (line.startsWith("worktree ")) seen.add(path.resolve(line.slice(9).trim()));
    }
  }
  for (const root of seen) {
    const p = path.join(root, rel);
    try {
      if (fs.existsSync(p)) return p;
    } catch {
      // an unreadable candidate is not a candidate
    }
  }
  return null;
}

/**
 * Ask bin/idp-circuit-breaker whether the next action may proceed.
 *
 * The estate's breaker is the authority. This shells out to it rather than reimplementing the
 * fingerprint, so a change to the fingerprint changes both at once (LAW 43: never a second copy).
 *
 * @param {string} repoRoot  the checkout that holds bin/idp-circuit-breaker
 * @param {{observations: Array<{finding: string, target: string}>, next: {finding: string, target: string}}} input
 * @returns {{block: boolean, reason?: string, lever?: string, blind?: string}}
 */
export function decide(repoRoot, input) {
  const tool = findTool(repoRoot);
  if (!tool) {
    // BLIND, never a pass. Measured 2026-09-12: the tool was on main but the primary checkout sat
    // on another branch, so the path did not resolve, spawnSync returned nothing, and this function
    // answered "not locked" for a pattern that was proved elsewhere. A guard that cannot run its
    // check must say so -- silence here is indistinguishable from a clean result.
    return {
      block: false,
      blind: `bin/idp-circuit-breaker not found under ${repoRoot}; the breaker did not run`,
    };
  }
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
