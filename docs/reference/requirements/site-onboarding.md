# Requirement: one parameterised path to a new site or API

Founder, 2026-10-18: *"we need a parameterized intent to deploy a new website or backend API."*

## The requirement

A new public site or backend API costs **one command and one lane**, and nothing it needs lives
outside that command. Given a label and a hostname, the estate derives every declaration a site
needs to be reachable at `https://<label>.${ESTATE_ZONE}`, and a gate refuses a tree in which any
one of them is missing.

The justification is measured, not asserted: meridian's application was written once, and bringing
it to the public internet took four merged fixes (#6503, #6511, #6513, #6518), every one of them a
missing declaration in a shared file, and every one of them presenting as a different symptom --
404, untrusted certificate, a hang after the handshake, a challenge that times out while the same
URL answers 200 from the node.

## What must be true

1. `site-onboard mode=plan` writes nothing and prints every CREATE and EDIT. It is the default.
2. `site-onboard mode=write` writes only: it never talks to the cluster, because Flux is the only
   writer of the cluster (AGENTS.md 2).
3. `site-onboard mode=verify` is a read-only gate, graded **in the tree** and not from its own
   arguments, and it fails for each declaration missing. Remove the listener, the lane row, the
   allowance, the fence or the edge-attach label and it says which one.
4. Both halves of the edge allowance are always written together (`flows.edge.egress` and
   `flows.<name>.ingress_from`). One half alone is not a 502, it is a hang: default-deny drops
   Traefik's SYN after the TLS handshake completed, so nothing sends a reset.
5. The hostname is `${ESTATE_ZONE}`, never a literal (`bin/estate-zone-gate`).
6. The image tag is Flux's (`$imagepolicy`), never typed; the pull secret comes from the cluster
   store, so no laptop has to exist for a node to pull.
7. A founder-facing site runs 2 replicas and they do not share a node (`founder-facing-runs-two`,
   `founder-facing-spreads-across-nodes`).
8. A credential arrives as a mounted file from the vault and the mount is `optional: true`: before
   the vault entry exists the site serves and an endpoint needing it answers 503 rather than
   accepting work it would drop.
9. The shared-file edits preserve comments and are refused if they would not parse. A second write
   changes nothing.

## Where it lives

| Part | Path |
|------|------|
| the generator, plan/write/verify | `platform/estate/libexec/site-onboard.py` |
| the intent (a verb, like every action) | `platform/estate/intents/site-onboard.yaml` |
| the runbook | `docs/runbooks/new-site.md` |
| the tests | `tests/estate/test_site_onboard.py` |

`bin/estate-runtime-sync` stages `platform/estate/{intents,libexec}` into `~/.estate` every five
minutes, so the intent reaches every door (MCP, harness, `estate-execute`) without a second copy:
the file in idp is the only one to edit.

## The proof

18 tests, and the assertions are about the two things that can actually be wrong: the generator's
output passes the generator's own gate, and the gate fails, one declaration at a time, when one is
removed. `test_second_run_with_force_adds_nothing_twice` and the `patches:` / comment-inside-a-flow
cases exist because the first version failed them against the real 700-line allowances file.

Not proven yet, and deliberately not claimed: a site has not been taken from `write` to a live
production log line by this path. That is what turns "built" into "operating" (AGENTS.md 3).
