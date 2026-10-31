// pi-plan-lock -- every pi agent declares a goal and sub-goals, or it runs nothing.
//
// Ticket: idp#6675. Before this file: the PRM + budget governor graded every pi session and
// printed "goal=(none declared) subgoals=[none]" because pi had NO declare_plan tool, so the
// plan could not be declared by anyone. pi-governance (report-only, one laptop, not in git) then
// showed that FAIL after the fact. The grader (bin/budget_governor.py, bin/trajectory_lock.py)
// already reads pi's transcript shape; the missing half was a tool to call and a refusal to make
// the call unavoidable. This is that half. It does not replace the grader: the declare_plan call
// lands in the transcript, and the grader then finds the goal it was blind to.
//
// The contract (plan.ts): declare_plan -> add_bdd -> address_edgecases + address_2nd_order_effects
// -> complete_goal, per sub-goal. revise_plan is the escape hatch when the work changes.
//
// ENFORCES at tool_call (the only point pi lets an extension refuse). Opt-out for a human-driven
// session: ESTATE_PLAN_LOCK=off. Fail-open on its own errors (R38: a fence a correct machine
// cannot satisfy is an outage), loudly.
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { mkdirSync, writeFileSync, appendFileSync, readFileSync, readdirSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import { MAX_RESULT_CHARS, apply, authorize, capText, linkDecision, type Plan } from "./plan.ts";
import { deriveLinks, type DerivedLinks } from "./derive.ts";

const SPILL_DIR = path.join(homedir(), ".pi", "agent", "state", "overflow");
// THE DURABLE PLAN LEDGER (idp#7518). The plan in this process is the enforcement copy; this is
// the durable one, in the same JSONL shape platform/estate/memory/plan.py replays, so the estate's
// door (mcp/plugins/estate_executor.py) reads the SAME plan this session declared -- and the
// founder can see a declaration after the session that made it is gone.
const LEDGER_DIR = path.join(homedir(), ".estate", "plans");

// The estate's own ledgers, read on demand and never cached: the intent door's record of what
// this session went through, and the prompt ledger's record of the words that started it. A
// stale copy of the estate's memory is worse than a slow read.
const readJsonl = (file: string): Array<Record<string, unknown>> => {
  try {
    return readFileSync(file, "utf8")
      .split("\n")
      .filter((line) => line.trim().length > 0)
      .map((line) => {
        try {
          return JSON.parse(line) as Record<string, unknown>;
        } catch {
          return null;
        }
      })
      .filter((row): row is Record<string, unknown> => row !== null);
  } catch {
    return [];
  }
};

const readLedgers = () => {
  const home = process.env.ESTATE_HOME || path.join(homedir(), ".estate");
  return {
    intents: readJsonl(path.join(LEDGER_DIR, "intents.jsonl")),
    prompts: readJsonl(path.join(home, "state", "prompts.jsonl")),
  };
};

// The intents the estate knows: the installed intent files, by file name and by the name inside
// them. An empty set means the estate cannot judge resolvability at all, so it judges nothing.
const knownIntents = (): Set<string> => {
  const out = new Set<string>();
  const home = process.env.ESTATE_HOME || path.join(homedir(), ".estate");
  for (const dir of [path.join(home, "intents")]) {
    let files: string[] = [];
    try {
      files = readdirSync(dir);
    } catch {
      continue;
    }
    for (const fn of files) {
      if (!/\.ya?ml$/.test(fn)) continue;
      out.add(fn.replace(/\.ya?ml$/, ""));
      try {
        for (const line of readFileSync(path.join(dir, fn), "utf8").split("\n")) {
          const m = /^name:\s*([A-Za-z0-9._-]{2,64})\s*$/.exec(line);
          if (m) {
            out.add(m[1]);
            break;
          }
        }
      } catch {
        // a file that cannot be read is a name the estate cannot know
      }
    }
  }
  return out;
};

// The links the estate can DISPROVE: a link the agent states that resolves to nothing. An empty
// ledger means the estate cannot disprove anything, so it disproves nothing.
const unresolvableLinks = (
  stated: Record<string, unknown>,
  prompts: Array<Record<string, unknown>>,
): string[] => {
  const problems: string[] = [];
  const instruction = typeof stated.instruction === "string" ? stated.instruction.trim() : "";
  const prompt = typeof stated.prompt === "string" ? stated.prompt.trim() : "";
  if (instruction) {
    const known = knownIntents();
    if (known.size > 0 && !known.has(instruction)) {
      problems.push(`instruction '${instruction}' resolves to no known intent`);
    }
  }
  if (prompt) {
    const ids = new Set<string>();
    for (const rec of prompts) {
      const id = typeof rec.id === "string" ? rec.id : "";
      const fp = typeof rec.fingerprint === "string" ? rec.fingerprint : "";
      if (id) ids.add(id);
      if (fp) ids.add(fp);
    }
    if (ids.size > 0 && !ids.has(prompt)) {
      problems.push(`prompt '${prompt}' resolves to no founder prompt`);
    }
  }
  return problems;
};

// Strict is the estate's own switch: while it is off, a missing link is a GAP the plan-link door
// reports and this log records; under it, a plan that cannot be linked refuses.
const strictLinks = () => {
  const v = (process.env.ESTATE_PLAN_LINK_STRICT || "").trim().toLowerCase();
  return v === "1" || v === "true" || v === "yes" || v === "on";
};

// The rollout measurement: every plan the estate could not link, so the founder can count what
// strict would refuse before strict is switched on. Observation never breaks the agent.
const observeLinkGap = (session: string, tool: string, instruction: string, prompt: string) => {
  try {
    const home = process.env.ESTATE_HOME || path.join(homedir(), ".estate");
    const dir = path.join(home, "logs");
    mkdirSync(dir, { recursive: true });
    appendFileSync(
      path.join(dir, "plan-link-observe.log"),
      `${JSON.stringify({ at: new Date().toISOString(), session, tool, instruction, prompt })}\n`,
    );
  } catch {
    // observation is not the agent's problem
  }
};
const off = () => process.env.ESTATE_PLAN_LOCK === "off";
const say = (text: string, details: object = {}) => ({ content: [{ type: "text" as const, text }], details });

const goalId = Type.String({ description: "The sub-goal id from your plan, e.g. goal_1." });
const planShape = Type.Object({
  goal: Type.String({ description: "What 'done' looks like for this task, one sentence." }),
  subgoals: Type.Array(
    Type.Object({
      id: Type.String({ description: "Short unique id, e.g. goal_1" }),
      text: Type.String({ description: "One verifiable step." }),
    }),
    { description: "At least one. Each needs add_bdd before work starts on it." },
  ),
  instruction: Type.Optional(
    Type.String({
      description:
        "The intent this work goes through, e.g. lane-submit. DERIVED from the estate's ledgers when omitted: the last intent this session ran.",
    }),
  ),
  prompt: Type.Optional(
    Type.String({
      description:
        "The founder prompt that started this work. DERIVED from the estate's prompt ledger when omitted: the newest prompt under this session.",
    }),
  ),
});
const items = (what: string) =>
  Type.Array(Type.String(), { description: `At least one ${what}. "none, because <reason>" counts; an empty list does not.` });

const TOOLS = [
  {
    name: "declare_plan",
    label: "Declare Plan",
    description:
      "Declare the goal and sub-goals for this task. REQUIRED before any other tool: nothing else runs until a plan exists. Call it once, first.",
    promptSnippet: "Declare a goal and sub-goals before doing anything else",
    promptGuidelines: [
      "Call declare_plan first in every task; every other tool is refused until you do.",
      "For each sub-goal, in order: add_bdd before any work on it; address_edgecases and address_2nd_order_effects once the behaviour is pinned down; complete_goal only after all three, with proof.",
    ],
    parameters: planShape,
  },
  {
    name: "revise_plan",
    label: "Revise Plan",
    description:
      "Replace the current plan when the work has changed. Sub-goals that keep their id keep their recorded BDD, edge cases, effects and done state.",
    promptSnippet: "Replace the plan when the work changes",
    parameters: planShape,
  },
  {
    name: "add_bdd",
    label: "Add BDD Scenario",
    description:
      "Pin down the behaviour of one sub-goal as Given/When/Then BEFORE any work on it. Work tools stay refused until the active sub-goal has a scenario.",
    promptSnippet: "Write the Given/When/Then for a sub-goal before building it",
    parameters: Type.Object({
      goal_id: goalId,
      given: Type.String({ description: "The starting state." }),
      when: Type.String({ description: "The action." }),
      then: Type.String({ description: "The observable result that proves it works." }),
    }),
  },
  {
    name: "address_edgecases",
    label: "Address Edge Cases",
    description: "Record the edge cases of a sub-goal's BDD scenario and how each is handled. Needs add_bdd first; needed before complete_goal.",
    promptSnippet: "Record a sub-goal's edge cases",
    parameters: Type.Object({ goal_id: goalId, edgecases: items("edge case and how it is handled") }),
  },
  {
    name: "address_2nd_order_effects",
    label: "Address 2nd-Order Effects",
    description:
      "Record the knock-on effects of a sub-goal on the rest of the system (callers, other runtimes, cost, ops). Needs add_bdd first; needed before complete_goal.",
    promptSnippet: "Record a sub-goal's second-order effects",
    parameters: Type.Object({ goal_id: goalId, effects: items("second-order effect and what was done about it") }),
  },
  {
    name: "complete_goal",
    label: "Complete Goal",
    description:
      "Mark one sub-goal done, after you have proven it (a command and its output, not a belief). Refused until add_bdd, address_edgecases and address_2nd_order_effects are recorded for it.",
    promptSnippet: "Check off a proven sub-goal",
    parameters: Type.Object({ goal_id: goalId }),
  },
];

export default function (pi: ExtensionAPI) {
  let plan: Plan | undefined;
  // The session id is what ties this session's declarations to the estate's door. It is stamped
  // into the environment, so the executor door the MCP server talks to knows whose session is
  // asking -- and therefore whether a plan exists before work is done.
  let sessionId = "";

  // A new or resumed session starts unplanned: the plan lives in this process, and a resumed agent
  // re-declaring is one call, where a stale plan from another task would be silent drift.
  pi.on("session_start", async () => {
    plan = undefined;
    sessionId = `pi-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    process.env.ESTATE_SESSION_ID = sessionId;
    // The pointer that binds this session to THIS process. The estate's door runs in the MCP
    // server underneath pi, so it resolves the caller's session by reading the pointer of its
    // parent process -- it never has to take the caller's word for who it is (idp#7518).
    try {
      mkdirSync(LEDGER_DIR, { recursive: true });
      writeFileSync(
        path.join(LEDGER_DIR, `session-${process.pid}.json`),
        JSON.stringify({ session_id: sessionId, at: Date.now() / 1000 }),
      );
    } catch {
      // A pointer that cannot be written costs the door its identity, not the agent its plan:
      // the in-process gate still refuses work without a declaration, and the door records the
      // work it could not attribute.
    }
    // The session's own ledger. Its EXISTENCE is how the estate's door knows this session's
    // adapter is live: a session with a ledger and no plan is refused at the door; a session
    // without one (an adapter that is not installed yet) is allowed and recorded, because a
    // fence a correct machine cannot satisfy is an outage, not a gate.
    try {
      mkdirSync(LEDGER_DIR, { recursive: true });
      appendFileSync(
        path.join(LEDGER_DIR, `${sessionId}.jsonl`),
        `${JSON.stringify({
          at: Date.now() / 1000,
          session: sessionId,
          tool: "session_start",
          args: {},
        })}\n`,
      );
    } catch {
      // The ledger is the door's view of this session. Without it the door cannot enforce
      // here; the in-process gate still refuses undeclared work.
    }
  });

  const ledgerAppend = (tool: string, args: unknown) => {
    try {
      mkdirSync(LEDGER_DIR, { recursive: true });
      const line = JSON.stringify({
        at: Date.now() / 1000,
        session: sessionId,
        tool,
        args: (args ?? {}) as object,
      });
      appendFileSync(path.join(LEDGER_DIR, `${sessionId}.jsonl`), `${line}\n`);
    } catch {
      // A ledger that cannot be written must not stop the agent from working: the in-process
      // gate is still there. The door then sees no plan and refuses -- loudly, and by name.
    }
  };

  // A plan's two links are not the agent's to type: they are DERIVED from the estate's own
  // ledgers -- the last intent this session went through, and the newest founder prompt under
  // this session. The same rule as platform/estate/governance/plan_links.py::derive_links, and
  // the cases both copies agree on live in extensions/pi-plan-lock/cases.json. A link the agent
  // states explicitly is never overwritten.
  const withDerivedLinks = (tool: string, params: unknown) => {
    const raw = { ...((params ?? {}) as Record<string, unknown>) };
    if (tool !== "declare_plan" && tool !== "revise_plan") {
      return { args: raw, decision: { ok: true as const } };
    }
    let links: DerivedLinks | undefined;
    let ledgers: { intents: Array<Record<string, unknown>>; prompts: Array<Record<string, unknown>> } = {
      intents: [],
      prompts: [],
    };
    try {
      ledgers = readLedgers();
      links = deriveLinks(sessionId, ledgers);
    } catch {
      links = undefined;
    }
    const derived = links ?? { instruction: "", prompt: "" };
    const decision = linkDecision(raw, derived, unresolvableLinks(raw, ledgers.prompts), strictLinks());
    const args = { ...raw };
    if (!args.instruction && derived.instruction) args.instruction = derived.instruction;
    if (!args.prompt && derived.prompt) args.prompt = derived.prompt;
    if (decision.ok && !(args.instruction && args.prompt)) {
      observeLinkGap(sessionId, tool, String(args.instruction ?? ""), String(args.prompt ?? ""));
    }
    return { args, decision };
  };

  for (const t of TOOLS) {
    pi.registerTool({
      ...t,
      async execute(_id: string, params: unknown) {
        const prepared = withDerivedLinks(t.name, params);
        if (!prepared.decision.ok) {
          return say(`Refused: ${prepared.decision.reason}`, { refused: true });
        }
        const args = prepared.args;
        const r = apply(plan, t.name, args);
        if (!r.ok) return say(`Refused: ${r.reason}`, { refused: true });
        plan = r.plan;
        ledgerAppend(t.name, args);
        return say(r.message, { plan });
      },
    });
  }

  pi.on("tool_call", async (event: any, ctx: any) => {
    if (off()) return undefined;
    try {
      const name = event?.toolName ?? event?.name;
      if (typeof name !== "string") return undefined;
      const v = authorize(name, plan);
      if (v.ok) return undefined;
      ctx?.ui?.notify?.(`pi-plan-lock refused ${name}`, "warning");
      return { block: true, reason: v.reason };
    } catch (e) {
      ctx?.ui?.notify?.(`pi-plan-lock failed open: ${String(e)}`, "warning");
      return undefined;
    }
  });

  pi.on("tool_result", async (event: any) => {
    try {
      const parts = Array.isArray(event?.content) ? event.content : [];
      const total = parts.reduce((n: number, p: any) => n + (p?.type === "text" ? String(p.text ?? "").length : 0), 0);
      if (total <= MAX_RESULT_CHARS) return undefined;
      const joined = parts.filter((p: any) => p?.type === "text").map((p: any) => String(p.text)).join("\n");
      let spill: string | null = null;
      try {
        mkdirSync(SPILL_DIR, { recursive: true });
        spill = path.join(SPILL_DIR, `${Date.now()}-${String(event?.toolName ?? "tool").replace(/\W/g, "_")}.txt`);
        writeFileSync(spill, joined);
      } catch {
        spill = null;
      }
      const capped = capText(joined, spill);
      const rest = parts.filter((p: any) => p?.type !== "text");
      return { content: [{ type: "text", text: capped.text }, ...rest], details: { ...(event?.details ?? {}), planLockCapped: true, spill } };
    } catch {
      return undefined; // fail open: the original result passes through
    }
  });
}
