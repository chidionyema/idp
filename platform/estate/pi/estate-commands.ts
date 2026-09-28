// estate-commands.ts — named estate capabilities with diagnosis enforcement.
//
// Layers (research-backed):
//   1. Tool surface: only estate_invoke for diagnosis tasks
//   2. Ulysses Contract: race required before any diagnosis intent
//   3. Exit gate: agent cannot conclude without racing
//   4. Audit: every call to ~/.estate/logs/mcp.jsonl
//   5. Shell removal: bash/sh filtered from active tools on session start
//
// Research: runtime enforcement adds 41pp over prompting.
import { execFile } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

const HOME = homedir();
const REPO = path.join(HOME, "Documents", "code", "idp");
const ESTATE_BIN = path.join(HOME, ".estate", "bin", "estate-execute");
const INTENTS_DIR = path.join(HOME, ".estate", "intents");
const MCP_LOG = path.join(HOME, ".estate", "logs", "mcp.jsonl");

// --- Session state ---
interface SessionState {
  raced: boolean;
  task_type: "diagnosis" | "other" | null;
  concluded: boolean;
  calls: number;
}

const SESSIONS = new Map<string, SessionState>();

function getSession(id: string): SessionState {
  const existing = SESSIONS.get(id);
  if (existing) return existing;
  const fresh: SessionState = { raced: false, task_type: null, concluded: false, calls: 0 };
  SESSIONS.set(id, fresh);
  return fresh;
}

const DIAGNOSIS_INTENTS = new Set([
  "k8s.debug", "hypotheses.race", "code-review",
  "litellm-status", "spire-proof-run", "flux-reconcile",
  "ci.errors", "ledger-verify",
]);

// --- Audit ---
function audit(sessionId: string, entry: Record<string, unknown>): void {
  try {
    const dir = path.dirname(MCP_LOG);
    if (!existsSync(dir)) return;
    writeFileSync(MCP_LOG, JSON.stringify({ ts: Date.now() / 1000, sessionId, ...entry }) + "\n", { flag: "a" });
  } catch { /* non-fatal */ }
}

// --- Estate binary ---
function runEstate(args: string[]): Promise<{ ok: boolean; text: string }> {
  return new Promise((resolve) => {
    execFile(ESTATE_BIN, args, { cwd: REPO, encoding: "utf8", timeout: 300_000 },
      (err, stdout, stderr) => {
        if (err) { resolve({ ok: false, text: [stdout, stderr].filter(Boolean).join("\n") }); return; }
        resolve({ ok: true, text: stdout || "(ok)" });
      });
  });
}

function listIntents(): string {
  try {
    const files = require("node:fs").readdirSync(INTENTS_DIR);
    const lines: string[] = [];
    for (const file of files) {
      if (!file.endsWith(".yaml")) continue;
      try {
        const content = readFileSync(path.join(INTENTS_DIR, file), "utf8");
        const nameM = content.match(/^name:\s*(.+)/m);
        const descM = content.match(/^description:\s*>\s*\n(.+)/);
        const name = nameM?.[1] ?? file.replace(".yaml", "");
        const desc = descM?.[1]?.trim().slice(0, 80) ?? "";
        lines.push(`  ${name}: ${desc}`);
      } catch { lines.push(`  ${file.replace(".yaml", "")}`); }
    }
    return "Available estate intents:\n" + lines.sort().join("\n");
  } catch (e) { return `error listing intents: ${e}`; }
}

function showIntent(name: string): string {
  try {
    const file = path.join(INTENTS_DIR, `${name}.yaml`);
    if (!existsSync(file)) return `[not found] intent: ${name}`;
    return readFileSync(file, "utf8");
  } catch (e) { return `[error] ${e}`; }
}

// --- Enforcement ---
function checkEnforcement(sessionId: string, intentName: string): string | null {
  const st = getSession(sessionId);
  if (st.task_type === null && DIAGNOSIS_INTENTS.has(intentName)) st.task_type = "diagnosis";
  if (intentName === "hypotheses.race") { st.raced = true; return null; }
  if (st.task_type === "diagnosis" && !st.raced) {
    st.concluded = true;
    return "[REFUSED] Diagnosis requires hypotheses.race first.\n" +
      "  1. Enumerate hypotheses with priors\n" +
      "  2. Write to /tmp/hypotheses.json\n" +
      "  3. estate_invoke('hypotheses.race', {file:'/tmp/hypotheses.json'})\n" +
      "  4. Act on ranked results\n" +
      "Enforced, not optional.";
  }
  if (st.concluded && !st.raced) return "[BLOCKED] No hypotheses.race before concluding.";
  return null;
}

