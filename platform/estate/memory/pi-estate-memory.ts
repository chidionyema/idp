// pi-estate-memory.ts — estate memory's brief, once, before a session's first turn (#6156).
//
// No memory code lives here: it runs bin/estate-brief, the command every runtime's session-start
// hook runs, with the first prompt as the task, and hands pi the text as a hidden message.
// bin/estate-memory-install links this file into ~/.pi/agent/extensions/.
//
// It also states the no-hand-back rule (lane/no-handback): the directive rides in that same hidden
// message. The refusal itself is NOT here -- the hard gate is the estate's own binary, and pi
// reaches it through extensions/pi-estate-enforce (#7006), so one rule decides for every runtime
// and every decision lands in one ledger. Two gates for one rule would let the runtimes disagree.
// Fails open; ESTATE_MEMORY_ENFORCE=0 opts out.
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
const TIMEOUT_MS = 8000;

function brief(task: string): Promise<string> {
  return new Promise((resolve) => {
    execFile("python3", [BRIEF, "--task", task.slice(0, 2000)], { timeout: TIMEOUT_MS }, (_err, stdout) =>
      resolve((stdout ?? "").trim()),
    );
  });
}

// handback.py prints the instruction text; the refusal is the binary's job now.
function handback(arg: string): Promise<string> {
  return new Promise((resolve) => {
    execFile("python3", [HANDBACK, arg], { timeout: TIMEOUT_MS }, (_err, stdout) =>
      resolve((stdout ?? "").trim()),
    );
  });
}

const enforcing = () => process.env.ESTATE_MEMORY_ENFORCE !== "0";

export default function (pi: ExtensionAPI) {
  let briefed = false;

  pi.on("session_start", async () => {
    briefed = false;
  });

  pi.on("before_agent_start", async (event) => {
    const prompt = event.prompt ?? "";
    if (briefed) return;
    briefed = true;
    const [text, rule] = await Promise.all([brief(prompt), enforcing() ? handback("directive") : Promise.resolve("")]);
    const content = [text, rule].filter(Boolean).join("\n\n");
    if (!content) return;
    return { message: { customType: "estate-memory", content, display: false } };
  });
}
