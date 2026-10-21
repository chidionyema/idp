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
import { mkdirSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import { MAX_RESULT_CHARS, apply, authorize, capText, type Plan } from "./plan.ts";

const SPILL_DIR = path.join(homedir(), ".pi", "agent", "state", "overflow");
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

  // A new or resumed session starts unplanned: the plan lives in this process, and a resumed agent
  // re-declaring is one call, where a stale plan from another task would be silent drift.
  pi.on("session_start", async () => {
    plan = undefined;
  });

  for (const t of TOOLS) {
    pi.registerTool({
      ...t,
      async execute(_id: string, params: unknown) {
        const r = apply(plan, t.name, params);
        if (!r.ok) return say(`Refused: ${r.reason}`, { refused: true });
        plan = r.plan;
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
