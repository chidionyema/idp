# RESUME HERE — 2026-09-02 ~01:3xZ (.wt-eye-breaker, session 54539261)

## Current thread: OTTO COMMERCIAL-INSTALL READINESS MAP (founder order 2026-09-02)
His words: "focus on otto readiness for comercial install, seamless all the way from
beginning, lets map current fragile process end to end." Deliverable = a map of the
CURRENT fragile process (assessment, not fixes), git-committed. Three read-only Explore
lanes in flight: (1) idp platform side of otto/hermes-agent install, (2) hermes-v2
product portability, (3) the authoritative Otto spec/records inventory.
Peer overlap: session a2aed3c9 owns otto-staging + idp#1123 + the self-service-tenancy
decision (origin/docs/self-service-tenancy @ d838734a — already read; one shared bot +
start-link, OttoTenant composition, order of work). Do not touch their lane; my map
cites their record.

## Done this session (all pushed)
- DEEP AUDIT delivered: idp feat/security-end-to-end @ c2fb97d7
  (docs/security-audit-2026-09-02.md, 4 P0s; end-to-end doc corrected). Founder
  acknowledged receipt 2026-09-02 and redirected to Otto.
- idp PR 1124 merged (main 3a73ec9b); feed publisher cured (~/.claude/scripts branch
  fix/feed-publish-state-mirror; local main 1 ahead, protected — known).
- Decisions awaiting his GO: 0016 Metabase (feat/metabase-login-decision @ 9ce4ebe6),
  0017 Bitwarden (feat/bitwarden-decision @ 64c4a4cd). Telegram secret hand still open.

## Next step when agents report
Compile one end-to-end map: customer-pays -> otto-answers, each step graded
(founder-hand / agent / code / missing), fragility named with file:line; commit on a new
idp branch (docs only) as estate-agents[bot], push, no PR; feed handoff; reply.
