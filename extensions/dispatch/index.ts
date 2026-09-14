/**
 * dispatch_job -- an agent submits work and its turn ENDS. It has no way to wait.
 *
 * WHY THIS EXISTS. Measured 2026-09-13: a session held 1,727,322 tokens across 7,594 messages
 * and re-sent its whole history on every turn -- 177,570 tokens per call, 56 calls in six
 * minutes, one key, $12.46 of a $15.00 budget. Every one of those calls happened because a turn
 * was still open. A turn that cannot stay open cannot spend.
 *
 * THE MECHANISM IS THE POINT, and it is not discipline. `bash` can be told not to block and an
 * agent can ignore the telling. This tool has NO WAIT PATH in its signature: it starts a detached
 * process, writes a record, and returns. There is no `poll`, no `wait`, no `status` argument and
 * no blocking read -- not because those are discouraged, but because they are not implemented.
 * The agent's turn ends the moment it gets the id back.
 *
 * WHAT THE AGENT GETS: a job id and a URL. What it gets later: an event, if it subscribed. It
 * never gets a spinning turn.
 *
 * OBSERVABILITY IS OUT OF BAND. State goes to a JSONL ledger the Backstage job entity reads, and
 * the console output goes to a log file named by the id. Neither is returned inline, so a long
 * job cannot grow the conversation's context -- which is the failure this whole change targets.
 *
 * IT REUSES ~/.pi/agent/bin/run, THE DISPATCHER THAT ALREADY EXISTS. That helper starts work
 * detached with nohup and returns in milliseconds; it is on PATH in every session. Writing a
 * second dispatcher would be two ways to start a job, which is the stitching this estate deletes.
 *
 * READ-ONLY WITH RESPECT TO THE ESTATE. It writes under ~/.estate/dispatch/ and starts a local
 * process. It never touches the cluster, never mints a credential, and never merges anything --
 * a dispatched job may do those things on its own authority, which is exactly the boundary that
 * keeps this tool from being a new hole.
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "typebox";
import { spawn } from "node:child_process";
import { appendFileSync, mkdirSync, existsSync, readFileSync, readdirSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const HOME = homedir();
const ROOT = join(HOME, ".estate", "dispatch");
const LEDGER = join(ROOT, "jobs.jsonl");
const RUN = join(HOME, ".pi", "agent", "bin", "run");

/** A name safe to put in a filename: it reaches the log path and the ledger. */
function slug(name: string): string {
  return name.replace(/[^a-zA-Z0-9._-]/g, "-").slice(0, 64) || "job";
}

/** One id per submission. Time-ordered so a directory listing reads as a history. */
function mintId(name: string): string {
  const now = new Date();
  const stamp = now.toISOString().replace(/[-:]/g, "").replace(/\..+/, "Z");
  return `${stamp}-${slug(name)}`;
}

type JobRecord = {
  id: string;
  task: string;
  command: string;
  cwd: string;
  at: string;
  log: string;
  pid?: number;
};

function record(job: JobRecord): void {
  mkdirSync(ROOT, { recursive: true });
  appendFileSync(LEDGER, `${JSON.stringify(job)}\n`, "utf8");
}

