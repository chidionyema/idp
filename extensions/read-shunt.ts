// read-shunt pi shim: offload bulk file reads to the estate's read-shunt core.
//
// Thin adapter only — every decision (threshold, worker model, router URL, ledger,
// enabled flag) lives in ~/Documents/code/claude-guards/read_shunt, shared with the
// Claude Code shim and the MCP/CLI. This file just translates a pi `read` tool_result
// into the neutral hook payload and applies the returned digest. Fail-open: if the core
// is missing, times out, or errors, the original read content passes through untouched.
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { execFile } from "node:child_process";

const CORE_DIR = `${process.env.HOME}/Documents/code/claude-guards`;
const TIMEOUT_MS = 60_000;

function shunt(payload: object): Promise<string | null> {
  return new Promise((resolve) => {
    let settled = false;
    const finish = (digest: string | null) => {
      if (!settled) {
        settled = true;
        resolve(digest);
      }
    };
    const child = execFile(
      "python3",
      ["-m", "read_shunt", "hook"],
      {
        cwd: CORE_DIR,
        env: { ...process.env, PYTHONPATH: CORE_DIR },
        timeout: TIMEOUT_MS,
        maxBuffer: 1024 * 1024,
      },
      (err, stdout) => {
        if (err) return finish(null); // fail open
        try {
          const r = JSON.parse(stdout);
          finish(r?.outcome === "shunted" && typeof r.digest === "string" ? r.digest : null);
        } catch {
          finish(null);
        }
      },
    );
    child.stdin!.on("error", () => finish(null));
    child.stdin!.end(JSON.stringify(payload));
  });
}

export default function (pi: ExtensionAPI) {
  pi.on("tool_result", async (event, ctx) => {
    if (event.toolName !== "read" || event.isError) return;
    const input = event.input as { path?: string; offset?: number; limit?: number };
    if (!input?.path) return;
    // Ranged reads (offset/limit) are exact-range requests and are never shunted; this
    // pre-filter only avoids spawning a subprocess — the core re-checks the same thing.
    if (input.offset || input.limit) return;

    const digest = await shunt({
      tool_name: "Read",
      tool_input: { path: input.path, offset: input.offset, limit: input.limit },
      cwd: ctx.cwd,
      session_id: ctx.sessionManager?.getSessionId?.() ?? "",
    });
    if (!digest) return;

    return {
      content: [{ type: "text", text: `[read-shunt digest of ${input.path}]\n\n${digest}` }],
      details: { readShunt: true },
    };
  });
}
