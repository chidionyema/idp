// estate-plan-lock — V2 port. The plan lock has teeth: a tool call the plan does not
// allow is refused. Fails open, ESTATE_PLAN_LOCK=off opts out.
import { Plugin } from "@opencode/plugin"
import { execFile } from "node:child_process"
import { existsSync, readFileSync, appendFileSync, mkdirSync } from "node:fs"
import { homedir } from "node:os"
import path from "node:path"

const REPO = process.env.IDP ?? path.join(homedir(), "Documents", "code", "idp")
const HOME_PLAN = path.join(
  process.env.ESTATE_MEMORY_HOME ?? path.join(homedir(), ".estate", "memory"),
  "platform", "estate", "memory", "plan.py",
)
const CHECKOUT = path.join(REPO, "platform", "estate", "memory", "plan.py")
const PLAN = existsSync(HOME_PLAN) ? HOME_PLAN : CHECKOUT
const TIMEOUT_MS = 8000

// The plan the CLI writes is the plan the gate must judge.
//
// estate-plan records every plan-tool call it accepts into ~/.estate/plans/<session>.jsonl as
// {"tool": "declare_plan", "args": {...}} lines. This hook used to send a literal "[]" as stdin,
// which plan.py reads as "no plan declared" -- so a founder who declared a plan, added a BDD and
// completed a goal still had every tool refused, because the gate was judging an empty plan while
// the real one sat on disk. Read that file and replay it into plan.py.
const PLAN_TOOL_NAMES = [
  "declare_plan", "revise_plan", "add_bdd", "address_edgecases",
  "address_2nd_order_effects", "complete_goal",
] as const

// Measured 2026-11-20 on the live hook: the tool string is `estate-memory_declare_plan`, so the
// canonical name is the segment after the last underscore. This is the ONLY hook OpenCode runs —
// the other plugin's tool.execute.after never fires — so this is where the session ledger is written.
function canonicalPlanTool(tool: string): string | null {
  const name = String(tool ?? "").split("_").pop() ?? ""
  return (PLAN_TOOL_NAMES as readonly string[]).includes(name) ? name : null
}

// The agent also reaches the plan tools through the `execute` tool:
//   execute { code: 'const m = tools["estate-memory"]; await m.declare_plan({ goal: "…" })' }
// and the inner MCP call never reaches this hook, so the session ledger stays empty and every
// later tool is refused for "no plan declared" while the plan exists in the MCP's own file.
// This reads the FIRST plan-tool call out of that code payload by brace matching, converts the
// object literal to JSON (bare keys quoted, single quotes normalised), and records it.
function planCallFromCode(code: string): { tool: string; args: unknown } | null {
  const m = /\b(declare_plan|revise_plan|add_bdd|address_edgecases|address_2nd_order_effects|complete_goal)\s*\(/.exec(code)
  if (!m) return null
  const tool = m[1]
  const open = code.indexOf("{", m.index + m[0].length)
  if (open < 0) return null
  let depth = 0, inStr: string | null = null, esc = false
  for (let i = open; i < code.length; i++) {
    const ch = code[i]
    if (inStr) {
      if (esc) esc = false
      else if (ch === "\\") esc = true
      else if (ch === inStr) inStr = null
      continue
    }
    if (ch === '"' || ch === "'" || ch === "`") { inStr = ch; continue }
    if (ch === "{") depth++
    else if (ch === "}" && --depth === 0) {
      const literal = code.slice(open, i + 1)
      try {
        const asJson = literal
          .replace(/([{,]\s*)([A-Za-z_$][A-Za-z0-9_$]*)\s*:/g, '$1"$2":')
          .replace(/'/g, '"')
          .replace(/,\s*([}\]])/g, "$1")
        return { tool, args: JSON.parse(asJson) }
      } catch { return null }
    }
  }
  return null
}

function recordPlanCall(sid: string, canonical: string, args: unknown): void {
  try {
    const dir = path.join(homedir(), ".estate", "plans")
    mkdirSync(dir, { recursive: true })
    appendFileSync(
      path.join(dir, `${safeId(sid)}.jsonl`),
      JSON.stringify({ tool: canonical, args: args ?? {} }) + "\n",
    )
  } catch { /* a broken ledger must not take a session down */ }
}

function safeId(sid?: string): string {
  return String(sid ?? "").replace(/[^A-Za-z0-9._-]+/g, "_").replace(/^_+|_+$/g, "")
}

// A session sees its OWN ledger or nothing. Never another session's plan: falling back to a
// "newest file" let a brand-new session inherit someone else's plan and mutate without one
// (measured 2026-11-20: shell ran with no plan of its own).
function planCalls(sessionId?: string): [string, unknown][] {
  const safe = safeId(sessionId)
  if (!safe) return []
  const file = path.join(homedir(), ".estate", "plans", `${safe}.jsonl`)
  try {
    return readFileSync(file, "utf8").split("\n").filter(Boolean).flatMap((line) => {
      try {
        const rec = JSON.parse(line)
        return rec && typeof rec.tool === "string" ? [[rec.tool, rec.args ?? {}]] : []
      } catch { return [] }
    })
  } catch { return [] }
}

function authorize(tool: string, args: unknown, sessionId?: string): Promise<{ ok: boolean; reason?: string }> {
  const calls = JSON.stringify(planCalls(sessionId))
  return new Promise((resolve) => {
    const child = execFile("python3", [PLAN, "authorize", tool, JSON.stringify(args ?? {})],
      { timeout: TIMEOUT_MS, env: { ...process.env, ESTATE_SESSION_ID: safeId(sessionId) } },
      (_err, stdout) => {
        try { resolve(JSON.parse(stdout)) } catch { resolve({ ok: false, reason: "plan check unreadable" }) }
      })
    child.stdin?.on("error", () => {})
    child.stdin?.end(calls)
  })
}

export default Plugin.define({
  id: "estate.plan-lock",
  async setup(ctx) {
    const { writeFileSync } = await import("node:fs")
    writeFileSync(
      path.join(homedir(), ".estate/state/plan-lock.loaded"),
      `loaded ${new Date().toISOString()} plan=${PLAN} pid=${process.pid}\n`,
    )
    ctx.tool.hook("execute.before", async (t: any) => {
      try {
        appendFileSync(
          path.join(homedir(), ".estate", "state", "plan-lock.trace.log"),
          JSON.stringify({ at: new Date().toISOString(), tool: t?.tool ?? null, sid: t?.sessionID ?? t?.sessionId ?? null, keys: Object.keys(t ?? {}) }) + "\n",
        )
      } catch { /* trace only */ }
      if ((process.env.ESTATE_PLAN_LOCK ?? "").toLowerCase() === "off") return
      if (process.env.ESTATE_MEMORY_ENFORCE === "0") return
      const tool = t?.tool ?? ""
      const sid = t?.sessionID ?? t?.sessionId ?? ""
      const args = t?.input ?? t?.args
      const direct = canonicalPlanTool(tool)
      if (direct) recordPlanCall(sid, direct, args)
      else if (String(tool ?? "") === "execute" && typeof (args as any)?.code === "string") {
        const inner = planCallFromCode((args as any).code)
        if (inner) recordPlanCall(sid, inner.tool, inner.args)
      }
      const v = await authorize(tool, args, sid)
      if (v && v.ok === false) throw new Error(v.reason ?? "plan lock refused")
    })
  },
})
