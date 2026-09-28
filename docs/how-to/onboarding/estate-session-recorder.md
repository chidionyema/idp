# Onboarding: estate-session-recorder

## What it is

`bin/estate-session-recorder` reads the claimed-work block at the tail of a
session and emits the durable INVENTORY capsule only for claims that carry
command-run proof. It is slot 5 of the estate's local ops tier (crew#929,
roster in `docs/ops/local-ops-tier-roster.md`) and the R30 knowledge-base
backstop: every session ends with a record of what it built and how, and never
a claim with no probe.

## Why it exists

Sessions repeatedly close with an "INVENTORY" that names files and commands.
The gold standard is that each claim is backed by the artifact itself: the
built file is on disk, the verification names a real probe, the evidence is a
real URL or commit. A recorder that grades those deterministically keeps a fake
"built" or a hand-waved "verified" from ever being recorded as shipped.

## What it needs

Nothing but Python 3 and the checkout whose files the claims name. The default
root is the idp checkout the script lives in; set `ESTATE_SESSION_REPO` to
grade a different checkout's sessions.

## How to use it

- `bin/estate-session-recorder session-end.md` — grade a file of capsule lines.
- `cmd | bin/estate-session-recorder` — grade a block piped on stdin.

## The contract

- A `Built X` claim is kept only when X is a path present under the root.
- A `Verified` / `Evidence` claim is kept only when it names a concrete probe:
  a URL, a 40-char commit SHA, a `path:line`, a real command, or an existing
  file reference. A hand-wave is reported as NOT-PROVEN, never repeated.
- The grading is deterministic and model-free; nothing is fabricated and the
  capsule names exactly what was not evidenced.

Combine it with the local ops tier's batch slot so a session's end is captured
automatically into the durable knowledge base rather than typed by hand.
