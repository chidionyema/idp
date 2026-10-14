// opencode-estate-memory.js — estate memory's brief in every opencode session's system prompt (#6156).
//
// No memory code lives here: it runs bin/estate-brief, the command every runtime's session-start
// hook runs, once per session, and appends the text to the system prompt of that session's calls.
// bin/estate-memory-install links this file into ~/.config/opencode/plugin/.
import { execFile } from "node:child_process";
import { homedir } from "node:os";
import path from "node:path";

const REPO = process.env.IDP ?? path.join(homedir(), "Documents", "code", "idp");
const BRIEF = path.join(REPO, "bin", "estate-brief");
const TIMEOUT_MS = 8000;

function brief() {
  return new Promise((resolve) => {
    execFile("python3", [BRIEF], { timeout: TIMEOUT_MS }, (_err, stdout) => resolve((stdout ?? "").trim()));
  });
}

export const EstateMemory = async () => {
  const sessions = new Map();
  return {
    "experimental.chat.system.transform": async (input, output) => {
      const id = input?.sessionID ?? "";
      if (!sessions.has(id)) sessions.set(id, brief());
      const text = await sessions.get(id);
      if (text) output.system.push(text);
    },
  };
};
