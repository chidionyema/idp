# The fleet interface: what it must become

Founder, 2026-09-18: *"jaw dropping and spectacular UI and UX, bleeding edge research, I'm not
accepting anything less than bleeding edge best in the world."*

This is the design, grounded in a council of three independent frontier models asked the same
question, and in what the running board actually shows.

## What the council converged on (three models, no coordination)

| decision | converged | why it matters |
|---|---|---|
| **Not cards, not a table — a spatial model** | 3/3 | "tables and cards force serial reading. A fleet of 30 agents cannot be read; it must be SEEN" |
| **Latent state is FOUR states, distinguished by MOTION** | 3/3 | collapsing them into one green dot "destroys the distinction" |
| **Voice must be addressed, confirmed, and show its target** | 3/3 | an unaddressed fleet mutation is a footgun |
| **Cost is a RATE, never a number wall** | 3/3 | "the CEO reads velocity of spend, not spend" |
| **Worst mistake: uniform "running" state** | 3/3 | the interface's whole value is discriminating the four |

## The core idea: motion carries meaning

Named by one model, endorsed by the other two. An agent that has not emitted for ten minutes is
not one thing — it is four — and each looks *physically* different:

| state | signal | the tell |
|---|---|---|
| **thinking** (long inference, no tokens yet) | slow 4s inhale/exhale, ring stays lit | it is *breathing* |
| **waiting** (CI, API, human) | ring goes **dashed**, node **drifts** 2px/s toward its dependency | **the drift is the tell** |
| **stuck** (retry loop, no progress) | ring desaturates, node **jitters** at 8Hz | jitter is caught pre-attentively |
| **finished** | breathing stops, ring closes solid, node **sinks** 8px and desaturates | sinking is terminal |

> **Never a spinner.** A spinner means "working" and destroys the distinction.

This is readable at three metres, which is the only test that matters for a person who is not
staring at the screen.

## What the running board shows today, against that standard

Measured in a browser, 2026-09-18, on /fleet:

    4 states, 4 signals?  2 distinct colours
    RUNNING   green  rgb(34,197,94)   pulses
    PAUSED    amber  rgb(245,158,11)  static
    thinking / waiting / stuck / finished   -- DO NOT EXIST

**22 of 23 agents render identically: an amber dot, no motion.** And an agent stuck in a retry
loop is labelled `running`, which is the single worst mistake all three models named.

## The other two decisions the council made

**Layout: position is fixed, only content changes.** From ATC strip boards — a controller scans
40 strips in two seconds *because position never moves*. The board should carry a single-line
fleet ticker (`12 running · 3 blocked · 1 needs you · $4.20/min`), and the CEO's eye should land
on **shape anomalies**, not read.

**Cost: one burn bar, whose LEADING EDGE GLOW WIDTH is the rate.** A fast-burning month has a hot
edge; a slow one is dim. Hover a node and its perimeter tints with its share. No dollar figure
anywhere except on tap. Peripheral vision reads motion and colour before foveal attention.

## What the API gives us, and what it must give us

Today, per session:

    session_id, runtime, task, state, repo, updated_at, spend_usd,
    trace_url, pull_requests, ticket, capability_class, capabilities

**Missing for the four states:** there is no `last_event_kind`, no `waiting_on`, no
`retry_count`, no `progress_at`. `state` + `updated_at` cannot tell *thinking* from *waiting*
from *stuck* — which is exactly why the board shows one amber dot.

So this is not a CSS job. The states must be **derived** from evidence the estate already
records (the prompt-ledger, `session_events`, tool-call rows) and the API must carry them.

## Build order

1. **Derive the four states server-side** from `session_events` + tool rows, and carry
   `activity` on each session. Without this the UI cannot be honest.
2. **The node, not the card.** One motion primitive per state, built from CSS so it is cheap at
   23 nodes and works at a glance.
3. **The fleet ticker** — fixed-position scan line.
4. **The burn bar** with a rate-driven edge.
5. **Voice** — the pipeline is specified separately
   (`docs/specs/2026-09-18-voice-conversation-pipeline.md`); the interface must show the
   **addressed target highlighted live while the CEO speaks**, and render parsed intent as a
   cancellable chip, not prose.

## The line this does not cross

Every motion signal must come from **measured evidence**. A node that jitters because it is stuck
must be jittering because a retry count is real; a node that drifts must be drifting toward a
`waiting_on` that was read. Inventing motion to look alive is the same offence as inventing a
green dot, and it is worse, because it is harder to notice.
