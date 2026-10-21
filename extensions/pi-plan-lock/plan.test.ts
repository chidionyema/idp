import test from "node:test";
import assert from "node:assert/strict";
import { MAX_RESULT_CHARS, apply, authorize, capText, validatePlan, type Plan } from "./plan.ts";

const good = { goal: "stop sessions exceeding the ceiling", subgoals: [{ id: "goal_1", text: "cap tool output" }] };
const two = { goal: good.goal, subgoals: [{ id: "a", text: "first step" }, { id: "b", text: "second step" }] };
const bdd = (goal_id: string) => ({ goal_id, given: "a huge result", when: "the tool returns", then: "it is capped" });

function run(...calls: Array<[string, unknown]>): Plan | undefined {
  let plan: Plan | undefined;
  for (const [tool, args] of calls) {
    const r = apply(plan, tool, args);
    assert.equal(r.ok, true, `${tool}: ${(r as any).reason}`);
    plan = (r as any).plan;
  }
  return plan;
}

test("no plan: an ordinary tool is refused and the refusal names declare_plan", () => {
  const r = authorize("estate_execute", undefined);
  assert.equal(r.ok, false);
  assert.match((r as any).reason, /declare_plan/);
});

test("no plan: the plan tools, escalate and memory reads are never refused", () => {
  for (const t of ["declare_plan", "revise_plan", "add_bdd", "address_edgecases", "address_2nd_order_effects", "complete_goal", "escalate", "brief", "recall", "estate-memory.brief"]) {
    assert.equal(authorize(t, undefined).ok, true, t);
  }
});

test("a declared plan with no BDD for the active sub-goal still refuses work, naming add_bdd", () => {
  const plan = run(["declare_plan", good]);
  const r = authorize("estate_execute", plan);
  assert.equal(r.ok, false);
  assert.match((r as any).reason, /add_bdd/);
});

test("a BDD scenario for the active sub-goal unlocks work", () => {
  assert.equal(authorize("estate_execute", run(["declare_plan", good], ["add_bdd", bdd("goal_1")])).ok, true);
});

test("a goal with no sub-goal, a stub goal, duplicate ids and empty text are all refused", () => {
  assert.equal(validatePlan({ goal: "stop sessions exceeding the ceiling", subgoals: [] }).ok, false);
  assert.equal(validatePlan({ goal: "x", subgoals: good.subgoals }).ok, false);
  assert.equal(validatePlan({ goal: good.goal, subgoals: [good.subgoals[0], good.subgoals[0]] }).ok, false);
  assert.equal(validatePlan({ goal: good.goal, subgoals: [{ id: "a", text: "" }] }).ok, false);
  assert.equal(validatePlan(undefined).ok, false);
});

test("edge cases and 2nd-order effects are refused before add_bdd: the BDD comes first", () => {
  const plan = run(["declare_plan", good]);
  for (const [tool, field] of [["address_edgecases", "edgecases"], ["address_2nd_order_effects", "effects"]]) {
    const r = apply(plan, tool, { goal_id: "goal_1", [field]: ["empty output passes untouched"] });
    assert.equal(r.ok, false, tool);
    assert.match((r as any).reason, /add_bdd comes first/);
  }
});

test("a BDD with a missing clause and an empty edge-case list are refused", () => {
  const plan = run(["declare_plan", good]);
  assert.equal(apply(plan, "add_bdd", { goal_id: "goal_1", given: "a huge result", when: "", then: "it is capped" }).ok, false);
  const withBdd = run(["declare_plan", good], ["add_bdd", bdd("goal_1")]);
  assert.equal(apply(withBdd, "address_edgecases", { goal_id: "goal_1", edgecases: [] }).ok, false);
});

