# RESUME HERE — 2026-09-04T22:2xZ, session 5f6f4e72

## What I am doing
Building crew#843, the portal modernisation, myself. The founder read the specification and
said "you may as well do it", so the DeepSeek handoff is off and this session builds it.

Branch: `feat/portal-modernisation`, worktree at
`$TMPDIR/.../scratchpad/wt-portal`, cut from `origin/main`.
Remove the worktree when the pull request is merged — worktrees must not accumulate.

## The specification
https://github.com/chidionyema/crew/issues/843 — ten checkpoints, six pull requests.
Checkpoint one is the Health page at `/ops`, which he named as broken.

## The two facts that shape every change
- The portal is on Backstage's new frontend system. Pages are changed by declaring
  extensions in a `createFrontendModule`, never by adding routes. Never convert
  `backstage/packages/app/src/App.tsx` back to `<Route>` elements.
- The Backstage UI stylesheet is loaded (`index.tsx:4`). The Health page looks wrong because
  `modules/home/Ops.tsx` renders `@backstage/ui` and Material-UI `makeStyles` in one file,
  not because a stylesheet is missing.

## Also open on this session
crew#841, the break-glass bridge: cloud-init runs out of memory installing the Oracle CLI
on a 1 GB machine, so the instance never joins the tailnet.

## RESUME HERE — 2026-09-05T00:0xZ, session 36c9262c (idp lane)

**Open:** idp#1632 (`fix/deepseek-lane-console-owned`, worktree `$SCRATCH/wt-ds`) — the DeepSeek
model row leaves the rendered config so the founder can delete and replace its key in the LiteLLM
console himself. Two acceptance checks read `llm/config.yaml` as the whole list of lanes the router
serves; `sovereign/policy.py console_lanes()` now unions it with `platform/vendors/consoles.yaml`
`router.console_lanes` and both pass. Waiting on `bdd-suites (acceptance)`. After it merges:
`bin/idp-vault-put --unset litellm-upstream DEEPSEEK_API_KEY`, then remove the worktree.

**Starting now:** `fix/dead-lane-consumers` (worktree `$SCRATCH/wt-mem`) — three workloads still
name the dead `deepseek` lane: Hindsight's extraction model, the infra-crew verifier and
otto-golden's bulk lane. All three move to `fast`.

**Measured 2026-09-04 23:5xZ–2026-09-05 00:0xZ:** Hindsight is live on the one estate Postgres
(bank `hermes`, 684 memory units, 15,054 links, 371 entities) and is the estate's memory provider,
but writes have stopped: 268 units on 08-30, 154 on 09-02, 14 on 09-03, 1 on 09-04. Only
`platform/hermes-agent` is wired to it (`HINDSIGHT_API_URL`); otto-gateway and otto-golden are not,
and `otto/boot/pipeline.py` round-trips a memory fact without ever writing it. So the one door
answers with no memory at all.

**Next:** the specification for one permanent fast-retrieval memory layer on the Hindsight row —
both Ottos, then crew, agents and k8sgpt, through a structured ingest/retrieval tool pair on the
existing estate MCP server (ADR 0006). Build goes to DeepSeek.
