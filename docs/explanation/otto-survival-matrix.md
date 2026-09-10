# Otto's survival matrix

Three homes that fail independently, crossed with sixteen inference lanes that refill on
different clocks — and one lane at the bottom that has no clock at all.

Otto has never been stable once. The reason is not that any single piece is weak. It is that
every piece has been in the same place. This note fixes the place, not the piece.

## The mistake this corrects

The previous attempt gave Otto five model lanes — MiniMax, Groq, Gemini, OpenRouter and a
direct line — and called them homes. They were not. All five were entries in one ConfigMap,
read by one sidecar, in one pod, on one cluster. They shared a node, a CNI, a load balancer, a
scheduler and a quota, so they shared every way of dying.

> "this route is still tied to our cluster, the cloudflare one is clear, the macbook is clear
> … by sophistication I mean a matrix of combinations"
>
> — Founder, 2026-09-10

A **home** is a failure domain: a place Otto runs that can die without taking the others with
it. A **lane** is a vendor that does the thinking. The two are independent, and the
sophistication is in the crossing.

### The second mistake, found while writing this

A fallback chain concentrates every request on lane one. Groq's free ceiling is 1,000
requests a day — measured, not quoted: its own `x-ratelimit-limit-requests` header said so on
2026-09-10. Under a chain, Groq drains to zero every afternoon and the ladder is permanently
one lane shorter for the rest of the day.

So the chooser does not walk a list. It spends **the lane with the most headroom left relative
to its own refill window**, which drains every lane at the same rate and makes them all reach
empty at the same moment — the arrangement that maximises the time before *any* lane is empty.

## The matrix

If all three homes could reach the same things, this would be three copies of a list. The
cells marked **only here** are what make it a matrix.

| | Home 1 · Cluster<br><small>OKE → Traefik → otto-gateway</small> | Home 2 · Cloudflare<br><small>Worker on the global edge</small> | Home 3 · MacBook<br><small>over the tailnet (WireGuard)</small> |
|---|---|---|---|
| **The 14 cloud lanes** | reachable | reachable | reachable |
| **Workers AI**<br><small>@cf/llama-3.3-70b</small> | — | **only here** — in-process, no network, no account id, no key: the binding *is* the credential | — |
| **Local Ollama**<br><small>qwen2.5-coder:7b</small> | over the tailnet | — no tailnet from the edge | **the floor** — on the metal, no quota and no refill clock |
| **Memory, tools, estate**<br><small>the real Otto</small> | **only here** — conversation history, the catalogue, every tool | — degraded, and says so | — degraded, and says so |
| **Telegram can reach it**<br><small>the door</small> | while our DNS and load balancer live | **always** — anycast, up when our cluster is a hole in the ground | only with a public door the founder opens |

Read down a column for what one home can do alone. Read across a row for how many homes
survive losing any one thing. No row is empty in fewer than two columns.

## The lane ledger

A free tier is not a switch that is on or off. It is a replenishing resource with a refill
window, and sorting by window is what turns "live forever" from a hope into arithmetic.

Figures marked **measured** came from the vendor's own rate-limit headers inside our cluster or
from this laptop on 2026-09-10. Every other limit is a published claim and stays a claim until
a header confirms it.

| Lane | Free ceiling | Refills | Credential | How we know |
|---|---|---|---|---|
| **NVIDIA NIM**<br><small>integrate.api.nvidia.com</small> | 10,000 req/day, 40 rpm | daily, per model | to mint | Published. The largest permanent free tier found, and per-model — three models is 30,000. |
| **Cerebras** | 1,000,000 tok/day | daily | to mint | Published. Highest token volume of any no-card tier. |
| **Cloudflare Workers AI**<br><small>`env.AI` binding</small> | 10,000 neurons/day | daily | none needed | Published. The binding is the credential — this retires the objection at `platform/vendors/consoles.yaml:387`. |
| **Google Gemini** | 1,500 req/day, 15–30 rpm | daily, per model | estate holds | **measured** — 2.5-flash-lite answered in 0.82s and made the tool call; plain 2.5-flash did not. |
| **Groq** | 1,000 req/day, 8,000 tok/min | daily | estate holds | **measured** — its own `x-ratelimit-limit-requests` header. 0.48s, 119 tokens, tool call made. |
| **GitHub Models** | 150 req/day mini, 50 frontier | daily, per model | estate holds | Published. Authenticates with the GitHub token CI already uses — zero new credential. |
| **Mistral** | $10 of credit | monthly | to mint | Published. A monthly clock, so it is the lane to lean on when the daily ones are spent. |
| **Cohere** | 1,000 calls/month | monthly | to mint | Published. Non-commercial terms — fine for the founder's own assistant, not for a product. |
| **MiniMax** | account balance | account | estate holds | **measured** — today's default lane, answering from inside the pod. |
| **Kimi · DeepSeek** | account balance | account | estate holds | Keys already in the registry. DeepSeek has answered 401 since 2026-09-04 — a lane on paper, not in fact. |
| **OpenRouter** | 50 req/day | daily | estate holds | **measured** — of four free models tried, one timed out, one 403'd, one 429'd, one answered in 8.68s. Last resort by evidence. |
| **Hugging Face router** | $0.10/month | monthly | to mint | Published. The allowance is negligible; the value is one token reaching 19 providers when a direct lane is blocked. |
| **Aion Labs · LLM7 · OVH** | 15 / 10 / 2 rpm | per minute | to mint | Published. Too small to carry load; each is one more thing that also has to be down. |
| **SiliconFlow · ModelScope** | 1,000 rpm / 2,000 req/day | daily | **identity check** | Both require government-ID verification against a Chinese account. Held out of the design deliberately. |
| **Kaggle GPU** | 30 GPU-hours | weekly | to mint | Already specced as a training launcher (`docs/specs/2026-09-09-forge-kaggle-second-launcher.md`). As an inference lane it needs a tunnel — the one genuinely new build here. |
| **Ollama on the MacBook**<br><small>on the metal, over the tailnet</small> | **no ceiling** | **never — no clock** | none at all | **measured** — answering now: HTTP 200 in 0.044s on loopback, 200 over the tailnet by address. Slow to generate; impossible to exhaust. |

