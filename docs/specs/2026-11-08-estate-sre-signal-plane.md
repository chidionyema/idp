# Estate SRE signal plane

Status: accepted

Date: 2026-11-08

## Goal

Give every agent and the founder one live, freshness-labelled answer to:

1. Is the estate working now?
2. What is failing, where is it failing, and what else shares that failure domain?
3. What can we not see, and why?
4. Which service objective is consuming error budget fastest?
5. What should be repaired first?

The plane is a synthesis and publication layer. It does not replace the critical-function spine, the estate-homes drill, the incident loop, estate-progress, estate-truth, OCI health, Fleetview or the founder surface.

## Existing authorities

| Concern | Authority |
|---|---|
| Critical-function liveness and goals | `catalog/critical-functions.json` and `critical-watch.py` |
| Cross-provider service ladders | `platform/ladder/critical-lanes.json` and `idp-estate-homes` |
| Founder-path predicates | `estate-truth.py` |
| Incidents and repair ownership | `incident-loop` and `~/.estate/state/incidents.db` |
| Delivery progress | `estate-progress` |
| OCI load-balancer and backend health | OCI CLI |
| Agent and founder projections | `Fleetview` and the shared founder surface |

The SRE plane must consume those sources. It must not add a second probe with the same meaning.

## Signal model

Every source result has:

```json
{
  "id": "oci-lb",
  "state": "OK|DEGRADED|DOWN|BLIND|STALE|NOT_HERE",
  "summary": "short machine-safe statement",
  "observedAt": "ISO-8601",
  "ageSeconds": 12.4,
  "vantage": "laptop|cloud|sandbox|unknown",
  "failureDomain": "oci-lb|cloudflare|model-provider|github|founder-client",
  "evidence": {}
}
```

States are not interchangeable:

- `DOWN` means a question was asked and the answer proves failure.
- `BLIND` means the question could not be asked from this vantage.
- `STALE` means evidence exists but is older than its declared limit.
- `NOT_HERE` means the question belongs to another node, not that the node failed.
- `DEGRADED` means the authority answered but missed its goal or redundancy requirement.

`BLIND`, `STALE` and `NOT_HERE` can never be counted as healthy.

## Planes and coverage

The estate is represented by weighted planes:

- founder path
- model routing
- memory and context
- agent execution
- agent continuity
- cloud substrate
- public doors and identity
- delivery
- observability
- security and secrets

Each plane declares required source IDs and a freshness limit. A missing required source is a blind spot, even when all observed sources are green.

## Dependency and correlation analysis

The synthesizer groups failures by `failureDomain`. Two or more failing public doors on the same OCI load balancer produce one `CORRELATED_FAILURE` finding, not fourteen unrelated incidents.

The projection groups those findings again by domain for display and issue ownership. A provider-wide
symptom that is explained by the sharper OCI load-balancer finding is not emitted as a second root
cause.

The projection includes:

- affected planes and services;
- shared failure domain;
- current evidence;
- blast radius;
- the single highest-leverage repair.

## Service objectives

Each SLO declares:

- objective (`target`);
- rolling window;
- source predicates;
- error-budget policy.

The first release measures only evidence available in stored snapshots. With fewer than the minimum samples, the result is `LEARNING`, never a fabricated green.

The rolling history is an aggregate object in the receipt bucket, downloaded before each cloud run.
Ephemeral runners therefore learn from earlier runs instead of resetting every SLO to zero samples.

The projection reports:

- observed availability;
- sample count;
- confidence;
- burn rate (`observedErrorRate / allowedErrorRate`);
- time to exhaustion when the burn rate is stable and greater than one;
- freshness of the evidence behind the number.

## Proactive rules

The first release raises deterministic findings for:

1. a required source that is blind or stale;
2. a critical plane that is down or degraded;
3. repeated failure over consecutive snapshots;
4. multiple services failing through one failure domain;
5. error-budget burn above 1;
6. agent capacity below the executor safety floor;
7. no fresh independent confirmation from a second failure domain.

Findings are ranked by founder impact, blast radius, irreversibility and burn rate. A model may explain a finding; only deterministic evidence may create or close it.

## Agent and founder projections

One snapshot and one hash back both surfaces:

```json
{
  "agent": {
    "state": "CRITICAL",
    "headline": "13 of 14 estate doors are unreachable",
    "topAction": "repair OCI load balancer backends",
    "canClaimHealthy": false
  },
  "founder": {
    "state": "CRITICAL",
    "headline": "...",
    "confidence": 0.86,
    "blindSpotCount": 2,
    "freshnessSeconds": 18
  }
}
```

The founder view always shows freshness and blindness. It never hides them behind an aggregate percentage.

## Publication

The scheduled collector publishes:

- `state/sre` in the estate receipt bucket;
- `state/sre.md` as the founder-readable brief;
- `state/sre-history` as the rolling signed-snapshot history;
- a JSON artifact;
- a Markdown operational brief;
- one stable GitHub issue per current failure domain;
- an `/api/sre` founder-surface route reading the same snapshot.

The collector is idempotent. Repeated runs update evidence and timestamps; they do not create duplicate issues.

GitHub issues carry the hidden marker `<!-- estate-sre-domain:<domain> -->`. The collector updates or
closes only issues carrying its own marker and does not touch lane tickets or human-authored incidents.

## Failure modes

| Failure | Required response |
|---|---|
| Probe runner loses network | `BLIND`; preserve last snapshot and mark stale |
| OCI authentication expires | `BLIND` on infrastructure plane; other planes remain measurable |
| Incident API unreadable | `BLIND` for ownership plane; do not claim incidents are zero |
| Snapshot publish fails | Surface local collection success separately from publication failure |
| Source returns incompatible schema | `BLIND`; never guess field meanings |
| Two authorities disagree | preserve both observations and mark `CONFLICT` |

## Acceptance

The slice is operational only when:

1. the same snapshot hash is returned to agent and founder projections;
2. a dead OCI load balancer reports `DOWN`, and its public doors are grouped as one correlated failure;
3. a source that cannot be read reports `BLIND`, not zero or healthy;
4. service-objective output remains `LEARNING` until the configured sample floor;
5. the scheduled workflow publishes a fresh artifact and maintains one issue per failure domain;
6. tests falsify healthy, blind, correlated, stale and degrading cases;
7. no secret value appears in any snapshot, issue, log or dashboard.

## Scope of first release

The first release consumes the existing critical-function spine, estate-homes, estate-truth,
estate-state, progress, incident, agent-session, OCI and DNS authorities. It does not create a
second scheduler, incident store, router or session ledger.

Agent token headroom and model-context capacity are not present in the current cloud authority
snapshot. The cloud projection therefore reports `capacity=UNMEASURED` and cannot claim the agent
plane healthy from a session count alone. Adding that evidence is the next adapter, not a reason to
infer capacity.
