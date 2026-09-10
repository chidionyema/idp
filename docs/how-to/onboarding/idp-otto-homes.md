# Onboarding: Otto's homes, and how to add one

`bin/idp-otto-homes` grades and deploys the places Otto can run. Read this before changing a
home, adding a lane, or moving the door.

## Door (from the UI)

Backstage → the `otto-gateway` component → **Otto homes**. That card is the surface a person
uses. This page is for the agent or engineer changing what the card reports on.

## The one distinction to hold on to

A **home** is a failure domain: a place Otto runs that can die without taking the others down
with it. A **lane** is a vendor that does the thinking. They are independent axes.

Five model lanes configured inside one pod are not three homes — they share a node, a network,
a load balancer, a scheduler and a quota, so they share every way of dying. Adding a lane makes
Otto cheaper to keep answering. Adding a home makes Otto harder to kill. Do not confuse the two,
because the estate already has once.

The three homes today: the OKE cluster, a Cloudflare Worker on the global edge, and the
founder's MacBook over the tailnet.

## Grade the homes

```
bin/idp-otto-homes            # same as: bin/idp-otto-homes status
```

Exits zero whatever it finds. A red home is a report, not a failure — Otto answers while any
one home is green.

## Deploy home 2

```
bin/idp-otto-homes deploy
```

Three things it does that are worth knowing before you run it:

1. **It derives the Cloudflare account id** from the zone read, the same way
   `bin/idp-bootstrap-cloudflare` does. No account id is written down anywhere in the tree.
2. **It passes the route on the command line**, not in `wrangler.toml`. A route in that file
   would name the estate's DNS zone as a literal, which LAW 46 and `bin/estate-zone-gate`
   refuse.
3. **Every secret goes in on stdin.** No key is ever an argument, an exported variable or a
   line in this session's scrollback (LAW 21, R52). A lane whose key is absent is skipped, and
   the edge simply runs a shorter ladder — a missing key is never a failed deploy.

If the token cannot read the zone, the command prints a `FOUNDER ACTION:` line naming the exact
scopes and the console URL, and stops. It never mints a credential on its own.

## Add a lane

Lanes live in `platform/lifeboat/src/homes.js`, one object each: a name, the vault field its key
comes from, the OpenAI-compatible URL, and the model. Add the object, add the matching row to
the `deploy` loop in `bin/idp-otto-homes`, and add a case to
`platform/lifeboat/test/lifeboat.test.mjs` — the test suite stubs every outbound call by
hostname, so a new lane is proved without a single network request.

## Move the door

Don't, without the founder's own plain words. Telegram accepts exactly one webhook URL per bot,
so a cutover repoints his live assistant with no second URL to fall back to. `cutover` prints
what would be required and stops there deliberately.

## Further reading

[Otto's survival matrix](../../explanation/otto-survival-matrix.md) — the full design: the three
homes crossed with sixteen inference lanes, the refill clock each lane runs on, and why a
fallback chain is the wrong primitive for a set of replenishing free tiers.
