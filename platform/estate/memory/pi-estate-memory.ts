// pi-estate-memory.ts — estate memory's brief, once, before a session's first turn (#6156).
//
// No memory code lives here: it runs bin/estate-brief, the command every runtime's session-start
// hook runs, with the first prompt as the task, and hands pi the text as a hidden message.
// bin/estate-memory-install links this file into ~/.pi/agent/extensions/.
//
// It also holds pi to the no-hand-back rule (lane/no-handback). The directive rides in that same
// hidden message, and when a turn ends with no tool call and its closing text hands work back
// ("still open", "want me to...?", platform/estate/memory/handback.py) the extension sends the
// refusal as a follow-up prompt. One retry per closing: a refusal is not judged again. Fails open;
// ESTATE_MEMORY_ENFORCE=0 opts out.
import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const REPO = process.env.IDP ?? path.join(homedir(), "Documents", "code", "idp");
const BRIEF = path.join(REPO, "bin", "estate-brief");
// The installed copy first: the shared checkout may be on any branch, and one without this file
// would leave the extension silently doing nothing (it fails open).
const HOME_COPY = path.join(process.env.ESTATE_MEMORY_HOME ?? path.join(homedir(), ".estate", "memory"), "platform", "estate", "memory", "handback.py");
const HANDBACK = existsSync(HOME_COPY) ? HOME_COPY : path.join(REPO, "platform", "estate", "memory", "handback.py");
const REFUSAL_MARK = "Do not stop here"; // in handback.REMEDY: how a refusal is told from a person
const TIMEOUT_MS = 8000;

function brief(task: string): Promise<string> {
  return new Promise((resolve) => {
    execFile("python3", [BRIEF, "--task", task.slice(0, 2000)], { timeout: TIMEOUT_MS }, (_err, stdout) =>
      resolve((stdout ?? "").trim()),
    );
  });
}

// handback.py reads stdin and prints one JSON line; `directive` prints the instruction text.
function handback(arg: string, stdin = ""): Promise<string> {
  return new Promise((resolve) => {
    const child = execFile("python3", [HANDBACK, arg], { timeout: TIMEOUT_MS }, (_err, stdout) =>
      resolve((stdout ?? "").trim()),
    );
    child.stdin?.on("error", () => {});
    child.stdin?.end(stdin);
  });
}

const enforcing = () => process.env.ESTATE_MEMORY_ENFORCE !== "0";

export default function (pi: ExtensionAPI) {
  let briefed = false;
  let refused = false; // the next prompt answers our refusal: do not judge its closing again

  pi.on("session_start", async () => {
    briefed = false;
    refused = false;
  });

  pi.on("before_agent_start", async (event) => {
    const prompt = event.prompt ?? "";
    refused = prompt.includes(REFUSAL_MARK);
    if (briefed) return;
    briefed = true;
    const [text, rule] = await Promise.all([brief(prompt), enforcing() ? handback("directive") : Promise.resolve("")]);
    const content = [text, rule].filter(Boolean).join("\n\n");
    if (!content) return;
    return { message: { customType: "estate-memory", content, display: false } };
  });

  pi.on("turn_end", async (event) => {
    try {
      const msg = (event as any)?.message;
      if (!enforcing() || refused || !msg || msg.role !== "assistant") return;
      const parts: any[] = Array.isArray(msg.content) ? msg.content : [];
      if (parts.some((p) => p?.type === "toolCall" || p?.type === "tool_use")) return; // mid-loop, not a closing
      const text = parts
        .filter((p) => p?.type === "text" && typeof p.text === "string")
        .map((p) => p.text)
        .join("\n")
        .trim();
      if (!text) return;
      const verdict = JSON.parse((await handback("check", text)) || "{}");
      if (verdict.block && verdict.reason) pi.sendUserMessage(verdict.reason, { deliverAs: "followUp" });
    } catch {
      /* fail open: an extension fault never takes a session down */
    }
  });
}
