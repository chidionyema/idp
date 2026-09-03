# Phone idea flow: continuity, hermes-v2 ingress, confirmation gate

Written by pm-agent on 2026-08-24 from a conversation with the founder. Tracked
at `chidionyema/crew` issue [#182](https://github.com/chidionyema/crew/issues/182).

## The founder's ask, in his own words (tidied)

He asked a different assistant (MiniMax) about a scenario and it misunderstood
him. The scenario:

> "what if I'm already deep in a session on the laptop and I quickly need to
> rush out and take my phone; there is a currently active session, then I
> think of an idea and I talk to my Hermes agent — what happens?"

Then a second, separate case:

> "what if I just want to explore an idea"

And the one hard rule that governs both:

> "I need it to confirm to me if I want it on the board. That's a simple
> solve."

## What the MiniMax answer got wrong

MiniMax named components this estate does not run. Every requirement below is
restated against the real component:

| MiniMax said | This estate actually has |
|---|---|
| Aider drives the laptop sessions | Claude Code sessions, launched from the crew CLI or by hand |
| "Foreman" dispatches queued work | `maestro` at `~/dev/code/maestro` — see "Measured state" below for what it actually does today |
| Plane.so holds the board | Kanboard (`idp/board`, SQLite) plus GitHub issues/PRs in `chidionyema/crew`, per the standing founder ruling that nothing generated may live only in vendor tooling |

## Measured state, 2026-08-24 — do not re-measure without a fresh command

**The board's real columns** (`idp/board/data/db.sqlite`, project `Estate`,
queried read-only):

```
1  1. Observed - agents write
2  2. Proposed - agents write
3  3. LIVE / CORE - founder only
4  4. Graveyard
```

There is no "To Do", "Icebox" or "Backlog" column today. R6's Icebox and R7's
watched column are both new columns this flow needs, not columns that already
exist. 25 tasks are currently on the board, all in columns 1 and 2.

**`maestro` does not watch the board or create worktrees.** `maestro.py`
(2,239 lines, `~/dev/code/maestro`) is a Sense/Think/Act reliability agent —
an experience graph, seven laws, failure-shape extraction, skill execution,
one Telegram bridge for its own alerts. Nothing in it reads `idp/board`,
`kanboard`, or calls `git worktree`. It runs under launchd
(`~/Library/LaunchAgents/com.chidionyema.maestro.plist`) via
`~/dev/code/maestro/bin/maestro-run`. Calling it "the local dispatcher" in
R7's sense — watches a column, creates a worktree and branch, starts a
session — describes work this repo does not have a component for yet.

**`hermes-v2` already has its own kanban system, separate from `idp/board`.**
`hermes-agent/AGENTS.md` documents a durable SQLite-backed board
(`hermes kanban <verb>` CLI, `tools/kanban_tools.py` for worker profiles, a
dispatcher loop that reclaims stale claims and spawns profiles, running
inside the gateway by default via `kanban.dispatch_in_gateway: true`). This
is a second, independent board and dispatcher living inside the messaging
agent, not the same store as `idp/board`. R3's "reads the board" and R11's
"persisted in the platform" both need to name `idp/board` specifically, or
hermes-v2's own kanban system satisfies the letter of the requirement while
leaving two boards that disagree.

**No MCP server exists for `idp/board` or `catalog/estate.db`** (confirmed
against `docs/specs/fortress-stack.md` CP5, still open). R3 and R7 below
specify MCP as the read/write surface hermes-v2 uses; today that surface does
not exist and is being built under `chidionyema/crew#180` CP5. This spec's
checkpoints for R3 and R7 are blocked on that landing, not duplicating it.

**hermes-v2's gateway supports Telegram already** (`hermes-agent/AGENTS.md`,
`gateway/platforms/` has a `telegram` adapter among ~20). The gateway itself
is provider-agnostic per that same directory structure — R12 is a property
this component already has, not new work.

**`git branch -a` in `idp` shows a `worktree-agent-<hash>` branch** with no
script in `crew` or `maestro` that produced it — confirming no dispatcher in
this estate currently creates worktree branches from board state; whatever
made that branch did so by another path.

## Where this lives, and where it does not

Per `~/AGENTS.md` headline: one platform. `idp/board` (Kanboard) and GitHub
issues/PRs in `chidionyema/crew` are the two sources of truth this flow reads
and writes — never Telegram chat history alone (R11). `hermes-v2` is the
phone-facing product; its own internal kanban system is not extended to cover
this flow, because that would be a second board next to `idp/board`, which is
exactly the stitching the headline forbids. Any board-write hermes-v2 performs
for this flow targets `idp/board`.

## Checkpoints

### CP1 — R1 continuity: the active laptop session is never touched

The founder's rule: leaving the laptop mid-session must not interrupt it.

**Requirement:** an active Claude Code session on the laptop keeps running
after he leaves. When the work finishes, it commits on its own branch, opens
a PR, and stops. The board card tracking that work reflects the PR. No
message or file originating from the phone flow is ever injected into that
session's context, transcript or working tree.

**Done when:** a session started before he leaves is still running (or has
completed with a PR) after a phone message is sent to hermes-v2 during the
same window, and `git log` on the session's branch shows no commit touching
files the phone flow drafted.

### CP2 — R2 phone ingress: hermes-v2 never touches the active session

