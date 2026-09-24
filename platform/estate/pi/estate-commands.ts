// estate-commands.ts — named, fixed-argv capabilities for the idp repo.
//
// WHY THIS EXISTS. The launchd executor daemon is dead (TCC + missing gtimeout) and an
// agent with a raw bash tool is worse than no tool at all. This gives the agent named
// commands with fixed argv: it picks a name, not a shell string. The timeout is enforced
// in JS, so there is no external `timeout` binary to install.
import { execFile } from "node:child_process";
import { Type } from "typebox";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const REPO = "/Users/roseonyema/Documents/code/idp";
const TIMEOUT_MS = 60_000;
const MAX_BUFFER = 10 * 1024 * 1024;
const ESTATE = `${process.env.HOME}/.estate/bin`;

type Spec = { argv: string[]; cwd: string; description: string };

const COMMANDS: Record<string, Spec> = {
  estate_list: {
    argv: [`${ESTATE}/estate-execute`, "--list"],
    cwd: REPO,
    description: "List all available estate intents.",
  },
  estate_show: {
    argv: [`${ESTATE}/estate-execute`],
    cwd: REPO,
    description: "Show estate intent definition. Pass intent name as arg=val.",
  },
  estate_invoke: {
    argv: [`${ESTATE}/estate-execute`],
    cwd: REPO,
    description: "Invoke an estate intent. Pass intent name and args.",
  },
  estate_git_status: {
    argv: ["git", "status", "--short", "--branch"],
    cwd: REPO,
    description: "git status for the idp repo (short form, with branch).",
  },
  estate_git_log: {
    argv: ["git", "log", "--oneline", "-15"],
    cwd: REPO,
    description: "Last 15 commits on the current branch.",
  },
  estate_git_diff: {
    argv: ["git", "diff", "--stat"],
    cwd: REPO,
    description: "Unstaged diffstat for the idp repo.",
  },
  estate_run_ci: {
    argv: ["./bin/idp-ci"],
    cwd: REPO,
    description: "Run the estate verification gate (bin/idp-ci).",
  },
  estate_run_pytest: {
    argv: ["python3", "-m", "pytest", "-q"],
    cwd: REPO,
    description: "Run pytest quietly at the repo root.",
  },
};

function run(spec: Spec): Promise<{ text: string; ok: boolean }> {
  return new Promise((resolve) => {
    execFile(
      spec.argv[0],
      spec.argv.slice(1),
      {
        cwd: spec.cwd,
        encoding: "utf8",
        timeout: TIMEOUT_MS,
        maxBuffer: MAX_BUFFER,
      },
      (err, stdout, stderr) => {
        if (err) {
          const code = (err as NodeJS.ErrnoException & { code?: number | string }).code;
          resolve({
            ok: false,
            text: [
              `command: ${spec.argv.join(" ")}`,
              `exit: ${code ?? "?"}`,
              stdout ? `--- stdout ---\n${stdout}` : "",
              stderr ? `--- stderr ---\n${stderr}` : "",
            ]
              .filter(Boolean)
              .join("\n"),
          });
          return;
        }
        resolve({ ok: true, text: stdout || "(no output)" });
      },
    );
  });
}

export default function (pi: ExtensionAPI) {
  for (const [name, spec] of Object.entries(COMMANDS)) {
    pi.registerTool({
      name,
      label: name,
      description: spec.description,
      promptSnippet: spec.description,
      parameters: name === "estate_list" || name === "estate_git_status" ||
                   name === "estate_git_log" || name === "estate_git_diff" ||
                   name === "estate_run_ci" || name === "estate_run_pytest"
        ? Type.Object({})
        : Type.Object({
            intent: Type.Optional(Type.String()),
            arg: Type.Optional(Type.String()),
            tool: Type.Optional(Type.String()),
            ttl: Type.Optional(Type.String()),
          }),
      async execute(_toolCallId, params, _signal, _onUpdate, _ctx) {
        let spec = { ...COMMANDS[name] };
        // Build argv based on intent name
        if (name === "estate_show") {
          spec = { ...spec, argv: [`${ESTATE}/estate-execute`, "--show", params.intent || ""] };
        } else if (name === "estate_invoke") {
          const intent = params.intent || "";
          const arg = params.arg ? `arg=${params.arg}` : "";
          spec = { ...spec, argv: [`${ESTATE}/estate-execute`, intent, arg].filter(Boolean) };
        }
        const result = await run(spec);
        return {
          content: [{ type: "text" as const, text: result.text }],
          details: { ok: result.ok },
        };
      },
    });
  }
}
