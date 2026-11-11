// fleetview-directives: the delivery half of FleetView's steering channel for pi sessions.
//
// WHY THIS EXISTS. The FleetView board can SEE every pi session and its four states, and until
// now it could not touch one: POST /steer returned 422 "pi has no live signal path yet". That
// message was accurate about the code and wrong about the capability -- the mailbox this reads,
// ~/.claude/state/directives/, already exists and already carries real traffic for claude-code
// sessions (verified 2026-09-19: consumed directives from 17-19 Sep). What was missing was a pi
// hook on the receiving end. This is that hook.
//
// THE CONTRACT. FleetView's signals.py writes one JSON file per steer:
//
//   { "session_id": "<repo>:<uuid>", "by": "<who>", "text": "<instruction>", "written_at": "..." }
//
// named "<uuid>.json" in the directives dir. This extension reads the file whose uuid matches
// THIS session, hands the text to the agent as a user message, and renames it `.consumed` so it
// is delivered exactly once -- the same protocol _dispatch_steer_claude_code already honours, so
// one mailbox serves both runtimes and neither needs its own transport (LAW 43).
//
// DELIVERY IS AT A TURN BOUNDARY, NOT MID-INFERENCE. `deliverAs: "steer"` is passed so that if
// the agent is mid-stream the text interrupts it, and "followUp" otherwise -- but a session that
// is blocked inside a provider call cannot see anything until that call returns. That limit is
// real for every runtime in this estate and is documented rather than hidden.
//
// FAIL-OPEN, ALWAYS. If the directory is missing, the file is malformed, or the uuid cannot be
// read from the session, this extension does nothing and the session continues untouched. A
// monitoring tool that can break a working session is worse than one that occasionally misses a
// steer.
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { readFile, readdir, rename, unlink } from "node:fs/promises";
import { execFile } from "node:child_process";
import { join } from "node:path";

const DIRECTIVES_DIR =
  process.env.FLEETVIEW_DIRECTIVES_DIR ??
  join(process.env.HOME ?? "", ".claude", "state", "directives");

/**
 * Where the board lives. The reply channel is a plain HTTP POST, so this is the only configuration
 * the receiving half needs.
 */
const FLEETVIEW_API = process.env.FLEETVIEW_API ?? "http://127.0.0.1:18790";

/**
 * The board's shared key, sent on the two routes that can end a process.
 *
 * `/work` writes the pid that `/kill` signals, so the pair is a destructive capability and the
 * backend refuses them without this header once `FLEETVIEW_BOARD_KEY` is set. A laptop with no
 * vault loaded has no key and the backend does not enforce one, so this is optional here and
 * required in a deployment -- the same shape as the executor relay's key.
 */
const BOARD_KEY = process.env.FLEETVIEW_BOARD_KEY ?? "";

/** Headers for a board write. Empty when no key is configured, which the backend accepts. */
function boardHeaders(): Record<string, string> {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  if (BOARD_KEY) h["X-Board-Key"] = BOARD_KEY;
  return h;
}

/**
 * Report what this session is WORKING ON -- the branch and the current step.
 *
 * WHY. The founder, 2026-09-20: "i dont know what feature they are working on". The board showed
 * `task`, which is the FIRST PROMPT VERBATIM -- frequently a typo or a test ("say OK", "Reply with
 * exactly: PIPELINE-TEST-OK"). The schema had `step`, `ticket` and `capability_class` columns, all
 * null, designed for exactly this and never filled.
 *
 * WHAT IT SENDS, and why each is real rather than inferred:
 *   branch  the git branch of this session's own working directory. On this estate a branch names
 *           the work (`feat/battalion-gov01-local-floor`), so it answers "which feature" exactly
 *           and for free.
 *   step    what the session is doing right now, from the tool it last ran. Editing a file, running
 *           a test, searching -- a verb, not a guess at intent.
 *
 * NOT A SUMMARY OF THE CONVERSATION. Asking a model to describe the work would be slower, cost
 * money, and produce a confident sentence that could be wrong. These two fields are read, not
 * imagined.
 */
