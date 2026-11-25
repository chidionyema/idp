// estate-plan-lock — V2 port. The plan lock has teeth: a tool call the plan does not
// allow is refused. Fails open, ESTATE_PLAN_LOCK=off opts out.
import { Plugin } from "@opencode/plugin"
import { execFile } from "node:child_process"
import { existsSync, readFileSync, appendFileSync } from "node:fs"
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
// The gate does NOT reconstruct plan calls from the agent's source text.
//
// MEASURED 2026-11-25: this hook used to read the FIRST plan-tool call out of the code payload
// by brace matching and rewrite the object literal as JSON. A payload it could not read -- an
// apostrophe, a nested literal, a second plan call -- was never recorded, so the plan never
// advanced, and the gate then refused every tool, including the add_bdd that would have
// repaired it: a session could brick itself with one apostrophe, and the refusal pointed at
// the one call the gate could not see.
//
// The ledger has ONE writer now: the estate-memory bridge, which records the STRUCTURED call it
// applied -- the tool name and the arguments it was given, not a guess about the agent's source.
// A call the bridge refuses is not recorded, so the ledger holds only calls that applied. The
// gate reads that ledger and judges. This is the same rule the other opencode plugin already
// follows (platform/estate/memory/opencode-estate-memory.js): the plugin publishes identity,
// never a second plan model.

// The CLI door (bin/estate-plan) resolves the session from the caller's own process tree, and
// the pointer for the runtime that owns this session is what it reads. Without it the sanctioned
// fallback landed on another session's ledger (measured 2026-11-25: "goal_diag_release is not on
// this plan"), so the gate publishes the pointer for the process that owns the session.
function publishSessionPointer(sid: string): void {
  if (!sid) return
  const pid = process.pid
  const pointer = path.join(homedir(), ".estate", "plans", `session-${pid}.json`)
  try {
    const current = JSON.parse(readFileSync(pointer, "utf8"))
    if (current && current.session_id === sid) return
  } catch { /* no pointer yet: publish one */ }
  try {
    execFile(
      "python3",
      [PLAN, "publish", "--session", sid, "--pid", String(pid), "--overwrite"],
      { timeout: TIMEOUT_MS },
      () => {},
    )
  } catch { /* a pointer that cannot be written is not a crash */ }
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
      publishSessionPointer(sid)
      const v = await authorize(tool, args, sid)
      if (v && v.ok === false) throw new Error(v.reason ?? "plan lock refused")
    })
  },
})