**Requirement:** he can message hermes-v2 on Telegram from anywhere. Handling
that message never reads from, writes to, or shares a process with the active
laptop session.

**Done when:** the active session's PID and hermes-v2's gateway PID are
distinct processes with no shared session file, and the active session's
transcript contains zero lines originating from the Telegram message.

### CP3 — R3 pre-flight dedup before drafting

**Requirement:** before hermes-v2 drafts anything, it reads `idp/board` (all
open columns, not just one), the estate's active branches and worktrees, and
open PRs — read-only, via MCP tools once `crew#180` CP5 lands. If a match
exists, it replies naming the card or branch and asks whether to update that
one or leave it, rather than drafting a duplicate.

**Done when:** given a phone idea whose subject already has an open card or
branch, hermes-v2's reply names that card or branch by ID before offering any
new draft.

### CP4 — R4 mode detection: exploring vs. building

**Requirement:** phrasing like "what if", "brainstorm", or "I'm just
exploring" puts hermes-v2 in sounding-board mode — discussion only, may read
estate state via MCP, creates zero cards and writes zero code. Phrasing like
"build this" or "write a spec" puts it in PM mode, which drafts a BDD feature
file.

**Done when:** the same estate state, given exploratory phrasing, produces no
card and no file; given build phrasing, produces a feature-file draft — shown
to him, not yet written to disk (CP5 gates that).

### CP5 — R5 confirmation gate: hermes-v2 never writes to the board alone

The founder's explicit ask, verbatim: "I need it to confirm to me if I want it
on the board. That's a simple solve."

**Requirement:** hermes-v2 never creates or moves a board card on its own
initiative. It shows the draft (feature file or RFC) in the Telegram chat and
asks for a destination with one-tap inline buttons: To Do / Icebox / Drop.
Only after he taps one does it call the board-write tool, and only with the
column he chose.

**Done when:** a drafted idea produces zero board writes until an inline
button is tapped, and the column written matches the button tapped, for all
three buttons.

### CP6 — R6 icebox: exploratory ideas are kept without entering the queue

**Requirement:** an idea he wants to keep but not build now goes to an
Icebox/Backlog column, as a Markdown RFC. The dispatcher that watches for new
work never reads that column.

**Done when:** a card lands in Icebox and, across a full dispatcher poll
cycle, is never claimed, worktreed, or started.

### CP7 — R7 dispatch: the watched column starts work, or waits

**Requirement:** when the laptop is awake, a new card in the watched column
("To Do") is picked up, gets an isolated git worktree and branch, and starts
a separate agent session. When the laptop is asleep, the card waits in that
column; nothing is lost or silently dropped.

**Done when:** a card placed in "To Do" while the laptop is awake results in
a new worktree, branch and running session within one poll cycle; a card
placed while asleep is still present, unclaimed, and starts within one poll
cycle of the laptop waking.

### CP8 — R8 welcome back: no conflicts between the two branches

**Requirement:** on his return, the original laptop session is exactly where
he left it. The phone idea is either a PR or an in-progress card. Both are
visible on the board. The two branches do not conflict.

**Done when:** after both sessions run concurrently, `git worktree list`
shows two distinct worktrees on two distinct branches with no merge conflict
between them, and the board shows both cards in a state that matches each
branch's actual state.

### CP9 — R9 later activation: turning an Icebox idea into work

**Requirement:** "remember that idea, let's do it" reads the Icebox RFC, turns
it into a feature file, and moves the card to "To Do" — gated by CP5's
confirmation exactly as a fresh idea would be.

**Done when:** referencing a specific Icebox card by name produces a feature
file drafted from that RFC's content, and the card only moves to "To Do"
after the same inline-button confirmation as CP5.

### CP10 — R10 urgency: open decision, default recorded

**Open question, not yet answered by the founder:** whether a "drop
everything" bug report from the phone may interrupt the active laptop
session.

**Requirement, until he rules otherwise:** the default is never to interrupt.
A phone message marked urgent is still gated by CP5 and CP3 like any other; it
may jump the board's priority ordering once queued, but it never injects into,
pauses, or redirects a session already running (CP1).

**Done when:** an urgent phone message during an active session produces no
change to that session's process, transcript or branch — identical evidence
to CP1 — and the resulting card, once confirmed, is flagged urgent on the
board.

### CP11 — R11 persistence: platform, not vendor chat

Standing founder ruling: nothing generated may live only in a vendor's chat
history.

**Requirement:** every draft, RFC, card and decision this flow produces is
written to `idp/board`'s SQLite (itself under git in `idp/board/data/`) or a
GitHub issue/PR in `chidionyema/crew`. Telegram history is a transport, never
the record.

**Done when:** for every draft this flow produces, a corresponding row exists
in `idp/board`'s database or a GitHub issue/PR, and deleting the Telegram
conversation loses no information a session or the founder needs.

### CP12 — R12 provider agnostic (LAW 34)

**Requirement:** the model hermes-v2 uses and the Telegram transport are both
swappable without changing this flow's logic — mode detection, the dedup
check, and the confirmation gate are not written against one vendor's API
shape.

**Done when:** `hermes-agent/gateway/platforms/` carries the adapter
interface this flow's ingress uses, and the flow's mode-detection and
confirmation-gate code carries no import naming one model provider or one
messaging vendor directly.
