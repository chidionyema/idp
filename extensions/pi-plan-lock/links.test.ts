/**
 * The link rule, replayed against the TypeScript copy.
 *
 * The cases live in cases.json so both copies (this one and platform/estate/memory/plan.py)
 * must agree: the Python test replays the same file. A rule that drifts in one copy fails
 * here.
 *
 * The rule, in one line: a link the estate can DISPROVE refuses; a link that is merely ABSENT
 * refuses only under strict. The classes are the classes platform/estate/governance/plan_links.py
 * separates, and they are the same classes for the same reason: a gate that cannot fail is not
 * a gate, and a gate that refuses on what it cannot see is an outage.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { linkDecision } from "./plan.ts";

const here = path.dirname(fileURLToPath(import.meta.url));

type LinkCase = {
  name: string;
  stated: { instruction?: string; prompt?: string };
  derived: { instruction?: string; prompt?: string };
  unresolvable: string[];
  strict: boolean;
  expect: boolean;
  reason?: string;
};

const cases = JSON.parse(readFileSync(path.join(here, "cases.json"), "utf8")) as {
  linkRules?: LinkCase[];
};

for (const c of cases.linkRules ?? []) {
  test(`link rule: ${c.name}`, () => {
    const d = linkDecision(c.stated, c.derived, c.unresolvable, c.strict);
    assert.equal(d.ok, c.expect, `expected ok=${c.expect}, got ${JSON.stringify(d)}`);
    if (!d.ok && c.reason) {
      assert.ok(
        d.reason.includes(c.reason),
        `reason "${d.reason}" does not mention "${c.reason}"`,
      );
    }
  });
}

test("link rule: a stated link wins over a derived one, and a derived one fills a gap", () => {
  const d = linkDecision(
    { instruction: "stated-intent" },
    { instruction: "derived-intent", prompt: "prompt-0002" },
    [],
    false,
  );
  assert.equal(d.ok, true);
  if (d.ok) {
    assert.equal(d.instruction, "stated-intent");
    assert.equal(d.prompt, "prompt-0002");
  }
});
