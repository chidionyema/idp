# 2026-10-28: the founder-decision door is one message per decision, and silence is not a yes

## Status

Accepted (issue #7340).

## Context

The estate had a Telegram bot, a webhook, a pinned card, and a sovereign bus that could park a
session in `asking` and halt it with `default-deny` on silence. It had no door: 102 intents in
`platform/estate/intents`, none of which reached the founder; an agent that needed a human
decision had to hand the question to a human, who re-typed it into a second surface.

The founder's requirement was precise: any agent, independent of harness and model, must be
able to reach the founder on the Otto Neumann Telegram channel for a decision, in a structured
form that is seamless for the founder to answer with comments; the capability must be easy to
access and must announce that it exists.

Two facts shaped the design, both measured rather than assumed:

* The cloud router was 503. A door that needed a model to deliver or to record an answer would
  have been dead on arrival.
* The founder's ingress was unreachable (#7343), so the estate's own reader of his replies was
  not receiving them.

## Decision

**One door, one message per decision, deterministic matching, fail closed.**

* The request is structured: `decision_id`, `question`, up to five `key: label` options, up to
  five context links, `deadline_min`, `requester`.
* The founder receives exactly ONE message per decision, the id first so he can quote it. The
  same id never produces a second message.
* The answer is his comment, verbatim. An exact option key (case-insensitive), or
  `approve`/`deny` when the request carries such an option, picks that option; anything else
  is stored whole with `option: null`. A comment is never coerced into an option and never
  dropped.
* Silence is `expired`, never an assumed yes. A wait that ends before the deadline leaves the
  decision `asked`; the wait ending is not the decision expiring.
* Delivery and recording call no model. The door imports nothing but the standard library, and
  a test asserts that it imports no model client.

**Where the record lives.** The door's own state file (`~/.estate/sovereign/decisions.json`) is the
door's index: the request, the Telegram message id, the state, the founder's comment verbatim,
and the bus session id when there is one. It is not a second authority, and the answer is
attributable to the founder because the comment carries the message id of the chat the door
posted in.

**The bus session is opt-in, and that is a measured choice.** A decision may also open a
session in the `ask` runner, so the founder's comment is steered into it and the estate's
signed receipt chain holds it with `by=founder`. The first live run of this door did exactly
that, and it produced TWO messages to the founder: the door's decision message (2056) and the
estate card's line message for the new session (2057). The founder's rule is one message per
decision, so the bus session is now opt-in (`--bus`): callers who want the receipt chain and
accept the card's line take it; the default door posts exactly one message. When the bus is
unreachable the door says `bus: "unavailable"` rather than pretending a receipt exists.

**The webhook.** The estate has exactly one bot and one webhook. The gateway's webhook is the
estate's reader of the founder's replies. While that ingress is unreachable, the founder's
reply has nowhere to land, so the door may HOLD the bot's updates -- but only after it has
checked that the registered webhook URL does not answer, and it restores the registration as
soon as the last live decision closes. If the estate's gateway re-registers the webhook, the
door yields (`getUpdates` answers 409). There is never more than one reader of the founder's
replies.

## What this refuses to be

* Not a second bot, a second webhook, a second decision layer, a new database or a new service.
  The card (`sovereign/otto/card.py`) is deliberately NOT changed: the door posts one message
  per decision, and adding the decision to the pinned card would be a second message per
  decision.
* Not an executor. An answer is an answer; it authorises nothing.
* Not a model in the loop. A 503 router cannot break this door.

## Consequences

* An agent asks, gets an id back, and continues its build when the answer lands. Nobody
  re-types an instruction into a second surface.
* The founder is never flooded: one message per decision, ever, and asking twice with the same
  id sends nothing.
* Every answer is attributable and durable: the founder's own words, in the estate's signed
  receipt chain.

## What the first live run measured

* The door delivered message 2056 to the founder's chat (the estate's card posted a second
  line message for the bus session -- 2057 -- which is why the bus session is opt-in now).
* The founder's four earlier Telegram messages had been sitting in Telegram's queue,
  undelivered, because the estate's reader was down. The door read them, correctly did NOT
  capture them as an answer (they quote no decision id and are not an option key), and the
  door answered the founder's own questions in one message (2063).
* The answer to "is any other session on this MacBook already doing this?" was measured, not
  guessed: one other agent is building the Telegram agent doctor (#7347) in
  `~/.estate/worktrees/otto-mvp`, on different files; the bus held exactly one session.

## Known limits (stated, not hidden)

* The door's state file is per host. A decision opened on the laptop and answered on the
  gateway is not captured by the gateway, because the gateway does not know that decision id.
  While the ingress is down this is moot -- the door holds the webhook and reads the reply on
  the laptop -- and closing the gap means letting the gateway match a decision id against the
  bus's live ask sessions.
* `sb approve` requires a signature; the founder's comment is steered (`sb steer`), which is
  the estate's free-text primitive for exactly this. The receipt's kind is therefore `steer`,
  with `by=founder` and the comment as the attestation.
* A bus session opened with `--bus` needs a budget that covers its wait: the first one was
  opened with 40 and the ask step exhausted it, so the session halted on budget rather than
  on the founder's deadline. The default is now 5000, and the engine's asking deadline is what
  produces the default-deny.
