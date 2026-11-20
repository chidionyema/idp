// estate-plan-lock — V2 port. The plan lock has teeth: a tool call the plan does not
// allow is refused. Fails open, ESTATE_PLAN_LOCK=off opts out.
import { Plugin } from "@opencode/plugin"
import { execFile } from "node:child_process"
import { existsSync } from "node:fs"
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

function authorize(tool: string, args: unknown): Promise<{ ok: boolean; reason?: string }> {
  return new Promise((resolve) => {
    execFile("python3", [PLAN, "authorize", tool, JSON.stringify(args ?? {})], { timeout: TIMEOUT_MS },
      (_err, stdout) => {
        try { resolve(JSON.parse(stdout)) } catch { resolve({ ok: true }) }
      })
  })
}

export default Plugin.define({
  id: "estate.plan-lock",
  async setup(ctx) {
    const { writeFileSync } = await import("node:fs")
    writeFileSync(
      path.join(homedir(), ".estate/state/plan-lock.loaded"),
      `loaded ${new Date().toISOString()} plan=${PLAN}\n`,
    )
    ctx.tool.hook("execute.before", async (t: any) => {
      if ((process.env.ESTATE_PLAN_LOCK ?? "").toLowerCase() === "off") return
      if (process.env.ESTATE_MEMORY_ENFORCE === "0") return
      const tool = t?.tool ?? ""
      const v = await authorize(tool, t?.input ?? t?.args)
      if (v && v.ok === false) throw new Error(v.reason ?? "plan lock refused")
    })
  },
})