async function postWork(
  sessionId: string,
  cwd: string,
  step?: string,
  pid?: number,
): Promise<void> {
  let branch = "";
  try {
    // `execFile`, not `exec`: no shell, so a branch name is data and never a command.
    const r = await new Promise<string>((resolve) => {
      execFile("git", ["-C", cwd, "branch", "--show-current"], { timeout: 4000 }, (err, stdout) =>
        resolve(err ? "" : String(stdout).trim()),
      );
    });
    branch = r.slice(0, 120);
  } catch {
    /* a directory that is not a repo simply has no branch */
  }
  if (!branch && !step && pid === undefined) return;
  try {
    await fetch(`${FLEETVIEW_API}/work`, {
      method: "POST",
      headers: boardHeaders(),
      body: JSON.stringify({
        session_id: sessionId,
        // A CONSTANT, not derived by splitting the id. This extension runs inside pi, so the
        // runtime is `pi` -- and the split produced "unknown" for this very extension (its id is a
        // bare uuid) while producing a REPO for claude-code (`<repo>:<uuid>`). One line, wrong in
        // two directions; a constant cannot be wrong.
        runtime: "pi",
        branch,
        step: (step || "").slice(0, 160),
        // Its OWN field. Sent as `step: "pid 1234"` it survived exactly until the first tool call
        // overwrote the step, so the board could kill a session only in the seconds before it
        // started working.
        pid: typeof pid === "number" ? pid : undefined,
      }),
    });
  } catch {
    /* the board is not listening; the session still is */
  }
}

/** One short verb for a tool call, which is what "step" means to a reader. */
function stepFor(toolName: string, input: any): string {
  const name = String(toolName || "");
  const file = input?.path || input?.file_path || input?.filePath || "";
  const short = file ? String(file).split("/").slice(-1)[0] : "";
  if (name === "edit" || name === "write" || name === "Edit" || name === "Write") {
    return short ? `editing ${short}` : "editing a file";
  }
  if (name === "bash" || name === "Bash") {
    const cmd = String(input?.command || "").split(/\s+/)[0] || "a command";
    return `running ${cmd}`;
  }
  if (name === "read" || name === "Read" || name === "grep" || name === "Grep") {
    return short ? `reading ${short}` : "reading files";
  }
  if (name === "web_search" || name === "researcher") return "researching";
  return name ? `using ${name}` : "working";
}

/**
 * Record what this session says, so the board can hear it.
 *
 * THE OTHER HALF OF THE CONVERSATION. Until this existed, a steer was written, consumed, and then
 * nothing: the board could give an order and could not hear the answer. That is the difference
 * between a command deck and a remote control with no screen.
 *
 * Fail-open and silent. A reply that cannot be posted must never break a session, and must never
 * interrupt one with an error about the monitoring of it -- so the catch is deliberately empty and
 * the caller is not told. The board showing one fewer message is a smaller fault than an agent
 * stopping mid-task to complain about telemetry.
 */
async function postReply(sessionId: string, text: string, inReplyTo?: number): Promise<void> {
  const body = (text || "").trim();
  if (!body) return;
  try {
    const res = await fetch(`${FLEETVIEW_API}/replies`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        // THE RUNTIME IS `pi`, because this file IS the pi extension.
        //
        // It used to be derived by splitting the id on ':', on the theory that every id is
        // `<runtime>:<uuid>`. It is not: this extension's own id is a bare uuid, so that produced
        // "unknown" for every session it ever reported. And for the runtimes where the theory DOES
        // hold, the prefix is a REPO, not a runtime (claude-code ids are `<repo>:<uuid>`) -- so the
        // same line was wrong in two different directions. A constant cannot be wrong.
        runtime: "pi",
        author: "agent",
        text: body.slice(0, 8000),
        in_reply_to: inReplyTo ?? null,
      }),
    });
    void res;
  } catch {
    /* the board is not listening; the session still is */
  }
}

