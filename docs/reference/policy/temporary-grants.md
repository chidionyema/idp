# Temporary grants

**How an agent gets write access to this estate, and why it cannot keep it.**

Founder, 2026-09-08, verbatim: *"do NOT use static keys or manual revocation. Implement
Just-In-Time (JIT) short-lived tokens using the native Kubernetes TokenRequest API and Oracle's
equivalent. The agent must request a TTL (Time-To-Live) token via my Telegram/phone. When I
approve, the system mints a token that mathematically auto-revokes when the TTL expires."*
Record: `~/.claude/docs/founder/2026-09-08T0609Z-you-are-completely-right-to-question-that-and-996c7f35.md`.

## The rule in one line

**Every agent is permanently read-only. Write access exists only for minutes, only after a tap on
the founder's phone, and it ends because a clock ran out — never because somebody remembered to
take it away.**

## The three states an agent can be in

| State | What it holds | How it ends |
|---|---|---|
| Normal, always | `agents:agent-reader` — reads on the whole cluster, writes on nothing | never; this is the resting state |
| Granted, minutes | one grant from the catalogue, at the TTL the founder saw | the token expires on its own |
| Break-glass | the founder's own principal, loudly, with a written reason | a human decision, recorded in `break-glass.log` |

`bin/idp-kube auth whoami` answers `system:serviceaccount:agents:agent-reader`, and a write
answers `Forbidden`. That is the acceptance line for the whole workstream, and it is true on main:

```console
$ bin/idp-kube auth whoami
Username   system:serviceaccount:agents:agent-reader
Groups     [system:serviceaccounts system:serviceaccounts:agents system:authenticated]

$ bin/idp-kube patch externalsecret jit-broker -n jit --type merge -p '{}'
Error from server (Forbidden): externalsecrets.external-secrets.io "jit-broker" is forbidden:
User "system:serviceaccount:agents:agent-reader" cannot patch resource "externalsecrets"
```

## What happens when an agent needs to write

1. **The agent names a grant.** It cannot describe a permission; it picks a row from
   `platform/jit/grants.yaml` and fills the parameters that row declares.

   ```console
   $ idp-jit ask --grant raise-memory-limit --namespace backstage --workload backstage \
                 --memory 2Gi --why "the Backstage pod is OOM crashing" --ttl 10m
   ```

2. **The founder's phone shows that row** — the grant, the namespace, the workload, the reason and
   the clock — with three buttons: `Approve 10m`, `Deny`, `Stop the broker`.

3. **On approve, one of two things happens**, and which one is a property of the grant, not a
   choice made at the time:

   - **`mode: token`** — the broker mints a Kubernetes ServiceAccount token through the
     **TokenRequest API** with the TTL the founder saw. Nothing revokes it. It stops working
     because it expired.
   - **`mode: broker-applies`** — the broker performs the exact parameterised change itself and
     hands back the result. **The agent never holds the verb.**

4. **The agent carries on.** `idp-jit ask` blocks until the tap, so an agent that hits the wall
   does not fail and does not report back — it waits. Exit codes are the contract: `0` granted,
   `3` denied, `4` refused before he was asked, `5` the approved change failed, `6` he never
   answered.

## Why two modes, and why that is not a detail

Kubernetes RBAC has no field-level scope. `patch deployment` is not the small permission it reads
as: whoever holds it can change `serviceAccountName` to a privileged account, or add a `hostPath`
mount, and escalate straight out of the grant. So **for every verb that can rewrite a pod spec the
agent gets an outcome, never a token.** `bin/idp-jit-grants` refuses any escalating grant that asks
for `mode: token`, so this is a property of the file rather than a habit anybody has to keep.

The same reasoning covers every layer under Kubernetes. A short-lived cloud key on a laptop is
still a key that can be copied inside its window, so **no temporary cloud credential is ever issued
to an agent** — the OCI, DNS and GitHub grants are all `broker-applies`.

## The catalogue

Six grants, and nothing outside this file can be asked for — which means nothing outside it can be
approved by a tired founder at 3am either.

| Grant | Layer | Mode | TTL | Rate |
|---|---|---|---|---|
| `raise-memory-limit` | kubernetes | broker-applies | 10m | 3/hour |
| `restart-workload` | kubernetes | token | 5m | 4/hour |
| `rollback-image` | kubernetes | broker-applies | 10m | 2/hour |
| `oci-scale-node-pool` | oci | broker-applies | 10m | 2/hour |
| `dns-point-record` | dns | broker-applies | 10m | 2/hour |
| `github-rerun-failed-checks` | github | broker-applies | 5m | 3/hour |

**30 minutes is the ceiling the file may declare.** The revoke is the token expiring, not a cleanup
job running, so a long life is not a convenience — it is the guarantee getting weaker.

Changing `platform/jit/grants.yaml` is **glass-break, permanently**: no auto-merge, no
self-approval, the founder's own review or nothing. `bin/idp-glass-break` is what enforces that —
it refuses a green check standing in for his review on the broker, the catalogue, the RBAC floor
and `bin/idp-kube`.

```console
$ idp-jit grants          # every grant, its layer and what it takes
$ python3 bin/idp-jit-grants   # the gate: no escalating verb as a token, no wildcard, no secrets,
                               # no core namespace, a TTL under the ceiling and a declared rate
```

## The record

Every ask, refusal, approval, denial, grant and expiry is appended to a **hash-chained, HMAC-signed
ledger**. Each line carries the hash of the one before it, so a removed or edited line is
arithmetic, not opinion.

The file on the broker's volume is the write-ahead copy and is `fsync`ed before anything else
happens. **Every record is then shipped to the estate's collector** (OTLP over HTTP), because a
ledger whose only copy is one node's disk is one hardware failure away from gone. Delivery is
best-effort on purpose: a collector outage costs delivery, never the record, and never the grant —
a broker that refuses a 3am approval because a metrics pipeline is unreachable has turned an
observability outage into an access outage.

## The stop button

Every message the broker sends carries `Stop the broker`. Tapping it writes a flag to the broker's
volume, so **a broker restarted mid-incident comes back still stopped**, and records `stopped` in
the ledger. Nothing is granted while that flag exists.

## What this does not do yet

- **`/ask` has no authentication.** `asked_by` is self-asserted, so anything that can reach the
  broker's port in-cluster can put a name on a request. The founder still sees and approves every
  one, so this is a provenance gap rather than an access gap — but it is a gap.
- **The broker has no public door.** An agent reaches it in-cluster or over the tailnet; an agent
  on a cloud runner cannot reach it at all yet.
- **The repository has no `CODEOWNERS` file.** The comment at the top of
  `platform/jit/grants.yaml` says one names the founder on `/platform/`, and it does not exist;
  `main` is not branch-protected either. So the no-self-approval rule is carried entirely by
  `bin/idp-glass-break` and by sessions obeying it, not by GitHub refusing the merge.
- **It has never been exercised end-to-end against the live cluster.** That costs the founder one
  tap, and until it happens the correct state for this system is `UNKNOWN`, not working.

## What is refused, and stays refused

- A standing IAM grant minted by hand in a provider console. That is not a temporary grant; it is a
  permanent one with a person as the audit trail. **R52: one root per provider, set once, then
  code** — see [Root trust](root-trust.md).
- A grant that widens the phone bridge to `cluster-admin`.
- A token for any verb that can rewrite a pod spec.
- Anything not already in `platform/jit/grants.yaml`.
