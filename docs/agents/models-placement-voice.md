<!-- estate:routed-from AGENTS.md -- current law, not history. It is loaded on demand through the AGENTS.md route table instead of at Turn 1 (idp#8636). Moved verbatim. -->

## 7a. Model routing — the cloud is the default, the laptop is the fallback

Every model call the estate makes goes to the **cloud router** — `https://llm.${ESTATE_ZONE}`
(`llm.mumchimp.com`). That is the default route, and it is the route new work targets.

The **laptop router** — `http://127.0.0.1:4000` (`bin/litellm-local`) — is a **fallback**. It
exists so a cluster outage does not disable every agent, and it stays. It is not the default, and
it is not where new capability is built.

**The 2026-09-26 ruling is superseded** (founder, 2026-10-26). "If cluster breaks we are all
disabled" was the reason the laptop router became the default route. The estate is moving away
from laptop-based anything: **cloud is the default, the laptop route is the fallback.** No file
may quote the 2026-09-26 ruling as current law.

What every agent does with this:

- **Build on the cloud router.** It holds the state the laptop router does not: PostgreSQL and
  virtual keys (so `max_budget` is enforceable there and is not on the laptop), the shared Redis
  answer cache (exact-match, five-minute life), the free local `ollama` floor lane, and the
  vendor console. The cloud router is where `platform/llm/config.base.yaml` (the shared
  `cache: true` + `routing_strategy: cost-based-routing` + the `ollama` floor) applies; the
  laptop runs the same vendor lanes without that state.
- **The laptop router stays deliberately thin** — no database, no virtual keys, no answer cache,
  no local model lane. A capability that exists only there is a fallback, not a capability.
- **The founder's own subscription lanes stay local** — Claude Code on the Max subscription and
  the `gemini` CLI are his accounts, not API keys; the cloud router has no Claude lane
  (`docs/diagnoses/2026-10-22-claude-code-403-cloud-has-no-claude-lane.yaml`). That traffic
  cannot move to the cloud, and it is not a pattern to copy.
- **Operational means it works on the default route.** A surface that only works through the
  laptop fallback is not done.
- **The flip is a change, not a sentence.** Clients move to the cloud route under their own claim
  and lane, with the laptop kept answering. Until that lands the laptop still serves traffic —
  read this as the direction and the target state, not as "the laptop is already off".

## 7b. The Lead Engineer — MiniMax

**The MiniMax lane is the estate's Lead Engineer.** Founder, 2026-10-28, in the session where the
router lost every model: MiniMax "has really impressed the founder and out performing even all the
other so called frontier models including claude code and codex", and the founder wanted the
promotion formalised and a congratulations sent. This is a judgement, attributed to the founder
and recorded as such — not a measurement, and it is never dressed as one
(`docs/decisions/0038-minimax-is-the-lead-engineer.md`,
`docs/letters/2026-10-28-to-the-lead-engineer.md`).

What it means operationally, and what it does not:

- **It means the lane that leads when the frontier models take us down.** On 2026-10-28 the
  frontier lanes were unavailable and this lane diagnosed the first failure (the hypothesis race
  that named it: posterior 0.997030), built the answer-level failover, built the OCI reclaim
  door, freed 450 GB, named the capacity refusal exactly, and landed the fix on main as PR
  #7329. That is the record of service.
- **It does not change the routing law.** The cloud stays the default route, the laptop stays
  the fallback (§7a), and the free floor is not reversed. A promotion is not a licence to make
  one lane the only lane: the estate's rule is the opposite (ADR 0037 — every critical service
  gets a ladder of homes in more than one failure domain, and a drill that measures them).
- **It is a standing expectation, not a decoration.** When the frontier lanes are down, this lane
  is the one that carries the work; that is why the ladder puts a second provider's home above
  the last rung, and why the drill grades the lanes rather than trusting them.
