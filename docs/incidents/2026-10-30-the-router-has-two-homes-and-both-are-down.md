# Incident: the router had two homes, each the other's only fallback, and both are down (2026-10-27 to 2026-10-30)

Status: OPEN. The class of cause is established, from this repository and from the laptop's own
state files. Six facts that would size it are not (see "Not established"). Founder, 2026-10-30
12:17 (spelling normalised): the LiteLLM router is down and the whole fleet with it, "despite
promises and founder edicts of seamless fall back lanes and never allowing a critical service to
be a single point of failure". He asked for this report, and for a blame culture in which the
responsible party for any critical-service interruption is named and disciplined (see
"Accountability").

## What happened

All times UTC. Sources are named; "attributed" values are the `Agent:` and `Claim:` lines in the
commit message body, which the agent types itself (nothing verifies them).

| when | what | source |
|---|---|---|
| 10-21 | The front records the law "no laptop overload or OKE outage may take out every model" (load 95, 4 GB swap) and meets it with two homes: the cloud router and the laptop's slots, each the other's fallback. #6815, attributed `claude-cli`, claim #6813 | `platform/llm/front.py` header |
| 10-24 22:21 | First load sample above 50 (above 100 at 22:22) | `~/.estate/logs/load-gate.log` |
| 10-25, 10-26 | The cloud becomes the front's primary (#7079, `zcode-kimi`, #7078) and then the law's default route (#7247, `pi`, #7244, AGENTS.md section 7a) | commits |
| 10-27 ~12:00 | The cloud route stops answering (503 "Starting up", then 504) | `2026-10-28-the-router-lost-every-model.md` |
| 10-28 | ADR 0037 and the drill (#7331, `pi`, #7142). The drill's first run: one of four router rungs alive, the laptop | `docs/specs/2026-10-28-the-fallback-ladder-and-the-drill.md` section 4 |
| 10-29 02:07 | Oracle removed the OKE entitlement (`cluster-count=0`): the cloud router has no home to return to | `2026-10-29-the-cluster-lost-its-control-plane.md` |
| 10-29 | The drill is scheduled every 15 minutes, on GitHub runners only (#7413, no `Agent:` or `Claim:` line) | `.github/workflows/estate-watch.yml` |
| 10-29 06:00 to 17:59 | Hourly peak load 816 to 1018, twelve hours running | `load-gate.log` |
| 10-29 20:21 | The front marks the cloud down: 12 failures in a row, pass-over at its 600 s cap | `~/.estate/front-state/cloud-down-4000` |
| 10-29 22:16 to 22:36 | The host's clock reads 2024-01-01; 40 load samples in the log carry that date | `2026-10-29-the-host-clock-fell-back-to-2024.md` |
| 10-30 | The front gets one 240 s budget per request, and a box above `LOAD_MAX` is refused at once with 503 and `Retry-After: 30` ("the load reached 701 on 4 CPUs that day"). #7547, `pi`, #7531 | `front.py` `handle()` |
| 10-30 10:18 | The laptop router's active slot becomes 4002 | `~/.estate/router-state/active` |
| 10-30 11:54 | The laptop router is re-rendered: 25 lanes served, 8 declarations refused for an absent credential | `router-state/lanes.json` |
| 10-30 12:26 | Load 566 to 578 | `load-gate.log` |

## Measured on the founder's Mac (read-only, 12:23 to 12:27Z)

- **Load.** Every hour of the last 30 that has a sample peaked at 49 or more; 22 of them above 300;
  the highest was 1018 (10-29 13:00). The log records only the runs the gate skipped, so this is a
  floor on the load and not a time series. The front's refusal line is `8 x CPUs`: 32 on the four
  CPUs the front's own comment names (the Mac's CPU count was not read).
- **The laptop router rendered a healthy config.** It serves 25 lanes with fallback chains that end
  in groq or openrouter, and the 10-30 MiniMax fallback fix is loaded (`minimax_m27: [minimax,
  gemini, groq]`). Whether its slot is answering now was not measured.
- **Four vendor families are not served.** glm (`ZAI_API_KEY`), cerebras (3 keys), nvidia and
  sambanova (3 keys) are refused for an absent credential. `bin/litellm-local` reads keys from the
  local sops store and then from `kubectl -n llm get secrets`, which is the dead cluster.
- **The earlier Mac-side drill never ran.** `~/.estate/logs/drills.log`: 19 lines, every one
  `Operation not permitted` on `~/Documents/.../scripts/drills/run.py`, last written 10-13; this is
  consistent with launchd being barred from `~/Documents`, which `bin/litellm-local` also notes.

## The cause, as far as it is established

1. **The serving path had two homes, and both are down.** OKE was removed by the vendor. The
   laptop is refusing or starving because of load. The agents that need the router run on that
   same box (section 7a), so the fleet's demand and its router share one failure domain.
2. **Shedding turned overload into outage.** A saturated front refuses at once, which is right
   for a queue it cannot serve, but there is no remote home to hand the request to, so the
   refusal is the whole answer.
3. **The ladder is measured and not wired.** `platform/ladder/critical-lanes.json` declares four
   router rungs in four providers. `git grep` finds it read by `bin/idp-estate-homes` and its test
   only. `platform/llm/front.py` has no reference to the lifeboat, the Groq floor or the file
   (0 occurrences). ADR 0037 R7 said the front's own legs should come from the same data.
4. **The measurement could not see the rung that carries the fleet.** The drill runs on GitHub
   runners (stated in `estate-watch.yml`). From there the laptop rung is `NOT_HERE` by
   construction, and the floor rung needs a vault read the job passes only `GH_TOKEN` for. The
   drill also (a) closes a ticket with "every lane answered again" while lanes are unasked,
   (b) grades a refused proxy tunnel as a dead lane (measured from a proxied sandbox; a runner has
   no proxy), and (c) never says how many independent providers are left. All three are fixed below.
5. **The law named the default without the clause that flips it.** Section 7a calls the cloud the
   default route; nothing says what the default is while the cloud is measured dead.
6. **The fallback's keys depended on the primary's cluster.** See the four families above.
7. **The selector is a home, and it was not counted.** Every local agent reaches every home
   through one process on one host (`127.0.0.1:4000`, "base URL for every agent",
   `bin/litellm-status`). `bin/idp-estate-homes --prove` finds `host:laptop` on the path of all
   of them: the loss of that one domain leaves a client no home at all, however many are declared.

## Chain of changes

Facts about each change, not verdicts on its author. `Agent:` is a lane or harness name (`pi` is
a harness), not a model; which model served each session is in the router's request ledger, which
was not read.

| change | attributed | what it did to the exposure |
|---|---|---|
| #6815 | `claude-cli`, #6813 | Built the two-home design; it has no third home for the case where both fail |
| #7079 | `zcode-kimi`, #7078 | Made the cloud the front's primary |
| #7247 | `pi`, #7244 | Wrote the cloud-default law with no measured-health clause |
| #7331 | `pi`, #7142 | Decided the ladder and built the drill, not the part that uses the ladder |
| #7413 | none | Scheduled the drill where it cannot see the laptop or the floor |
| #7547 | `pi`, #7531 | Added the budget and the load shed, with no remote home to shed to |

The founder's own ruling of 10-26 (cloud default) is in the chain: ADR 0037's three-homes rule
came two days after the flip, and nothing gated the flip on the rule.

## The class, and how it is eliminated

**The class** is a critical service whose answer depends on one failure domain: a provider, a
host, a process, a secret store or a clock that lies on the path of every home. 10-28 was an
instance (the cluster), 10-30 is another (the laptop). Patching an instance (restart the router,
free the volumes, raise a budget) leaves the class, and the next instance arrives under a new
name. The estate had written the rule down on 2026-09-10 ("A HOME IS A FAILURE DOMAIN, NOT A
MODEL", `platform/lifeboat/src/homes.js`) and then built a router front whose homes all sit
behind one process on one host.

**Why it recurs: the arithmetic.** If homes fail independently with unavailability `u_i`, the
chance that all are down is the product of the `u_i`: each independent home added multiplies the
risk by its own `u_i`. A domain `D` on the path of every home puts a floor under it: all-down is
at least `u_D`. Illustrative arithmetic, not a measurement: four homes at 95% each give
1 - 0.05^4 = 99.9994%, and one box at 90% in front of them caps the service at 90%. Hardening
one home moves one factor; removing a common domain removes the cap, and only that changes the
order of magnitude. Every outage so far was a cap.

**The asymmetries this uses.**

1. *A mechanism must be right every time; an outage only once.* So the guarantee cannot be a fix
   people remember. It has to be a property a machine checks on every change, which is why the
   proof and the matrix below are tests, with strict `xfail` markers: a fix cannot land without
   the marker coming off, and a regression cannot land without the test going red.
2. *Failure is cheap when chosen and expensive when surprising.* Losing one home on purpose costs
   one canary request. Losing the second home on 10-27 cost the fleet its redundancy for three
   days with nobody knowing the ladder was one box. Failing constantly in small, rehearsed ways
   is what lets the real failure not matter, because every defect the real outage would expose is
   exposed first by the drill, in minutes, with a blast radius of one request.

**The five properties, each a check and not a promise.**

| property | the check | status today |
|---|---|---|
| P1 no failure domain is on the path of every home | `bin/idp-estate-homes --prove` (no network, runs in CI) | built. **Fails for `llm-router`: `host:laptop`.** `otto` is `UNDECLARED`. Ticket `router-second-selector` |
| P2 any single loss still answers | `tests/test_router_front_survives_every_single_loss.py` | built. One cell fails (a saturated laptop with a healthy cloud), as a strict `xfail`. Ticket `router-ladder-actuator` |
| P3 the ladder is measured from where the demand is | `bin/idp-estate-homes --gate` run on the laptop | gate built; the laptop run is ticket `drill-from-the-laptop` |
| P4 failure is rehearsed continuously | a scheduled drill that loses each single domain in turn and sends one canary | not built. Ticket `router-fault-drill` |
| P5 a change cannot make P1 to P3 worse | CI runs the proof and the matrix on any change to the front, the ladder or section 7a | strict markers built; the CI wiring is in `router-fault-drill` |

**What this change does and does not do.** It does not eliminate the class. It makes the class
checkable: P1 and P2 turn this incident into two failing facts that run in under a second on any
machine, and they stay red or marked until the topology is fixed. The class is eliminated when P1
is `PROVEN` for every critical service, P2 has no `xfail`, P3 reports from the laptop, and P4 and
P5 are running. Until then the claim is only that the estate can no longer fail this way unseen.

**The limits of the proof, so it can be attacked.** P1 knows only the domains someone wrote in
`fate`. It cannot see an unlisted shared domain: a wall clock (10-29), DNS, an expiring
certificate, one billing account behind two vendors, one rate limit, one operator. P4 exists
because P1 cannot find those. P2 covers single losses only, and its box-saturated cell shows the
front can be wrong about its own box. The proof checks one loss at a time; two at once is the
12:17 state and needs a third independent home before any test can pass it.

## Not established

- **What is generating the load.** The process list was not read. Candidates only: concurrent
  agent sessions, parallel test runs (`pytest -n auto`), runaway children. Ticket `fleet-load-source`.
- **How many requests the front refused, and whether the running front has the shed rule.**
  `~/Library/Logs/litellm-local.log` and `~/.estate/litellm-local/front.py` were not read.
  Check: `grep -c 'box is saturated' ~/Library/Logs/litellm-local.log; grep -c LOAD_MAX ~/.estate/litellm-local/front.py`.
- **Whether the lifeboat (the Cloudflare home) is deployed.** On 10-28 its name did not resolve;
  its only deploy path is the manual `otto-lifeboat` workflow, and no run is visible in git.
  GitHub Actions and issues were unreadable from the session that wrote this.
- **Whether the recovery host exists and `router-recovery` has run.** The workflow, the host's
  Terraform and the placement in AD-2 on E2.1.Micro are on `main` (#7508, #7525, #7535); with
  `cutover=true` it points `llm.mumchimp.com` at the host through a Cloudflare tunnel. That is the
  shortest path back for the cloud rung, and it shares Cloudflare with the lifeboat.
- **Whether `estate-watch` filed tickets for the dead cloud, and who held them.**
  Check: `gh issue list --search '"[lane] llm-router" in:title' --state all`.
- **Which model sat behind each `Agent:` value.** The router ledger was not read.

## Fixed in this change

`bin/idp-estate-homes` judges each ladder (`REDUNDANT`: two or more providers answer;
`UNPROVEN`: fewer than two answer and a rung was not asked; `SPOF`: one provider; `DOWN`: none),
prints the state and what it could not ask, files a ticket for `SPOF` and `DOWN` even when no
lane failed, closes with what was asked instead of "every lane answered", grades a refused proxy
tunnel `UNKNOWN`, and `--gate` exits 1 for `SPOF` or `DOWN`, 2 for `UNPROVEN`, else 0.
`--prove` adds the topology proof (P1) and declares the `llm-router` topology in
`critical-lanes.json` from what `front.py` and `bin/litellm-status` show. The new
`test_router_front_survives_every_single_loss.py` is P2. `tests/test_estate_homes.py` has 33
tests (24 new, one strict `xfail`); the matrix has 6 (one strict `xfail`). With `--runxfail` the
saturated cell fails because the front logs `the box is saturated ... refusing` while the cloud
is healthy: the 12:17 mechanism, offline.

Not fixed here: the actuator, the second selector, the laptop run, the fault drill, the keys, the
load. Each is a ticket (`router-ladder-actuator`, `router-second-selector`,
`drill-from-the-laptop`, `router-fault-drill`, `laptop-keys-without-the-cluster`,
`fleet-load-source`).

## Accountability

Needs the founder's sign-off. It amends ADR 0038, whose performance review already moves usage
and spend by measured evidence, so it adds no second mechanism.

1. **Every critical service has an owner of record**: the claim that holds it, in
   `critical-lanes.json`. A critical service with no owner is a finding the drill raises.
2. **Every incident record carries a chain of changes** like the one above. A change with no
   `Agent:` line is `UNATTRIBUTED`, and the strike passes to the gate that let it land.
3. **A strike** is recorded in the review against the lane whose change left the gap, or whose
   claim held the service and went idle, with the minutes the ladder spent `SPOF`, `DOWN` or
   `UNPROVEN` (the drill's own board).
4. **A strike costs what the estate controls**: routing weight and spend (ADR 0038). Two strikes
   in 30 days remove the lane from critical-path claims until a remediation lands with a proof.
   Only a proof clears a strike, never time.
5. **No strike without evidence.** Naming a party on assertion is the slop the review punishes.
   A harness name is not a model: a model-level consequence waits for the join with the router
   ledger (ticket `attribution-proof`).
