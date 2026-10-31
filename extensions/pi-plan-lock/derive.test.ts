/**
 * The derivation cases, replayed against the TypeScript copy of the rule.
 *
 * The cases live in cases.json so both copies (this one and
 * platform/estate/governance/plan_links.py) must agree: the Python test replays the same file.
 * A rule that drifts in one copy fails here.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { deriveLinks } from "./derive.ts";

const here = path.dirname(fileURLToPath(import.meta.url));

type DerivationCase = {
  name: string;
  session: string;
  intents: Array<Record<string, unknown>>;
  prompts: Array<Record<string, unknown>>;
  instruction: string;
  prompt: string;
};

const cases = JSON.parse(readFileSync(path.join(here, "cases.json"), "utf8")) as {
  derivations?: DerivationCase[];
};

for (const c of cases.derivations ?? []) {
  test(`derivation: ${c.name}`, () => {
    const links = deriveLinks(c.session, { intents: c.intents, prompts: c.prompts });
    assert.equal(links.instruction, c.instruction);
    assert.equal(links.prompt, c.prompt);
  });
}

test("derivation: a session's own rows only, never another session's", () => {
  const links = deriveLinks(
    "s1",
    {
      intents: [
        { session: "s2", intent: "other-intent" },
        { session: "s1", intent: "lane-submit" },
      ],
      prompts: [
        { session: "s2", id: "prompt-9999" },
        { session: "s1", id: "prompt-0001" },
      ],
    },
  );
  assert.equal(links.instruction, "lane-submit");
  assert.equal(links.prompt, "prompt-0001");
});

test("derivation: an absent ledger derives nothing, it never invents a link", () => {
  const links = deriveLinks("s1", {});
  assert.equal(links.instruction, "");
  assert.equal(links.prompt, "");
});
