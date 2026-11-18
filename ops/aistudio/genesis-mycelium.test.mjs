import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createContext, runInContext } from "node:vm";

const source = readFileSync(new URL("./genesis-mycelium.user.js", import.meta.url), "utf8");
const sandbox = {
  module: { exports: {} },
  exports: {},
  crypto,
  TextEncoder,
  TextDecoder,
  btoa,
  atob,
  console,
};
createContext(sandbox);
runInContext(source, sandbox);
const { extractArtifacts, sha256Hex, pathFromHeader } = sandbox.module.exports;

test("extracts fenced code blocks that name a file", () => {
  const text = [
    "Built the control plane.",
    "```ts:src/engine/routerCore.ts\nconst lanes = 4;\n```",
    "```json:package.json\n{\"name\":\"pennyd\"}\n```",
    "```bash\nnpm test\n```",
  ].join("\n");
  const files = extractArtifacts(text);
  assert.deepEqual(
    Array.from(files, (file) => file.path),
    ["src/engine/routerCore.ts", "package.json"],
  );
  assert.equal(files[0].content, "const lanes = 4;\n");
});

test("falls back to a leading path comment", () => {
  const text = "```ts\n// src/components/App.tsx\nexport const App = () => null;\n```";
  const files = extractArtifacts(text);
  assert.equal(files.length, 1);
  assert.equal(files[0].path, "src/components/App.tsx");
});

test("dedupes the same path inside one turn", () => {
  const text = "```ts:a.ts\none\n```\n```ts:a.ts\ntwo\n```";
  const files = extractArtifacts(text);
  assert.equal(files.length, 1);
  assert.equal(files[0].content, "two\n");
});

test("sha256 matches the engine's digest for the same bytes", async () => {
  assert.equal(
    await sha256Hex("const lanes = 4;\n"),
    "982372e0d00fda4d776f1ff6a5252e78324826dbdc875c4b550d5129904b0962",
  );
  assert.equal(pathFromHeader("ts src/engine/keyStore.ts", ""), "src/engine/keyStore.ts");
});
