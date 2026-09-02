# Auth is infrastructure: the extreme-code-review pattern

Founder, 2026-09-02, on finding webhook HMAC validation written into application code
("note this pattern down for extreme code review", and the edict of the same night:
"If a requirement can be handled by cluster infrastructure ... it is STRICTLY FORBIDDEN
to write application code for it"). This page is the durable record; every code review
in the estate grades against it.

## The rule

A capability the platform already owns is never re-implemented in an application.
The application stays completely ignorant of it.

| Requirement | Where it lives | Never in |
|---|---|---|
| Inbound auth (tokens, secret headers, HMAC) | Gateway API HTTPRoute match, oauth2-proxy, Kyverno | app code |
| Retry / timeout | the mesh / gateway | app code |
| Data shape validation | a strict schema (CRD, kubeconform, Kyverno) | hand-rolled checks |
| Secrets | vault → ExternalSecret → mount / Flux substitution | literals, env-var plumbing |

The worked example: Otto's Telegram webhook. The wrong build validated
`X-Telegram-Bot-Api-Secret-Token` inside `otto.boot` (deleted, hermes-v2 branch
`otto/webhook-secret`, 2026-09-02). The right build is an exact header match on the
HTTPRoute (`platform/otto-staging/httproute.yaml`): the gateway forwards only a POST
whose header equals the vault-fed value; the pod has no auth code at all.

## What review flags (the dragon classes)

1. **App-level auth**: any inbound token parsing, HMAC or header validation in a
   service. Move it to the route or a policy; delete the code and its tests.
2. **Schema-compensating tests**: a unit test asserting a single file's shape that a
   strict schema or admission policy could refuse. Cross-file agreement tests (a vault
   key name pinned across ExternalSecret, deployment and runbook) are NOT this class —
   no schema sees across files; they stay.
3. **Masked pipes**: `a | b` where the left exit code decides nothing. `set -o
   pipefail` or an explicit rc check; a pipe inside `$( )` with its own `|| { ... }`
   guard is already loud.

## Why

Application auth code is a second implementation of a platform layer: it drifts, it
needs its own tests, its bugs are CVEs (GHSA-3vpc-7q5r-276h is the same door), and a
buyer's engineer takes it apart in one sitting. The gateway match is declarative,
provable from the manifest, and rotates with the vault.
