# One SRE signal plane over the existing authorities

Status: accepted

Date: 2026-11-08

## Context

The estate already runs independent critical-function, lane, truth, progress, incident and telemetry controls. During the November 2026 outage those controls produced useful raw evidence, but no single projection connected the facts: public doors were timing out, their DNS resolved to one OCI load balancer, both backend sets were critical, and the founder-facing visibility path was inside the same failed surface.

Adding another probe collection would duplicate existing authority and would not close the synthesis gap.

## Decision

Build one SRE synthesizer that consumes the existing authorities and publishes a signed, freshness-labelled snapshot.

The plane:

- treats `BLIND` and `STALE` as first-class failure states;
- groups failures by dependency and failure domain;
- computes deterministic service objectives from snapshot history;
- emits one agent projection and one founder projection from the same snapshot hash;
- publishes through the existing receipt bucket and Fleetview;
- creates or updates one issue per failure domain rather than one per symptom.

## Alternatives considered

### Replace the existing probes

Rejected. The critical-function spine, lane drill, truth instrument and incident loop each have a distinct authority and existing tests. Replacing them would create migration risk without adding evidence.

### Add a second dashboard-only collector

Rejected. A dashboard that probes independently becomes another source of truth and still leaves agent execution blind.

### Put the collector in the cluster

Rejected as the only home. The cluster cannot report its own total loss. Cloud-hosted collection is required, and local collection remains necessary for host-only evidence.

## Consequences

- Source freshness and vantage become part of every projection.
- A green aggregate is impossible while any required source is blind.
- Incidents remain owned by the existing incident loop.
- The collector can be unavailable without changing the state of underlying services; publication freshness exposes that.
- Future providers and services are added by contract configuration, not new dashboard code.

## Proof

The contract test and collector tests must falsify:

- green-with-blind-source;
- uncorrelated reporting of one shared dependency failure;
- fabricated SLOs before the sample floor;
- missing or stale snapshot publication;
- divergent agent and founder state hashes.
