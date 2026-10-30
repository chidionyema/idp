# The infrastructure department, the stamped vision, and one harness from the ground up

- Status: PROPOSED 2026-10-30. Needs the founder's signature on each of the three decisions below.
- Deciders: founder
- Founder, 2026-10-30 13:07 (spelling normalised): "infra is the elephant in the room ... we need a
  dedicated infra department to guarantee our infra has strong eyes on it"; 13:02: "the vision is
  the correct one and needs to be stamped, but I need the on-ground truth, given the pi agents
  have so much tooling and workflow, which we are trying to converge into a unified way of
  working, harness- and model-agnostic".
- Evidence: `docs/incidents/2026-10-30-the-router-has-two-homes-and-both-are-down.md`, and the
  measurements below, read from `origin/main` and from the founder's Mac on 2026-10-30.

## The ground truth

### Infrastructure: plenty of work, no owner, no outcome

- The OKE cluster is gone (`cluster-count=0`, 10-29). With it went the cloud router, memory,
  Temporal (`platform/temporal`, which `sovereign/engine`, `sovereign/shadow` and `spine` import),
  Backstage, and the `dagster` and `observability` (Langfuse) namespaces of the 10-30 infra
  inventory (`docs/audits/2026-10-30-infra-inventory/`). Nothing in the estate says which of them has a home now.
- The router's two homes are both down (the incident record). The prover says
  `FAILS llm-router: host:laptop`.
