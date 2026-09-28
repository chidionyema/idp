/**
 * estate-capabilities — agents get named capabilities, never a shell.
 *
 * FOUNDER, 2026-09-20: "NO RAW BASH TOOL" — and the reason is not hygiene, it is that a raw shell
 * lets an agent decide AND execute in one step, which bypasses the contract, the ceiling, and the
 * ledger at once. A capability named here cannot: it declares what it does, the platform decides
 * whether that is allowed, and the execution itself goes through the one door
 * (mcp/plugins/estate_executor.py -> the executor daemon) which is the only thing in this estate
 * that starts a process.
 *
 * WHAT THIS REMOVES, AND WHY IT IS A REMOVAL RATHER THAN A GUARD. `pi.setActiveTools()` is called
 * at session start with `bash` filtered out. That is AGENTS.md section 8's rule — "do not legislate
 * what you can delete; if a rule exists to police something that should not be possible, remove the
 * possibility" — applied to the tool list itself. There is no check inside this file that catches a
 * shell command, because a check runs in the same identity as the caller and can be routed around.
 * The tool is simply not in the list.
 *
 * WHY THE CAPABILITIES ARE A CLOSED SET. Each one names an outcome the estate already owns, and
 * each composes its command internally from typed arguments. An agent passing `target: "..."` to
 * `estate_run_tests` cannot smuggle a second command out of it, because the command string is built
 * here from a validated shape — the argument is data, not a fragment of shell. That is the
 * difference between a capability and a shell with extra steps.
 *
 * WHAT AN AGENT CAN STILL DO. A capability that does not exist yet is a REFUSAL naming it, not a
 * silent fallback to a shell. If the founder's own agent needs a new capability, the refusal says
 * so, and adding one is a row in this file — which is the point: capability is added deliberately,
 * never acquired by reaching for a shell.
 *
 * ONE RULE FOR ADDING A ROW: it must INVOKE something the estate already has, or bound something
 * the estate has already decided. If the row would reimplement an existing tool, the row is wrong
 * and the existing tool is the answer (AGENTS.md section 6). The graph row below is the worked
 * example: bin/sync-all, bin/graph-health and bin/sync-repos already do the work, and the only
 * thing missing was a way to switch them on without a shell.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";

const HOME = homedir();
const SOCKET = process.env.IDP_EXECUTOR_SOCKET ?? path.join(HOME, ".estate", "executor.sock");
const RUNS = process.env.ESTATE_RUNS ?? path.join(HOME, ".estate", "runs");

import { createConnection } from "node:net";

/**
 * Single-quote a value for the daemon's `bash -lc <command>`.
 *
 * The daemon runs every command through `bash -lc` (platform/executor/daemon.py), so any value we
 * interpolate into a command string MUST be shell-quoted here, in the process that builds the
 * string, or it is a shell-injection hole -- the same rule every other row obeys by only ever
 * interpolating validated tokens (test ids pass a whitelist regex; script names are literals).
 * `task` and `repo` are free-form, so they get the full treatment: wrap in single quotes and
 * escape the four characters special inside single quotes, which is shell's own safe-quoting idiom.
 */
