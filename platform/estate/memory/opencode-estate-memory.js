// opencode-estate-memory.js — estate memory's brief in every opencode session's system prompt (#6156).
//
// No memory code lives here: it runs bin/estate-brief, the command every runtime's session-start
// hook runs, once per session, and appends the text to the system prompt of that session's calls.
// bin/estate-memory-install links this file into ~/.config/opencode/plugin/.
//
// It also holds opencode to the plan lock (#6675): tool.execute.before throws, which refuses the
// call, until the session's plan allows it. The bridge answers the plan tools in its own process,
// so this keeps the session's plan-tool calls and asks platform/estate/memory/plan.py -- the rules
// the Claude Code hook replays -- whether the next tool may run. Fails open; ESTATE_PLAN_LOCK=off
// opts out.
import { execFile } from "node:child_process";
import { homedir } from "node:os";
import path from "node:path";

const REPO = process.env.IDP ?? path.join(homedir(), "Documents", "code", "idp");
const BRIEF = path.join(REPO, "bin", "estate-brief");
const PLAN = path.join(REPO, "platform", "estate", "memory", "plan.py");
const TIMEOUT_MS = 8000;
const PLAN_TOOL = /(?:^|_)(declare_plan|revise_plan|add_bdd|address_edgecases|address_2nd_order_effects|complete_goal)$/;

function brief() {
  return new Promise((resolve) => {
    execFile("python3", [BRIEF], { timeout: TIMEOUT_MS }, (_err, stdout) => resolve((stdout ?? "").trim()));
  });
}

// `estate-plan <plan_tool> '<json>'` through bash is the door that works when the bridge did not
// load; plan.py decides whether a command is exactly that, this only keeps the candidates.
const isPlanCall = (tool, args) =>
  PLAN_TOOL.test(tool) || (tool === "bash" && /estate-plan/.test(args?.command ?? ""));

function authorize(tool, calls, args) {
  return new Promise((resolve) => {
    const argv = [PLAN, "authorize", tool, JSON.stringify(args ?? {})];
    const child = execFile("python3", argv, { timeout: TIMEOUT_MS }, (err, stdout) => {
      try {
        resolve(JSON.parse(stdout));
      } catch {
        resolve({ ok: true, reason: `plan check failed open: ${err?.message ?? "no answer"}` });
      }
    });
    child.stdin?.on("error", () => {});
    child.stdin?.end(JSON.stringify(calls));
  });
}

export const EstateMemory = async () => {
  const sessions = new Map();
  const plans = new Map(); // sessionID -> [[tool, args], ...] plan-tool calls, oldest first
  return {
    "experimental.chat.system.transform": async (input, output) => {
      const id = input?.sessionID ?? "";
      if (!sessions.has(id)) sessions.set(id, brief());
      const text = await sessions.get(id);
      if (text) output.system.push(text);
    },
    "tool.execute.before": async (input, output) => {
      if ((process.env.ESTATE_PLAN_LOCK ?? "").toLowerCase() === "off") return;
      const tool = input?.tool ?? "";
      const verdict = await authorize(tool, plans.get(input?.sessionID ?? "") ?? [], output?.args);
      if (verdict && verdict.ok === false) throw new Error(verdict.reason);
    },
    "tool.execute.after": async (input) => {
      const tool = input?.tool ?? "";
      const args = input?.args ?? {};
      if (!isPlanCall(tool, args)) return;
      const id = input?.sessionID ?? "";
      // A call the bridge refused is refused again on replay, so every call is kept as made.
      plans.set(id, [...(plans.get(id) ?? []), [tool, args]]);
    },
  };
};