// --- Run idp tools ---
function runTool(spec: { argv: string[]; cwd: string }): Promise<{ ok: boolean; text: string }> {
  return new Promise((resolve) => {
    execFile(spec.argv[0], spec.argv.slice(1), { cwd: spec.cwd, encoding: "utf8", timeout: 60_000 },
      (err, stdout, stderr) => {
        if (err) {
          const code = (err as NodeJS.ErrnoException & { code?: number | string }).code;
          resolve({ ok: false, text: [`command: ${spec.argv.join(" ")}`, `exit: ${code ?? "?"}`, stdout ? `--- stdout ---\n${stdout}` : "", stderr ? `--- stderr ---\n${stderr}` : ""].filter(Boolean).join("\n") });
          return;
        }
        resolve({ ok: true, text: stdout || "(no output)" });
      });
  });
}

export default function estateCommands(pi: ExtensionAPI): void {
  const SESSION_ID = `pi-${Date.now()}`;
  const st = getSession(SESSION_ID);

  // Estate tools
  pi.registerTool({
    name: "estate_list", label: "Estate List",
    description: "List all available estate intents",
    promptSnippet: "list available estate intents",
    parameters: Type.Object({}),
    async execute() {
      st.calls++;
      audit(SESSION_ID, { tool: "estate_list", calls: st.calls });
      return { content: [{ type: "text" as const, text: listIntents() }] };
    },
  });

  pi.registerTool({
    name: "estate_show", label: "Estate Show",
    description: "Show one intent's definition by name",
    promptSnippet: "show intent definition",
    parameters: Type.Object({ intent: Type.String() }),
    async execute(_id, params) {
      st.calls++;
      audit(SESSION_ID, { tool: "estate_show", intent: params.intent, calls: st.calls });
      return { content: [{ type: "text" as const, text: showIntent(params.intent) }] };
    },
  });

  pi.registerTool({
    name: "estate_invoke", label: "Estate Invoke",
    description: "Run an estate intent. For DIAGNOSIS tasks: enumerate hypotheses, call hypotheses.race first. Sequential testing is not permitted. Harness refuses if you skip the race.",
    promptSnippet: "run an estate intent",
    parameters: Type.Object({ intent: Type.String(), args: Type.Optional(Type.Record(Type.String(), Type.String())) }),
    async execute(_id, params) {
      st.calls++;
      const refusal = checkEnforcement(SESSION_ID, params.intent);
      if (refusal) {
        audit(SESSION_ID, { tool: "estate_invoke", refused: true, intent: params.intent });
        return { content: [{ type: "text" as const, text: refusal }], isError: true };
      }
      audit(SESSION_ID, { tool: "estate_invoke", intent: params.intent });
      const args: string[] = [params.intent];
      for (const [k, v] of Object.entries(params.args ?? {})) args.push(`${k}=${v}`);
      const result = await runEstate(args);
      return { content: [{ type: "text" as const, text: result.text }], details: { ok: result.ok } };
    },
  });

  // idp tools
  const IDP_TOOLS = [
    { name: "estate_git_status", argv: ["git", "status", "--short", "--branch"], description: "git status for the idp repo (short form, with branch)." },
    { name: "estate_git_log", argv: ["git", "log", "--oneline", "-15"], description: "Last 15 commits on the current branch." },
    { name: "estate_git_diff", argv: ["git", "diff", "--stat"], description: "Unstaged diffstat for the idp repo." },
    { name: "estate_run_ci", argv: ["./bin/idp-ci"], description: "Run the estate verification gate (bin/idp-ci)." },
    { name: "estate_run_pytest", argv: ["python3", "-m", "pytest", "-q"], description: "Run pytest quietly at the repo root." },
  ];

  for (const tool of IDP_TOOLS) {
    pi.registerTool({
      name: tool.name, label: tool.name,
      description: tool.description,
      promptSnippet: tool.description,
      parameters: Type.Object({}),
      async execute() {
        st.calls++;
        audit(SESSION_ID, { tool: tool.name, calls: st.calls });
        const result = await runTool({ argv: tool.argv, cwd: REPO });
        return { content: [{ type: "text" as const, text: result.text }], details: { ok: result.ok } };
      },
    });
  }

  // Session lifecycle
  pi.on("session_start", async () => {
    st.raced = false; st.task_type = null; st.concluded = false; st.calls = 0;
    const active = pi.getActiveTools();
    const withoutShell = active.filter((t) => t !== "bash" && t !== "shell");
    if (withoutShell.length !== active.length) {
      pi.setActiveTools(withoutShell);
      console.log("[estate] raw shell removed; estate_invoke is the only execution path");
    }
    console.log("[estate] enforcement active");
    audit(SESSION_ID, { event: "session_start" });
  });

  pi.on("session_end", async () => {
    audit(SESSION_ID, { event: "session_end", calls: st.calls, raced: st.raced });
    SESSIONS.delete(SESSION_ID);
  });
}
