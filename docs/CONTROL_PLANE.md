# Estate control plane — policy off the machine

Status: local client verified; remote key custody specified, not deployed. This document is the
canonical reference. If it disagrees with a script, the script is wrong.

## 1. Principle

The laptop holds no authority to define its own rules. It holds a pinned public key and a verified
policy cache. Policy is signed off-machine. There is no local signing path and no override flag.

    phone / remote control plane          this machine
      policy.key  (never here)             policy.pub (pinned once)
      sign policy bundle                   verify signature
      epoch++ on every change              reject rollback below floor
      Telegram approval                    adopt cache, enforce it

## 2. Components

| Component | Path | Role |
|---|---|---|
| Policy client | ~/.estate/bin/estate-policy | fetch, verify, adopt; no signing |
| Pinned key | ~/.estate/policy/policy.pub | trust anchor, written once |
| Cache | ~/.estate/policy/policy.json + .sig | last verified policy |
| Epoch floor | ~/.estate/policy/epoch.floor | anti-rollback |
| Cage | ~/.estate/cage/cage.py | token + sandbox execution |
| Broker | ~/.estate/cage/cage_broker.py | request, approve, revoke |
| Telegram adapter | ~/.estate/cage/cage_tg.py | structured approval only |
| Founder gate | ~/.estate/bin/estate-founder-gate | the only channel to the founder |
| Yield protocol | ~/.estate/bin/estate-protocol | YIELD/1 numeric records |
| Escalation | ~/.estate/bin/estate-escalate | ESCALATE/1 only |

## 3. Invariants

| ID | Invariant |
|---|---|
| C1 | The private policy key is never on this machine |
| C2 | No local flag can mint, edit, or bypass policy |
| C3 | Unsigned, tampered, expired, or rollback bundles are refused |
| C4 | The verified cache is the only policy the gate reads |
| C5 | A policy fetch failure fails closed; the last good policy stays, no silent default |
| C6 | Every founder message is YIELD/1 or ESCALATE/1; prose is a logged violation |
| C7 | A violation-log write failure returns 500, never a silent success |
| C8 | Revocation is an epoch bump; the floor refuses older bundles |

## 4. Zero-cost deployment

Option A, Cloudflare Worker + KV (free tier):

    /policy        returns signed policy JSON
    /policy.sig    returns the detached Ed25519 signature
    /grant         Telegram-authenticated approval; not exposed without auth

The Worker secret holds the private key. KV holds the current policy and epoch. Nothing is added to
the laptop except the pinned public key.

Option B, static signed bundle on any HTTPS host. Same verification; lower operational complexity,
manual rotation.

Telegram approval: bot callback with secret header, chat allowlist, nonce, 60s freshness, TOTP for
high risk. The bot does not hold policy authority; it signals the control plane.

## 5. Operator runbook

    # off-machine (phone/password manager/Worker secret)
    estate-policy keygen            # never run on the laptop for production
    estate-policy sign policy.json  # produces policy.json.sig

    # on the laptop
    estate-policy fetch https://<control-plane>/policy
    estate-policy check             # POLICY OK version=.. epoch=..

    # change policy
    edit on control plane -> sign -> epoch++ -> publish
    laptop fetch adopts only if signature valid and epoch >= floor

    # revoke
    epoch++ -> publish -> laptop fetch -> old grants invalid

    # break-glass
    founder-signed record naming agent, action, expiry; audited; no standing bypass

## 6. Verification

    estate-policy check                  # signed cache
    cage-demo                            # 11/11 allow/deny/replay/revoke
    cage-tg-demo                         # 5/5 Telegram callback checks
    estate-protocol demo                 # prose rejected, numbers accepted
    estate-founder-gate                  # 422 prose, 200 valid, violations logged
    curl -s http://127.0.0.1:4320/violations
    curl -s http://127.0.0.1:4300/yield

## 7. Residual risk, stated plainly

Root on this laptop can delete the client, replace the pinned key, or ignore the gate. Signed policy
prevents authorized configuration drift; it does not defeat a root attacker. True closure requires
execution off this machine or a locked OS with an unprivileged agent user. Until then, this is a
control plane against mistakes and drift, not against root.

## 8. Related documents

- Cage architecture: ~/.estate/cage/ARCHITECTURE.md
- Enrollment: ~/.estate/cage/ENROLLMENT.md
- Security map: ~/.estate/cage/SECURITY_MAP.md
- Build plan: ~/.estate/cage/BUILD_PLAN.md
- Recursive factory: ~/.estate/protocol/RECURSIVE_FACTORY.md
- Founder gate: ~/.estate/founder-gate/PROTOCOL.md
- Yield protocol: ~/.estate/protocol/PROTOCOL.md
