# 0037. Every critical service gets a ladder of homes, and a drill that measures them

- Status: DECIDED 2026-10-28. Founder: "and lastly recurring drill that verifies these critical
  lanes"; "so our estate can never go down like this again"; "we attempted to do something like
  this for otto, always available so we need to formalist this for all critical services multi
  cross platform fallback so our estate can never go down like this again"; and, on capacity,
  "the router failing because of casopacity is a disaster and should never have happend, we ate
  blind to the capacity issue and should be proactive rather than reactive".
- Date: 2026-10-28
- Deciders: founder
- Design: [the spec](../specs/2026-10-28-the-fallback-ladder-and-the-drill.md)
- Amends: [0034](0034-workloads-are-placed-by-the-free-tier-not-by-the-cluster.md) (the free
  tier decides placement; this adds that the free tier's **allowance is a design constraint on
  every critical service**, and that a design which exceeds it is refused by a vendor's 400
  instead of by the estate)
- Amends: `AGENTS.md` §7a — no. The routing law stands: the cloud is the default route, the
  laptop is the fallback, the free floor is not reversed.

## The ruling

1. **Every critical service has at least three homes, in at least two providers' failure
   domains.** A home is a place the service runs that can die without taking the others with
   it. The estate's own cluster is never the only first rung.
2. **The switch between homes needs no human and fails over on the answer**, not on the
   connect: a home that answers 5xx, stalls, or refuses a model the caller may use is passed
   over; a 4xx that is the caller's own fault is relayed unretried.
3. **The last rung is free**, so the floor cannot run out of credit.
4. **A recurring drill measures every lane** — `bin/idp-estate-homes`, on a schedule — and a
   dead lane becomes a **ticket**, not a log line. The verdict vocabulary is Otto's
   (`MEASURED_OK`, `MEASURED_FAIL`, `UNKNOWN`): a lane nobody asked is `UNKNOWN`, never OK.
5. **The ladder is configuration**, not code: `platform/ladder/critical-lanes.json`. Adding a
   home is a line in a file.
6. **Capacity is measured before the apply, not after the refusal.** The estate asks the free
   tier for what the free tier gives: one A1 node, one LiteLLM replica, and a capacity guard
   that reads the compartment and compares it with the declared allowance before anything is
   created.

## Why, measured

On 2026-10-28 the router lost every model. The cloud answered 503 and then 504; the front
decided the route on the connect and relayed the failure while a healthy lane sat unused; the
estate's only other lane was the founder's laptop; and Otto's Cloudflare edge — the "always
available" home the founder remembered — did not resolve
(`dig +short lifeboat-llm.mumchimp.com` → nothing). The cause underneath the outage was
capacity the estate never measured before the apply:
`(400, LimitExceeded, false) You cannot create a volume because you have reached your limit.`
and `400-LimitExceeded, LimitExceeded: nodes-per-node-pool limit has been exceeded.`

A fallback that is not measured is a hope, and a capacity question that is not asked before the
apply is answered by a vendor at the worst possible moment.