/**
 * The key the board used to name this session's directive file.
 *
 * THIS FUNCTION WAS THE BUG, AND IT MADE THE WHOLE CHANNEL DEAD.
 *
 * It was written to mirror signals.py's `rsplit(':')` -- but the two sides do not agree on what a
 * session id looks like, and the disagreement was invisible because it produced a `null` rather
 * than an error:
 *
 *   the BOARD's id     `pi:01a0bb54-6a2b-7293-abed-a620dbb25113`  (runtime:uuid)
 *   the EXTENSION's id `01a0bb54-6a2b-7293-abed-a620dbb25113`     (bare uuid)
 *
 * `ctx.sessionManager.getSessionId()` returns a BARE UUID. pi enforces
 * `/^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$/` on it (session-manager.js:15), so a colon is
 * IMPOSSIBLE, `lastIndexOf(':')` is always -1, and this returned null for every real session.
 *
 * The consequence was total, and the board reported success throughout: no directive was ever
 * claimed, so no steer was delivered, no stop honoured, no reply posted, no PID reported -- which
 * meant no kill either. Meanwhile `POST /nudge` answered 200 with "queued · delivered at its next
 * turn", because the dispatcher only checked that this FILE existed, not that the id could ever
 * match. The directive files were sitting in the mailbox under exactly the right names.
 *
 * PYTHON'S VERSION WAS ALWAYS RIGHT. `bin/idp-directive-consume`'s `_raw_uuid` returns the whole
 * string when there is no colon. This now does the same: strip a `<prefix>:` when one is present,
 * otherwise use the id as-is. Both shapes work, and neither returns null for a valid id.
 */
function rawUuid(sessionId: string | undefined): string | null {
  if (!sessionId) return null;
  const i = sessionId.lastIndexOf(":");
  const key = i === -1 ? sessionId : sessionId.slice(i + 1);
  return key.trim() || null;
}

interface Directive {
  session_id?: string;
  by?: string;
  text?: string;
  written_at?: string;
}

/**
 * Read and claim this session's directive, if one is waiting.
 *
 * Claims by renaming FIRST, so two concurrent checks cannot both deliver it. If the rename
 * fails the directive is left alone and we return null -- a steer delivered twice is worse
 * than one delivered late.
 */
async function claim(uuid: string): Promise<Directive | null> {
  const file = join(DIRECTIVES_DIR, `${uuid}.json`);
  try {
    const raw = await readFile(file, "utf8");
    const parsed = JSON.parse(raw) as Directive;
    if (!parsed?.text || !parsed.text.trim()) return null;
    await rename(file, `${file}.consumed`);
    return parsed;
  } catch {
    // ENOENT (no directive), bad JSON, or a lost rename race: all mean "nothing to deliver".
    return null;
  }
}

/**
 * Has the board asked this session to stop?
 *
 * A marker file rather than a mailbox message, because a stop must be idempotent and must survive
 * being read twice: `claim()` renames a directive to deliver it ONCE, which is right for a steer
 * and wrong for a stop -- a session that checks twice would miss the second look. The file is left
 * in place and the caller may consult it as often as it likes.
 */
async function stopRequested(sessionId: string | undefined): Promise<boolean> {
  const uuid = rawUuid(sessionId);
  if (!uuid) return false;
  try {
    await readFile(join(DIRECTIVES_DIR, `${uuid}.stop`), "utf8");
    return true;
  } catch {
    return false;
  }
}

/**
 * Disarm the stop marker for this session.
 *
 * Called immediately before `ctx.shutdown()`. Without it the flag stays set for ever and any
 * process that later inherits the same session id stops on its first turn -- which is the worst
 * kind of bug to debug, because the cause is a file written hours earlier and nothing on screen
 * mentions it. Failure is ignored: if the marker cannot be removed the session still stops, which
 * was the request.
 */
async function clearStopRequest(sessionId: string | undefined): Promise<void> {
  const uuid = rawUuid(sessionId);
  if (!uuid) return;
  try {
    await unlink(join(DIRECTIVES_DIR, `${uuid}.stop`));
  } catch {
    /* already gone, or unwritable: the shutdown proceeds either way */
  }
}

