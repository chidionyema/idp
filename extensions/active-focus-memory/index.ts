/**
 * active-focus-memory — every session starts from the estate's bi-temporal truth.
 *
 * WHY THIS EXISTS. An agent's context window is not memory: the founder's standing
 * instructions, the facts the estate has proven, and the actions already known to fail get
 * re-derived by every session, and re-derived wrongly. `bin/estate-memory-engine` holds that
 * state (fact rows carry valid_to_ts, so a superseded fact is retained rather than deleted,
 * and can be queried as of any point), and this hook compiles the <1,200-token Active Focus
 * header into the session once.
 *
 * WHY THE "context" EVENT AND NOT "before_turn". The SDK's ExtensionAPI exposes
 * `on("context", handler)`, whose result is `{ messages?: AgentMessage[] }`.
 * That is the one supported way to place text in the model's context, so it is the one used.
 * There is no appendSystemContext(): it does not exist, and an extension calling it would
 * throw at session start.
 *
 * WHY THE HEADER IS INSERTED ONCE, GUARDED BY A MARKER. The context event can fire more than
 * once per session; inserting unconditionally would stack N copies of the register and spend
 * the token budget the register exists to protect. The marker is checked against the live
 * message list, not against a module-level flag, so a session that compacts and loses the
 * header gets it back.
 *
 * WHY A FAILED COMPILE IS NOT AN ERROR. Memory is an optimisation, never a blocker. If the
 * engine is missing, the DB is locked, or sqlite3 is unavailable, the session proceeds
 * without the header. A hook that refuses a session because memory could not be read would
 * make the estate's own memory surface an outage — the R6 failure mode, a recovery path that
 * depends on what it recovers.
 *
 * WHAT IT MUST NOT DO: it does not write, does not decide, does not retry in a loop.
 */
import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const ENGINE = join(homedir(), ".estate", "bin", "estate-memory-engine");
const MARKER = "GENESIS ACTIVE FOCUS REGISTER";
/**
 * Measured cost is ~1.3 s (it reads a bounded ledger tail plus three indexed queries).
 * The budget is 3x that so a loaded machine still gets its header; a timeout shorter than
 * the real cost is not a safety margin, it is a silent failure -- an earlier 2500 ms budget
 * against a 3.9 s render meant this hook injected NOTHING, on every session, quietly.
 */
const ENGINE_TIMEOUT_MS = 4000;

/** Renders the register, or returns null when it cannot be read. Never throws. */
function renderFocus(): string | null {
  if (!existsSync(ENGINE)) return null;
  try {
    const out = execFileSync(ENGINE, ["render-focus"], {
      encoding: "utf8",
      timeout: ENGINE_TIMEOUT_MS,
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
    return out.includes(MARKER) ? out : null;
  } catch {
    // A failed compile is a missing header, not a failed session (R6).
    return null;
  }
}

/** True when the header is already in the live message list. */
function alreadyPresent(messages: readonly unknown[]): boolean {
  for (const message of messages) {
    const content = (message as { content?: unknown })?.content;
    if (typeof content === "string" && content.includes(MARKER)) return true;
    if (Array.isArray(content)) {
      for (const part of content) {
        if (
          typeof part === "object" &&
          part !== null &&
          typeof (part as { text?: unknown }).text === "string" &&
          (part as { text: string }).text.includes(MARKER)
        ) {
          return true;
        }
      }
    }
  }
  return false;
}

export default function activeFocusMemory(pi: ExtensionAPI) {
  pi.on("context", async (event) => {
    if (alreadyPresent(event.messages ?? [])) return;

    const header = renderFocus();
    if (!header) return;

    return {
      messages: [
        { role: "system" as const, content: header },
        ...(event.messages ?? []),
      ],
    };
  });
}
