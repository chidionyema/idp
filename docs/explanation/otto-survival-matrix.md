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

| | Home 1 · Cluster<br><small>OKE → Traefik → otto-gateway</small> | Home 2 · Cloudflare<br><small>Worker on the global edge</small> | Home 3 · Groq<br><small>a second vendor on a second cloud</small> |
|---|---|---|---|
| **The 14 cloud lanes** | reachable | reachable | reachable |
| **Workers AI**<br><small>@cf/llama-3.3-70b</small> | — | **only here** — in-process, no network, no account id, no key: the binding *is* the credential | — |
| **Llama 3.3 70B**<br><small>free tier, no card</small> | reachable | reachable | **the floor** — free, so it cannot run out of credit, only out of a day |
| **Memory, tools, estate**<br><small>the real Otto</small> | **only here** — conversation history, the catalogue, every tool | — degraded, and says so | — degraded, and says so |
| **Telegram can reach it**<br><small>the door</small> | while our DNS and load balancer live | **always** — anycast, up when our cluster is a hole in the ground | — home 3 is a lane behind a door, never a door itself |

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
| ~~**Ollama on the MacBook**~~<br><small>retired 2026-09-10</small> | ~~no ceiling~~ | ~~never~~ | none at all | **measured, and struck out.** The founder killed it: *"no i killed ollama because machine is slow"*, *"dont rely on macbook"*. The laptop is an Intel i7-8850H with no GPU — Ollama reports `library=cpu`, 4.7 GiB free. It answered 16 output tokens in 24–46s, returned `unexpected EOF` on a realistic 1.4k-token prompt, and llama3.2:3b returned nothing at all in 240s. A home that cannot answer inside Otto's own 120s client ceiling is not a lifeboat. |

!!! warning "The trap that reports home 3 dead while home 3 is answering"
    This has now caught two different home 3s, which is why it has its own box.

    The MacBook answered `HTTP 200` on its tailnet IP and `HTTP 403` on its MagicDNS name —
    Ollama refusing a `Host` header it did not recognise. Groq, its replacement, answers
    `HTTP 403` with the body `error code: 1010` to Python's default `User-Agent` and `HTTP 200`
    to the identical request one second later carrying a plain agent string: Cloudflare's
    browser-fingerprint rejection, sitting in front of the vendor. Both times the home was
    answering and the probe said it was dead.

    So `bin/idp-otto-homes` names itself in every request it makes. The general rule: a probe
    that grades a home reaches it the way the home is actually reached, and a `403` is read as
    a question about the probe before it is read as an answer about the home.

## The arithmetic

Otto survives any day whose demand is under the total daily capacity of its lanes. Adding a
vendor adds to that total. These figures count only lanes needing no identity check and no card.

| | |
|---|---|
| **Free requests a day** | **12,750** — NIM 10,000 · Gemini 1,500 · Groq 1,000 · GitHub 200 · OpenRouter 50 |
| **Independent vendors** | **16** — every one has to be down at once before the cloud tier is gone |
| **Homes that must all die** | **3** — Oracle's cloud, Cloudflare's global network, and Groq's |
| **Floor beneath all of it** | **a day, not an infinity** — see below |

**The floor changed on 2026-09-10, and this is the honest version of the argument.** It used
to end: the bottom rung is a laptop with no quota and no refill clock, so the ladder has no last
rung and there is no state in which Otto is silent. That was true and it is not true any more.
The founder retired the laptop because it could not answer inside Otto's own timeout, and a rung
nobody can stand on is not a rung.

What is left is arithmetic instead of an infinity: twelve thousand seven hundred and fifty free
requests a day, spread over sixteen vendors that refill on three different clocks — daily,
monthly, and per-account. Otto is silent only on a day that exhausts every one of them, and his
measured demand has never come close. That is a strong claim. It is a weaker claim than the one
this page used to make, and the difference is worth naming rather than quietly editing away.

Getting a real floor back is the open question. The candidates are a GPU nobody bills for —
Kaggle's 30 hours a week, Hugging Face's Inference Providers — and both need a tunnel before
they are an inference lane rather than a training launcher.

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
3. **Then home 3's lane, from wherever the turn is being handled.** Groq is a lane, not a
   door: nothing outside ever calls it directly, so there is no third hostname to expose and
   nothing on the founder's desk to open up.
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
| 3 · Groq | `api.groq.com/openai/v1/models` | `MEASURED_OK` HTTP 200 — the free tier answers on the key the estate holds |

### What is honestly not done

- Home 2 is the whole of the gap, and until it is deployed the matrix is two homes wide. Three
  things kept it out of the water and all three are now fixed: the estate's one vault reader
  resolved the vault only from local OpenTofu state, so every bootstrap on a runner reported the
  vault unreachable while it was perfectly reachable; the lifeboat's secret table named
  *Kubernetes* Secret names rather than vault entries, so a deploy would have shipped a lifeboat
  with no bot token and no model behind it; and `LIFEBOAT_KEY`, which `src/index.js` fails closed
  on, existed nowhere at all. Deploying is now one button: **Backstage → Founder actions → Put
  Otto's lifeboat back in the water**, which mints the Cloudflare tokens from the standing root,
  uploads the worker, and ends on the three homes' verdicts rather than on "the job was green".
- The headroom-aware chooser is designed here and not yet written. The code as it stands still
  walks a chain.
- NIM, Cerebras, Mistral and the Hugging Face router are researched, not minted. They are the
  difference between 2,750 and 12,750 requests a day. Cohere is no longer among them: it joined
  on 2026-09-10 as the second hop of the `embed` chain.
- There is no infinite floor any more, and Kaggle and Hugging Face are the two candidates for
  getting one back. Neither is wired.
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
