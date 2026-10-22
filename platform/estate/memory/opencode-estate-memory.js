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
//
// And it holds opencode to the no-hand-back rule (lane/no-handback): the directive rides in the
// system prompt of every call, and when a session goes idle with a closing message that hands work
// back ("still open", "want me to...?", platform/estate/memory/handback.py) the plugin sends the
// refusal as the next prompt. One retry per closing: a refusal is not judged again. Fails open;
// ESTATE_MEMORY_ENFORCE=0 opts out.
import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";

const REPO = process.env.IDP ?? path.join(homedir(), "Documents", "code", "idp");
const BRIEF = path.join(REPO, "bin", "estate-brief");
const PLAN = path.join(REPO, "platform", "estate", "memory", "plan.py");
// The installed copy first: the shared checkout may be on any branch, and one without this file
// would leave the plugin silently doing nothing (it fails open).
const HOME_COPY = path.join(process.env.ESTATE_MEMORY_HOME ?? path.join(homedir(), ".estate", "memory"), "platform", "estate", "memory", "handback.py");
const HANDBACK = existsSync(HOME_COPY) ? HOME_COPY : path.join(REPO, "platform", "estate", "memory", "handback.py");
const REFUSAL_MARK = "Do not stop here"; // in handback.REMEDY: how a refusal is told from a person
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

// handback.py reads stdin and prints one JSON line; `directive` prints the instruction text.
function handback(arg, stdin) {
  return new Promise((resolve) => {
    const child = execFile("python3", [HANDBACK, arg], { timeout: TIMEOUT_MS }, (_err, stdout) => resolve((stdout ?? "").trim()));
    child.stdin?.on("error", () => {});
    child.stdin?.end(stdin ?? "");
  });
}

const textOf = (m) => (m?.parts ?? []).filter((p) => p?.type === "text" && typeof p.text === "string").map((p) => p.text).join("\n").trim();

// The closing message of the session, judged unless it already answers a refusal.
async function refusalFor(client, sessionID) {
  const res = await client.session.messages({ path: { id: sessionID } });
  const msgs = Array.isArray(res) ? res : (res?.data ?? []);
  const last = msgs[msgs.length - 1];
  if (last?.info?.role !== "assistant") return "";
  const prompt = [...msgs].reverse().find((m) => m?.info?.role === "user");
  if (textOf(prompt).includes(REFUSAL_MARK)) return ""; // already refused once: never loop
  const verdict = JSON.parse((await handback("check", textOf(last))) || "{}");
  return verdict.block ? verdict.reason : "";
}

export const EstateMemory = async ({ client } = {}) => {
  let directive; // read once from handback.py: one definition for every harness
  const sessions = new Map();
  const plans = new Map(); // sessionID -> [[tool, args], ...] plan-tool calls, oldest first
  return {
    "experimental.chat.system.transform": async (input, output) => {
      const id = input?.sessionID ?? "";
      if (!sessions.has(id)) sessions.set(id, brief());
      const text = await sessions.get(id);
      if (text) output.system.push(text);
      if (process.env.ESTATE_MEMORY_ENFORCE === "0") return;
      directive ??= handback("directive");
      const rule = await directive;
      if (rule) output.system.push(rule);
    },
    event: async ({ event }) => {
      try {
        if (event?.type !== "session.idle" || process.env.ESTATE_MEMORY_ENFORCE === "0" || !client) return;
        const sessionID = event.properties?.sessionID;
        const reason = sessionID ? await refusalFor(client, sessionID) : "";
        if (reason) await client.session.prompt({ path: { id: sessionID }, body: { parts: [{ type: "text", text: reason }] } });
      } catch {
        /* fail open: a plugin fault never takes a session down */
      }
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
