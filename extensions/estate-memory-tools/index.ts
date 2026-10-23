/**
 * estate-memory-tools — pi gets the estate's memory tools, from the estate's own bridge.
 *
 * WHY THIS FILE EXISTS. Estate memory is one store behind one door (the MCP gateway), and every
 * runtime reaches it through one bridge: bin/estate-memory-mcp, an MCP server that speaks JSON-RPC
 * over stdio. Claude Code, Cursor, Gemini and OpenCode register that server as an MCP server, so
 * their agents get brief, recall and remember as tools.
 *
 * pi has no MCP client. pi's own docs say so outright: "It intentionally does not include built-in
 * MCP, sub-agents, permission popups, plan mode, to-dos, or background bash." The estate's
 * installer nevertheless wrote an `mcpServers` block into ~/.pi/mcp.json for pi (the manifest's
 * "mcp" entry), and pi has never read that file: it is inert config that reads like a working
 * integration. The result was a runtime that could read the session brief and nothing else -- it
 * could not recall mid-session, and it could not remember anything at all. Meanwhile the router
 * tells every agent, pi included, "Record what you learn with the estate memory `remember` tool",
 * so pi agents were told to use a tool they did not have, and their learning went nowhere.
 *
 * WHAT THIS IS. A transport, not an implementation. It spawns the same bridge every other runtime
 * runs and speaks the same JSON-RPC to it, so the behaviour is the estate's behaviour, not a second
 * copy of it: the tool descriptions come from the bridge's own tools/list, the calls are the
 * bridge's own calls, and the store behind them is the one store. If the bridge changes what
 * remember means, this file changes nothing.
 *
 * WHY NOT A SECOND DOOR. A pi-only memory implementation would be the estate's ninth copy of the
 * same capability and would drift from the other eight the first time the schema changed. There is
 * one door (AGENTS.md section 6); this is a client for it.
 *
 * FAILURE IS A MESSAGE, NOT A CRASH. If the bridge is missing, slow, or broken, the tool returns
 * what went wrong and the session keeps going. Memory that cannot be reached must never take an
 * agent's turn down with it.
 */

import { Type } from "typebox";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Bridge } from "./bridge.ts";

/** The tools the estate's memory serves. Names are the contract the router's instructions use. */
const TOOL_NAMES = ["brief", "recall", "remember"] as const;

type ToolName = (typeof TOOL_NAMES)[number];

/**
 * The tool arguments, as the bridge's own schemas declare them.
 *
 * Every field the bridge marks optional is optional here too, and every field the bridge gives a
 * default for is left to the bridge's default. A model that has to invent an empty subject to
 * satisfy a schema learns nothing and wastes a turn on it; the bridge already knows the
 * defaults, so the schema says what the bridge says.
 */
const PARAMETERS: Record<ToolName, any> = {
  brief: Type.Object({
    task: Type.Optional(
      Type.String({ description: "What you are about to do, in a sentence." }),
    ),
    limit: Type.Optional(
      Type.Number({ description: "How many memories in each half of the brief." }),
    ),
  }),
  recall: Type.Object({
    query: Type.String({ description: "What to look for, in your own words." }),
    subject: Type.Optional(
      Type.String({ description: "Filter on the subject remember wrote." }),
    ),
    kind: Type.Optional(
      Type.String({
        description:
          "Filter on the kind remember wrote: decision, incident, measurement, preference, fact.",
      }),
    ),
    tags: Type.Optional(
      Type.Array(Type.String(), { description: "Filter on the tags remember wrote." }),
    ),
    limit: Type.Optional(Type.Number({ description: "How many memories to return." })),
  }),
  remember: Type.Object({
    content: Type.String({ description: "What happened, in prose." }),
    subject: Type.Optional(Type.String({ description: "What it is about." })),
    kind: Type.Optional(
      Type.String({
        description: "One of decision, incident, measurement, preference, fact.",
      }),
    ),
    tags: Type.Optional(Type.Array(Type.String(), { description: "Further filters." })),
    runtime: Type.Optional(Type.String({ description: "The agent runtime writing it." })),
  }),
};

/** Descriptions used only if the bridge cannot be asked for them; the bridge's own text wins. */
const FALLBACK_DESCRIPTION: Record<ToolName, string> = {
  brief: "What to know before starting: call once at the start of a session or task.",
  recall: "Read back what the estate already knows, ranked, under a byte ceiling.",
  remember:
    "Write one memory to the estate's permanent store, in the estate's structured form. " +
    "Content is what happened; subject, kind and tags are the filters recall can name later.",
};

export default async function (pi: ExtensionAPI) {
  const bridge = new Bridge();

  const call = async (name: ToolName, args: Record<string, unknown>) => {
    try {
      await bridge.ensure();
      // A memory written by pi says so. The estate has to be able to see which runtime wrote
      // what -- Claude Code's writes carry source "claude-code" -- so this names the runtime it
      // is, unless the caller already said.
      const payload = name === "remember" ? { source: "pi", runtime: "pi", ...args } : args;
      const result = await bridge.call(name, payload);
      const content = Array.isArray(result.content) ? result.content : [];
      return {
        content: content.length ? content : [{ type: "text", text: "" }],
        details: result.structuredContent ?? {},
      };
    } catch (error) {
      // Memory that cannot be reached must not take the turn down with it.
      return {
        content: [
          {
            type: "text",
            text: `estate memory is unavailable: ${(error as Error).message}`,
          },
        ],
        details: { error: (error as Error).message },
      };
    }
  };

  // The bridge's own descriptions, fetched before the tools are registered: the same text every
  // other runtime's agents read, so a change in the estate's wording reaches pi too. A bridge
  // that is down must not hold the session hostage, so this waits a few seconds and then
  // registers the fallback wording.
  const descriptions = new Map<ToolName, string>();
  try {
    await Promise.race([
      bridge.ensure().then(async () => {
        const tools = await bridge.tools();
        for (const tool of tools) {
          if ((TOOL_NAMES as readonly string[]).includes(tool?.name) && tool?.description) {
            descriptions.set(tool.name as ToolName, tool.description);
          }
        }
      }),
      new Promise((resolve) => setTimeout(resolve, 3000)),
    ]);
  } catch {
    // The fallback descriptions stay; the tools still work against the bridge on first call.
  }

  for (const name of TOOL_NAMES) {
    pi.registerTool({
      name,
      label: `Estate ${name}`,
      description: descriptions.get(name) ?? FALLBACK_DESCRIPTION[name],
      parameters: PARAMETERS[name],
      async execute(_toolCallId, params) {
        return await call(name, (params ?? {}) as Record<string, unknown>);
      },
    });
  }

  pi.on("session_end", async () => {
    bridge.close();
  });
}
