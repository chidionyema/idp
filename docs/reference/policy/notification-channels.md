# Notification channels: who hears what, where

Founder, 2026-08-30: "the issue is I get everything in one channel — alerts, noise, requests for
the founder, 'send this' — so it's hard to locate information", and "use Slack for alerts and keep
Telegram for founder-useful things". Tracked as crew#682. This page is the policy; the Flux
providers, Alertmanager receivers and the send guard are its implementation.

## The rule in one line

**Messages are routed by kind, not by whoever wrote them. Machines talk in Slack. Telegram carries
only what needs the founder, split into three threads. Everything else goes on the board.**

## Routing table

| Kind | Example | Surface | Who reads it |
|---|---|---|---|
| P1 page | a routed surface is down; a P1 drill is red | Telegram `P1 page` **and** Slack `#alerts-p1` | founder, on-call session |
| Founder action | `FOUNDER ACTION:` with the exact URL or word; `APPROVE:` / `DENY:` questions | Telegram `Founder action` | founder |
| Receipt | one line: what he asked for is done, with the link | Telegram `Receipts` | founder |
| Machine alert, P2 | Flux reconcile failed, Alertmanager rule fired, drill red, CI red on main | Slack `#alerts-p2` | sessions |
| Machine noise | reconcile recovered, image updated, scheduled run green | Slack `#alerts-noise` | nobody, it is searchable |
| Lane traffic | CI results, drill results | Slack `#ci`, `#drills` | sessions |
| Session-to-session, status, questions between agents | anything not in the rows above | the board (crew issues, `~/.estate/feed.md`) | sessions |

## What is refused

- A Telegram send that names no kind, or a kind that does not belong on that thread.
- A Flux `Alert` or Alertmanager receiver that routes anything below P1 to the Telegram provider.
- A session writing prose, options or a status paragraph to any Telegram thread.

The guard has the same shape as the one idp#732 added after 1,743 bot messages reached the founder's
private chat in 48 hours: the bad input is removed from the route, not filtered after the fact.

## Credentials

One Slack root (bot token) and one Telegram root, each set once and named in the secret store
(R52); channels and threads are created by code, never by a console click.

## Status

| Checkpoint | State |
|---|---|
| CP0 kinds and threads defined | this page |
| CP1 Slack root and channels | open |
| CP2 Flux Provider and Alertmanager receiver, proved in staging | open |
| CP3 guard: below-P1 never reaches Telegram | open |
| CP4 runbook and daily drill (a synthetic P1 reaches both surfaces) | open |

Progress is on [crew#682](https://github.com/chidionyema/crew/issues/682).
