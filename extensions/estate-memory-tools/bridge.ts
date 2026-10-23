/**
 * bridge.ts — the estate memory bridge, spoken to over stdio. One MCP client, no dependencies.
 *
 * WHY THIS IS SEPARATE FROM index.ts. index.ts needs typebox (pi's tool schemas); this file needs
 * nothing but Node. Keeping the transport free of the schema library means the transport can be
 * tested on its own -- a test spawns a stub bridge and reads the bytes this sends and receives --
 * and so a broken handshake is caught by a test rather than by an agent's first tool call.
 *
 * THE PROTOCOL. The bridge (bin/estate-memory-mcp) reads stdin line by line and writes one JSON
 * object per line: JSON-RPC 2.0 over stdio, newline delimited. There is no Content-Length
 * framing here and no HTTP: this is the same framing every other runtime's MCP client uses,
 * because it is the bridge's own.
 */

import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";

export const MEMORY_HOME = path.resolve(
  process.env.ESTATE_MEMORY_HOME ?? path.join(homedir(), ".estate", "memory"),
);
export const BRIDGE = path.join(MEMORY_HOME, "bin", "estate-memory-mcp");
export const PYTHON = process.env.ESTATE_MEMORY_PYTHON ?? "python3";
export const CALL_TIMEOUT_MS = 35_000; // the bridge's own ceiling is 30s; give it room, then give up
export const START_TIMEOUT_MS = 10_000;

export class Bridge {
  private proc: ChildProcessWithoutNullStreams | null = null;
  private buffer = "";
  private nextId = 1;
  private readonly pending = new Map<
    number,
    { resolve: (value: any) => void; reject: (error: Error) => void }
  >();
  private stderr = "";
  private starting: Promise<void> | null = null;

  /** Start the bridge and complete the MCP handshake. One process per session, like every other runtime. */
  start(): Promise<void> {
    if (this.starting) return this.starting;
    this.starting = (async () => {
      if (!existsSync(BRIDGE)) {
        throw new Error(
          `the estate memory bridge is not installed at ${BRIDGE}. ` +
            `Run bin/estate-memory-install to install it.`,
        );
      }
      const proc = spawn(PYTHON, [BRIDGE], { stdio: ["pipe", "pipe", "pipe"] });
      this.proc = proc;
      proc.stdout.on("data", (chunk: Buffer) => this.onData(chunk));
      proc.stderr.on("data", (chunk: Buffer) => {
        this.stderr = (this.stderr + chunk.toString()).slice(-2000);
      });
      proc.on("exit", (code) => {
        this.proc = null;
        const error = new Error(
          `the estate memory bridge exited (code ${code})${this.stderr ? `: ${this.stderr.trim()}` : ""}`,
        );
        for (const { reject } of this.pending.values()) reject(error);
        this.pending.clear();
      });
      await this.request("initialize", {
        protocolVersion: "2025-06-18",
        capabilities: {},
        clientInfo: { name: "pi-estate-memory-tools", version: "1" },
      });
      this.notify("notifications/initialized", {});
    })();
    return this.starting;
  }

  /** Start the bridge if it is not running yet. */
  async ensure(): Promise<void> {
    if (!this.proc) this.starting = null;
    await this.start();
  }

  private onData(chunk: Buffer): void {
    this.buffer += chunk.toString();
    let index = this.buffer.indexOf("\n");
    while (index !== -1) {
      const line = this.buffer.slice(0, index).trim();
      this.buffer = this.buffer.slice(index + 1);
      if (line) this.resolveLine(line);
      index = this.buffer.indexOf("\n");
    }
  }

  private resolveLine(line: string): void {
    let message: any;
    try {
      message = JSON.parse(line);
    } catch {
      return; // a line that is not JSON is not an answer
    }
    const waiter = this.pending.get(message?.id);
    if (waiter) {
      this.pending.delete(message.id);
      waiter.resolve(message);
    }
  }

  private notify(method: string, params: unknown): void {
    this.proc?.stdin.write(JSON.stringify({ jsonrpc: "2.0", method, params }) + "\n");
  }

  request(method: string, params: unknown, timeoutMs = CALL_TIMEOUT_MS): Promise<any> {
    const proc = this.proc;
    if (!proc) return Promise.reject(new Error("the estate memory bridge is not running"));
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`the estate memory bridge did not answer ${method} within ${timeoutMs}ms`));
      }, timeoutMs);
      this.pending.set(id, {
        resolve: (value) => {
          clearTimeout(timer);
          resolve(value);
        },
        reject: (error) => {
          clearTimeout(timer);
          reject(error);
        },
      });
      proc.stdin.write(JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n");
    });
  }

  /** The bridge's own tool list: the names and descriptions every other runtime sees. */
  async tools(): Promise<any[]> {
    const reply = await this.request("tools/list", {});
    return reply?.result?.tools ?? [];
  }

  async call(name: string, args: Record<string, unknown>): Promise<any> {
    const reply = await this.request("tools/call", { name, arguments: args });
    if (reply?.error) {
      throw new Error(`the estate memory bridge refused ${name}: ${reply.error.message}`);
    }
    return reply?.result ?? { content: [{ type: "text", text: "the bridge gave no result" }] };
  }

  close(): void {
    this.proc?.stdin.end();
    this.proc?.kill();
    this.proc = null;
  }
}
