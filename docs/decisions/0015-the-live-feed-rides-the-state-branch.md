# The live feed rides the state branch

Date: 2026-09-01

## Status

Accepted.

## Context

Every working session writes a short handoff to a shared feed every fifteen
minutes. That feed lived only on one machine. The portal's live diagram is
published from a branch that holds generated state, but the feed never reached
it, so a person reading the portal could not see what the sessions were doing
or hand work between machines.

## Decision

The published state now carries the feed. The publishing step renders the last
two days of handoffs, removes anything secret, and writes the result next to
the live diagram. The page that renders the catalogue picks the feed up from
there, so the portal shows it like everything else. A test proves the rendered
page carries the published feed.

## Consequences

The feed survives any one machine. A person reads the portal and sees the last
two days of handoffs without opening a terminal. If publishing breaks, the
test and the page go stale visibly instead of silently.
