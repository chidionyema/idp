// estate-protocol-gate -- Pi adapter for protocol_gate.py (stop-the-line + oracle-rationing budget).
// Pi refuses at tool_call only; this blocks there. The gate itself is plain Python, one source of truth for Pi, Claude Code and launchers.
// Fails OPEN on its own errors, loudly (a broken adapter must not become an outage). Off switch for a human-driven session: ESTATE_PROTOCOL_GATE=off.
import { spawnSync } from "node:child_process";
import { homedir } from "node:os";
import path from "node:path";

const GATE = process.env.ESTATE_PROTOCOL_GATE_PATH ?? path.join(homedir(), ".estate", "gates", "protocol_gate.py");
const off = () => process.env.ESTATE_PROTOCOL_GATE === "off";
const SESSION = process.env.ESTATE_GOAL_ID ?? `pi-${process.pid}`;

function run(phase: "pre" | "post", payload: object) {
  return spawnSync("python3", [GATE, "hook", phase, "--format", "json"], {
    input: JSON.stringify(payload),
    encoding: "utf8",
    timeout: 20000,
    // The pass budget is OFF by default here, exactly as the Claude Code hook does it for interactive sessions:
    // the estate already grades pi turns through ~/.pi/agent/extensions/pi-governance -> bin/idp-budget --run,
    // and AGENTS.md s6 says one layer of each kind (a second live budget on the same turns is a stitch).
    // Arm it for a lane with ESTATE_BUDGET=on. The break gate below is always on unless ESTATE_PROTOCOL_GATE=off.
    env: { ...process.env, ESTATE_BUDGET: process.env.ESTATE_BUDGET ?? "off" },
  });
}

export default function (pi: any) {
  pi.on("tool_call", async (event: any, ctx: any) => {
    if (off()) return undefined;
    try {
      const name = event?.toolName ?? event?.name;
      if (typeof name !== "string") return undefined;
      const r = run("pre", { tool_name: name, tool_input: event?.input ?? event?.args ?? event?.arguments ?? {}, session_id: SESSION });
      if (r.error || r.status === null) throw r.error ?? new Error("gate timed out");
      const out = (r.stdout ?? "").trim();
      if (out) {
        const j = JSON.parse(out.split("\n").filter((l: string) => l.startsWith("{")).pop() ?? "{}");
        if (j.allow === false) {
          ctx?.ui?.notify?.(`protocol-gate refused ${name}`, "warning");
          return { block: true, reason: String(j.reason ?? "protocol gate refused") };
        }
      }
      return undefined;
    } catch (e) {
      ctx?.ui?.notify?.(`protocol-gate FAILED OPEN: ${String(e)}`, "warning");
      return undefined;
    }
  });

  pi.on("tool_result", async (event: any) => {
    if (off()) return undefined;
    try {
      const parts = Array.isArray(event?.content) ? event.content : [];
      const text = parts.filter((p: any) => p?.type === "text").map((p: any) => String(p.text ?? "")).join("\n").slice(0, 4000);
      run("post", { tool_name: event?.toolName ?? "", tool_response: text, session_id: SESSION });
    } catch {
      /* detection is best-effort; the next pre-call still sees any break that opened */
    }
    return undefined;
  });
}
