# ADR: Backstage is frozen history, not a candidate — never fetch it onto this machine again

**Status:** accepted (frozen)
**Date:** 2026-11-12
**Decider:** judgment — founder (issue #8000)

## Irreducibility (AGENTS.md §12)

This is a `judgment` decision with reason **`value-tradeoff`**. Two goods the estate cannot
rank by machine:

- **Good 1** — a Backstage developer portal is a real capability (service catalog, scaffolder,
  techdocs). Tenet T-3 says *best-of-breed selection by evidence*, and Backstage is the industry
  default, so it deserves to be considered on its merits.
- **Good 2** — Genesis is the product the founder is shipping. A portal that keeps 2.4 GB of
  install cache resident on the laptop, is not wired into Genesis, and is used by nobody costs
  disk, attention and boot time every single day.

The founder resolved that tradeoff against Backstage on 2026-11-12. No machine rule can rank
"an industry-standard portal might be useful later" against "2.4 GB gone today and nothing is
using it", because the ranking depends on which good is valued more. That is a value tradeoff,
and it is recorded so that nobody re-litigates it.

## Context

On 2026-11-12 the founder said, in order:

> "BABACKSTAGE OS using up soave and not even beung used in genesis, get rif of it locally"
> "ands oprevent it being download ed on tis machine, it must remoin frozen as hsotory for
> furrueleanring how not to do backstage"

Measured at that moment:

| what | measured value | how |
|---|---|---|
| `~/.estate/frontend/idp/backstage` | **2,419 MB** (`node_modules` alone 2,287 MB) | `du -sm` |
| a `backstage` process | **none** | `pgrep -fl backstage` → exit 1 |
| the product it was staged for | **Genesis does not use it** | founder; no Genesis import |
| `~/.estate/frontend` before → after | 2,451 MB → **33 MB** | `du -sm` |
| repo-tracked Backstage source | 505 files, 297 MB working tree, `node_modules` **0 MB** | `git ls-files backstage \| wc -l` |

The local install cache — 2.4 GB — was pure cost: not running, not imported, not used. It was
deleted, and `~/.estate/frontend` fell from 2,451 MB to 33 MB.

## Decision

1. **The local Backstage install is deleted and stays deleted.**
   `~/.estate/frontend/idp/backstage` is gone and nothing recreates it.
2. **Fetching Backstage onto this machine is refused by a machine, not by a convention.**
   `bin/backstage-refused` is the single door that answers "may I install Backstage here?".
   It exits non-zero and prints this record's path. Any bootstrap or install path that would
   clone/install Backstage calls that door first.
3. **The repo-tracked Backstage source is NOT deleted by this ADR.** The 505 tracked files under
   `backstage/`, `clusters/oke/backstage.yaml`, `clusters/oke/kustomization.yaml`,
   `probes/backstage.py`, `mkdocs.yml` and `policy/agent-diff-forbidden.txt` form a repo-wide purge
   with its own blast radius. That is a separate claim on its own lane. This ADR freezes the
   *install* and names the purge as the remaining work; it does not silently perform it.

## Why a decision record plus a refusing door, and not a tombstone

A tombstone says "there was a thing here". It rots: in a year nobody knows why, and the next agent
re-evaluates Backstage from scratch, re-downloads 2.4 GB and re-learns the lesson at the founder's
expense. A record plus a refusing door cannot rot: the door refuses, the refusal names the reason,
and the reason is this document. **The lesson is enforced, not remembered.**

## The lesson, stated once

The estate downloaded a 2.4 GB portal for a product it was never wired into. The failure was not
choosing Backstage — Backstage is fine technology. The failure was **staging infrastructure for a
capability that no caller required**. The rule this teaches:

> Do not install a layer until a real caller in the estate imports it. A capability with no
> caller is not a capability, it is disk.

This is §6 (one of each layer) seen from the other side: a layer nobody calls is not a second copy
to delete, it is a first copy that was never needed.

## Falsifier

`tests/test_backstage_stays_frozen.py` proves both halves, so this is a gate and not a wish:

- the door **refuses** a Backstage fetch — exit non-zero, message carries this record's path;
- the door **accepts** everything that is not Backstage — no false refusals, because a guard that
  refuses correct work is an outage (§12);
- the local install path is **absent** on this machine.

## Consequences

- 2.4 GB reclaimed on the laptop and never re-spent.
- Any agent that tries to fetch Backstage receives a refusal naming this record — not a silent
  2.4 GB download discovered hours later as disk pressure.
- The repo-tracked source remains and must be purged deliberately under its own claim, with the
  kustomize, mkdocs and policy references updated in the same change (§6: never leave two).
