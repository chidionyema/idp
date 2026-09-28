# Demo: take Otto's cluster away and watch him keep answering

**Door (from the UI):** Backstage → **Create** → *Which home is Otto on?* — one button, no
parameters. It asks Otto a real question through his own switch and the run names the home that
produced the token: a MiniMax model id is home 1 or 2, `qwen2.5-coder` is the founder's laptop.
The rows after it say whether the other two homes are there if that one goes. Nothing below
needs a terminal; the terminal lines are here so a buyer's engineer can reproduce the claim
rather than take it.

## What this shows

Otto is the founder's personal assistant. Before 2026-09-09 he had one brain: the estate's
LiteLLM router, reached across the cluster network. Every shared failure in the estate was an
Otto outage — and on 2026-09-09 a single broken VXLAN link between the two workers took out
CoreDNS, the SigNoz collector, one router replica and Otto in one stroke.

He now has three, in three different failure domains:

| home | where it is | dies when |
|---|---|---|
| 1 | the estate router, `litellm.llm.svc.cluster.local:4000` | OKE pod networking breaks, or the router pod does |
| 2 | a direct vendor line, `api.minimax.io`, no cluster hop and no router | pod egress to the internet breaks, or the vendor does |
| 3 | Groq, `api.groq.com`, free tier, `openai/gpt-oss-120b` | Groq does, or the day's 1000 free requests are spent |
| 4 | Gemini, free tier, `gemini-2.5-flash-lite` | Google does, or that tier is spent too |
| 5 | OpenRouter, a free slug — last, and never counted on | it already fails often; see the onboarding page |

Home 3 was the founder's Mac on Ollama until 2026-09-10, when he killed it: *"no i killed
ollama because machine is slow"*, *"dont rely on macbook"*. The laptop is an Intel i7-8850H
with no GPU; it could not answer a real prompt inside Otto's own timeout. Nothing about Otto
depends on that machine any more.

Homes 3, 4 and 5 are all free, so the floor cannot run out of credit — the one property the
laptop was ever chosen for. They are three different vendors on purpose: a free tier ends, and
the answer to *"what if the limit is reached"* is another vendor, not a bigger promise. A
spent lane is parked for five minutes on its first 429 (`allowed_fails: 1`) so the turns behind
it go straight past it.

The switch is the same `litellm` binary the estate already runs, as a sidecar in Otto's own pod
on `127.0.0.1:4010`. Reaching it crosses no Service, no DNS, no CNI and no node.

## Demo

**1. Otto is on home 1, and home 1 is the estate router.**

```
bin/idp-kube -n otto-gateway exec deploy/otto-gateway -c otto-brain -- \
  sh -c 'wget -qO- http://127.0.0.1:4010/health/liveliness'
```

Expect `"I'm alive!"`.

**2. Ask him something through the door and see which home answered.**

Send any message to Otto on Telegram. Then:

```
bin/idp-kube -n otto-gateway logs deploy/otto-gateway -c otto-brain --tail=20 | grep -i "selected model\|fallback"
```

Expect the estate lane name (`minimax`) and no fallback line: home 1 answered.

**3. Take home 1 away.** This is the demo's whole point, so do it for real rather than by
argument. Scale the estate router to zero:

```
bin/idp-kube --break-glass "three-homes demo: prove Otto survives losing the estate router" \
  -n llm scale deploy/litellm --replicas=0
```

**4. Ask him again on Telegram.** He answers. The log now names the hop:

```
bin/idp-kube -n otto-gateway logs deploy/otto-gateway -c otto-brain --tail=30 | grep -i fallback
```

Expect a fallback to `home-direct` — the vendor line, with the cluster router gone.

**5. Take home 2 away too**, by denying the pod's internet egress, and ask a third time. He
answers from the laptop on your desk: the log names `home-mac`, and the reply comes back from
`qwen2.5-coder:7b` over the tailnet.

**6. Put it back.**

```
bin/idp-kube --break-glass "three-homes demo over: restore the estate router" \
  -n llm scale deploy/litellm --replicas=2
```

## What you have just proved

The assistant answered the founder with the estate's model router scaled to zero, and again
with the estate's internet egress gone. There is no configuration in which Otto is silent while
the founder's laptop is on and Telegram can reach the door.

## The honest edge

- Home 3 is a 7B model on a laptop. It is a competent assistant, not the frontier lane; a long
  tool-using turn will be slower and shallower there. It is the floor, not the ceiling.
- Homes 2 and 3 carry no spend ledger and no Langfuse trace. Every happy-path turn is home 1
  and is fully accounted; a lifeboat turn is recorded in the sidecar's log and nowhere else.
- If the founder's laptop is shut and both cloud lanes are down, Otto is silent. Three homes,
  not infinite.