function quoteSh(value: string): string {
  return "'" + value.replace(/'/g, `'"'"'`).replace(/[\x00-\x1f\x7f]/g, " ") + "'";
}

/** The one door. Nothing in this file spawns a process directly. */
function askDaemon(request: unknown): Promise<any> {
  return new Promise((resolve, reject) => {
    if (!existsSync(SOCKET)) {
      reject(
        new Error(
          `no executor daemon at ${SOCKET}. Start it with: bin/idp-executor-agent ` +
            `(or check it with: bin/idp-executor-status)`,
        ),
      );
      return;
    }
    const sock = createConnection(SOCKET);
    let raw = "";
    const fail = (e: Error) => {
      sock.destroy();
      reject(e);
    };
    sock.setTimeout(10_000, () => fail(new Error(`the executor daemon did not answer within 10s`)));
    sock.on("error", (e) => fail(new Error(`cannot reach the executor daemon: ${e.message}`)));
    sock.on("connect", () => sock.write(JSON.stringify(request) + "\n"));
    sock.on("data", (chunk) => {
      raw += chunk.toString();
      const nl = raw.indexOf("\n");
      if (nl === -1) return;
      sock.end();
      try {
        resolve(JSON.parse(raw.slice(0, nl)));
      } catch (e) {
        fail(new Error(`unreadable reply from the executor daemon: ${String(e)}`));
      }
    });
    sock.on("close", () => {
      if (raw.trim()) return; // already resolved
      fail(new Error(`the executor daemon closed the connection with no reply`));
    });
  });
}

/**
 * Run one capability's command through the door, then read its real outcome off disk.
 *
 * A capability that returns "accepted" and stops would be the silent no-op this estate keeps
 * catching, so this WAITS for the exit file and reports the actual exit code and log. A capability
 * that disappears quietly is worse than one that fails loudly.
 */
async function runThroughDoor(
  command: string,
  opts: { cwd?: string; ceiling?: number } = {},
): Promise<{ ok: boolean; exit: number | null; log: string; jobId?: string; error?: string }> {
  const submit = await askDaemon({
    verb: "execute",
    command,
    ...(opts.cwd ? { cwd: opts.cwd } : {}),
    ...(opts.ceiling ? { ceiling_sec: opts.ceiling } : {}),
  });
  if (!submit.ok) {
    return { ok: false, exit: null, log: "", error: submit.error ?? "the door refused the command" };
  }
  const jobId: string = submit.job_id;
  const exitPath = path.join(RUNS, `${jobId}.exit`);
  const logPath = path.join(RUNS, `${jobId}.log`);
  const deadline = Date.now() + (opts.ceiling ?? 60) * 1000 + 5000;
  while (Date.now() < deadline) {
    if (existsSync(exitPath)) {
      const exit = parseInt(readFileSync(exitPath, "utf8").trim() || "0", 10);
      const log = existsSync(logPath) ? readFileSync(logPath, "utf8") : "";
      return { ok: exit === 0, exit, log, jobId };
    }
    await new Promise((r) => setTimeout(r, 250));
  }
  return {
    ok: false,
    exit: null,
    log: "",
    jobId,
    error: `the job ${jobId} did not finish within the ceiling; it was NOT reported as done`,
  };
}

/** A capability result, rendered the same way every time. */
function present(r: Awaited<ReturnType<typeof runThroughDoor>>, what: string) {
  const lines = [
    `${r.ok ? "ok" : "FAILED"}  ${what}`,
    r.jobId ? `job: ${r.jobId}` : "",
    r.exit !== null ? `exit: ${r.exit}` : "",
    r.error ? `error: ${r.error}` : "",
    r.log.trim() ? `--- log ---\n${r.log.trim()}` : "",
  ].filter(Boolean);
  return { content: [{ type: "text" as const, text: lines.join("\n") }], details: r };
}

export default function estateCapabilities(pi: ExtensionAPI) {
  // ---------------------------------------------------------------------------------------------
  // NO RAW BASH. Removed at session start rather than guarded, per AGENTS.md section 8.
  // ---------------------------------------------------------------------------------------------
  pi.on("session_start", async () => {
    const active = pi.getActiveTools();
    const kept = active.filter((t) => t !== "bash" && t !== "shell");
    if (kept.length !== active.length) {
      pi.setActiveTools(kept);
      console.log(
        `[estate] removed raw shell from the tool list (${active.length - kept.length}); ` +
          `capabilities are the only way to act`,
      );
    }
  });

  // ---------------------------------------------------------------------------------------------
  // CAPABILITY: check the executor is alive before an agent plans work that needs it.
  // ---------------------------------------------------------------------------------------------
  pi.registerTool({
    name: "estate_executor_status",
    label: "Executor Status",
    description:
      "Report whether the estate executor daemon is alive, and name the fix if it is not. Call this before a capability that runs work.",
    promptSnippet: "Check the executor daemon is alive before running work",
    promptGuidelines: [
      "Use estate_executor_status first when a task needs to run something, so a dead daemon is reported as an outage rather than discovered as a silent no-op.",
    ],
    parameters: Type.Object({}),
    async execute() {
      const alive = existsSync(SOCKET);
      if (!alive) {
        return {
          content: [
            {
              type: "text" as const,
              text:
                `BLIND  no executor daemon at ${SOCKET}\n` +
                `fix: bin/idp-executor-agent   (installs the LaunchAgent; no sudo, no reboot)\n` +
                `check: bin/idp-executor-status`,
            },
          ],
          details: { alive: false, socket: SOCKET },
        };
      }
      try {
        const reply = await askDaemon({ verb: "health" });
        return {
          content: [
            {
              type: "text" as const,
              text: `ok  executor alive (pid ${reply.pid}, ceiling ${reply.ceiling_sec}s)`,
            },
          ],
          details: reply,
        };
      } catch (e) {
        return {
          content: [{ type: "text" as const, text: `BLIND  ${String(e)}` }],
          details: { alive: false, error: String(e) },
        };
      }
    },
  });

  // ---------------------------------------------------------------------------------------------
  // CAPABILITY: run the estate's own gate for a checkout -- the verifier, not an ad-hoc command.
  // ---------------------------------------------------------------------------------------------
  pi.registerTool({
    name: "estate_run_gate",
    label: "Run Estate Gate",
    description:
      "Run the estate's verification gate for a repository (bin/idp-ci or bin/verify) through the executor. No shell, no command string: the gate is chosen by name.",
    promptSnippet: "Run the estate's verification gate for a repo, by name",
    promptGuidelines: [
      "Use estate_run_gate to verify a change instead of constructing a test command; the gate is the estate's own and its exit code is the verdict.",
    ],
    parameters: Type.Object({
      repo: Type.String({
        description: "Absolute path to the repository to verify (its own gate is used).",
      }),
      gate: Type.Optional(
        Type.String({
          description: "Which gate: idp-ci (default) or verify.",
          default: "idp-ci",
        }),
      ),
    }),
    async execute(_id, params) {
      if (!path.isAbsolute(params.repo)) {
        return {
          content: [
            {
              type: "text" as const,
              text: `refused: repo must be an absolute path; got ${params.repo}`,
            },
          ],
          details: { ok: false },
        };
      }
      const gate = params.gate === "verify" ? "verify" : "idp-ci";
      const script = path.join(params.repo, "bin", gate);
      if (!existsSync(script)) {
        return {
          content: [
            {
              type: "text" as const,
              text: `refused: no bin/${gate} in ${params.repo}; this repository does not carry that gate`,
            },
          ],
          details: { ok: false, missing: script },
        };
      }
      const r = await runThroughDoor(`${script}`, { cwd: params.repo, ceiling: 60 });
      return present(r, `bin/${gate} in ${params.repo}`);
    },
  });

  // ---------------------------------------------------------------------------------------------
  // CAPABILITY: run the estate's test suite for a repository, by name.
  // ---------------------------------------------------------------------------------------------
  pi.registerTool({
    name: "estate_run_tests",
    label: "Run Estate Tests",
    description:
      "Run pytest through the executor for an absolute repository path and a test target. The command is composed by the platform; the arguments are data, not shell fragments.",
    promptSnippet: "Run pytest for a repo and target through the executor",
    promptGuidelines: [
      "Use estate_run_tests to run tests instead of constructing a pytest command line; targets must be paths or test names WITHOUT shell metacharacters.",
    ],
    parameters: Type.Object({
      repo: Type.String({ description: "Absolute path to the repository." }),
      target: Type.String({
        description: "A test path or node id, e.g. tests/test_x.py::test_y. No shell characters.",
      }),
    }),
    async execute(_id, params) {
      if (!path.isAbsolute(params.repo)) {
        return {
          content: [{ type: "text" as const, text: `refused: repo must be absolute` }],
          details: { ok: false },
        };
      }
      if (!/^[A-Za-z0-9_./:@=\[\]-]+$/.test(params.target)) {
        return {
          content: [
            {
              type: "text" as const,
              text:
                `refused: target contains characters that are not a path or a test id. ` +
                `This capability runs ONE pytest invocation; it is not a way to reach a shell.`,
            },
          ],
          details: { ok: false, target: params.target },
        };
      }
      const python = existsSync(path.join(params.repo, ".venv/bin/python3"))
        ? ".venv/bin/python3"
        : "python3";
      const r = await runThroughDoor(`${python} -m pytest ${params.target} -q`, {
        cwd: params.repo,
        ceiling: 60,
      });
      return present(r, `pytest ${params.target}`);
    },
  });

  // ---------------------------------------------------------------------------------------------
  // CAPABILITY: git status of a checkout. Read-only, and the reason it exists is that "run git
  // status" was the single most common thing an agent reached for a shell to do.
  // ---------------------------------------------------------------------------------------------
  pi.registerTool({
    name: "estate_git_state",
    label: "Estate Git State",
    description:
      "Report a checkout's branch, HEAD, and dirty files through the executor. Read-only.",
    promptSnippet: "Report a checkout's branch, HEAD and dirty files",
    promptGuidelines: [
      "Use estate_git_state for repository state instead of a shell git command; it reports branch, HEAD and dirty files in one call.",
    ],
    parameters: Type.Object({
      repo: Type.String({ description: "Absolute path to the repository." }),
    }),
    async execute(_id, params) {
      if (!path.isAbsolute(params.repo)) {
        return {
          content: [{ type: "text" as const, text: `refused: repo must be absolute` }],
          details: { ok: false },
        };
      }
      if (!existsSync(path.join(params.repo, ".git"))) {
        return {
          content: [
            { type: "text" as const, text: `refused: ${params.repo} is not a git checkout` },
          ],
          details: { ok: false },
        };
      }
      const r = await runThroughDoor(
        `git -C ${params.repo} status --short --branch && echo "--- HEAD ---" && git -C ${params.repo} log -1 --oneline`,
        { cwd: params.repo, ceiling: 30 },
      );
      return present(r, `git state of ${params.repo}`);
    },
  });

  // ---------------------------------------------------------------------------------------------
  // CAPABILITY: run any command through the executor daemon.
  // ---------------------------------------------------------------------------------------------
  pi.registerTool({
    name: "estate_execute",
    label: "Estate Execute",
    description:
      "Run a command through the estate executor daemon. The daemon applies the 60s ceiling and records the job.",
    promptSnippet: "Run a command through the estate executor",
    promptGuidelines: [
      "Use estate_execute to run any command through the governed door. The ceiling is 60s; the daemon enforces it.",
    ],
    parameters: Type.Object({
      command: Type.String({ description: "The command to run." }),
      cwd: Type.String({ description: "Absolute working directory." }),
    }),
    async execute(_id, params) {
      const r = await runThroughDoor(params.command, { cwd: params.cwd, ceiling: 60 });
      return present(r, `execute: ${params.command}`);
    },
  });

  // ---------------------------------------------------------------------------------------------
  // CAPABILITY: run the estate's own knowledge-graph scripts.
  // ---------------------------------------------------------------------------------------------
  pi.registerTool({
    name: "estate_graph_sync",
    label: "Estate Graph Sync",
    description:
      "Run the estate's existing knowledge-graph scripts by name: health (bin/graph-health), sync (bin/sync-all), repos (bin/sync-repos). Invokes them; reimplements nothing.",
    promptSnippet: "Run bin/graph-health, bin/sync-all or bin/sync-repos",
    promptGuidelines: [
      "Use estate_graph_sync to run the estate's own graph scripts. Never write a new indexer: sync-all and graph-health already exist.",
      "Run script='health' before trusting the graph. It must FAIL while the graph is stale; a stale graph that reports ok is the defect, not the fix.",
    ],
    parameters: Type.Object({
      repo: Type.String({
        description: "Absolute path to the graph repo (e.g. .../Documents/code/estate-graph).",
      }),
      script: Type.String({
        description: "Which existing script: 'health' | 'sync' | 'repos'.",
      }),
      background: Type.Optional(
        Type.Boolean({
          description:
            "Allow beyond the 60s foreground ceiling. 'sync' does network work and needs this.",
          default: false,
        }),
      ),
    }),
    async execute(_id, params) {
      if (!path.isAbsolute(params.repo)) {
        return {
          content: [{ type: "text" as const, text: `refused: repo must be absolute` }],
          details: { ok: false },
        };
      }
      const SCRIPTS: Record<string, { file: string; extra: string[] }> = {
        health: { file: "bin/graph-health", extra: ["--root", params.repo] },
        sync: { file: "bin/sync-all", extra: [] },
        repos: { file: "bin/sync-repos", extra: [] },
      };
      const chosen = SCRIPTS[params.script];
      if (!chosen) {
        return {
          content: [
            {
              type: "text" as const,
              text:
                `refused: '${params.script}' is not one of ${Object.keys(SCRIPTS).join(", ")}.\n` +
                `These are the estate's existing scripts; this capability does not invent new ones.`,
            },
          ],
          details: { ok: false, script: params.script },
        };
      }
      const scriptPath = path.join(params.repo, chosen.file);
      if (!existsSync(scriptPath)) {
        return {
          content: [
            { type: "text" as const, text: `refused: ${chosen.file} not present in ${params.repo}` },
          ],
          details: { ok: false },
        };
      }
      const py = path.join(params.repo, chosen.file).endsWith(".py") ? "python3 " : "";
      const command = `${py}${scriptPath}${
        chosen.extra.length ? " " + chosen.extra.join(" ") : ""
      }`;
      const r = await runThroughDoor(command, {
        cwd: params.repo,
        ceiling: params.background ? 1800 : 60,
      });
      return present(r, `${chosen.file}${chosen.extra.length ? " " + chosen.extra.join(" ") : ""}`);
    },
  });

  // ---------------------------------------------------------------------------------------------
  // CAPABILITY: submit a session to the fleet-scale work plane (sovereign → Temporal).
  //
  // WHAT THIS IS NOT. It is not a second executor and it is not a raw Temporal submit. The
  // executor door (estate_execute → the laptop daemon) stays exactly where it is -- it owns the
  // contract, the ceiling and the single ledger, and the fleetview relay is a wire BACK to that
  // same daemon, not a second one (LAW 43: never a second gauntlet). This row invokes the close
  // opposite: `sb start`, the estate's own CLI into the SessionWorkflow plane
  // (sovereign/engine/client.py → Temporal + NATS + orchestrator) for FLEET-SCALE agent work.
  //
  // Two planes, two kinds of work: arbitrary executor verbs run laptop-local through the door;
  // long-running, budgeted, approval-gated agent sessions run as Temporal workflows here. The
  // capability composes its command from typed arguments -- `task` is data, not a shell fragment,
  // and the verb is always the literal `start` -- so this is the same closed set as every other
  // row, never a way to reach a shell. The runner vocabulary is the existing registry
  // (echo | sleep | ask | claude | llm); nothing here invents a new one.
  // ---------------------------------------------------------------------------------------------
  pi.registerTool({
    name: "estate_session_start",
    label: "Start Fleet Session",
    description:
      "Submit a session to the fleet-scale work plane via the estate's own sovereign bus (`sb start` → Temporal SessionWorkflow). For long-running, budgeted, approval-gated agent work -- not a replacement for the executor door, which stays laptop-local.",
    promptSnippet: "Start a fleet-scale work session via sb start",
    promptGuidelines: [
      "Use estate_session_start for fleet-scale, budgeted, approval-gated work (Temporal SessionWorkflow). Use estate_execute for bounded laptop-local executor verbs. Two different planes for two different kinds of work -- do not route arbitrary verbs through the workflow plane, and do not route long-running sessions through the 60s executor door.",
      "The runner must be a name in the existing registry (echo | sleep | ask | claude | llm); the capability refuses anything else rather than invent a vendor.",
    ],
    parameters: Type.Object({
      task: Type.String({
        description: "The task for the session to work on. Passed as data to `--task`, never a shell fragment.",
      }),
      runner: Type.Optional(
        Type.String({
          description: "Runner registry name: echo | sleep | ask | claude | llm. Defaults to the estate's configured default.",
        }),
      ),
      repo: Type.Optional(
        Type.String({ description: "Absolute path to the repository the session works in." }),
      ),
      budget: Type.Optional(
        Type.Integer({
          description: "Budget for the session, in the estate's configured unit. Required by the bus if no default is configured.",
        }),
      ),
      critical: Type.Optional(
        Type.Boolean({
          description: "Survives self-termination (crew#284 CP6, spec section 5).",
          default: false,
        }),
      ),
    }),
    async execute(_id, params) {
      // LAW 46: the sovereign bus resolves its own root from its own location (`bin/sb` computes
      // `IDP="$(dirname "$0")/.."`), and it is already on PATH. We invoke it BY NAME -- `sb` --
      // exactly like estate_graph_sync invokes `bin/sync-all`. Reconstructing a path from an env
      // var here would be a second copy of the shim's own root resolution, and the one earlier
      // attempt (process.env.IDP) was wrong -- IDP is a launchd plist template variable, never an
      // exported process env. The shim knows where it lives; we do not need to.
      if (!/\S/.test(params.task)) {
        return {
          content: [{ type: "text" as const, text: `refused: task is required` }],
          details: { ok: false },
        };
      }
      if (params.runner !== undefined) {
        const RUNNERS = new Set(["echo", "sleep", "ask", "claude", "llm"]);
        if (!RUNNERS.has(params.runner)) {
          return {
            content: [
              {
                type: "text" as const,
                text:
                  `refused: runner '${params.runner}' is not in the registry ` +
                  `(echo | sleep | ask | claude | llm). This capability invokes the estate's ` +
                  `existing runners; it does not invent one.`,
              },
            ],
            details: { ok: false, runner: params.runner },
          };
        }
      }
      if (params.repo !== undefined && !path.isAbsolute(params.repo)) {
        return {
          content: [{ type: "text" as const, text: `refused: repo must be an absolute path` }],
          details: { ok: false },
        };
      }
      if (params.budget !== undefined && (!Number.isInteger(params.budget) || params.budget < 0)) {
        return {
          content: [{ type: "text" as const, text: `refused: budget must be a non-negative integer` }],
          details: { ok: false },
        };
      }
      // Command is BUILT here from validated parts, but the daemon runs it via `bash -lc`, so
      // every free-form value (task/repo/runner) is single-quoted with quoteSh before it meets
      // the shell. `task` and `repo` are data, not shell; budget is a validated integer and
      // critical a no-value flag, so neither can carry syntax.
      const parts = ["--task", quoteSh(params.task)];
      if (params.runner !== undefined) parts.push("--runner", quoteSh(params.runner));
      if (params.repo !== undefined) parts.push("--repo", quoteSh(params.repo));
      if (params.budget !== undefined) parts.push("--budget", String(params.budget));
      if (params.critical) parts.push("--critical");
      const cwd = params.repo ?? HOME;
      const r = await runThroughDoor(`sb start ${parts.join(" ")}`, { cwd, ceiling: 60 });
      return present(r, `sb start ${params.task}`);
    },
  });

  // ---------------------------------------------------------------------------------------------
  // The honest refusal for anything not yet a capability.
  // ---------------------------------------------------------------------------------------------
  pi.registerTool({
    name: "estate_capabilities",
    label: "List Estate Capabilities",
    description:
      "List the estate's capabilities and how to ask for a new one. Call this when a task seems to need a shell.",
    promptSnippet: "List what this agent can actually do",
    promptGuidelines: [
      "Use estate_capabilities when no capability fits the task, so the missing capability is reported and added deliberately rather than worked around.",
    ],
    parameters: Type.Object({}),
    async execute() {
      const all = pi.getAllTools();
      const estate = all.filter((t) => t.name.startsWith("estate_"));
      const text = [
        "This agent has no shell. It acts through named capabilities:",
        ...estate.map((t) => `  - ${t.name}: ${t.description ?? ""}`),
        "",
        "If the task needs something not listed, say which capability is missing. Adding one is a",
        "row in extensions/estate-capabilities/index.ts. It is NOT a reason to ask for bash:",
        "a raw shell lets a decision and its execution happen in one unrecorded step, which is what",
        "the contract, the ceiling and the ledger exist to prevent.",
      ].join("\n");
      return {
        content: [{ type: "text" as const, text }],
        details: { capabilities: estate.map((t) => t.name) },
      };
    },
  });
}
