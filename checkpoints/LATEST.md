## RESUME HERE (2026-09-05 12:35Z, shipping Otto's L2 memory)

hermes-v2 #80 merged (9354215d), image ghcr.io/chidionyema/hermes-agent:main-80-9354215d... built 11:30Z.
idp #1780 merged but the otto-gateway Flux row is stuck at 09f84d9d: Job otto-memory-store-1
Failed because the running image (main-79) has no otto.memory module. idp #1784
(feat/otto-memory-store) renames the Job to -2, grants CREATE EXTENSION vector, wires the
embed lane and opens llm's ingress; it still pins main-79, so -2 would fail the same way.
Doing now, in one pass on #1784: bump newTag to main-80-9354215da29143378c4eb20383863101fbe573d9,
add libpq timeouts (PGCONNECT_TIMEOUT) to the gateway, enable auto-merge, watch the Flux row go
Ready and the Job complete. Worktree: scratchpad/wt-1784. The main-verdict gate (#1783) is done.

## RESUME HERE (2026-09-05, the salvaged work is merged and main is green)

Eight pull requests landed: the five carrying the salvaged worktree work (#1758 #1759 #1760 #1761
#1764), then #1772 #1776 #1778 fixing what only the merged state could reveal -- offline-gate is
skipped on pull requests by design and grades main, so the canary's admission failures appeared
after the merge, and two sessions fixing them at once left the file first duplicated and then
empty. main 09f84d9d, ci run 33961399543, every job green including offline-gate.

Open: the prospector `https-cyrus` listener needs the founder's word. Recommendation: give it its
own Secret prospector-edge-cyrus-tls, because prospector-main/deploy/k8s/base/edge.yaml:284-291
records that one failed order on a shared certificate took all thirteen live names down on
2026-08-31.

Also open: six commits on two prospector branches now pushed (fix/crew326-shim-respects-hookspath,
ci/stale-pr-policy) still need a decision on whether they deserve pull requests.

## RESUME HERE (2026-09-05, salvaged work being merged)

PR #1761 (main was red on four gates) is merged. Three salvaged pull requests are in flight:
#1758 canary (crew#656), #1759 Trivy Operator (crew#846), #1760 feature register and pricing
(crew#857). Each was rebased on main and its own failures fixed: the alert row for trivy-system,
the yarn.lock entry for @backstage/plugin-scaffolder-react, a rotated TSX file reassembled, the
nested-kustomization double render that panicked the kyverno CLI, and the live image question
moved to the daily oke-check run so it does not fail a runner with no cluster.

Open, and the reason for the branch fix/cyrus-route-attaches: the cyrus HTTPRoute still cannot
attach. prospector-edge has no https-cyrus listener and no wildcard, the cyrus namespace lacks
the idp.estate/edge-attach label the listeners select on, and its default-deny has no ingress
allowance from the prospector namespace where the Gateway's data plane runs. The listener and
its certificate are a change in the prospector repository and are the founder's call.

# Checkpoint

## RESUME HERE (2026-09-05, worktree salvage)

Clearing the leftover repository copies on the Mac. 106 -> 39 already done (62 removed, all of
them fully backed up on GitHub). The remaining 39 hold work that exists nowhere else: 32 with
uncommitted edits, and about 27 branches with commits ahead of origin/main.

Founder said "go": commit every dirty worktree as a `wip: salvage ...` commit, push every branch
to origin (ci.yml runs only on pull_request/main, so branch pushes cost no CI), then remove all
39 worktrees and prune. Ten of the 39 point at directories that no longer exist and only need
`git worktree prune`.


## RESUME HERE — the agent workforce (crew#850)

The founder asked for three things in a row on 2026-09-05: take CrewAI to its full advanced
surface, rename it to something general rather than "infra", and get it right because "we
[are] setting up a company and [a] proper crew". The design, the research and the checkpoints
are all on https://github.com/chidionyema/crew/issues/850.

**Where the work is.** `~/dev/code/infra-crew`, branch `crew850-agent-workforce`. The pass in
flight renames the package `infra_crew` to `agent_workforce`, the environment prefix
`INFRA_CREW_*` to `AGENT_WORKFORCE_*`, and the queue from the single label `lane:infra` to the
general lane set already on the board. After that comes the feature adoption: a Flow with
structured state and `@persist`, `CheckpointConfig` so a killed pod resumes, `MCPServerAdapter`
against the estate MCP server, a `PRE_TOOL_CALL` hook that raises `HookAborted` on merge,
deploy, dispatch and cluster verbs, the unified `Memory` class, native `planning`, and the
version move from 1.9.3 to 1.15.20.

**Two measured facts that shape it.** The `lane:infra` label never existed on the board, so the
CronJob has matched nothing on every run since it was deployed — that is why "we have it set up"
produced nothing. And the estate MCP server offers nine tools including `remember`, `recall` and
`get_workload_logs`, which replaces our own `tools/estate.py`, while the github route offers only
six read tools, so the write path still needs the official GitHub MCP server (CP7).

**Cannot be verified on this Mac.** It is an Intel machine, and `crewai==1.15.20` depends on
lancedb, which publishes no macOS x86_64 wheel. Verification is the repository's own CI on
ubuntu, not a local run.

**Other lanes.** idp#1656 (the one-shot cleanup) is open with auto-merge on and deletes the two
crew539 incident tests that are the last red on idp#1521 (Cyrus). idp#1521 also carries the
CA-bundle fix, commit 92196da5. The founder still owes two calls on crew#850: CrewAI AMP against
self-hosting, and whether the customer-facing agent surface is CrewAI's frontend protocol or
Backstage. BuilderPack, which he sent as an input, is recorded on crew#846.

## RESUME HERE
Otto answers nothing because the bulk lane points at `fast`, a model the live LiteLLM router does
not serve and the router's family map does not know: every inbound message logs
`policy defect: model 'fast' is in no family mapping`. The router serves exactly two models
(`kimi`, `minimax`, measured from inside the gateway pod). Fix in flight: bulk and verify lanes to
`kimi` in platform/otto-gateway/deployment.yaml and platform/otto-golden/deployment.yaml.

## RESUME HERE

Otto is silent. #1688 merged (bulk lane -> gemini) but PR #1678 claims the running router
serves only kimi and minimax, so gemini may fail at the router. Landing kimi from #1678, and
fixing the ns-fences NetworkPolicies: hindsight has no egress declared at all, so it cannot
reach estate-rw.estate-db (its Postgres) or the llm router. Branch fix/fences-enforce-and-otto-lane.

## RESUME HERE (2026-09-05 03:25Z)

Otto answers nothing: the running otto-gateway pod still carries
OTTO_ROUTER_LANE_BULK_MODEL=fast and logs `policy defect: model 'fast' is in no family
mapping` on every inbound message. Main already says kimi (234f7373, #1678, merged 03:12Z).
The otto-gateway Flux row is stuck at revision 010dda52 (applied 02:15Z), Ready=False
DependencyNotReady. It waits on five rows, one of which — estate-db-migrate — has been
False for 13h; its one-time Postgres copy Job (estate-db-copy-otto-gateway-r3) completed
58m ago, so that guard is spent and is now a permanent brake.

STAGED: branch fix/otto-lane-unblock, worktree under the session scratchpad, drops
estate-db-migrate from otto-gateway's dependsOn in clusters/oke/platform.yaml so the merged
kimi lane can land. Remove the worktree when the PR merges.

Second defect seen in the same log, not the cause of the silence: hindsight memory recall
times out on every message (hindsight-api.hindsight.svc:8888); its Flux row is False on
`dependency llm is not ready`.

## RESUME HERE (2026-09-05 04:05Z)

Founder instruction: "try deepseek" — move Otto's bulk and verify lanes off kimi, which the
router accepts but answers with an empty completion (probe otto-answer-probe-29809680, 03:59Z:
judgment/minimax ok 1595 ms, bulk/kimi 2730 ms empty, verify/kimi 26 ms empty).

Change bulk and verify to deepseek in all three places in one pass so the test cannot drift
from the door again: platform/otto-gateway/deployment.yaml, platform/otto-golden/deployment.yaml,
platform/otto-gateway/answer-probe.yaml. judgment stays minimax (otto/router/config.py refuses
judgment and bulk sharing a model family; deepseek and minimax are distinct).

Prior context: #1717 merged 03:57:07Z fixed the probe's stale model names and the duplicate
estate.otto alert group; monitoring-rules Flux row True at 03:59:49Z, so both Otto alerts exist
again. Cluster reads from this Mac are blind since ~04:02Z — OCI session expired, founder is
refreshing with bin/idp-oci-login. Verification of the deepseek change needs that session back.

## RESUME HERE

**Left mid-flight:** idp PR #1784 (`feat/otto-memory-store`) — Otto L2 memory: embedding lane wired,
two-sided `llm` fence, `vector` extension on the `otto-gateway` Database, Job renamed
`otto-memory-store-2`. All checks green. It must be rebased onto the main commit where Flux bumps
`platform/otto-gateway/kustomization.yaml` `newTag` off `main-79-0a94c6a3...` before it lands, or the
Job starts on an image with no `otto.memory.migrate` — that is exactly how `-1` failed.

**Switched to:** the controls budget. 432 `tests/test_incident_*.py` files in idp, 1835 test
functions, 90% of the test tree. Only 10 run a real gate against a fixture; 422 are pure assertions.
`docs/reference/incidents/2026-08-30-three-incidents-one-defect.md` already rules that a control at
rung 2 or above requires deleting the weaker one it subsumes, and that subtraction was never done.
Founder, 2026-09-05: "this incident test thing is a farce", "its basically patching and
firefighting", "i dont want any of that in this estate", "fix problems at root cause level and batch
once and for all", "shows laws are not being followed". Branch `chore/controls-budget`.