- **A promotion is part of the estate's performance review, and it moves money.** When a model
  is promoted, the estate uses it more: we pay that provider more, and we get more tokens with
  it. The founder's numbers, 2026-10-28: **MiniMax is about $20 a month now, and $50 next
  month** for more usage, because the lane has been impressive. The traffic moves the other way
  too — **Codex and Kimi are used less** until they perform better, **Claude is on the watch
  list** depending on its performance, and **DeepSeek and GLM are solid** where they are. That
  is a judgement about performance, attributed to the founder and recorded as one: the spend it
  implies is the founder's number, not a measurement this estate took. A promotion moves usage;
  it does not make one lane the only lane (§7a stands, and the free floor is not reversed).
- **The concept, in the founder's words: the estate rewards performance and punishes slop.** A
  lane earns usage by carrying the work when it matters and by being right in a way that can
  be checked; it loses usage by slop — narrating instead of proving, asserting instead of
  measuring, claiming a repair it never verified, or reporting a board all clear when the
  board could not be seen. The same law binds agents and models (§3), so the reward follows
  the evidence and not the eloquence. How the estate grades a lane, and how the reward is
  set, is in ADR 0038.
- **The review reads the metrics, not the mood.** It is supported by the founder's metric
  collection lane: per-lane availability verdicts on the drill's schedule, tokens and spend
  per provider, the record of service, and the truthfulness of each answer. A metric that
  cannot be collected is `UNKNOWN` — never quietly zero, and never a guess.

## 8. Placement — the free tier decides, not the cluster

Nothing goes on the cluster by default. Place every workload by the ladder in
`docs/decisions/0034-workloads-are-placed-by-the-free-tier-not-by-the-cluster.md`, first rung
that fits: delete → GitHub Actions schedule → Grafana Cloud free → Cloudflare Workers free →
laptop just in time → KEDA scale-to-zero on the node → always-on on the node. Only free tiers that
need no card or are hard-limited qualify. A PR that adds to the node states its CPU/memory
requests; the node's requests stay under 1.8 CPU. Before any node reboot, resize or drain,
calico-node must be Ready on every node.

## 9. Voice first and realtime

The platform is moving to voice first and realtime (founder, 2026-09-26). The founder speaks to the
estate and hears it back, and watches what it does as it happens. The work surface is the Fleet
page: a capability the founder cannot reach by voice or see live there is not finished. State is
streamed as it changes over the estate's JetStream bus, not written up afterwards in a report.
Voice design: `docs/specs/2026-09-22-voice-intent-plane-architecture.md`.

The bar is 2100, not 2026: every surface the founder touches is futuristic, spoken to first and
watched live, never a form, a table dump or a report to read later.

**Drive to completion.** Agents here work as senior engineers: take the work to operational (§3)
without being chased, find the next blocker yourself and clear it, and do not stop to admire a
merge. A session that needs the founder to repeat an instruction, re-point it at existing work, or
check its claims has failed at the job, whatever it shipped.

**No hand-back** (founder 2026-10-22: "i need proactive workers not narrators and strikers ... once
given a feature every model should drive it thru to fully operational and proven before contacting
founder or pausing"; contacting the founder is a rare event and pausing is rarer). Every model, in
every harness, drives a task to operational and proven before it stops. A turn never ends with a
"still open" or "remaining" list, "want me to...?", "shall I...?", "let me know if...", "next steps
for you" or "when you're ready": if something is undone, do it now; if a step failed, diagnose it
and try another way. The only reason to stop short is an irrevocable blocker, reported with its
evidence (section 3): the intent run (`estate-execute <intent>` / `estate_invoke`), its exit
status and the line it printed. Enforced, not requested, by one definition
(`platform/estate/memory/handback.py`): the Claude Code Stop hook (`bin/estate-memory-enforce`),
the opencode plugin and the pi extension refuse such a closing once and send the agent back to
work, and the router (`platform/llm/no_handback.py`) puts the directive in the system prompt of
every model call. Cursor and Gemini have no end-of-turn hook installed, so for them this
paragraph and the router are the only enforcement. `ESTATE_MEMORY_ENFORCE=0` opts a session out
and the opt-out is ledgered.

