import assert from "node:assert/strict";
import { test } from "node:test";
import { codexCatalog, profileToml } from "../scripts/codex-profile.mjs";

const template = { slug: "t", display_name: "T", base_instructions: "x", context_window: 1, supports_search_tool: true, supports_parallel_tool_calls: true };
const lanes = [
  { id: "deepseek-flash", vendor: "deepseek", maxContextTokens: 1048576 },
  { id: "minimax-m3", vendor: "minimax", maxContextTokens: 512000 },
];
const args = { catalogPath: "/h/meridian-models.json", keyCommand: "/v/secret-load", keyArgs: ["dev", "MERIDIAN_CLIENT_KEY", "MERIDIAN_CLIENT_KEY"], defaultModel: "coder" };

test("one catalog entry per lane, with the lane's own window, cloned from Codex's own entry", () => {
  const { models } = codexCatalog(template, lanes);
  assert.deepEqual(models.map((m) => m.slug), ["deepseek-flash", "minimax-m3"]);
  assert.deepEqual(models.map((m) => m.context_window), [1048576, 512000]);
  assert.ok(models.every((m) => m.supports_search_tool === false && m.base_instructions === "x"));
  assert.equal(template.slug, "t", "the template is not mutated");
});

test("a template that is not a full Codex entry, or no lanes, is refused", () => {
  assert.throws(() => codexCatalog({ slug: "t" }, lanes), /full Codex model entry/);
  assert.throws(() => codexCatalog(template, []), /no lane/);
});

test("the profile selects the Responses wire, names its key, and holds no secret", () => {
  const toml = profileToml(args);
  assert.match(toml, /wire_api = "responses"/);
  assert.match(toml, /args = \["dev", "MERIDIAN_CLIENT_KEY", "MERIDIAN_CLIENT_KEY"\]/, "the key is named, not carried");
  assert.doesNotMatch(toml, /bearer_token|api_key\s*=/i);
  const firstTable = toml.split("\n").findIndex((l) => l.startsWith("["));
  const keysBefore = toml.split("\n").slice(0, firstTable).filter((l) => /^model(_provider|_catalog_json)? =/.test(l));
  assert.equal(keysBefore.length, 3, "model keys precede every table, or they would join one");
});

test("regenerating gives the same bytes", () => {
  assert.equal(profileToml(args), profileToml({ ...args }));
});

test("a profile without a key command is refused", () => {
  assert.throws(() => profileToml({ ...args, keyCommand: "" }), /key command/);
});

test("the profile is valid TOML with the keys at the top level", async () => {
  const { spawnSync } = await import("node:child_process");
  const py = ["python3.13", "python3.12", "python3.11", "python3"].find(
    (p) => spawnSync(p, ["-c", "import tomllib"]).status === 0
  );
  assert.ok(py, "a Python with tomllib is required to prove the profile parses");
  const r = spawnSync(py, ["-c", "import sys,tomllib;d=tomllib.loads(sys.stdin.read());print(d['model_providers']['meridian']['wire_api'],d['model'],d['model_provider'])"], { input: profileToml(args), encoding: "utf8" });
  assert.equal(r.status, 0, r.stderr);
  assert.equal(r.stdout.trim(), "responses coder meridian");
});