/** Deliver any pending directive for this session. */
async function drain(
  pi: ExtensionAPI,
  sessionId: string | undefined,
  idle?: boolean,
): Promise<number> {
  const uuid = rawUuid(sessionId);
  if (!uuid) return 0;

  const d = await claim(uuid);
  if (!d?.text) return 0;

  const who = d.by ? ` from ${d.by}` : "";
  const at = d.written_at ? ` (queued ${d.written_at})` : "";
  const body =
    `[FleetView steer${who}${at}]\n\n` +
    `${d.text.trim()}\n\n` +
    `This is an instruction from the fleet board, not a question. Act on it, then continue ` +
    `your current task.`;

  // `steer` INTERRUPTS a mid-stream turn; `followUp` QUEUES until the agent finishes.
  //
  // The header above has promised this distinction since the file was written and the code always
  // passed "followUp", so a steer never interrupted anything -- a person watching an agent loop
  // could send "stop doing that" and be read only after the loop ended, which on a runaway is
  // never. `isIdle()` is what makes the promise true: it is the runtime's own answer to "is a turn
  // in flight", so the branch is a fact rather than a guess.
  //
  // When idle, `followUp` is still correct -- `steer` on an idle agent is undefined behaviour in
  // most runtimes and can drop the message.
  pi.sendUserMessage(body, { deliverAs: idle === false ? "steer" : "followUp" });
  // ACKNOWLEDGE, so the board can show that the order was HEARD and not merely sent. The steer
  // was accepted with a 200 when it was only written to a file; this is the first moment anything
  // can say the session actually picked it up.
  await postReply(sessionId, `steer received: ${d.text.trim().slice(0, 300)}`);
  return 1;
}

