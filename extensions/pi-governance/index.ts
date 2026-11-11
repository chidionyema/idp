// pi-governance/index.ts — the pi-side wiring for the estate's end-of-turn gates.
//
// WHY THIS EXISTS. bin/reasoning_gateway_hook.py grades a finished session with the PRM
// (bin/idp-prm --grade) and the budget governor (bin/idp-budget --run) and writes the verdict to
// ~/.pi/agent/reasoning-gateway/<session_id>.json. It is correct and its self-test passes. It was
// also not wired to anything: measured 2026-09-23, all 16 verdicts on this machine read
// `prm_exit=1 budget_exit=1` and not one of them had ever been shown to a human or an agent. A
// gate whose verdict nobody reads is not a gate (LAW: a gate that cannot fail is not a gate) — so
// this file is the missing caller, not a second gate.
//
// REPORT, DON'T BLOCK. This is the hook's own documented contract, and it is deliberate: PRM and
// budget grade a WHOLE transcript from turn one, so blocking Stop on an early step of a long
// session that was later corrected would teach agents to route around the gate. This extension
// therefore never denies a turn, never throws at the caller, and never delays a session: it fires
// the grade, and it puts the FAIL verdict where a person and the agent will both see it.
//
// FAIL OPEN, LOUDLY. Every error path here returns without blocking (LAW 38 — a fence a correct
// machine cannot satisfy is an outage): a missing hook script, an unreadable transcript, a spawn
// failure. Fail-open is not silence, though; the failure is reported, never swallowed.

import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const REPO = "/Users/roseonyema/Documents/code/idp";
const HOOK = `${REPO}/bin/reasoning_gateway_hook.py`;
const TIMEOUT_MS = 45_000;

type Gate = { exit: number; stdout: string };
type Verdict = { prm?: Gate; budget?: Gate; blind?: string; session_id?: string };

/** Fire the hook with the transcript path on stdin. Resolves to the hook's own exit code and
 *  stdout; never rejects — a governor that can take a session down is an outage, not a governor. */
function grade(transcriptPath: string, sessionId: string): Promise<Verdict | null> {
  return new Promise((resolve) => {
    let proc;
    try {
      proc = spawn("python3", [HOOK, "--hook"], { cwd: REPO, stdio: ["pipe", "pipe", "pipe"] });
    } catch {
      resolve(null);
      return;
    }
    let out = "";
    const timer = setTimeout(() => {
      try {
        proc.kill("SIGKILL");
      } catch {
        /* already gone */
      }
      resolve(null);
    }, TIMEOUT_MS);
    proc.stdout?.on("data", (d) => {
      out += String(d);
    });
    proc.on("error", () => {
      clearTimeout(timer);
      resolve(null);
    });
    proc.on("close", () => {
      clearTimeout(timer);
      // The hook --report prints the ledger; --hook writes it. Read the file it just wrote, so
      // this reflects the recorded verdict rather than a scraped stdout.
      resolve(verdictFor(sessionId) ?? null);
      void out;
    });
    try {
      proc.stdin?.end(JSON.stringify({ transcript_path: transcriptPath, session_id: sessionId }));
    } catch {
      clearTimeout(timer);
      resolve(null);
    }
  });
}

/** The ledger the hook writes. Read synchronously: it is one small JSON file, and keeping this
 *  path free of an await keeps the notification immediate. */
function verdictFor(sessionId: string): Verdict | null {
  try {
    const p = `${process.env.HOME}/.pi/agent/reasoning-gateway/${sessionId}.json`;
    if (!existsSync(p)) return null;
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    return JSON.parse(require("node:fs").readFileSync(p, "utf8")) as Verdict;
  } catch {
    return null;
  }
}

/** One line a human can act on. The hook already writes the actionable text ("no plan declared.
 *  Call declare_plan first"), so quote it rather than re-deriving it. */
function summarise(v: Verdict): { text: string; level: "info" | "warning" | "error" } {
  if (v.blind) return { text: `Governance: BLIND — ${v.blind}`, level: "warning" };
  const fail: string[] = [];
  if (v.prm && v.prm.exit !== 0) fail.push("PRM");
  if (v.budget && v.budget.exit !== 0) fail.push("budget");
  if (fail.length === 0) return { text: "Governance: PRM + budget green", level: "info" };
  const first = (v.budget?.stdout || v.prm?.stdout || "").split("\n")[0].trim();
  return {
    text: `Governance FAIL (${fail.join(" + ")}): ${first || "see ~/.pi/agent/reasoning-gateway/"}`,
    level: "warning",
  };
}

export default function (pi: ExtensionAPI) {
  pi.on("turn_end", async (event, ctx) => {
    try {
      const msg = (event as any)?.message;
      if (!msg || msg.role !== "assistant") return;
      if (!existsSync(HOOK)) return; // not this repo's checkout; nothing to fire

      const sessionId = ctx.sessionManager.getSessionId();
      // getSessionFile() is the on-disk transcript; without it the hook would grade nothing.
      const transcript = ctx.sessionManager.getSessionFile?.() ?? "";
      if (!transcript) return;

      const verdict = await grade(transcript, sessionId);
      if (!verdict) return;

      const { text, level } = summarise(verdict);
      ctx.ui.notify(text, level);
    } catch {
      // Fail open, per the file header. Never take a live session down for a governor.
    }
  });

  // A visible way to read the ledger back from inside a session — the same data the founder had
  // to ask for, now one command away.
  pi.registerCommand("governance", {
    description: "Show the last governance verdicts (PRM + budget) recorded on this machine",
    handler: async (_args, ctx) => {
      const dir = `${process.env.HOME}/.pi/agent/reasoning-gateway`;
      try {
        const { readFileSync, readdirSync } = require("node:fs");
        const files = readdirSync(dir).filter((f: string) => f.endsWith(".json"));
        let failing = 0;
        let total = 0;
        for (const f of files) {
          total += 1;
          const v = JSON.parse(readFileSync(`${dir}/${f}`, "utf8")) as Verdict;
          if (v.blind || v.prm?.exit !== 0 || v.budget?.exit !== 0) failing += 1;
        }
        ctx.ui.notify(
          `Governance: ${total} session(s) graded, ${failing} failing. Ledger: ${dir}`,
          failing > 0 ? "warning" : "info",
        );
      } catch {
        ctx.ui.notify("Governance: no ledger on this machine yet", "info");
      }
    },
  });
}
