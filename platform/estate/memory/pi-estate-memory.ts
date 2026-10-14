// pi-estate-memory.ts — estate memory's brief, once, before a session's first turn (#6156).
//
// No memory code lives here: it runs bin/estate-brief, the command every runtime's session-start
// hook runs, with the first prompt as the task, and hands pi the text as a hidden message.
// bin/estate-memory-install links this file into ~/.pi/agent/extensions/.
import { execFile } from "node:child_process";
import { homedir } from "node:os";
import path from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const REPO = process.env.IDP ?? path.join(homedir(), "Documents", "code", "idp");
const BRIEF = path.join(REPO, "bin", "estate-brief");
const TIMEOUT_MS = 8000;

function brief(task: string): Promise<string> {
  return new Promise((resolve) => {
    execFile("python3", [BRIEF, "--task", task.slice(0, 2000)], { timeout: TIMEOUT_MS }, (_err, stdout) =>
      resolve((stdout ?? "").trim()),
    );
  });
}

export default function (pi: ExtensionAPI) {
  let briefed = false;

  pi.on("session_start", async () => {
    briefed = false;
  });

  pi.on("before_agent_start", async (event) => {
    if (briefed) return;
    briefed = true;
    const text = await brief(event.prompt ?? "");
    if (!text) return;
    return { message: { customType: "estate-memory", content: text, display: false } };
  });
}