export default function (pi: ExtensionAPI) {
  mkdirSync(ROOT, { recursive: true });

  /**
   * Submit work. Returns an id. There is deliberately no second call to await it.
   */
  pi.registerTool({
    name: "dispatch_job",
    label: "Dispatch job",
    description:
      "Start work in the background and return immediately with a job id. Use this for anything " +
      "that takes more than a moment: a build, a test suite, a merge, a rollout, a long query. " +
      "The job runs detached and its output goes to a log file; its state lands in the dispatch " +
      "ledger the Backstage jobs page reads. This tool CANNOT wait for the job -- there is no " +
      "status or wait mode. If you need the result, dispatch it and read the log on a later turn.",
    parameters: Type.Object({
      task: Type.String({
        description: "One sentence, plain English: what this job does. Shown on the jobs page.",
      }),
      command: Type.String({
        description:
          "The shell command to run. It is executed with `bash -lc` in the given directory.",
      }),
      cwd: Type.Optional(
        Type.String({ description: "Working directory. Defaults to the current one." }),
      ),
    }),
    async execute(_id, params, _signal, _onUpdate, ctx) {
      const cwd = params.cwd ?? process.cwd();
      const name = mintId(params.task.slice(0, 40));
      // `run` writes the log itself, at ~/.estate/runs/<name>.log. Reading its layout instead of
      // inventing a path is what makes `dispatch_result` find the output: the first version
      // recorded a path under ~/.estate/dispatch/ that nothing ever wrote to.
      const log = join(HOME, ".estate", "runs", `${name}.log`);
      const job: JobRecord = {
        id: name,
        task: params.task,
        command: params.command,
        cwd,
        at: new Date().toISOString(),
        log,
      };

      if (!existsSync(RUN)) {
        // A tool that cannot dispatch must say so, never pretend it did. The alternative is an
        // agent that reports "dispatched" about a job that never started.
        return {
          content: [
            {
              type: "text",
              text:
                `dispatch_job cannot start anything: ${RUN} does not exist.\n\n` +
                `That helper is the estate's one detached runner (it uses nohup and returns in ` +
                `milliseconds). Without it this tool has no way to start work, and it will not ` +
                `run the command inline -- doing that is what this tool exists to prevent.`,
            },
          ],
        };
      }

      // `run` ends in `nohup "$@"`, so it EXECUTES the arguments directly -- there is no `sh -c`
      // in it. Passing the command as one string made nohup try to execute the whole command line
      // as a binary name:
      //   nohup: printf "...": No such file or directory
      // Caught by reading the log after dispatching a trivial job. The ledger row is written even
      // when the job fails to start, so the ledger alone would have shown a fine-looking job that
      // never ran -- which is the exact failure mode this estate keeps hitting.
      // `bash -lc <command>` is the one argv word that makes a caller's shell string work.
      const child = spawn(RUN, [name, "bash", "-lc", params.command], {
        cwd,
        detached: true,
        stdio: "ignore",
        env: { ...process.env, PI_DISPATCH_ID: name },
      });
      child.unref();
      job.pid = child.pid;
      record(job);

      // The Backstage entity is generated from the ledger by bin/idp-jobs-page, so the link is
      // stable and the page reads the same file this line wrote.
      //
      // THE ZONE IS READ, NEVER TYPED (LAW 46; bin/estate-zone-gate refused this line, and it was
      // right). A hostname written into a source file is a second copy of a value the estate
      // declares once in clusters/<cluster>/estate-config.yaml, and two copies drift. The portal
      // origin comes from the environment the way every other module reads it, and when it is
      // unset the job still dispatches -- the link is a convenience, the work is not.
      const portal = (process.env.IDP_PORTAL_URL ?? "").replace(/\/$/, "");
      const url = portal
        ? `${portal}/catalog/default/component/dispatched-jobs`
        : "the jobs page (IDP_PORTAL_URL is unset)";

      return {
        content: [
          {
            type: "text",
            text:
              `Dispatched: ${name}\n` +
              `Task:      ${params.task}\n` +
              `Log:       ${log}\n` +
              `State:     ${url}\n\n` +
              `This tool cannot report when it finishes, by design. Your turn ends here. ` +
              `The job's exit and output land in the log above and on the jobs page.`,
          },
        ],
      };
    },
  });

  /**
   * A read-only view for an agent that genuinely needs to know how something ended. It reads the
   * log file, never the running process, so it cannot block on a job that is still going.
   */
  pi.registerTool({
    name: "dispatch_result",
    label: "Dispatch result",
    description:
      "Read the recorded outcome of a dispatched job: its exit reason if it has finished, or the " +
      "last lines so far if it has not. Never waits -- it reads what is on disk and returns.",
    parameters: Type.Object({
      id: Type.String({ description: "The job id returned by dispatch_job." }),
      tail: Type.Optional(
        Type.Number({ description: "How many trailing log lines to show. Default 20." }),
      ),
    }),
    async execute(_id, params, _signal, _onUpdate, _ctx) {
      const log = join(homedir(), ".estate", "runs", `${slug(params.id)}.log`);
      if (!existsSync(log)) {
        // List what does exist rather than only saying no: the id may be a typo or from another
        // session, and both are settled faster by showing the ids that are real.
        const known = existsSync(ROOT)
          ? readdirSync(ROOT)
              .filter((f) => f.endsWith(".log"))
              .slice(-10)
          : [];
        return {
          content: [
            {
              type: "text",
              text: `No log for ${params.id}. Known jobs:\n${known.join("\n") || "(none)"}`,
            },
          ],
        };
      }
      const lines = readFileSync(log, "utf8").split("\n").filter(Boolean);
      const n = params.tail ?? 20;
      const shown = lines.slice(-n).join("\n");
      // `run` records the pid at <name>.pid and removes it is not its contract, so a live
      // pid is what "running" means here. The marker file this first looked for is not a
      // thing `run` writes, so it reported every job finished.
      const pidFile = join(homedir(), ".estate", "runs", `${slug(params.id)}.pid`);
      let running = false;
      if (existsSync(pidFile)) {
        const pid = Number(readFileSync(pidFile, "utf8").trim());
        try {
          process.kill(pid, 0);
          running = true;
        } catch {
          running = false;
        }
      }
      return {
        content: [
          {
            type: "text",
            text: `${params.id}: ${running ? "still running" : "finished"}\n\n${shown}`,
          },
        ],
      };
    },
  });
}
