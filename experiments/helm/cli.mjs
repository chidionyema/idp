import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { compileContext, evidenceFromCompiler, seal, unseal, evaluate, distill } from "./helm.mjs";

const root = new URL(".", import.meta.url);
const local = path => new URL(path, root);
const read = path => JSON.parse(readFileSync(local(path), "utf8"));
const write = (path, value) => {
  mkdirSync(resolve("experiments/helm/out"), { recursive: true });
  writeFileSync(resolve("experiments/helm/out", path),
    JSON.stringify(value, null, 2) + "\n", { mode: 0o600 });
};
const command = process.argv[2] || "help";
try {
  if (command === "compile") {
    const task = read("fixtures/tasks.json").tasks[0];
    const evidence = read("fixtures/tasks.json").evidence;
    const context = compileContext(task, evidence);
    const packed = seal(context);
    if (unseal(packed).included.length !== context.included.length - packed.dropped)
      throw new Error("cartridge round-trip lost content");
    write("cartridge.json", packed);
    console.log(JSON.stringify({ status: "CARTRIDGE_COMPILED", bytes: packed.bytes,
      dropped: packed.dropped, digest: packed.sha256 }));
  } else if (command === "live") {
    const {tasks, evidence} = read("fixtures/tasks.json");
    const url = process.env.HELM_INFERENCE_URL;
    const token = process.env.HELM_TOKEN;
    const model = process.env.HELM_MODEL || "openai/gpt-4.1-mini";
    if (!url || !token) throw new Error("HELM_INFERENCE_URL and HELM_TOKEN required; live trial not run");
    // Three task pairs, four configurations = 12 first-round model calls.
    const chosen = tasks.slice(0, 3);
    const result = await evaluate({ tasks: chosen, evidence,
      arms: ["baseline", "skills", "memory", "helm"], url, token, model,
      sha256: process.env.GITHUB_SHA || "local-unpinned", maxCalls: 24 });
    write("live-trial.json", result);
    console.log(JSON.stringify({ status: "LIVE_TRIAL_FINISHED", model, summary: result.summary,
      source: result.sourceSha, failedCalls: result.results.reduce((n,r) =>
        n+r.attempts.filter(a=>a.error).length,0) }));
    if (result.results.some(row => row.attempts.some(a => a.error)))
      process.exitCode = 2;
  } else if (command === "distill") {
    const file = process.argv[3];
    if (!file) throw new Error("usage: distill TRACE.jsonl");
    const traces = readFileSync(file, "utf8").split(/\r?\n/).filter(Boolean)
      .map(line => JSON.parse(line));
    const pairs = distill(traces);
    write("preference-candidates.json", { pairs,
      caveat: "candidate pairs only; no model fine tuning performed" });
    console.log(JSON.stringify({ pairs: pairs.length }));
  } else if (command === "from-compiler") {
    const path = process.argv[3];
    if (!path) throw new Error("usage: from-compiler PLAN.json");
    const plan = JSON.parse(readFileSync(path, "utf8"));
    const context = compileContext({ domain: "software", question: String(plan.task || "") },
      evidenceFromCompiler(plan));
    const cartridge = seal(context);
    write("cartridge.json", cartridge);
    console.log(JSON.stringify({ sourceRecords: context.included.length,
      bytes: cartridge.bytes, digest: cartridge.sha256 }));
  } else {
    throw new Error("usage: node experiments/helm/cli.mjs [compile|live|distill TRACE.jsonl|from-compiler PLAN.json]");
  }
} catch (error) {
  console.error("HELM_RESEARCH_ERROR:", String(error.message || error));
  process.exitCode = 1;
}