- **39 commits touched infrastructure on `main` between 10-27 and 10-30**: `pi` 14, `claude-code` 7,
  `estate-agent` 6, `claude-architect` 2, `pi-aei-ops` 2, `pi-incident-loop` 1, and **7 with no
  `Agent:` line**. The recovery host alone was re-placed four times in two days (A1 at 2/12 ->
  1 OCPU/6 GB -> AD-2 -> E2.1.Micro, #7427, #7430, #7439, #7508), then fixed twice for transport
  limits (#7535, #7539). No record on `main` says it answers.
- So the founder's reading ("nobody has done anything") is wrong about activity and right about
  outcome. **Seven agents worked on infrastructure, none of them owned "the router answers", and
  nobody told the founder the state.** That is what a department fixes.
- The eyes that exist: `estate-watch` grades the lanes every 15 minutes and files `[lane] <service>`
  issues (whether anyone owns them is unread); `bin/idp-estate-capacity` daily;
  `bin/idp-storage-budget`; `bin/estate-clocks`. The eyes that do not: a probe of the tenancy's
  service limits (the 10-29 incident's weakness 0), a load series for the Mac, a drill run from the
  laptop, a topology proof in CI. The Mac-side drill has not run since 10-13
  (`Operation not permitted`, 19 of 19 lines).

### The harness: pi carries the fleet, and runs a different estate from the repo

pi is the fleet's largest producer: the `pi` family carries 154 of the 400 attributed commits on
`main` since 10-16. Its default model is `minimax_m27` through the estate router
(`~/.pi/agent/settings.json`), so `Agent: pi` means MiniMax by default, not per session. Read from
`~/.pi` (all 1,031 entries listed) and compared with `origin/main`:

| | state |
|---|---|
| `pi-plan-lock` | the installed copy is from 10-21 and differs from the repo by 63 lines; the repo changed it on 10-30 |
| `estate-commands` | differs from `platform/estate/pi/estate-commands.ts` by 12 lines |
| `fleetview-directives`, `read-shunt`, `epistemic-firewall-hook`, `pi-governance` | live in pi, **not in the repo**: behaviour nobody can review or reproduce |
| `pi-estate-enforce`, `pi-founder-governance` | in the repo, **not installed** |
| `~/.pi/system_prompt.md` | dated 9-20; mentions none of `lane-submit`, `claim-open`, `declare_plan`, `estate-execute`, Greenlane or the router (0 hits each). Whether pi also loads the repo's `AGENTS.md` was not checked; if it does, this is the older of two instructions it holds |
| MCP | `~/estate-mcp-stdio.py`, a file in the home folder, not the repo's bridge `bin/estate-memory-mcp` |

The mechanism is written in `bin/pi-plan-lock-install`: "the extension is copied there, not
linked". Nothing compares the copy with the repo afterwards. Claude Code, Codex and Gemini were not
inventoried in this record.

## Decision A: an infrastructure department

**A role, not a model.** The estate is model- and harness-agnostic, so the department is a standing
claim that a lane holds, measured by the ADR 0038 review like any other lane. The holder can change;
the duty cannot lapse.

1. **Owns outcomes, not activity**: every service in `platform/ladder/critical-lanes.json` (the
   router, Otto, the doors) and, once added, memory, the scheduler and the workflow engine. Each
   service names the department's claim as its `owner` (ticket `incident-accountability`).
2. **On duty, visibly**: one issue, `infra: on duty`, held by a claim with the usual heartbeat. A
   lapsed heartbeat is itself a `[lane]` finding. The founder sees who is on duty on `/fleet`.
3. **Eyes it runs**: the drill (`--gate`) from a runner and from the laptop; `--prove` in CI; the
   capacity board; a daily limits probe of every cloud account; the Mac's load series; backup
   freshness; the clock guard. A metric it cannot collect is `UNKNOWN`, never quiet.
4. **Authority**: hold a lane that makes `--prove` worse; run the recovery buttons
   (`router-recovery`, `otto-lifeboat`) inside a spend limit the founder sets; ask the founder for a
   decision through the decision door (#7384) with a deadline, never by waiting.
5. **Duty in an incident (proposed defaults, for the founder to set)**: the `[lane]` issue owned
   within 30 minutes; a status line to the founder within 60 minutes and every 2 hours until it is
   closed; the incident record within 24 hours, with the class section ("how it is eliminated") and
   the chain of changes.
6. **First 72 hours**: get `llm.mumchimp.com` answering (`router-recovery`: candidate host first,
   then cutover); give memory a home (`memory-second-home`); land tickets
   `router-ladder-actuator`, `drill-from-the-laptop`, `fleet-load-source`; bring
   `router-second-selector` to the founder as a decision.

## Decision B: the vision, stamped, with five amendments

Stamped (from the 2026-10-30 Gemini review): one chain of custody, decision -> claim -> plan ->
commit; one progress writer (`bin/estate-progress`), with `docs/NEXT.md` retired or regenerated;
one operational surface (`/fleet`) as the view of that writer; every off-repo session brought in as
a receipt; salvage or tombstone for every red or retired lane; flow, WIP and orphan measures.

Amendments, each from the ground truth above:

1. **Single in authority, never single in availability.** One door per layer, more than one home
   per door. A door with one home is the class in the incident record.
2. **No workflow needs the cluster to move work forward.** Delivery stays on GitHub and git refs
   (the Greenlane survived the cluster); Temporal stays where it is used (`sovereign/engine`) and
   gets a home before anything new depends on it. It does not become the delivery backbone.
3. **Every turn reaches memory and traces through a local outbox that replays**, not by a live
   call to a cluster service, so a dead door delays a record and never blocks a turn.
4. **Numbers are measured or labelled.** The review's "4,000-token cap" and "restores in under
   10 seconds" exist nowhere in the code. A threshold enters law with its measurement.
5. **Salvage before burial.** No automatic kill at "50 commits behind": that rule would have killed
   the memory recovery lane. A lane is retired with a tombstone record after a salvage decision.

## Decision C: one harness, from the ground up

Harness-agnostic means the three contracts (plan, claim, hand-back) are enforced at the estate's
doors, and each harness carries a thin adapter that is **verified, not trusted**.

1. **Drift is refused.** At session start each adapter (pi extension, Claude hook, Codex config)
   compares the hash of what is installed with `origin/main` and refuses or repairs on a
   difference. The copy-not-link install stays; the check is what was missing.
2. **What runs is in the repo.** The four pi extensions that live only in `~/.pi` are brought into
   the repo with tests, or deleted. The two never installed are installed or deleted.
3. **One install door** (`estate-execute skill.install`, `bin/pi-plan-lock-install`) for every
   runtime's extensions, prompts and MCP config, so a harness is reproducible from the repo.
4. **One bridge.** Every runtime reaches memory through `bin/estate-memory-mcp`.
5. **Prompts are generated from `AGENTS.md`**, not kept by hand, so a law reaches every harness on
   the day it lands.

## What this does not decide

The spend limit and the duty times (A.4, A.5) are the founder's numbers. Where the second router
selector lives (Cloudflare edge, recovery host, both) is ticket `router-second-selector`. Claude
Code, Codex and Gemini are not yet inventoried the way pi is here.
