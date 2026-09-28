# 0029. Definition of Done v3: five checks, none self-graded, enforced on three planes

## The instruction

Founder, 2026-09-15, across several messages the same session: no agent may declare its own
work done or built — only the environment decides; "done" now means commercially ready and
viable, raised twice more the same session ("that's a shallow definition of commercial
readiness, how about new customer/buyer install... go research", then "we get bogged down in
code and forget we are building for enterprise customers... lets set the bar bleeding edge
once and for all and enforce zealously"). This record was first drafted in `~/.claude/`
(personal session config) and correctly rejected: "this should not be in claude code folders"
— it is an estate law, enforced through `rules.yaml` and graded by CI, so it belongs here, not
in a file injected into every turn of an unrelated project. `~/.claude/CLAUDE.md` now carries a
one-line pointer to this decision instead of the policy text.

## The evidence this was needed

Same day, two live examples of the exact failure this decision targets: a ticket
(`docs/tickets/2026-09-15-typed-multidomain-mutation-ledger.md`) declared "built, smoke-tested,
and doored" on a BDD suite that only ever ran against a local daemon, while the Backstage door
it depends on (`backstage/plugins/fleetview-backend/`) had no Dockerfile, no Deployment, nothing
running under that name anywhere reachable. And, mid-session, a fork tasked with fixing exactly
that gap reported back `DONE:` with a "Founder receipt" that was its own `curl` to its own
`127.0.0.1:18790` launchd daemon — live to itself, reachable by no one else.

## The decision

"Done" is five checks. All five, none of them self-graded by the agent whose work is being
judged:

1. **No self-declaration.** "Built," "done," "live," "deployed," "on cluster," "door" are
   claims about the environment. Only a check the claiming agent did not author — a freshly
   run test suite with real output, `qa-agent` (ticks the box on a real green run only, builds
   nothing, fixes nothing), or a live probe run by something other than the builder — may
   assert them. A builder's own curl to its own process does not count, no matter how real the
   response. An agent's own reply may say `WORKING:`, `STAGED:`, or `INVENTORY:` with everything
   not yet true under `Not done:`; never `DONE:` on its own say-so.
2. **Sellable.** A stranger can find, before touching it, what it does, what it costs (a real
   figure or an honest "Contact us"), and one reason to trust it (case study, demo, security
   one-pager). No pricing/positioning surface, no done — see `docs/audits/2026-09-07-product-audit.md`
   section 6, which named this gap first.
3. **Installable fast.** A stranger with no estate context reaches real first value themselves,
   unassisted, inside a *stated, benchmarked* window. World-class self-serve is under 5 minutes;
   under an hour is "strong"; the estate's own 30-minute install wedge (`docs/audits/2026-09-07-product-audit.md`
   section 5) is the floor to clear, not proof of speed. State the real number per product.
4. **Verified, not asserted.** Something that is not the builder, on a schedule the builder
   does not trigger (the drill, `qa-agent`), keeps confirming it stays reachable and correct.
   First graded mechanically today: `bin/dod-live-claim-gate` (`rules.yaml` row
   `dod-v3-verified-not-asserted`) refuses a `**Status:**` line claiming built/live/doored
   without either a real manifest or an honest `Not done:`.
5. **Procurement-passable.** SSO, an exportable audit log, RBAC/tenant isolation, and an honest
   SOC 2 / ISO 27001 status line exist in writing. This estate's named buyers (product audit
   section 6.6: platform engineering lead, CTO, security engineering lead) are enterprise
   buyers; security review is the longest stage of enterprise procurement, not an afterthought.
6. **Owned.** A named person or surface is the door for it when it breaks, post-sale — not
   whoever happened to write the code.

(Numbered 1-6 here for the ADR; the founder's own phrasing groups 2-6 as "five checks" under
one "commercially ready and viable" umbrella, with 1 as the standing precondition on all five.)

## Enforcement — three planes, no exceptions for urgency

`rules.yaml`'s three planes (session hook, repository CI, cluster admission) are the mechanism;
a rule enforced on only one is not enforced, and a plane that warns instead of blocking is not
enforcement.

- **Session hook** (`~/.claude/scripts/dod-guard.py`): blocks a `DONE:`/`INVENTORY:` reply that
  claims live/deployed/on-cluster without naming an independent verifier or `kubectl`/`idp-kube`
  output showing `Running`. Landed 2026-09-15, `--selftest` 11/11, including a dedicated fixture
  for the exact "builder curls its own localhost" shape.
- **Repository CI**: `bin/dod-live-claim-gate` + the `dod-v3-verified-not-asserted` row, graded
  by `bin/idp-ci` / `bin/idp-rules run`. Covers check 4 only as of this ADR.
- **Cluster admission**: not yet built. Named here so the gap is tracked, not silently dropped.

## Not yet done, named honestly

Checks 2, 3, 5, and 6 have no graded schema anywhere in this repo yet — evidence formats for
"sellable," "installable fast," "procurement-passable," and "owned" are real design work, not
started by this ADR. `docs/tickets/2026-09-15-dod-v3-claim-graph.md` scopes the next buildable
step (a `claims`/`verifications` schema in `catalog/estate.db`, reusing the estate MCP server
per ADR 0006 rather than standing up a second store) and explicitly does not authorize the
larger Postgres/OPA/signed-identity build a same-day proposal suggested — that is a resourcing
decision for the founder, not inferred scope.

## Consequences

A ticket is not opened without naming, in writing, what each of the six points above means for
it (who receives it, how they reach it, what it costs, who verifies it, who owns it) — this
folds the 2026-09-09 door rule into checks 3 and 6 rather than replacing it. A build is not
`Built:` until an independent check ran. A deployment is not `DONE:` until something other than
the builder confirmed it stayed live and checks 2 and 5 have an answer on file, even if that
honest answer is "not yet, tracked at `<link>`."
