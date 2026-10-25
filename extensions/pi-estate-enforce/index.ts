// pi-estate-enforce -- pi agents get the estate's write-side gates: the claim write gate and
// the write-back stop gate (#7006).
//
// Ticket: idp#7006. Before this file the gates ran only in Claude Code: bin/estate-memory-enforce
// is wired into the Claude Code settings as a PreToolUse hook (Edit|Write|MultiEdit|NotebookEdit
// -> pre) and a Stop hook (-> stop). pi has no hooks, so a pi agent could change any file in the
// estate's own checkout with no live claim over it, and could end a turn having changed files and
// written nothing back -- the two rules the founder asked for, invisible to pi.
//
// The decisions are not re-implemented here. This extension renders pi's session into the
// transcript shape the estate's binary reads (hook.ts), sends the binary the hook payload, and
// turns its answer into pi's two refusal points: { block: true } on a tool call, and a turn
// pushed back when the run ends. The claim register (focus.py), the hand-back judge (handback.py)
// and the write-back rule stay in the binary, so both runtimes are decided by the same code and
// every decision lands in the same ledger (~/.estate/memory/enforce-ledger.jsonl).
//
// Fail-open on its own errors (R38: a fence a correct machine cannot satisfy is an outage),
// loudly. ESTATE_MEMORY_ENFORCE=0 opts out, exactly as the binary does.
import { execFile } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { filePathOf, isEditTool, parseBlock, parseDeny, renderTranscript, wireToolName } from "./hook.ts";

const HOME = process.env.ESTATE_MEMORY_HOME ?? path.join(homedir(), ".estate", "memory");
// The installed copy, never a checkout: the shared checkout is on somebody's branch and may not
// have this file at all (the same rule the memory bridge follows).
const ENFORCE = path.join(HOME, "bin", "estate-memory-enforce");
const STATE_DIR = path.join(homedir(), ".pi", "agent", "state", "enforce");
const TIMEOUT_MS = 15_000;

const enabled = () => process.env.ESTATE_MEMORY_ENFORCE !== "0";

function enforce(mode: string, payload: Record<string, unknown>): Promise<string> {
  return new Promise((resolve) => {
    if (!existsSync(ENFORCE)) {
      resolve("");
      return;
    }
    const child = execFile(
      "python3",
      [ENFORCE, mode],
      { timeout: TIMEOUT_MS, env: process.env },
      (_err, stdout) => resolve(String(stdout ?? "")),
    );
    child.stdin?.on("error", () => {});
    child.stdin?.end(JSON.stringify(payload));
  });
}

function sessionId(ctx: any): string {
  try {
    return String(ctx?.sessionManager?.getSessionId?.() ?? "pi-session");
  } catch {
    return "pi-session";
  }
}

function entries(ctx: any): unknown[] {
  try {
    return (ctx?.sessionManager?.getEntries?.() ?? []) as unknown[];
  } catch {
    return [];
  }
}

function writeTranscript(text: string, sid: string): string {
  const dir = STATE_DIR;
  mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `${sid.replace(/\W/g, "_")}.jsonl`);
  writeFileSync(file, text);
  return file;
}

export default function (pi: ExtensionAPI) {
  // A refusal ends the turn; the retry after it is not judged again (one retry, never a loop).
  let refused = false;

  pi.on("tool_call", async (event: any, ctx: any) => {
    if (!enabled()) return undefined;
    try {
      const name = String(event?.toolName ?? event?.name ?? "");
      if (!isEditTool(name)) return undefined;
      const file = filePathOf(event?.input);
      if (!file) return undefined;
      const sid = sessionId(ctx);
      const transcript = writeTranscript(renderTranscript(entries(ctx)), sid);
      const out = await enforce("pre", {
        tool_name: wireToolName(name),
        tool_input: { file_path: file },
        session_id: sid,
        transcript_path: transcript,
      });
      const deny = parseDeny(out);
      if (!deny) return undefined;
      ctx?.ui?.notify?.("pi-estate-enforce refused a write with no live claim over it", "warning");
      return { block: true, reason: deny };
    } catch (e) {
      ctx?.ui?.notify?.(`pi-estate-enforce failed open: ${String(e)}`, "warning");
      return undefined;
    }
  });

  // The stop gate runs when the run ends (agent_end), which is pi's Claude Code Stop hook: a
  // turn is one model response, and a run is the whole answer to one prompt.
  pi.on("agent_end", async (event: any, ctx: any) => {
    if (!enabled()) return undefined;
    try {
      const messages: any[] = Array.isArray(event?.messages) ? event.messages : [];
      const last = messages[messages.length - 1];
      const sid = sessionId(ctx);
      const transcript = writeTranscript(renderTranscript(entries(ctx), last), sid);
      const out = await enforce("stop", {
        session_id: sid,
        transcript_path: transcript,
        stop_hook_active: refused,
      });
      const block = parseBlock(out);
      if (!block) {
        refused = false;
        return undefined;
      }
      refused = true;
      pi.sendUserMessage(block.reason, { deliverAs: "followUp" });
      return undefined;
    } catch (e) {
      ctx?.ui?.notify?.(`pi-estate-enforce failed open: ${String(e)}`, "warning");
      return undefined;
    }
  });
}
