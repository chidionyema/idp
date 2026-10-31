// pi-plan-lock/plan.ts -- the pure rules. No pi import, so `node --test` can run them.
//
// Two rules, both deterministic (AGENTS.md gate 6):
//   1. NO TOOL WITHOUT A CONTRACT. Until declare_plan has been called with a goal and at least one
//      sub-goal, every tool except the plan tools and estate-memory reads is refused. This is the
//      first mechanism of docs/onboarding/trajectory-lock.md, enforced at the one place pi lets us
//      refuse: the tool_call event. The contract has an order:
//        declare_plan -> add_bdd (before any work on the sub-goal) -> address_edgecases and
//        address_2nd_order_effects -> complete_goal.
//      The behaviour is pinned down before it is built; the edges and knock-on effects are of that
//      behaviour, so they come after it and before the sub-goal may be called done.
//   2. NO TOOL RESULT WITHOUT A SIZE. A result above MAX_RESULT_CHARS is cut to head + tail and the
//      whole thing is spilled to a file the agent can read in ranges.
//
// WHY RULE 2 LIVES HERE. Measured 2026-10-20 on a real pi session: ONE estate_execute result was
// 1,411,712 characters (~350k tokens). Pi checks "should I compact" only AFTER an assistant
// message completes, so a result that big lands between the check and the next call, and the next
// call carries all of it. No post-turn compaction can stop a single turn that large; the only
// place to stop it is before it enters the history.

export type Subgoal = { id: string; text: string };
export type Bdd = { given: string; when: string; then: string };
export type Plan = {
  goal: string;
  subgoals: Subgoal[];
  done: string[];
  bdd: Record<string, Bdd>;
  edgecases: Record<string, string[]>;
  effects: Record<string, string[]>;
  // The plan's two links to the estate: the INSTRUCTION (the intent the work goes through) and
  // the PROMPT (the founder prompt that started it). The shape is checked here, in both copies
  // of the contract; whether the names RESOLVE is checked by the governance layer
  // (platform/estate/governance/plan_links.py), which is where the ledgers live.
  instruction?: string;
  prompt?: string;
};
export type Checked<T> = ({ ok: true } & T) | { ok: false; reason: string };

export const MIN_GOAL_CHARS = 8;
export const MIN_SUBGOAL_CHARS = 4;

// An intent name and a founder prompt id. The same two shapes the Python copy checks, so a plan
// accepted by one copy is accepted by the other.
const INSTRUCTION_RE = /^[a-z0-9][a-z0-9._-]{1,63}$/;
const PROMPT_ID_RE = /^[A-Za-z0-9._:-]{3,120}$/;

export const PLAN_TOOLS = [
  "declare_plan",
  "revise_plan",
  "add_bdd",
  "address_edgecases",
  "address_2nd_order_effects",
  "complete_goal",
] as const;

// Never refused: a trapped agent must be able to say it is trapped (trajectory-lock.md,
// "Never blocked"); memory reads are how a plan is made from context; and a runtime's own
// bookkeeping (loading a tool's schema, asking the human, a todo list) is not work. The same
// three lists as platform/estate/memory/plan.py; cases.json holds the two to it.
const NEVER_BLOCKED = new Set<string>([...PLAN_TOOLS, "escalate"]);
const MEMORY_READS = /^(?:brief|recall|remember)$/;
const HOUSEKEEPING = new Set(["toolsearch", "askuserquestion", "todowrite", "todoread", "enterplanmode", "exitplanmode"]);

// 100,000 chars ~ 25k tokens at pi's own 4:1 estimator: far above any result a turn needs, far
// below the 200,000-token ceiling the router enforces.
export const MAX_RESULT_CHARS = 100_000;
const HEAD_CHARS = 60_000;
const TAIL_CHARS = 20_000;

/** A tool's name without the MCP prefix a runtime adds: Claude Code's
 *  mcp__estate-memory__declare_plan, opencode's estate-memory_declare_plan. */
export function bare(name: string): string {
  return name.replace(/^mcp__.+?__/, "").replace(/^estate[-_]memory(?:__|[._-])/, "");
}

const str = (v: unknown) => (typeof v === "string" ? v.trim() : "");
const refuse = (reason: string) => ({ ok: false as const, reason });

