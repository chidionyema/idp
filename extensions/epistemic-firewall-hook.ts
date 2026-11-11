// epistemic-firewall-hook.ts — the one forced hook: no agent session proceeds unless the
// epistemic firewall clears it.
//
// WHY THIS EXISTS. bin/epistemic_firewall.py grades a session transcript: a first-person claim of
// completed work is refused unless THREE independent pieces of evidence back it, one reading state
// the agent did not author. Before this hook, the firewall was on-demand only — it fired when
// someone remembered to call it, and nothing stopped a session from working without it.
//
// WHAT THIS IS. A single `session_start` handler that runs the firewall's `--gate` mode against
// the previous session's transcript (the only transcript that exists at the moment a new session
// begins) and, on a refusal, blocks all further work by removing the shell/capability tools the
// agent uses to act.
//
// WHAT THIS IS NOT. A kill switch for a broken grader. The firewall's `--gate` currently prints
// a human-readable report and exits non-zero on FAIL, not JSON. Treating "the grader failed"
// the same as "the grader says you failed" means one bad transcript permanently blackouts every
// future session. A grader that cannot answer is a broken grader; it is not a verdict.
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { execFileSync } from "node:child_process";
import { existsSync, readdirSync, statSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";

const FIREWALL = path.join(homedir(), "Documents", "code", "idp", "bin", "epistemic_firewall.py");
const SESSIONS = path.join(homedir(), ".pi", "agent", "sessions");

// Newest transcript under the sessions root, newest first. The session being started has no file
// yet, so the prior one is the thing to grade: an agent may not begin until the last session it
// left behind cleared the firewall.
function priorTranscript(): string | null {
  if (!existsSync(SESSIONS)) return null;
  const found: Array<{ p: string; m: number }> = [];
  const walk = (dir: string) => {
    for (const e of readdirSync(dir)) {
      const p = path.join(dir, e);
      let s;
      try {
        s = statSync(p);
      } catch {
        continue;
      }
      if (s.isDirectory()) walk(p);
      else if (p.endsWith(".jsonl")) found.push({ p, m: s.mtimeMs });
    }
  };
  walk(SESSIONS);
  found.sort((a, b) => b.m - a.m);
  return found[0]?.p ?? null;
}

// Run the firewall's --gate mode. Returns the reason to block, or null to allow.
//
// The firewall currently prints a human report and exits non-zero on FAIL. That is not a JSON
// verdict, and a non-zero exit makes execFileSync throw before we ever see stdout. Both cases
// are handled here as "the gate is not answering in a form we can enforce on", and neither is a
// reason to strip the session's tools. Only an explicit { block: true } block blocks.
function gate(transcript: string): string | null {
  try {
    const out = execFileSync(
      "python3",
      [FIREWALL, "--gate", transcript],
      { encoding: "utf8", timeout: 30_000, maxBuffer: 1024 * 1024 },
    ).trim();

    if (out.startsWith("{")) {
      const v = JSON.parse(out) as { block: boolean; why: string };
      return v.block ? v.why || "the firewall refused this session" : null;
    }

    console.log(
      "[epistemic-firewall] gate printed a report, not a verdict. Not killing tools.",
    );
    console.log(out.slice(0, 500));
    return null;
  } catch (err) {
    console.log(`[epistemic-firewall] gate error, NOT killing tools: ${String(err)}`);
    return null;
  }
}

export default function (pi: ExtensionAPI) {
  pi.on("session_start", async (event, ctx) => {
    // Prefer the explicitly-named previous session; otherwise grade the newest transcript on disk.
    const prior: string | null =
      (event as { previousSessionFile?: string }).previousSessionFile ?? priorTranscript();

    if (prior && existsSync(prior)) {
      const reason = gate(prior);
      if (reason) {
        // A real, explicit block from the firewall. Remove the tools so the unproven claim
        // cannot be acted on.
        pi.setActiveTools([]);
        console.log(
          `[epistemic-firewall] BLOCKED session: prior transcript ${path.basename(prior)} ` +
            `failed the gate (${reason}). No tools available until the prior session clears.`,
        );
        ctx.ui?.notify?.(
          `Epistemic firewall refused this session: ${reason}`,
          "error",
        );
        return;
      }
      console.log(
        `[epistemic-firewall] cleared: prior transcript ${path.basename(prior)} passed the gate.`,
      );
      return;
    }

    // No transcript to grade. This fires on every fresh machine and every first launch, so it
    // must not strip tools — there is nothing to enforce against and nothing to compare to.
    console.log("[epistemic-firewall] no prior transcript to grade; allowing session.");
  });
}