!!! warning "The trap that reports home 3 dead while home 3 is answering"
    The Mac answers `HTTP 200` when addressed by its tailnet IP and `HTTP 403` when addressed
    by its MagicDNS name — Ollama refuses a `Host` header it does not recognise. A probe
    written against the name grades a working home as down. `bin/idp-otto-homes` reads
    `TailscaleIPs` from `tailscale status --json` for exactly this reason.

## The arithmetic

Otto survives any day whose demand is under the total daily capacity of its lanes. Adding a
vendor adds to that total. These figures count only lanes needing no identity check and no card.

| | |
|---|---|
| **Free requests a day** | **12,750** — NIM 10,000 · Gemini 1,500 · Groq 1,000 · GitHub 200 · OpenRouter 50 |
| **Independent vendors** | **16** — every one has to be down at once before the cloud tier is gone |
| **Homes that must all die** | **3** — Oracle's cloud, Cloudflare's global network, and a laptop on a desk |
| **Floor beneath all of it** | **∞** — Ollama on the metal: no quota, no refill window, nothing to exhaust |

The floor is the whole argument. Twelve thousand requests a day is a large number, but it is a
number, and a number can be reached. The lane at the bottom of the ladder has no number, so the
ladder has no last rung. Otto degrades — slower, no memory, no tools — but there is no state in
which he is silent.

## The door

Multi-homing the brain is the easy half. The door is harder, because Telegram accepts exactly
one webhook URL per bot — today `otto.${ESTATE_ZONE}/webhook/telegram`, which
`platform/otto-gateway/registration-reconciler.yaml` calls "the one door" in a comment. A brain
with sixteen lanes behind a door with one hostname still has one way to die.

So the door is not multiplied. It moves to the home that cannot be partitioned from Telegram,
and that home fans out to the others.

1. **Telegram calls Cloudflare.** Anycast, present in every region, with no dependency on our
   DNS, our load balancer or our cluster.
2. **The edge forwards to the cluster first, every time.** Home 1 is the only home that
   remembers the conversation and holds the tools, so a degraded answer is never preferred
   while home 1 can be had. It gets 8 seconds to say hello.
3. **Then the MacBook, if it has a public door.** It runs the real Otto and costs no vendor
   quota at all. Opening that door exposes the founder's laptop, so it stays shut until he
   says otherwise.
4. **Otherwise the edge answers, and says that it is the edge.** Every degraded reply opens by
   naming the home and the lane. An assistant that silently degrades teaches its owner to trust
   a quality it is no longer delivering — and the degradation is itself the outage alert.

## Where it stands

`bin/idp-otto-homes` asks each home a question only a working home can answer, and reports in
the estate's three-state vocabulary. This is its real output from 2026-09-10.

| Home | Probe | Verdict |
|---|---|---|
| 1 · Cluster | `otto.${ESTATE_ZONE}/healthz` | `MEASURED_OK` HTTP 200 — full Otto: memory, tools, the estate |
| 2 · Cloudflare | `lifeboat-llm.${ESTATE_ZONE}/health` | `MEASURED_FAIL` no answer — written and tested, 20 of 20 behaviour tests green with no network touched, but not deployed |
| 3 · MacBook | tailnet address `:11434` | `MEASURED_OK` HTTP 200 — Ollama is up and serving models |

### What is honestly not done

- Home 2's credential exists in code but not yet in the vault. The first deploy attempt failed
  with Cloudflare error 10000, *Authentication error* — measured, not assumed: the estate's DNS
  token reads the zone (the account id derived cleanly) and cannot upload a script, which is
  correct scoping, not a defect. So `bin/idp-bootstrap-cloudflare` now mints a second token from
  the same standing root — Workers Scripts Write and Workers AI Write on the account, Workers
  Routes Write on the zone — and proves it can list the account's scripts before the vault write.
  Running that mint is one button: **Backstage → Run the estate bootstrap → scope `cloudflare`,
  mode `live`**. Until it has run, home 2 stays `MEASURED_FAIL` and the matrix is two homes wide.
- The headroom-aware chooser is designed here and not yet written. The code as it stands still
  walks a chain.
- NIM, Cerebras, Mistral, Cohere and the Hugging Face router are researched, not minted. They
  are the difference between 2,750 and 12,750 requests a day.
- Otto's actual daily demand has never been measured, so the headroom above it is unknown.
  Only the capacity is known.
- Moving Telegram's webhook to the edge repoints the founder's live assistant. That is his to
  authorise in his own words.

## Door (from the UI)

Backstage → Docs → Explanation → *Otto's survival matrix*. The live grade of the three homes
appears on the Otto component page; nothing here needs a terminal to read.

---

Sources for published limits: the awesome-free-llm-apis registry, OpenRouter's 2026 free-API
comparison, GitHub community discussion #149698, and Hugging Face's Inference Providers
documentation. Measured figures came from probes run inside the otto-gateway pod and from this
laptop on 2026-09-10, and are named as measured in the ledger.
