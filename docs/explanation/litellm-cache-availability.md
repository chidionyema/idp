# The model router's cache runs one replica on purpose

The model router runs as two pods, and until pull request 1244 each pod kept its own
private copy of the state that should be shared: provider cooldowns, budget spend, rate
counters and the answer cache. The router's own startup banner said so — limits were
enforced once per worker, twice in total. Pull request 1244 gave the two pods one small
shared memory: a single bounded Redis (192 MB, least-recently-used eviction, password
minted in-cluster), plus an exact-match answer cache with a five-minute life.

## Why one replica, when the availability standard demands two

The availability standard refuses any one-pod workload in a founder-facing area of
the cluster, because one pod is one node event away from an outage. For almost everything
that rule is right. For this cache it is exactly wrong: two plain Redis replicas behind
one Service name are two caches that disagree. Each router pod would learn a different
half of the cooldowns and budgets, which is precisely the split-state defect the cache
exists to remove. A second naive replica moves the failure; it does not remove it.

What a node event costs here is cache hits, not answers. The router pods keep serving
without their cache; they fall back to per-worker state until the pod returns. That
trade is recorded honestly in `platform/availability.yaml` (surface `llm/litellm-cache`,
issue 1184), and the named remedy is Redis Sentinel or a managed Redis — real
replication with one writer, not two independent stores.

## Why the policy exception exists

The first landing of the cache (pull request 1182) was reverted the same night (pull
request 1192): the admission policy refused the one-replica Deployment, and because the
cluster's apply step checks every object in the llm layer together, the refusal wedged
the whole layer and everything that depends on it — healing, hindsight and the infra
crew all stopped reconciling. The waiver row was written, but a waiver in a YAML file is
invisible to the admission webhook.

`platform/edge/litellm-cache-exception.yaml` is the admission-side half of that record:
a PolicyException scoped to exactly one Deployment by name, excepting only the two
replica rules. Every other rule still grades this workload, every other workload in the
model-routing area is untouched, and the router itself stays at two spread replicas. It
lives in `platform/edge` beside the estate's other exceptions because the admission policy honours an exception
only from its own area of the cluster, and that directory applies independently of the layer
being excused — an exception riding inside the llm layer could never unwedge it.

## When this page dies

Issue 1184 retires the exception: when Sentinel or a managed Redis lands, the cache
meets the standard on its own and both the exception file and this page are deleted.
