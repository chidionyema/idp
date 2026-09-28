/**
 * executor-door — the agent's ONLY road to a shell, and it runs through the daemon.
 *
 * ORDER (founder, 2026-09-13), verbatim:
 *
 *   "Solution 2: Decoupled Execution Daemon (The True Enterprise Pattern). If you want ultra-high-tech
 *    governance, the agent shouldn't have raw, unrestricted bash spawned directly from its own process
 *    tree anyway. It should request execution from an isolated daemon.
 *
 *    - We strip the native bash tool from pi entirely.
 *    - We replace it with an MCP (Model Context Protocol) server called idp-executor-mcp.
 *    - The Hard Boundary: this MCP server runs as a background macOS launchd service under a restricted
 *      configuration or a separate user profile (e.g. _idp_executor).
 *    - The Enforcement: the MCP server accepts execute_command JSON payloads from the agent. The server
 *      wraps the command in the 60-second timeout, runs it, and returns the stdout/stderr.
 *    - The Result: the agent can still run git commit or pytest, but it does so via the MCP daemon.
 *      Because the agent cannot edit the daemon's binary or launchd plist, it cannot bypass the ceiling.
 *      The execution plane is completely severed from the agent's local write privileges."
 *
 * WHY THIS IS AN EXTENSION AND NOT AN MCP SERVER
 *
 * pi has no MCP support. Its own README, line 495: "No MCP. Build CLI tools with READMEs, or build an
 * extension that adds MCP support."
 *
 * So the daemon half of the order is exactly as specified -- `platform/executor/daemon.py` is a real
 * launchd service that owns the ceiling and refuses to duplicate the number anywhere else. The door
 * INTO it, on this harness, is an extension. That is the same architecture the founder named, using
 * the one mechanism this harness actually has. Writing an MCP server pi cannot load would have been a
 * file, not a tool -- and a file that no session loads is decoration.
 *
 * WHAT THIS DOES, IN ORDER
 *
 * 1. Registers `execute_command` -- the tool the founder's spec names, taking a command, a cwd, and an
 *    optional ceiling. It posts to the daemon's UNIX socket and returns a job id IMMEDIATELY. It never
 *    waits. The daemon runs the command detached, under `gtimeout`, and writes the output to a file.
 * 2. Registers `read_job` -- fetch one job's state, exit code and output.
 * 3. REMOVES `bash` from the active tool set. This is the severance, and it is the step that makes the
 *    ceiling unexpressible rather than merely caught: a command that never runs inside this process's
 *    tree cannot hold a turn open, whatever it was written to do.
 * 4. Intercepts any `tool_call` that still names a removed tool and refuses it. Defence in depth: a
 *    tool removed from the active set is gone from the model's view, and this catches the case where a
 *    session already had its tool list built when the extension loaded.
 *
 * WHAT IT DELIBERATELY DOES NOT DO
 *
 * It does not implement a second timeout. The daemon owns the ceiling (LAW 44: a second copy of the
 * number is a second answer, and the two drift). If the daemon is unreachable this REFUSES -- a door
 * that silently falls back to spawning a shell locally is the exact defect class this estate keeps
 * catching. Fail closed, always.
 */

import { Type } from "typebox";
import { connect } from "node:net";

/** The daemon's socket. Named by the environment, never guessed, so a service uid can move it. */
const SOCKET_PATH =
  process.env.IDP_EXECUTOR_SOCKET ??
  `${process.env.HOME ?? ""}/.estate/executor.sock`;

/** Tools this extension removes from the agent's surface. The severance is these names. */
const SEVERED_TOOLS = ["bash"];

/** How long to wait for the daemon to ACCEPT a job. Small: it accepts in milliseconds or is down. */
const ACCEPT_TIMEOUT_MS = 5_000;

