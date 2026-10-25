// The pi side of the estate's write-side gates: the seam, not a second implementation.
//
// Claude Code runs the estate's gates as hooks. bin/estate-memory-enforce reads a JSON payload on
// stdin, answers on stdout, and reads the session transcript in Claude's shape. pi has no hooks
// -- it has extensions, and its session is a different shape. So this module renders pi's session
// into the transcript the estate's binary reads, and reads the binary's answer back.
//
// The DECISIONS stay where they are. The claim register (focus.py), the hand-back judge
// (handback.py) and the write-back rule live in bin/estate-memory-enforce; nothing here decides
// whether a change is allowed. Pure, so it runs under node's own test runner (hook.test.ts) with
// no pi import, and the estate's gates stay the only place that says no.

/** pi's edit tools, and the names Claude's hook contract uses for them. */
export const EDIT_WIRE: Record<string, string> = {
  edit: "Edit",
  write: "Write",
  multiedit: "MultiEdit",
  notebookedit: "NotebookEdit",
};

/** The estate's memory tools carry their MCP wire name, so the binary's patterns match them. */
export const MEMORY_WIRE: Record<string, string> = {
  brief: "mcp__estate-memory__brief",
  recall: "mcp__estate-memory__recall",
  remember: "mcp__estate-memory__remember",
};

/** The wire name of a pi tool, in the vocabulary the estate's binary already reads. */
export function wireToolName(name: string): string {
  if (Object.prototype.hasOwnProperty.call(EDIT_WIRE, name)) return EDIT_WIRE[name];
  if (Object.prototype.hasOwnProperty.call(MEMORY_WIRE, name)) return MEMORY_WIRE[name];
  return name;
}

/** True for the tools that change a file -- the ones the claim write gate watches. */
export function isEditTool(name: string): boolean {
  return Object.prototype.hasOwnProperty.call(EDIT_WIRE, name);
}

/** The path a write touches: pi's tools call it path, Claude's call it file_path. */
export function filePathOf(input: unknown): string {
  const i = (input ?? {}) as Record<string, unknown>;
  for (const key of ["path", "file_path", "notebook_path"]) {
    const v = i[key];
    if (typeof v === "string" && v.trim()) return v;
  }
  return "";
}

function textOf(content: unknown): string {
  if (typeof content === "string") return content;
  if (!Array.isArray(content)) return "";
  return content
    .filter((b: any) => b && b.type === "text" && typeof b.text === "string")
    .map((b: any) => b.text)
    .join("\n");
}

function prose(role: string, text: string): string {
  return JSON.stringify({
    type: role,
    message: { role, content: [{ type: "text", text }] },
  });
}

function briefLine(text: string): string {
  // A system line, not a user line: the brief arrives after the prompt, and a user line would
  // reset the hand-back judge's "last agent text" to nothing.
  return JSON.stringify({ type: "system", message: { role: "system", content: text } });
}

function toolUse(name: string, args: unknown): string {
  const input = isEditTool(name) ? { file_path: filePathOf(args) } : ((args ?? {}) as object);
  return JSON.stringify({
    type: "assistant",
    message: { role: "assistant", content: [{ type: "tool_use", name: wireToolName(name), input }] },
  });
}

function messageLines(msg: any): string[] {
  const role = msg?.role;
  if (role === "user") {
    const t = textOf(msg.content).trim();
    return t ? [prose("user", t)] : [];
  }
  if (role === "assistant") {
    const out: string[] = [];
    const content = Array.isArray(msg.content) ? msg.content : [];
    const text = textOf(content).trim();
    if (text) out.push(prose("assistant", text));
    for (const b of content) {
      if (b?.type === "toolCall") out.push(toolUse(String(b?.name ?? ""), b?.arguments));
    }
    return out;
  }
  if (role === "custom" && msg?.customType === "estate-memory") {
    const t = textOf(msg.content).trim();
    return t ? [briefLine(t)] : [];
  }
  return [];
}

function fingerprint(msg: any): string {
  try {
    return JSON.stringify({ role: msg?.role, content: msg?.content, timestamp: msg?.timestamp });
  } catch {
    return "";
  }
}

/**
 * pi's session, rendered as the transcript the estate's binary reads.
 *
 * `extra` is a message the session may not have flushed yet (the turn's own closing message); it
 * is added only when it is not already in the entries, so a message is never counted twice.
 */
export function renderTranscript(entries: unknown[], extra?: unknown): string {
  const lines: string[] = [];
  let extraSeen = false;
  const extraPrint = extra ? fingerprint(extra) : "";
  for (const entry of (entries ?? []) as any[]) {
    if (entry?.type === "message") {
      const msg = entry.message ?? {};
      if (extraPrint && fingerprint(msg) === extraPrint) extraSeen = true;
      lines.push(...messageLines(msg));
    } else if (entry?.type === "custom_message" && entry?.customType === "estate-memory") {
      const t = textOf(entry.content).trim();
      if (t) lines.push(briefLine(t));
    }
  }
  if (extra && !extraSeen) lines.push(...messageLines(extra));
  return lines.length ? lines.join("\n") + "\n" : "";
}

/** The pre gate's answer: the reason a change is refused, or null when it may go ahead. */
export function parseDeny(stdout: string): string | null {
  try {
    const data = JSON.parse(String(stdout ?? "").trim() || "{}");
    const h = data?.hookSpecificOutput;
    if (h?.permissionDecision === "deny") {
      return String(h.permissionDecisionReason ?? "Refused by the estate's write gate.");
    }
    return null;
  } catch {
    return null;
  }
}

/** The stop gate's answer: the reason a turn may not end, or null when it may. */
export function parseBlock(stdout: string): { reason: string } | null {
  try {
    const data = JSON.parse(String(stdout ?? "").trim() || "{}");
    if (data?.decision === "block") {
      return { reason: String(data.reason ?? "Refused by the estate's stop gate.") };
    }
    return null;
  } catch {
    return null;
  }
}