export function validatePlan(input: unknown): Checked<{ goal: string; subgoals: Subgoal[]; instruction: string; prompt: string }> {
  const i = (input ?? {}) as { goal?: unknown; subgoals?: unknown; instruction?: unknown; prompt?: unknown };
  const goal = str(i.goal);
  if (goal.length < MIN_GOAL_CHARS) return refuse(`goal must be a sentence of at least ${MIN_GOAL_CHARS} characters`);
  if (!Array.isArray(i.subgoals) || i.subgoals.length === 0) {
    return refuse("declare at least one sub-goal; a goal with no steps is a wish");
  }
  const seen = new Set<string>();
  const subgoals: Subgoal[] = [];
  for (const raw of i.subgoals as Array<{ id?: unknown; text?: unknown }>) {
    const id = str(raw?.id);
    const text = str(raw?.text);
    if (!id || seen.has(id)) return refuse(`sub-goal ids must be unique and non-empty (got "${id}")`);
    if (text.length < MIN_SUBGOAL_CHARS) return refuse(`sub-goal ${id} needs text of at least ${MIN_SUBGOAL_CHARS} characters`);
    seen.add(id);
    subgoals.push({ id, text });
  }
  const instruction = str(i.instruction);
  const prompt = str(i.prompt);
  if ("instruction" in i && !instruction) {
    return refuse("instruction must name the intent this plan serves");
  }
  if ("prompt" in i && !prompt) {
    return refuse("prompt must name the founder prompt this plan answers");
  }
  if (instruction && !INSTRUCTION_RE.test(instruction)) {
    return refuse(`instruction "${instruction}" is not an intent name`);
  }
  if (prompt && !PROMPT_ID_RE.test(prompt)) {
    return refuse(`prompt "${prompt}" is not a founder prompt id`);
  }
  return { ok: true, goal, subgoals, instruction, prompt };
}

/** One plan-tool call against the current plan: the next plan and what to tell the agent, or why
 *  it is refused. Never mutates `plan`. */
export function apply(plan: Plan | undefined, tool: string, args: unknown): Checked<{ plan: Plan; message: string }> {
  const name = bare(tool);
  const a = (args ?? {}) as Record<string, unknown>;
  if (name === "declare_plan" || name === "revise_plan") {
    const v = validatePlan(a);
    if (!v.ok) return v;
    // A revision keeps what was recorded about the sub-goals it keeps: it is an escape hatch, not
    // a reset button for evidence.
    const ids = new Set(v.subgoals.map((s) => s.id));
    const keep = <T>(rec: Record<string, T> | undefined) =>
      Object.fromEntries(Object.entries(rec ?? {}).filter(([id]) => ids.has(id)));
    const next: Plan = {
      goal: v.goal,
      subgoals: v.subgoals,
      done: (plan?.done ?? []).filter((id) => ids.has(id)),
      bdd: keep(plan?.bdd),
      edgecases: keep(plan?.edgecases),
      effects: keep(plan?.effects),
      // A revision keeps the links it does not restate: the work is still the same work.
      instruction: v.instruction || plan?.instruction || "",
      prompt: v.prompt || plan?.prompt || "",
    };
    const first = next.subgoals.find((s) => !next.done.includes(s.id)) ?? next.subgoals[0];
    const links = [
      next.instruction ? `instruction ${next.instruction}` : "",
      next.prompt ? `founder prompt ${next.prompt}` : "",
    ].filter(Boolean);
    return {
      ok: true,
      plan: next,
      message:
        `Plan ${name === "declare_plan" ? "declared" : "revised"}: ${next.goal}\n` +
        next.subgoals.map((s) => `  ${s.id}: ${s.text}`).join("\n") +
        (next.bdd[first.id] ? "" : `\nNext: add_bdd for ${first.id} before any work on it.`) +
        (links.length ? `\nLinked to ${links.join(" and ")}.` : ""),
    };
  }
  if (!(PLAN_TOOLS as readonly string[]).includes(name)) return refuse(`${tool} is not a plan tool`);
  if (!plan) return refuse("no plan declared; call declare_plan first");
  const id = str(a.goal_id);
  if (!plan.subgoals.some((s) => s.id === id)) {
    return refuse(`${id || "(no goal_id)"} is not on this plan (${plan.subgoals.map((s) => s.id).join(", ")})`);
  }
  const next: Plan = structuredClone(plan);

  if (name === "add_bdd") {
    const b: Bdd = { given: str(a.given), when: str(a.when), then: str(a.then) };
    const short = (["given", "when", "then"] as const).filter((k) => b[k].length < MIN_SUBGOAL_CHARS);
    if (short.length) {
      return refuse(`the scenario for ${id} needs ${short.join(", ")}: each a clause of at least ${MIN_SUBGOAL_CHARS} characters`);
    }
    next.bdd[id] = b;
    return { ok: true, plan: next, message: `Scenario for ${id}: Given ${b.given}, When ${b.when}, Then ${b.then}` };
  }

  if (name === "address_edgecases" || name === "address_2nd_order_effects") {
    const field = name === "address_edgecases" ? "edgecases" : "effects";
    const what = name === "address_edgecases" ? "edge case" : "second-order effect";
    if (!plan.bdd[id]) {
      return refuse(`${id} has no BDD scenario yet. add_bdd comes first: the ${what}s are of the behaviour it pins down`);
    }
    const raw = a[field];
    const items = Array.isArray(raw) ? raw.map(str).filter((s) => s.length >= MIN_SUBGOAL_CHARS) : [];
    if (!items.length) {
      return refuse(`list at least one ${what} for ${id} in \`${field}\` ("none, because <reason>" counts; silence does not)`);
    }
    next[field][id] = items;
    return { ok: true, plan: next, message: `${items.length} ${what}(s) recorded for ${id}` };
  }

  // complete_goal
  const missing = [
    !plan.bdd[id] && "add_bdd",
    !plan.edgecases[id] && "address_edgecases",
    !plan.effects[id] && "address_2nd_order_effects",
  ].filter(Boolean);
  if (missing.length) return refuse(`${id} cannot be marked done yet: call ${missing.join(", then ")} first`);
  if (!next.done.includes(id)) next.done.push(id);
  const remaining = next.subgoals.map((s) => s.id).filter((s) => !next.done.includes(s));
  return {
    ok: true,
    plan: next,
    message: remaining.length ? `${id} done. Remaining: ${remaining.join(", ")}` : `${id} done. All sub-goals complete.`,
  };
}