test("complete_goal is refused until BDD, edge cases and 2nd-order effects are all recorded", () => {
  const steps: Array<[string, unknown]> = [
    ["declare_plan", two],
    ["add_bdd", bdd("a")],
    ["address_edgecases", { goal_id: "a", edgecases: ["empty output passes untouched"] }],
    ["address_2nd_order_effects", { goal_id: "a", effects: ["none, because only pi loads it"] }],
  ];
  for (let n = 1; n < steps.length; n++) {
    const r = apply(run(...steps.slice(0, n)), "complete_goal", { goal_id: "a" });
    assert.equal(r.ok, false, `after ${n} step(s) complete_goal must refuse`);
  }
  const done = apply(run(...steps), "complete_goal", { goal_id: "a" });
  assert.equal(done.ok, true);
  assert.match((done as any).message, /Remaining: b/);
  assert.equal(apply(run(...steps), "complete_goal", { goal_id: "zzz" }).ok, false);
});

test("after a sub-goal is done, work is refused again until the next one has its BDD", () => {
  const plan = run(
    ["declare_plan", two],
    ["add_bdd", bdd("a")],
    ["address_edgecases", { goal_id: "a", edgecases: ["empty output passes untouched"] }],
    ["address_2nd_order_effects", { goal_id: "a", effects: ["none, because only pi loads it"] }],
    ["complete_goal", { goal_id: "a" }],
  );
  assert.match((authorize("edit", plan) as any).reason, /b \("second step"\) has no BDD/);
  assert.equal(authorize("edit", run(...([] as any), ["declare_plan", two])).ok, false);
});

test("revise_plan keeps what was recorded for the sub-goals it keeps and drops the rest", () => {
  const plan = run(["declare_plan", two], ["add_bdd", bdd("a")], ["add_bdd", bdd("b")]);
  const revised = run(["declare_plan", two], ["add_bdd", bdd("a")], ["add_bdd", bdd("b")], ["revise_plan", { goal: good.goal, subgoals: [{ id: "a", text: "first step" }, { id: "c", text: "new step" }] }]);
  assert.ok(plan!.bdd.b);
  assert.ok(revised!.bdd.a);
  assert.equal(revised!.bdd.b, undefined);
});

test("apply never mutates the plan it is given", () => {
  const plan = run(["declare_plan", good]);
  const before = JSON.stringify(plan);
  apply(plan, "add_bdd", bdd("goal_1"));
  assert.equal(JSON.stringify(plan), before);
});

test("the measured 1,411,712-char result is cut under the cap, keeps head and tail, and names the spill", () => {
  const big = "H".repeat(10) + "x".repeat(1_411_698) + "TAIL"; // 1,411,712 chars, the measured size
  const r = capText(big, "/tmp/spill.txt");
  assert.equal(r.capped, true);
  assert.ok(r.text.length < MAX_RESULT_CHARS + 500, `${r.text.length}`);
  assert.ok(r.text.startsWith("HHHH") && r.text.endsWith("TAIL"));
  assert.equal(big.length, 1_411_712);
  assert.match(r.text, /1,411,712 chars/);
  assert.match(r.text, /\/tmp\/spill\.txt/);
});

test("a result at the cap passes untouched", () => {
  const s = "y".repeat(MAX_RESULT_CHARS);
  assert.deepEqual(capText(s, null), { text: s, capped: false });
});

// cases.json is the contract with platform/estate/memory/plan.py: tests/test_estate_plan.py replays
// the same file through the Python copy, so the two cannot drift apart unnoticed.
test("every case in cases.json holds", async () => {
  const { readFileSync } = await import("node:fs");
  const { cases } = JSON.parse(readFileSync(new URL("./cases.json", import.meta.url), "utf8"));
  assert.ok(cases.length > 10);
  for (const c of cases) {
    let plan: Plan | undefined;
    for (const [tool, args] of c.calls) {
      const r = apply(plan, tool, args);
      if (r.ok) plan = r.plan;
    }
    const v = authorize(c.tool, plan);
    assert.equal(v.ok, c.expect, c.name);
    if (c.reason) assert.match((v as any).reason, new RegExp(c.reason), c.name);
  }
});
