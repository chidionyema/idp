import { Plugin } from "@opencode/plugin"
import { spawnSync } from "node:child_process"
import { existsSync } from "node:fs"
import { homedir } from "node:os"
import { join } from "node:path"

const GUARD = join(homedir(), "Documents/code/idp/bin/estate-zero-worktree")

function refusal(shell: string): string | null {
  if (!existsSync(GUARD)) return "GUARD MISSING: " + GUARD
  const r = spawnSync(GUARD, ["check", "--", shell], { encoding: "utf8" })
  if (r.status === 78) return (r.stderr || r.stdout || "").trim()
  return null
}

export default Plugin.define({
  id: "estate.zero-worktree",
  async setup(ctx) {
    const { writeFileSync } = await import("node:fs")
    writeFileSync(join(homedir(), ".estate/state/zero-worktree.loaded"),
      `loaded ${new Date().toISOString()} guard=${GUARD}\n`)
    ctx.tool.hook("execute.before", (t: any) => {
      const cmd = t?.input?.command ?? t?.args?.command
      if (typeof cmd !== "string" || !cmd) return
      const why = refusal(cmd)
      if (why) throw new Error(why)
    })
  },
})
