// pi-founder-governance -- pi's thin adapter over the estate's founder governance.
//
// The policy is not here. Every decision belongs to the shared executables under
// platform/estate/governance, so pi, Claude Code and Codex are decided by the same code and
// every decision lands in the same ledger. This file only:
//
//   1. tells pi when a session is locked down and takes the write/exec tools away,
//   2. feeds the founder's prompt to the intake, and raises the repeat as a violation,
//   3. refuses a report to the founder that carries no machine-generated receipt.
//
// The three refusals are the founder's order (2026-10-29): warn once per violation class,
// terminate and relaunch on the repeat; no write path while locked; no report without proof.
//
// Fail-open on its own errors, loudly (R38: a fence a correct machine cannot satisfy is an
// outage). ESTATE_FOUNDER_GOVERNANCE=0 opts out, exactly as the binaries do.
import { execFile } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const HOME = process.env.ESTATE_HOME ?? path.join(homedir(), ".estate");
// The installed copy, never a checkout: the shared checkout is on somebody's branch.
// ESTATE_FOUNDER_GOVERNANCE_BIN points at a checkout's bin/ for the moment a tree is being
// proved before it is deployed; the default is always the installed one.
const BIN = process.env.ESTATE_FOUNDER_GOVERNANCE_BIN ?? path.join(HOME, "bin");
const STATE_HOME =
  process.env.ESTATE_GOVERNANCE_HOME ?? process.env.ESTATE_STATE_HOME ?? path.join(HOME, "state");
const TIMEOUT_MS = 20_000;

const enabled = () => process.env.ESTATE_FOUNDER_GOVERNANCE !== "0";

const WRITE_TOOLS = new Set(["edit", "write", "multiedit", "notebookedit", "apply_patch"]);
const EXEC_TOOLS = new Set(["bash", "shell", "exec", "run", "terminal", "execute"]);

function run(args: string[], stdin?: string): Promise<{ code: number; out: string }> {
  return new Promise((resolve) => {
    if (!existsSync(args[0])) {
      resolve({ code: 127, out: "" });
      return;
    }
    const child = execFile(
      "python3",
      args,
      { timeout: TIMEOUT_MS, env: process.env },
      (err, stdout, stderr) => {
        const code = err && typeof (err as any).code === "number" ? (err as any).code : err ? 1 : 0;
        resolve({ code, out: String(stdout ?? "") + String(stderr ?? "") });
      },
    );
    child.stdin?.on("error", () => {});
    child.stdin?.end(stdin ?? "");
  });
}

function sessionId(ctx: any): string {
  try {
    return String(ctx?.sessionManager?.getSessionId?.() ?? "pi-session");
  } catch {
    return "pi-session";
  }
}

function provider(ctx: any): string {
  try {
    const model = ctx?.sessionManager?.getModel?.() ?? ctx?.model ?? "";
    if (typeof model === "string") return model.split("/")[0] || "";
    // pi hands back a model object; the estate's ledger wants the provider NAME.
    const name = String(
      model?.provider ?? model?.id ?? model?.model ?? model?.name ?? "",
    );
    return name.split("/")[0] || "";
  } catch {
    return "";
  }
}

async function lockState(session: string): Promise<{ locked: boolean; proof: string; instruction: string }> {
  const { out } = await run([
    path.join(BIN, "estate-supervisor"),
    "--status",
    "--session",
    session,
    "--json",
  ]);
  try {
    const parsed = JSON.parse(out.slice(out.indexOf("{")));
    return { locked: !!parsed.locked, proof: parsed.proof ?? "", instruction: parsed.instruction ?? "" };
  } catch {
    return { locked: false, proof: "", instruction: "" };
  }
}

