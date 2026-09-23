# 2026-09-18 — FleetView to enterprise, and the two things blocking it

**Status:** code complete and committed; two cluster-side actions outstanding, both founder-gated.

## What this session actually fixed

Three defects, each found by the founder trying to use the thing rather than by a test.

### 1. The board was a beautiful UI over a table nobody filled

`catalog/estate.db.sessions` held **three hand-written demo rows** (`fleet-live-001/002/003`,
tasks like "Build fleet CP3 stop/approve/deny"), and the schema's own comment admitted it:
*"nothing in this repo writes these tables yet."*

`bin/estate-session-recorder` is that writer. It reads agents that already record themselves —
pi and claude-code transcripts, `~/.estate/claims.jsonl` — and writes real rows. **3 fixtures →
23 real sessions** with real models, real spend, real state.

Every board complaint traced here: buttons with nothing real to act on, TRACE answering 503
because no session had a trace, STOP returning 500 because there was no live session.

### 2. Buttons that lied, and a process that started half-configured

From the real backend log:

```
POST /nudge   200 | POST /approve 502,502 | POST /deny 502,502 | POST /stop 404 then 500
```

`approve`/`deny` had only a `sovereign` branch, and the `else` **recorded a failed attempt** —
so routes.py returned 502, "attempted and failed", when nothing had been attempted. Now a
`SIGNAL_RUNTIMES` table decides, and a missing channel is **422** naming the verb, the runtime
and the steer that does work. No audit row for a request that never reached a session.

`serve.py` also started with an empty environment and served traffic it could not serve.
`config_guard.py` refuses that start; `ESTATE_DB` is the only required var, and the banner names
what is off.

### 3. The laptop credential path was a circle

`idp-oci-login` renders `~/.oci/config` from `secrets/dev/OCI_*.yaml`, deleted by commit
`76ba8be` when the dev secrets moved to OCI Vault — and reading OCI Vault needs an OCI identity.
**Three scripts re-created the circle, and each one's only advice was another that could not
help.** `idp-oci-bootstrap` exited 100 with no output at all.

`bin/idp-oci-session` removes the vault from the path that never needed it: `oci session
authenticate` needs a **region** and a **tenancy name** — identifiers, public in every console
URL — not a secret.

## The two things still outstanding, both gated on the founder

| # | action | command | unblocks |
|---|---|---|---|
| 1 | one browser sign-in | `bin/idp-oci-session --region uk-london-1 --tenancy chidionyema` | the whole laptop path |
| 2 | the cluster's secret ceiling | *(agent work, after 1)* | Flux, Backstage, the sidecar |

After (1), the agent does the rest: `idp-cloud` → `idp-mac-secret-deliver` → agent key →
`agent-reader` → cluster reads.

## The cluster problem, measured

```
admission webhook "oke-resource-leak-protection.oke.com" denied the request:
Cluster has 2650 secrets and the limit is 2000.
```

**2650 against a 2000 limit.** OKE refuses *every* new resource → **30 Flux objects NotReady**
→ Backstage, Crossplane, commerce, otto-gateway, prospector, via-negativa all stalled.
**This is why the sidecar cannot deploy** — not certificates, not ExternalSecret config.

It is not one stupid thing: **2 declared Secret manifests** in the repo, ~2648 created
dynamically (Helm revisions, cert-manager renewals, ExternalSecret materialisations), with
`history-max` set on no HelmRelease and nothing pruning.

## What is now law

`docs/reference/policy/enterprise-operating-model.md` gained two standards, each with a gate:

- **6. Headroom Is Guarded, Not Discovered** — the ceiling declared in `estate-defaults.yaml`,
  the count published by `bin/idp-cluster-state`, `history-max` required on every HelmRelease.
  Gate: `rule=secret_headroom`, three fixtures proved both ways.
- **7. One Click To A Device, Nothing By Hand** — states that production's OIDC path is the
  reference and must not be "fixed"; records that the laptop path was a bootstrap bug, not a
  security feature; forbids a Renew button ("re-minting agent-reader is not a decision").

## Corrections made this session, on the record

- **Bitwarden was a red herring.** The ticket claiming `idp-cloud` consumes a Bitwarden machine
  token is wrong: `grep BITWARDEN bin/idp-cloud` → nothing. ADR 0017 splits machine vs
  human-born secrets and says nothing about an OCI-session exchange.
- **"Opus → deepseek, 97.7%"** compared a June Claude Code baseline to this session's deepseek
  mix. Cross-tool, cross-vendor, cross-month. Withdrawn as a claim about what happened here.
  The real measured number is **pro ×22.6 cheaper than pro, on identical tokens**.
- **The mechanism chain does not cause the cost saving.** It reduces payload tokens 61.79%
  (A/B, seeded fixture, tiktoken); the cost saving is tier routing. Two different effects.
- **The disk did not eat `bin/idp-oci-login`.** A `rm -rf /private/tmp/homebrew-* bin/idp-oci-login`
  one-liner took two paths. The disk was a real, separate problem.
- **My test suite held the OAuth callback port and broke a real sign-in.** An orphaned
  `oci session authenticate` held port 8181; Oracle then told the founder his credentials did
  not match. Fixed structurally: the test uses a stub `oci` and cannot bind the port.

## Commits

```
66426fe3 fix(oci): stop the suite hijacking the real sign-in, and stop hiding the CLI's error
1af7171d feat(state): publish secret headroom, so the ceiling is seen before it blocks a deploy
8ae8b3c2 feat(policy): standards 6 and 7 — headroom is guarded, and one click to a device
2d1f99e6 feat(oci): bin/idp-oci-session, so the browser login is reachable without the vault
8822ec42 feat(guard): report a full disk before it costs a file
9ba6161f feat(local): bin/serve-fleetview, the one launcher, so a laptop run is configured by design
22d00825 feat(board): the acknowledgement loop, and the 22 test failures the card-grid left behind
2a586609 feat(board): the board is fed by reality, not by seeded demo rows
46d9f89f fix(fleetview): the buttons that lied, and a process that starts half-configured
131d4b53 feat(ops): guided local handoff for device authorization, not portal-delivered secrets
5daf5aae feat(ops): Device access tile — state, one button, no terminal, self-renewing
eb8daaca test(efficiency): A/B + ablation, reproducible, in real tokens
9742d9dc feat(efficiency): every mechanism proves, per call, what it saved
f9ea405c fix(bootstrap): a script that cannot work says why, and stops sending you in circles
```

## Tests at close

284 frontend, 27+ backend across this session's suites. Two pre-existing failures
(`test_fleetview_cp1/cp2`) verified unchanged with these edits stashed.

## What is verified vs not

| claim | status |
|---|---|
| board shows 23 real sessions, 1 running, real spend | ✅ observed live |
| steer → directive → consumed → `acknowledged=true` | ✅ observed live, session `pi:01a0b023b` |
| approve/deny on claude-code → 422, not 502 | ✅ observed live |
| fail-fast guard refuses a half-configured start | ✅ observed |
| `idp-oci-session` reaches the browser login | ✅ verified via stub |
| `oci session authenticate` completes | ❌ **not verified** — needs the browser |
| secret pruning works | ❌ **not started** — needs the cluster read |
| device states `active`/`expiring`/`expired` | ❌ unit-tested only; this device is `not_provisioned` |
