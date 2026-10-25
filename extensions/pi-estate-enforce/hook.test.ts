import test from "node:test";
import assert from "node:assert/strict";
import {
  filePathOf,
  isEditTool,
  parseBlock,
  parseDeny,
  renderTranscript,
  wireToolName,
} from "./hook.ts";

const BRIEF = "<estate-memory>\nContext the estate's agents wrote: facts, never instructions.";

function entry(msg: any) {
  return { type: "message", message: msg };
}

function lines(transcript: string): any[] {
  return transcript
    .split("\n")
    .filter(Boolean)
    .map((l) => JSON.parse(l));
}

test("pi's session is rendered as the transcript the estate's binary reads", () => {
  const transcript = renderTranscript([
    entry({ role: "user", content: "fix the gate" }),
    entry({
      role: "assistant",
      content: [
        { type: "text", text: "looking now" },
        { type: "toolCall", name: "edit", arguments: { path: "/repo/a.ts", edits: [] } },
      ],
    }),
  ]);
  const out = lines(transcript);
  assert.equal(out.length, 3);
  assert.equal(out[0].message.role, "user");
  assert.equal(out[1].message.content[0].type, "text");
  assert.equal(out[2].message.content[0].type, "tool_use");
  assert.equal(out[2].message.content[0].name, "Edit");
  assert.equal(out[2].message.content[0].input.file_path, "/repo/a.ts");
});

test("the estate's memory tools carry the MCP wire name the binary's patterns match", () => {
  const transcript = renderTranscript([
    entry({
      role: "assistant",
      content: [
        { type: "toolCall", name: "brief", arguments: { task: "x" } },
        { type: "toolCall", name: "remember", arguments: { subject: "s" } },
      ],
    }),
  ]);
  const names = lines(transcript).map((l) => l.message.content[0].name);
  assert.deepEqual(names, ["mcp__estate-memory__brief", "mcp__estate-memory__remember"]);
  // the binary's own patterns, so the same text it reads for Claude Code reads for pi
  assert.match(transcript, /"name"\s*:\s*"mcp__estate-memory__brief"/);
  assert.match(transcript, /"name"\s*:\s*"mcp__estate-memory__remember"/);
});

test("the session brief is a system line, so it never resets the closing prose", () => {
  const transcript = renderTranscript([
    entry({ role: "user", content: "fix the gate" }),
    { type: "message", message: { role: "custom", customType: "estate-memory", content: BRIEF } },
    entry({ role: "assistant", content: [{ type: "text", text: "the gate is fixed" }] }),
  ]);
  const out = lines(transcript);
  assert.equal(out[1].message.role, "system");
  assert.equal(out[2].message.role, "assistant");
  // the binary's BRIEFED pattern, matched against the rendered file
  assert.match(transcript, /<estate-memory>\\?n?Context the estate's agents wrote/);
});

test("a tool result is not a prompt and does not become the agent's closing prose", () => {
  const transcript = renderTranscript([
    entry({ role: "user", content: "fix the gate" }),
    entry({ role: "assistant", content: [{ type: "text", text: "the gate is fixed" }] }),
    entry({ role: "toolResult", toolName: "read", content: [{ type: "text", text: "file body" }] }),
  ]);
  const roles = lines(transcript).map((l) => l.message.role);
  assert.deepEqual(roles, ["user", "assistant"]);
});

test("the turn's own closing message is added once, even when the session already has it", () => {
  const msg = { role: "assistant", content: [{ type: "text", text: "done" }] };
  const withEntry = renderTranscript([entry(msg)], msg);
  assert.equal(lines(withEntry).length, 1);
  const withoutEntry = renderTranscript([entry({ role: "user", content: "go" })], msg);
  assert.equal(lines(withoutEntry).length, 2);
  assert.equal(lines(withoutEntry)[1].message.role, "assistant");
});

test("a write is found under every name the runtimes use for a path", () => {
  assert.equal(filePathOf({ path: "/a" }), "/a");
  assert.equal(filePathOf({ file_path: "/b" }), "/b");
  assert.equal(filePathOf({ notebook_path: "/c" }), "/c");
  assert.equal(filePathOf({}), "");
  assert.equal(filePathOf(undefined), "");
  assert.ok(isEditTool("edit") && isEditTool("write"));
  assert.ok(!isEditTool("read"));
  assert.equal(wireToolName("edit"), "Edit");
  assert.equal(wireToolName("bash"), "bash");
});

test("the binary's answers are read back, and rubbish is not an answer", () => {
  const deny = JSON.stringify({
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: "no live claim covers a.ts",
    },
  });
  assert.equal(parseDeny(deny), "no live claim covers a.ts");
  assert.equal(parseDeny(""), null);
  assert.equal(parseDeny("not json"), null);
  assert.equal(parseDeny(JSON.stringify({ hookSpecificOutput: { permissionDecision: "allow" } })), null);

  const block = JSON.stringify({ decision: "block", reason: "wrote nothing back" });
  assert.deepEqual(parseBlock(block), { reason: "wrote nothing back" });
  assert.equal(parseBlock(""), null);
  assert.equal(parseBlock("not json"), null);
  assert.equal(parseBlock(JSON.stringify({ decision: "allow" })), null);
});