/**
 * How long to hold the socket open for the blocking `wait` verb.
 *
 * The DAEMON owns the ceiling; this is only the connection's patience for it, plus a margin for the
 * reply to cross the socket. Deliberately NOT the number 60 -- a second copy of the ceiling is a
 * second answer and the two drift (LAW 44); this is a different fact, the transport's patience, and
 * it is therefore derived rather than typed twice.
 */
const WAIT_TIMEOUT_MARGIN_MS =
  Number(process.env.IDP_EXECUTOR_CEILING_SEC ?? 60) * 1000 + 5_000;

interface DaemonReply {
  ok: boolean;
  job_id?: string;
  ceiling_sec?: number;
  refused?: boolean;
  error?: string;
  result?: unknown;
}

/**
 * Post one request to the daemon over its UNIX socket and read one reply.
 *
 * Bounded, and bounded SMALL: this is the accept handshake, not the command. The daemon answers a
 * submission in milliseconds because it only records the job and starts a detached runner. A socket
 * that does not answer inside ACCEPT_TIMEOUT_MS is a daemon that is not there, and the caller gets a
 * refusal -- never a local fallback.
 */
function callDaemon(
  payload: Record<string, unknown>,
  acceptTimeoutMs = ACCEPT_TIMEOUT_MS,
): Promise<DaemonReply> {
  return new Promise((resolve) => {
    let settled = false;
    const done = (reply: DaemonReply) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      socket.destroy();
      resolve(reply);
    };

    const timer = setTimeout(
      () =>
        done({
          ok: false,
          error:
            `the executor daemon did not answer within ${acceptTimeoutMs}ms at ${SOCKET_PATH}. ` +
            `Nothing was run. Start it with \`launchctl kickstart -k gui/$(id -u)/ai.estate.executor\`, ` +
            `or check \`bin/idp-executor-status\`.`,
        }),
      acceptTimeoutMs,
    );

    const socket = connect(SOCKET_PATH);
    socket.on("connect", () => socket.write(JSON.stringify(payload) + "\n"));
    socket.on("data", (chunk: Buffer) => {
      try {
        done(JSON.parse(chunk.toString("utf-8").trim()) as DaemonReply);
      } catch (err) {
        done({ ok: false, error: `unreadable reply from the daemon: ${String(err)}` });
      }
    });
    socket.on("error", (err: Error) =>
      done({
        ok: false,
        error:
          `the executor daemon is unreachable at ${SOCKET_PATH} (${err.message}). ` +
          `Nothing was run -- this extension never falls back to a local shell.`,
      }),
    );
  });
}

