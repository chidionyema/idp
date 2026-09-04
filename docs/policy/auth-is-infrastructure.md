# Auth is infrastructure: The extreme-code-review pattern

Founder, 2026-09-02, on finding webhook secret-checking code written into an application
("note this pattern down for extreme code review," and the edict of the same night:
"If a requirement can be handled by cluster infrastructure ... it is STRICTLY FORBIDDEN
to write application code for it"). This page is the durable record; every code review
in the estate grades against it.

## The rule

A capability the platform already owns is never re-implemented in an application.
The application stays completely ignorant of it.

| Requirement | Where it lives | Never in |
|---|---|---|
| Inbound auth (secret headers, shared-key signatures) | an exact match rule on the route, or the login proxy | application code |
| Retry and timeout | the mesh or the gateway | application code |
| Data shape checks | a strict schema or an admission policy | hand-rolled checks |
| Secrets | the vault, through the vault-fed secret or a Flux substitution | literals, environment plumbing |

The worked example: Otto's Telegram webhook. The wrong build checked the
`X-Telegram-Bot-Api-Secret-Token` header inside the application (deleted the same
night, 2026-09-02). The right build is an exact header match on the route
(`platform/otto-gateway/httproute.yaml`, which since crew#768 is the estate's one
door for an inbound channel): the gateway forwards only a POST whose header equals
the vault-fed value; the pod holds no auth code at all.

## What review flags (the dragon classes)

1. **Application-level auth**: any inbound token parsing or secret checking in a
   service. Move it to the route or a policy; delete the code and its tests.
2. **Schema-compensating tests**: a unit test asserting a single file's shape that a
   strict schema or an admission policy could refuse. Tests that pin agreement across
   files (a vault key name matching in the secret manifest, the deployment and the
   runbook) are not this class — no schema sees across files; they stay.
3. **Masked pipes**: a shell pipe where the left side's exit code decides nothing.
   Turn on pipefail or check the code explicitly; a pipe inside a command substitution
   with its own explicit failure branch is already loud.

## Why

Application auth code is a second implementation of a platform layer: it drifts, it
needs its own tests, its bugs become published vulnerabilities (the same door has one
on record against the upstream bot framework), and a buyer's engineer takes it apart
in one sitting. The route's match rule is declared in git, provable from the manifest,
and rotates with the vault.