export default function (pi: ExtensionAPI) {
  let warned = false;

  // THE STEP, AS IT CHANGES. `tool_execution_start` fires before the tool runs, so the board
  // shows "editing FleetReactorApp.tsx" while the edit is happening rather than after it -- which
  // is what "what is it doing right now" actually means.
  //
  // Only a verb and a filename: a tool INPUT can contain a whole file's contents, a token, or a
  // command line, and none of that belongs on a screen someone else may be looking at.
  pi.on("tool_execution_start", async (event, ctx) => {
    try {
      const e = event as any;
      void postWork(ctx.sessionManager.getSessionId(), ctx.cwd, stepFor(e?.toolName, e?.input));
    } catch {
      /* fail open — telemetry must never break a tool call */
    }
  });

  // Session start: the primary delivery point, and where a steer sent while the session was
  // down finally lands. `ctx.ui` and `ctx.sessionManager` are non-optional on ExtensionContext
  // (types.d.ts:209), so neither is guarded -- absent UI is a mode, not a missing object, and
  // `notify` is a no-op in the modes that have none.
  pi.on("session_start", async (_event, ctx) => {
    // ONE CALL, NOT TWO. This was `postWork(..., "starting")` followed immediately by
    // `postWork(..., "starting", process.pid)` -- two `git branch` subprocesses and two HTTP posts
    // for a single fact. The second is a superset of the first (same branch, same step, plus the
    // pid), so the first was pure duplication.
    //
    // Report the branch the moment the session opens, so the board knows which feature this is
    // before the agent has done anything, and the PID so "kill this session" has something to
    // kill. The step follows on the first tool call.
    void postWork(ctx.sessionManager.getSessionId(), ctx.cwd, "starting", process.pid);
    try {
      const n = await drain(pi, ctx.sessionManager.getSessionId(), ctx.isIdle());
      if (n) ctx.ui.notify("FleetView: steer received", "info");
    } catch (e) {
      if (!warned) {
        warned = true;
        ctx.ui.notify(`FleetView directives: ${(e as Error).message}`, "warning");
      }
    }
  });

  // Turn boundary: makes a long-running session responsive without a timer in the agent loop.
  // The design forbids "a 50ms polling interrupt in every agent loop", and this is not one --
  // it is one `stat` against a directory the estate already reads, at a point where the agent
  // was going to pause anyway.
  pi.on("turn_start", async (_event, ctx) => {
    // A STOP REQUEST IS HONOURED HERE, at the boundary the session was going to pause at anyway.
    //
    // WHY NOT SIGKILL. The board could in principle kill the process outright once the extension
    // reports its PID -- but that discards whatever the agent had in flight and leaves a session
    // file that ended mid-tool-call. `ctx.shutdown()` is the runtime's own graceful exit: it runs
    // the shutdown hooks, so `session_shutdown` fires and the session closes cleanly.
    //
    // This is also the ONLY stop that can work for an agent that is busy. A wedged session does not
    // read its mailbox, which is why `POST /stop` writing a directive was never enough: the
    // directive is read on the next turn, and there is no next turn. `turn_start` is where a
    // running session is reachable, and `shutdown()` acts immediately once reached.
    // RE-REPORT THE PID EVERY TURN, so a session that started before this feature existed still
    // becomes killable, and so a restarted process corrects the record rather than leaving a stale
    // pid that would SIGTERM whatever inherited the number.
    void postWork(ctx.sessionManager.getSessionId(), ctx.cwd, undefined, process.pid);

    if (await stopRequested(ctx.sessionManager.getSessionId())) {
      ctx.ui.notify("FleetView: stop requested by the board", "warning");
      await postReply(ctx.sessionManager.getSessionId(), "stopping — stop requested by the board");
      // THE MARKER IS REMOVED BEFORE SHUTTING DOWN.
      //
      // A `.stop` file is a flag the loop checks at every turn boundary, and nothing deleted it --
      // so the flag stayed true for ever. A session restarted with the same id (a resume, a
      // worktree reuse, a test harness) would shut itself down on its FIRST turn, having been
      // stopped by a request from hours earlier. `ctx.shutdown()` is called after the unlink so a
      // shutdown that does not complete cannot leave the flag armed behind it.
      await clearStopRequest(ctx.sessionManager.getSessionId());
      try {
        ctx.shutdown();
      } catch {
        /* a mode without shutdown still got the reply, which is the record */
      }
      return;
    }
    try {
      // `isIdle()` here reads false whenever the agent is mid-turn, which is exactly the case a
      // steer must interrupt rather than queue behind.
      await drain(pi, ctx.sessionManager.getSessionId(), ctx.isIdle());
    } catch {
      // fail open; session_start already warned once
    }
  });

  // A VISIBLE WAY TO CHECK THE CHANNEL, and the manual half of the reply channel: whatever the
  // person types here is posted to the board as this session. It is how the reply path is proved
  // end to end without waiting for an agent to happen to speak.
  pi.registerCommand("fleetview-say", {
    description: "Post a message from this session to the FleetView board",
    handler: async (args, ctx) => {
      const sid = ctx.sessionManager.getSessionId();
      const text = (args || "").trim();
      if (!text) {
        ctx.ui.notify("usage: /fleetview-say <message>", "warning");
        return;
      }
      await postReply(sid, text);
      ctx.ui.notify("posted to the fleet board", "info");
    },
  });

  // THE SESSION'S OWN VOICE, WITHOUT ASKING IT TO COOPERATE.
  //
  // Every time the agent finishes a turn, its last assistant text is posted as a reply. That is
  // what makes the board two-way for a session that has not been taught any new behaviour: the
  // most recent thing it said is exactly what a person watching would want to hear, and it needs
  // no prompt engineering on the agent's side.
  //
  // Only assistant TEXT, never tool arguments or raw events -- a reply is shown to a human and
  // must not leak a command line, a token or a file path out of a tool call.
  pi.on("turn_end", async (event, ctx) => {
    try {
      const msg = (event as any)?.message;
      if (!msg || msg.role !== "assistant") return;
      const parts = Array.isArray(msg.content) ? msg.content : [];
      const text = parts
        .filter((p: any) => p?.type === "text" && typeof p.text === "string")
        .map((p: any) => p.text)
        .join(" ")
        .trim();
      if (!text) return;
      await postReply(ctx.sessionManager.getSessionId(), text.slice(0, 2000));
    } catch {
      /* fail open — see postReply */
    }
  });

  // A visible way to check the channel from inside a session, and to prove it in a demo.
  pi.registerCommand("fleetview-status", {
    description: "Show whether the FleetView steering mailbox is present and readable",
    handler: async (_args, ctx) => {
      const uuid = rawUuid(ctx.sessionManager.getSessionId());
      let files: string[] = [];
      try {
        files = (await readdir(DIRECTIVES_DIR)).filter((f) => f.endsWith(".json"));
      } catch {
        files = [];
      }
      const mine = uuid ? files.includes(`${uuid}.json`) : false;
      ctx.ui.notify(
        `FleetView: dir=${DIRECTIVES_DIR} waiting=${files.length} mine=${mine ? "YES" : "no"}`,
        "info",
      );
    },
  });
}