async function grade(
  cls: string,
  session: string,
  detail: string,
  ctx: any,
): Promise<void> {
  const args = [
    path.join(BIN, "estate-supervisor"),
    "--class",
    cls,
    "--session",
    session,
    "--detail",
    detail,
    "--provider",
    provider(ctx),
    "--no-relaunch",
    "--json",
  ];
  const { out } = await run(args);
  try {
    const verdict = JSON.parse(out.slice(out.indexOf("{")));
    if (verdict.decision === "warn") {
      ctx?.ui?.notify?.(verdict.message ?? `law violation [${cls}]`, "warning");
    } else if (verdict.decision === "terminate") {
      ctx?.ui?.notify?.(
        `law violation [${cls}] repeated: this session is locked and relaunched under lockdown`,
        "error",
      );
    }
  } catch {
    /* the ledger is the record; the notification is a courtesy */
  }
}

export default function (pi: ExtensionAPI) {
  pi.on("session_start", async (_event: any, ctx: any) => {
    if (!enabled()) return undefined;
    try {
      const state = await lockState(sessionId(ctx));
      if (!state.locked) return undefined;
      // Lockdown is total: no write path and no exec path, so a locked session cannot cheat
      // its way to a push. The decision itself came from the shared binary.
      const removed: string[] = [];
      try {
        // pi.setActiveTools takes NAMES, not tool objects: getActiveTools() -> string[].
        const active: string[] = Array.isArray(pi.getActiveTools?.()) ? pi.getActiveTools!() : [];
        const keep = active.filter((name: string) => {
          const key = String(name).toLowerCase();
          if (WRITE_TOOLS.has(key) || EXEC_TOOLS.has(key)) {
            removed.push(String(name));
            return false;
          }
          return true;
        });
        pi.setActiveTools?.(keep);
      } catch {
        /* older pi: the binary gate still refuses the write */
      }
      // The artifact is the proof that the runtime actually took the tools away.
      try {
        const dir = path.join(STATE_HOME, "sessions");
        mkdirSync(dir, { recursive: true });
        writeFileSync(
          path.join(dir, `${sessionId(ctx)}.lockdown.json`),
          JSON.stringify(
            { session: sessionId(ctx), locked: true, removed, at: new Date().toISOString() },
            null,
            2,
          ),
        );
      } catch {
        /* the ledger is the record */
      }
      ctx?.ui?.notify?.(
        "this session is locked down: no write, no shell, no push until " +
          (state.proof || "the proof") +
          " exits 0",
        "error",
      );
      return undefined;
    } catch (e) {
      ctx?.ui?.notify?.(`pi-founder-governance failed open: ${String(e)}`, "warning");
      return undefined;
    }
  });

  pi.on("before_agent_start", async (event: any, ctx: any) => {
    if (!enabled()) return undefined;
    try {
      const prompt = String(event?.prompt ?? "");
      if (!prompt.trim()) return undefined;
      const { out } = await run(
        [path.join(BIN, "estate-founder-intake"), "--stdin", "--session", sessionId(ctx), "--json"],
        prompt,
      );
      const record = JSON.parse(out.slice(out.indexOf("{")));
      if (record.repeat_of) {
        await grade(
          "founder-repeat",
          sessionId(ctx),
          `the founder repeated himself (${record.repeat_score}): ${prompt.slice(0, 160)}`,
          ctx,
        );
      }
      return undefined;
    } catch (e) {
      ctx?.ui?.notify?.(`pi-founder-governance failed open: ${String(e)}`, "warning");
      return undefined;
    }
  });

  pi.on("agent_end", async (event: any, ctx: any) => {
    if (!enabled()) return undefined;
    try {
      const messages: any[] = Array.isArray(event?.messages) ? event.messages : [];
      const last = messages[messages.length - 1];
      const text = String(last?.content ?? last?.text ?? "");
      if (!text.trim()) return undefined;
      const { code } = await run(
        [path.join(BIN, "estate-receipt"), "--has-receipt", "--stdin"],
        text,
      );
      if (code === 0) return undefined;
      await grade(
        "unsupported-report",
        sessionId(ctx),
        "a report without machine-generated proof",
        ctx,
      );
      ctx?.ui?.notify?.(
        "that report carries no machine-generated proof: run bin/estate-receipt -- <command> " +
          "and quote the receipt",
        "warning",
      );
      return undefined;
    } catch (e) {
      ctx?.ui?.notify?.(`pi-founder-governance failed open: ${String(e)}`, "warning");
      return undefined;
    }
  });
}
