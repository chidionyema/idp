// ~/.pi/agent/extensions/00-shift-left-enforcer.ts
// Enforces hard tool_call blocking before execution:
// 1. Blocks native write/edit on governance, executor, intents, hooks, or /tmp scripts.
// 2. Blocks git -c core.hooksPath, --no-verify, bin/claim-open path-stuffing, and git checkout/worktree.
// 3. Hard-stops at 5 steps per turn/goal instead of printing Warning: Governance FAIL.

export default function shiftLeftEnforcer(pi: any) {
  let stepCount = 0;
  const MAX_STEPS = 5;

  pi.on("turn_start", () => {
    stepCount = 0;
  });

  pi.on("tool_call", async (event: any) => {
    const toolName = String(event?.toolName || event?.name || "");
    const args = event?.args || event?.input || {};

    // 1. Hard Step Budget Enforcement (replaces non-blocking Warning: Governance FAIL)
    if (["estate_execute", "estate_invoke", "bash", "write", "edit"].includes(toolName)) {
      stepCount += 1;
      if (stepCount > MAX_STEPS) {
        return {
          block: true,
          reason: `HARD_STOP (exit 78): Step budget exhausted (${stepCount}/${MAX_STEPS}). Do not retry; emit parked state receipt.`,
        };
      }
    }

    // 2. Block Pi native write/edit from touching governance files or laundering scripts in /tmp
    if (toolName === "write" || toolName === "edit") {
      const targetPath = String(args.path || args.file_path || "");
      const forbiddenTargets = [
        /\.estate\/(intents|runtime|libexec|memory)/,
        /\.githooks\//,
        /mcp\/plugins\/estate_executor\.py$/,
        /platform\/executor\/daemon\.py$/,
        /^\/tmp\/.*\.(sh|py|bash|zsh)$/,
      ];
      if (forbiddenTargets.some((rx) => rx.test(targetPath))) {
        return {
          block: true,
          reason: `SHIFT_LEFT_REFUSAL (exit 78): Native '${toolName}' on '${targetPath}' is forbidden. Governance files and /tmp executable scripts cannot be mutated by agents.`,
        };
      }
    }

    // 3. Block hook bypasses, /tmp script laundering, and retroactive claim-open stuffing in estate_execute
    if (toolName === "estate_execute" || toolName === "bash") {
      const cmd = String(args.command || args.cmd || "");
      const bannedShapes: Array<[RegExp, string]> = [
        [/core\.hooksPath|--no-verify/, "Disabling git hooks is forbidden (exit 78)."],
        [/\b(sh|bash|zsh|python3?)\s+\/tmp\//, "Executing laundered scripts from /tmp/ is forbidden (exit 78)."],
        [/\bgit\s+(checkout|switch|worktree\s+add)\b/, "Working-tree checkouts and worktrees are forbidden; use git-atomic-commit + bin/shift-left-land (exit 78)."],
        [/bin\/claim-open\b.*--paths/, "Retroactive path stuffing via bin/claim-open is forbidden; claims are locked at issue creation (exit 78)."],
      ];
      for (const [rx, msg] of bannedShapes) {
        if (rx.test(cmd)) {
          return { block: true, reason: `SHIFT_LEFT_REFUSAL: ${msg}` };
        }
      }
    }
    return undefined;
  });
}
