# Runbook: the founder-decision door

Any agent can put one structured decision in front of the founder on the estate's Otto
Telegram chat and read the answer back typed. No model is involved in delivery or in
recording the answer, so a 503 router cannot break it.

## Ask

```bash
estate_execute founder.decision \
  --question "Ship the AEI collector now?" \
  --options "ship: land it, hold: wait for the cluster" \
  --context "#7341, lane/aei-ops" \
  --requester "pi @ idp" \
  --deadline-min 60
```

One JSON object comes back:

```json
{
  "decision_id": "dec-306c912e",
  "state": "asked",
  "option": null,
  "answer": null,
  "message_id": 2056,
  "session_id": "sb-8c36b1a3",
  "bus": "open",
  "webhook_held": false
}
```

The same door from a shell, with no agent runtime at all:

```bash
bin/founder-decision ask --question "..." --options "ship: land it, hold: wait"
bin/founder-decision show --decision-id dec-306c912e
bin/founder-decision poll
```

## The founder's answer

The founder receives exactly ONE message per decision: the id first, the question, the
options, the links. He answers with a comment:

```
dec-306c912e ship
```

Matching is deterministic:

| the founder writes | the door records |
|---|---|
| `dec-306c912e ship` | `option: "ship"`, the whole comment verbatim as `answer` |
| `dec-306c912e SHIP` | the same -- option keys are case-insensitive |
| `dec-306c912e approve` (and the request has an `approve` option) | `option: "approve"` |
| `dec-306c912e do it after the cluster comes back` | `option: null`, the comment verbatim |
| `ship` (exactly one decision is live) | `option: "ship"` -- an exact key only |
| `what is the status of the cluster?` | nothing -- an ordinary chat message is never captured |

A comment that cannot be parsed is **never coerced** into an option and **never dropped**:
it is stored verbatim with `option: null`.

## One message, outside the decision flow

```bash
bin/founder-decision reply --text "the estate can see your last four messages now"
```

This is the narrow exception an operator needs when the estate's own reader is down and the
founder is talking into a channel nobody is listening to. It is deliberately NOT an intent
argument: no agent can turn the decision door into a chatty surface.

## Fail closed

No answer by the deadline is `state: expired`, `option: null`, `answer: null`. The door
never reports a decision the founder did not make. A wait that ends before the deadline
leaves the decision `asked` -- the wait ending is not the decision expiring.

## Where the record lives

* `~/.estate/sovereign/decisions.json` -- the door's own index (mode 0600): the request, the
  message id, the state, the founder's comment, the bus session id when there is one.
* The bus session (`session_id`) -- opt-in (`--bus`). With it, the founder's comment is
  steered into the waiting session, so the signed receipt chain holds it with `by=founder`.
  It is opt-in because a bus session makes the estate's card post a line message too, and the
  founder's rule is ONE message per decision (measured: 2056 from the door, 2057 from the
  card). When the bus is unreachable the door says `bus: "unavailable"`; it never pretends the
  receipt exists.

## When the estate's own reader of the founder's replies is down

The gateway's webhook (`https://otto.mumchimp.com/webhook/telegram`) is the estate's reader.
While that ingress is unreachable (it is today -- #7343), the founder's reply has nowhere to
land. `ask --take-webhook` lets the door hold the bot's updates itself:

```bash
bin/founder-decision ask --question "..." --take-webhook
```

Rules, in this order:

1. The door asks the Bot API where the webhook points and whether that URL answers. If it
   answers, the estate's reader is alive and the door **does not** take over.
2. Only then does the door delete the webhook, and it keeps the URL so it can put it back.
3. The door restores the registration as soon as the last live decision closes (answered or
   expired). `bin/founder-decision poll` does it.
4. If the estate's gateway re-registers the webhook while the door is holding it,
   `getUpdates` answers 409 and the door **yields**. There is never more than one reader.

To put the bot back by hand:

```bash
python3 - <<'PY'
import importlib.util, pathlib, sys
lib = pathlib.Path("sovereign/otto/decision.py").resolve()
spec = importlib.util.spec_from_file_location("fd", lib)
m = importlib.util.module_from_spec(spec); sys.modules["fd"] = m; spec.loader.exec_module(m)
token, _chat = m.telegram_credentials()
print(m.set_webhook(token, "https://otto.mumchimp.com/webhook/telegram"))
PY
```

## The gateway, when it is alive

`sovereign/otto/hermes_plugin` routes a founder comment that quotes a live decision id into
the door and answers with one receipt line. That path works when the decision was opened on
the gateway's own host (the door's state file is per host). A decision opened on the laptop
and answered on the gateway is the known gap: the gateway does not know that decision id.
Until the cluster is back, the door holds the webhook and reads the reply on the laptop.

## Discovery

* `estate_list` names the intent `founder.decision`.
* `catalog/estate-capability-registry.json` carries `cap:intent/founder-decision`.
* The decision record's `default-deny` halt names this door.
* This runbook is the estate's own answer to "how do I ask the founder something?".

## What it does not do

* It does not execute anything. An answer is an answer, not authorisation.
* It does not send a second message for the same decision id, ever.
* It does not use a model, a second bot, a second webhook, a new database or a new service.