export default function (pi: any) {
  // ---------------------------------------------------------------------------------------------
  // 1. execute_command -- submit a command to the daemon and return the job id at once.
  // ---------------------------------------------------------------------------------------------
  pi.registerTool({
    name: "execute_command",
    label: "Execute Command",
    description:
      "Run a shell command through the executor daemon and return a job id immediately. " +
      "The command runs detached, outside this agent's process tree, under the estate's ceiling. " +
      "This never blocks: it returns a job id in milliseconds and you read the result later with read_job.",
    promptSnippet:
      "execute_command: run a shell command through the executor daemon; returns a job id at once",
    promptGuidelines: [
      "Use execute_command to run any shell command. It returns a job id immediately -- it never waits.",
      "Use read_job with the job id from execute_command to fetch the output, the exit code and the elapsed time.",
      "Never expect execute_command to return output itself: it dispatches, and read_job reads.",
    ],
    parameters: Type.Object({
      command: Type.String({ description: "The shell command to run." }),
      cwd: Type.Optional(
        Type.String({ description: "Working directory. Defaults to the daemon's own." }),
      ),
      ceiling_sec: Type.Optional(
        Type.Number({
          description:
            "Hard ceiling in seconds. The daemon clamps this to its own maximum (60). " +
            "Omit to accept the estate default.",
        }),
      ),
    }),
    async execute(
      _id: string,
      params: { command: string; cwd?: string; ceiling_sec?: number },
    ) {
      const reply = await callDaemon({
        verb: "execute",
        command: params.command,
        cwd: params.cwd,
        ceiling_sec: params.ceiling_sec,
      });

      if (!reply.ok) {
        // A refusal is the correct outcome when the daemon cannot take the job. Say so plainly and
        // name the way back -- never pretend the command ran, and never run it here instead.
        return {
          content: [
            {
              type: "text",
              text:
                reply.refused === true
                  ? `REFUSED by the executor daemon: ${reply.error}`
                  : `The executor daemon could not take this command: ${reply.error}`,
            },
          ],
          isError: true,
        };
      }

      return {
        content: [
          {
            type: "text",
            text:
              `Dispatched. job_id: ${reply.job_id}\n` +
              `ceiling: ${reply.ceiling_sec}s (enforced by the daemon, not by this tool)\n` +
              `Read it with read_job job_id="${reply.job_id}".`,
          },
        ],
      };
    },
  });

  // ---------------------------------------------------------------------------------------------
  // 1b. execute_and_wait -- run a command and return its output in THIS turn.
  //
  // WHY THIS EXISTS (founder, 2026-09-13, in his own words). The door above is correct for a long
  // job and wrong for a short one. An agent calling `echo hi` had to spend one turn submitting and
  // another reading, and an agent that cannot read its own output guesses at it -- which is exactly
  // what this estate's epistemic gate refuses. The founder named the fix: "The server wraps the
  // command in the 60-second timeout, runs it, and returns the stdout/stderr."
  //
  // WHAT IT DOES NOT DO. It does not own a timeout. The bound is the daemon's `CEILING_SEC`, passed
  // straight through -- there is no second copy of the number here (LAW 44). It never falls back to
  // a local shell: an unreachable daemon is a refusal, exactly as above.
  // ---------------------------------------------------------------------------------------------
  pi.registerTool({
    name: "execute_and_wait",
    label: "Execute Command and Wait",
    description:
      "Run a shell command through the executor daemon and return its exit code and output in the " +
      "same turn. Blocks on the daemon only up to the estate's ceiling; on reaching it returns " +
      "state timeout_ceiling_reached with an empty log. Use for anything that finishes quickly; " +
      "use execute_command for long work and read it later.",
    promptSnippet:
      "execute_and_wait: run a shell command and get its exit code and output in this same turn",
    promptGuidelines: [
      "Use execute_and_wait for short commands -- you get the output immediately, with no polling.",
      "Read the returned exit_code before describing the result. Never describe a command's outcome from the command text.",
      "If it returns state timeout_ceiling_reached, the job is still running detached: read it later with read_job.",
    ],
    parameters: Type.Object({
      command: Type.String({ description: "The shell command to run." }),
      cwd: Type.Optional(
        Type.String({ description: "Working directory. Defaults to the daemon's own." }),
      ),
      ceiling_sec: Type.Optional(
        Type.Number({
          description:
            "Hard ceiling in seconds. The daemon clamps this to its own maximum (60). " +
            "Omit to accept the estate default.",
        }),
      ),
    }),
    async execute(
      _id: string,
      params: { command: string; cwd?: string; ceiling_sec?: number },
    ) {
      const reply = await callDaemon(
        {
          verb: "wait",
          command: params.command,
          cwd: params.cwd,
          ceiling_sec: params.ceiling_sec,
        },
        WAIT_TIMEOUT_MARGIN_MS,
      );

      if (!reply.ok) {
        return {
          content: [
            {
              type: "text",
              text:
                reply.refused === true
                  ? `REFUSED by the executor daemon: ${reply.error}`
                  : `The executor daemon could not take this command: ${reply.error}`,
            },
          ],
          isError: true,
        };
      }

      const result = reply.result as
        | { state: string; exit_code: number | null; log: string; job_id: string }
        | undefined;
      if (!result) {
        return {
          content: [{ type: "text", text: "the daemon returned no result for the wait" }],
          isError: true,
        };
      }

      // A timeout is not a failure and must never read as one: the job is still running detached and
      // its output is retrievable. Say which of the two happened, in the daemon's own vocabulary.
      if (result.state === "timeout_ceiling_reached") {
        return {
          content: [
            {
              type: "text",
              text:
                `state: timeout_ceiling_reached\n` +
                `job_id: ${result.job_id}\n` +
                `The command is still running detached. Read it later with read_job job_id="${result.job_id}".`,
            },
          ],
        };
      }

      return {
        content: [
          {
            type: "text",
            text: `exit_code: ${result.exit_code}\n--- output ---\n${result.log}`,
          },
        ],
        isError: result.exit_code !== 0,
      };
    },
  });

  // ---------------------------------------------------------------------------------------------
  // 2. read_job -- one job's state, exit code, elapsed time and output.
  // ---------------------------------------------------------------------------------------------
  pi.registerTool({
    name: "read_job",
    label: "Read Job",
    description:
      "Read one dispatched job: its state, exit code, elapsed seconds and captured output.",
    promptSnippet: "read_job: fetch the state, exit code and output of a dispatched job",
    promptGuidelines: [
      "Use read_job with a job id from execute_command to see whether the command finished and what it printed.",
    ],
    parameters: Type.Object({
      job_id: Type.String({ description: "The job id returned by execute_command." }),
    }),
    async execute(_id: string, params: { job_id: string }) {
      const reply = await callDaemon({ verb: "read", job_id: params.job_id });
      if (!reply.ok) {
        return {
          content: [{ type: "text", text: `Could not read job ${params.job_id}: ${reply.error}` }],
          isError: true,
        };
      }
      return {
        content: [{ type: "text", text: JSON.stringify(reply.result, null, 2) }],
      };
    },
  });

  // ---------------------------------------------------------------------------------------------
  // 3. THE SEVERANCE -- `bash` leaves the agent's tool surface.
  // ---------------------------------------------------------------------------------------------
  pi.on("session_start", async (_event: unknown, ctx: any) => {
    try {
      const all: Array<{ name: string }> = pi.getAllTools?.() ?? [];
      const active: string[] = (pi.getActiveTools?.() ?? []).map((t: any) =>
        typeof t === "string" ? t : t.name,
      );
      const kept = active.filter((name) => !SEVERED_TOOLS.includes(name));
      pi.setActiveTools(kept);

      const removed = active.filter((name) => SEVERED_TOOLS.includes(name));
      if (removed.length > 0) {
        ctx?.ui?.notify?.(
          `executor-door: ${removed.join(", ")} removed. Shell commands now run through the ` +
            `executor daemon (execute_command / read_job), under a ${60}s ceiling owned by the daemon.`,
          "info",
        );
      }
      void all;
    } catch (err) {
      // A guard that crashes is worse than the defect it reports (R38). Report, never throw.
      ctx?.ui?.notify?.(`executor-door could not adjust the tool set: ${String(err)}`, "error");
    }
  });

  // ---------------------------------------------------------------------------------------------
  // 4. Defence in depth: refuse a call to a severed tool even if it is somehow still callable.
  //
  // A tool removed from the active set is not offered to the model. This catches the window where a
  // session's tool list was built before this extension loaded -- which is exactly the live-session
  // case the founder named: "no, all live sessions currently need to be aware."
  // ---------------------------------------------------------------------------------------------
  pi.on("tool_call", async (event: any, ctx: any) => {
    const name = event?.toolName ?? event?.name;
    if (typeof name === "string" && SEVERED_TOOLS.includes(name)) {
      ctx?.ui?.notify?.(
        `executor-door refused a direct ${name} call. Use execute_command instead.`,
        "warning",
      );
      return {
        block: true,
        reason:
          `The ${name} tool is severed on this estate. Run the command through execute_command, ` +
          `which dispatches it to the executor daemon under the estate's 60-second ceiling.`,
      };
    }
    return undefined;
  });
}
