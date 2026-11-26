import test from "node:test";
import assert from "node:assert/strict";
import {sanitizeAndValidate, pushDirectToGitHub, sha256} from "./aistudio_direct_github_drop.mjs";

const file = {path: "platform/example.txt", content: "approved\n"};
async function release() {
  return {repo: "chidionyema/idp", public_release: true, base_sha: "a".repeat(40),
    files: [{path: file.path, sha256: await sha256(file.content)}]};
}
test("explicit approved bytes only", async () => {
  assert.deepEqual(await sanitizeAndValidate([file], await release()), [file]);
  await assert.rejects(sanitizeAndValidate([{...file, content: "changed"}], await release()));
});
test("protected or private paths refused", async () => {
  for (const path of [".github/workflows/test.yml", "bin/idp-auth", "platform/../test", "platform/.env"]) {
    const r = await release(); r.files[0].path = path;
    await assert.rejects(sanitizeAndValidate([{...file, path}], r));
  }
});
test("create-only custody; no force even on collision", async () => {
  const calls = [];
  const answers = [
    {object:{sha:"a".repeat(40)}}, {tree:{sha:"b".repeat(40)}},
    {sha:"c".repeat(40)}, {sha:"d".repeat(40)}, {sha:"e".repeat(40)},
  ];
  const fetchImpl = async (url, init) => {
    calls.push({url,method:init.method,body:init.body});
    const result = answers.shift();
    return result ? new Response(JSON.stringify(result), {status:200}) : new Response("collision", {status:422});
  };
  await assert.rejects(pushDirectToGitHub({token:"fixture", files:[file], release:await release(), fetchImpl}), /GITHUB_HTTP_422/);
  assert.equal(calls.length, 6);
  assert.ok(calls.every(c => c.method !== "PATCH"));
  assert.match(calls.at(-1).body, /refs\/heads\/quarantine\/aistudio-/);
});
