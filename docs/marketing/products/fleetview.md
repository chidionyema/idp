# FleetView

**One screen for every AI agent you run.**

## The problem

Companies adopting AI coding agents lose sight of them within a week. Sessions run on laptops,
in CI, in chat bots and in schedulers; each has its own log, its own cost line and its own way
of asking a person for help. Nobody can answer "what are our agents doing right now, and what
is it costing us?" without opening five tools.

## What you get

- A live board of every agent session across every runtime, on your portal, on any device.
- Each session tied to its pull request, its trace, its spend and its ticket.
- Stop, approve, deny or steer any session from the page; every press leaves an audit row.
- Alerts that name the session and the one button that fixes it. No terminal, ever.
- Thirty days of history with replay, scoped per tenant.

## How it works

Two Backstage plugins: a backend that turns every runtime into one session record, and a
frontend that draws the board and a card on every agent in your catalogue. The record is one
versioned JSON schema; a runtime we do not ship an adapter for needs one adapter, written
against that schema.

## Why us

We run our own engineering on ten concurrent AI agents and one human. FleetView is the screen
we built to survive that. Every claim on this page is graded by a drill in CI, not a demo script.

## Pricing

Standalone, up to ten agent runtimes: $24,000 a year. Included in the Enterprise plan.

## Status

In development; two-week delivery plan in
`docs/specs/2026-09-08-fleetview-backstage-offering.md`.

## How to start

Open your portal at `/fleet`. If it is not there yet, ask us for the preview tenant.
