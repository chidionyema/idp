# Every deployable has a release identity

Status: proposed

Date: 2026-11-08

## Context

The estate has several components called "router". They were deployed without a shared way to
name the component, its interface version, its source revision or the exact configuration running
in production. Agents consequently inferred authority from process names, local paths and stale
memory. The same failure applies to web surfaces, workers and adapters.

## Decision

Every deployable component must publish a release envelope with these fields:

- `contractId`: stable component identity, for example `estate.model-router`.
- `schemaVersion`: semantic version of the machine interface.
- `release.version`: semantic version of this deployed implementation.
- `release.id`: immutable release identifier.
- `release.sourceSha`: exact Git commit built into the artifact.
- `release.artifactDigest`: immutable image, archive or file digest.
- `release.configDigest`: exact deployed configuration digest.
- `release.deployedAt`: deployment timestamp.
- `release.healthUrl` and `release.authority`: the live health endpoint and the role this
  component is allowed to perform.

The health response must echo `contractId`, `release.id` and `release.sourceSha`. A client that
cannot verify the contract and release identity must become read-only. It must not infer
authority from a hostname, process name, local port or remembered state.

For routing specifically, `estate.model-router` is the only authoritative model-inference role.
The Rust control router and the Mac LiteLLM fallback are separate roles and cannot claim that
identity.

## Enforcement

Deployment is incomplete until:

1. the release envelope validates against `catalog/release-envelope.v1.schema.json`;
2. the live health response echoes the same release identity;
3. the founder surface shows component ID, version, source SHA and health together; and
4. the capability catalogue points to the envelope rather than duplicating its values.

## Consequences

Rollback becomes a release selection rather than a filesystem guess. Agents can identify the
authority and deployed bytes without archaeology. Existing components need an adoption slice;
until adopted they are reported as `UNVERSIONED`, which is never healthy.