export function authorize(tool: string, plan: Plan | undefined): Checked<{}> {
  const name = bare(tool);
  if (NEVER_BLOCKED.has(name) || MEMORY_READS.test(name) || HOUSEKEEPING.has(name.toLowerCase())) return { ok: true };
  if (!plan) {
    return refuse(
      `No plan declared, so ${tool} is refused. Call declare_plan first with a goal and at ` +
        `least one sub-goal: declare_plan({goal: "<what done looks like>", subgoals: ` +
        `[{id: "goal_1", text: "<first step>"}]}). Nothing else runs until you do.`,
    );
  }
  const active = plan.subgoals.find((s) => !plan.done.includes(s.id));
  if (!active) {
    return refuse(`Every sub-goal of "${plan.goal}" is done, so ${tool} is refused. Call revise_plan to declare what is next.`);
  }
  if (!plan.bdd[active.id]) {
    return refuse(
      `${active.id} ("${active.text}") has no BDD scenario, so ${tool} is refused. Pin the behaviour down ` +
        `before building it: add_bdd({goal_id: "${active.id}", given: "<state>", when: "<action>", then: "<observable result>"}).`,
    );
  }
  return { ok: true };
}

/** Head + tail of an over-long result, with the size and the spill path in the marker so the
 *  agent can read the rest by range instead of re-running the command. */
export function capText(text: string, spillPath: string | null, max = MAX_RESULT_CHARS): { text: string; capped: boolean } {
  if (text.length <= max) return { text, capped: false };
  const cut = text.length - HEAD_CHARS - TAIL_CHARS;
  const where = spillPath
    ? `full output (${text.length.toLocaleString("en-US")} chars) saved to ${spillPath}; read it with offset/limit`
    : `full output was ${text.length.toLocaleString("en-US")} chars and could not be saved; re-run with a narrower command`;
  return {
    capped: true,
    text:
      text.slice(0, HEAD_CHARS) +
      `\n\n[... ${cut.toLocaleString("en-US")} chars cut by pi-plan-lock to protect the context window: ${where} ...]\n\n` +
      text.slice(text.length - TAIL_CHARS),
  };
}
