# Brief for DeepSeek — paste this whole file

You are writing code for a Kubernetes platform called `idp`. You do not have the repository, the
cluster or any credential, and you will not be given one. Everything you need is below. Return
**complete files, ready to commit** — no placeholders, no "add your logic here", no pseudo-code.
Where you are unsure of a local detail, write the file anyway and add a short `# UNSURE:` comment
on that line saying what you assumed; those get checked against the repository, and a guess that
is labelled costs nothing while a guess that is silent costs a day.

---

## 1. The platform, in one screen

Kubernetes on Oracle Cloud, two nodes, v1.35. Everything is GitOps: **Flux is the only writer of
the cluster.** A human's `kubectl apply` is refused by admission — "Git is the only writer of this
cluster; change the file on main and Flux applies it". The one excused identity is the service
user `estate-ci`, which GitHub Actions assumes through OIDC identity propagation. So anything that
must touch the cluster is either a file Flux reconciles or a step in a GitHub workflow.

What runs, and it matters because you must extend it rather than replace it:

- **CNI:** flannel (`kube-flannel-ds`), and nothing else. **This is the defect — see section 2.**
- **Edge:** Traefik. It supports `ForwardAuth` middleware, so external authorization needs
  configuration plus one service, not an edge migration.
- **Identity for workloads:** SPIRE, running nine days, in `spire-server`, `spire-system`,
  `spire-mgmt`. SPIFFE certificates are already issued.
- **Admission policy:** Kyverno. One more policy on it, never a second engine.
- **Portal:** Backstage (`backstage/`), the service catalogue and the front door.
- **Secrets:** External Secrets Operator reading an OCI vault. A register at
  `docs/reference/policy/root-trust.md` records every entry, with an `Owner` column whose values
  are `Operator`, `Supplier` or `Customer`.
- **Model routing:** LiteLLM (`llm/config.yaml`).
- **Chaos:** chaos-mesh is installed.

## 2. The measured facts. Do not re-derive these; build on them.

**Fact 1 — the network fences enforce nothing.** The cluster carries 154 NetworkPolicy objects,
40 of them a both-ways default-deny. Only `kube-flannel-ds` runs; flannel does not implement
NetworkPolicy; no Calico, Cilium or Antrea is present. Measured 2026-09-05 from a pod in the
`dagster` namespace, which carries `default-deny-all` with `policyTypes: [Ingress, Egress]` and an
empty `podSelector`:

```
TCP 1.1.1.1:443                                      -> CONNECTED
TCP 8.8.8.8:53                                       -> CONNECTED
TCP 10.244.1.240:3100  (backstage/catalogue, equally fenced) -> CONNECTED
```

Three packets on paths the fences deny, three arrivals.

**Fact 2 — Bitwarden Secrets Manager is written through its client, never its REST API.** It is
zero-knowledge: fields are encrypted client-side before they reach the API, so a plaintext POST
returns `400 {"validationErrors":{"Key":["Key is not a valid encrypted string."]}}`. The vendor
client does that encryption with the key carried in the machine access token
(`0.<id>.<secret>:<base64 encryption key>`), and it writes fine — measured 2026-09-05T22:08Z,
`bws secret create` into the estate project, deleted in the same run. So a credential-ingest
interface may target such a store, and every write to one goes through that store's client.

**Fact 3 — a drill here is two artefacts, not one.** A "drill" is a scheduled workflow under
`.github/workflows/` **plus** a row in `drills/catalogue.yaml`. A checker grades only how fresh
the last green run of that workflow is. A row with no workflow is a drill that never fires.

## 3. The five conventions every change obeys

1. **One item is one pull request**, branched from `main`.
2. **A rule that can be broken gets a gate, and a gate gets a fixture pair** — one file the gate
   must reject and one it must accept — plus a row in the repository's `AGENTS.md` table naming
   both paths. Both fixtures must grade differently in a single run. A gate with one fixture
   proves nothing.
3. **The gate is a shell function or command in `bin/idp-ci`**, the single CI entry point.
4. **A generator is idempotent**: two runs over one inventory produce byte-identical output.
5. **No absolute paths naming a checkout, a home directory or a machine.** And no test may assert
   on prose — a test grades behaviour or parsed structure, never sentences in a file.

### The house style for a gate

Python 3, no network, standard library plus `yaml`. Module docstring says what it grades and why
it exists, naming the real incident. Prints one line per finding prefixed `FAIL` or `PASS`, then a
count line. Exit 0 is pass. It reads files and nothing else. This is the shape:

```python
#!/usr/bin/env python3
"""<Name> gate: <one sentence>.

Reads <what> and grades <n> things, never a proxy:
  1. ... -> FAIL;
  2. ... -> FAIL.
Prints one line per finding, then a count line. Exit 0 = PASS.
No network, no secret values: it reads two kinds of file and nothing else.
"""
import os, re, sys
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))

def grade(...):           # returns a list of "FAIL  <detail>" strings
    ...

def main(argv):
    findings = grade(...)
    for f in findings:
        print(f)
    if findings:
        print(f"FAIL    <name>: {len(findings)} finding(s)")
        return 1
    print("PASS    <name>: <what a green run means>")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

### The house style for a scheduled drill workflow

```yaml
# button: <what a human would call it>
# founder: <one sentence a non-engineer understands>
# Daily drill: <what it proves>. Catalogued in drills/catalogue.yaml as <name>.
name: <name>
on:
  schedule:
    - cron: "<minute> <hour> * * *"
  workflow_dispatch: {}
permissions:
  contents: read
jobs:
  <job>:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@<full 40-char sha>  # v7.0.1
      ...
```

Third-party actions are pinned to a full commit SHA with the version in a trailing comment.

And its catalogue row:

```yaml
  - name: <name>
    owner: idp
    workflow: <file>.yml
    job: <job>
    schedule: "<the same cron string, verbatim>"
    max_age_hours: 26
    proves: >-
      <one sentence: what a green run actually demonstrates>
```

### The house style for a Backstage backend module

New file under `backstage/packages/backend/src/`, registered in `index.ts`. Uses
`createBackendPlugin` and `coreServices` from `@backstage/backend-plugin-api`, an express `Router`,
and a leading comment block listing every endpoint and every status code it returns.

---

## 4. The four things to build, in order

### Task A — Calico in policy-only mode beside flannel, log-only first

The remedy for fact 1. Calico provides NetworkPolicy enforcement while flannel keeps providing the
pod network — the combination that shipped for years as Canal. It turns all 154 existing policies
on at once and rewrites none of them.

**The danger, and it shapes the whole task.** Those 154 policies have never enforced, so no
service's real traffic has ever been graded against them. Switching enforcement on switches all
154 on at once, and any policy that does not allow traffic a service actually needs takes that
service down the moment Calico starts. A flag-day cutover is an estate-wide outage with 154
possible causes.

So produce, as Flux-reconciled manifests under `platform/`:

1. Calico installed in **policy-only** mode alongside flannel, with the data plane left to
   flannel, and enforcement configured so that a denied flow is **logged and allowed**, not
   dropped. Say explicitly which Calico setting achieves that in this posture and what its
   limitations are — if Calico cannot express "log and allow" for Kubernetes NetworkPolicy
   directly, say so plainly and give the closest honest mechanism (for example a global policy
   ordered ahead of the rest with a `Log` action followed by `Allow`, and what that does and does
   not cover).
2. The flow-log collection: where the denied-flow records land and the exact query that answers
   "which flows would have been dropped in the last 24 hours, by source namespace, destination
   namespace and port".
3. The cutover procedure as an ordered checklist, with the specific observation that must hold
   before enforcement goes on, and the single-step rollback.

Do not produce a Cilium migration. Do not rewrite the 154 policies; they are correct, nothing
reads them.

### Task B — the `fence-enforcement` drill

So that fact 1 can never silently return. Both artefacts: the workflow and the catalogue row.

It runs against the live cluster as `estate-ci` inside GitHub Actions. In two namespaces the
fences forbid to talk, it must:

1. **Prove the probe works first**, by reaching a destination the fences allow. A probe that
   cannot reach anything measures nothing.
2. Open TCP from one to the other, and separately to a public address.
3. **Fail unless both are refused, and fail when step 1 could not run.**

Step 1 exists because of a real mistake: a first pass of this probe reported the fence as holding,
when in truth the pod had no `wget` and the shell returned 127. A drill that grades a missing
binary as a passing fence is worse than no drill. Fail closed, and make the failure say which of
the two things happened.

Note the constraint: the drill cannot `kubectl apply` a namespace from a laptop. Inside the
workflow it runs as `estate-ci`, which is excused; say clearly in the workflow which steps need
that identity.

### Task C — `bin/idp-tenant-split`, the two-plane gate

Background: the founder is one person with two identities the platform must treat as strangers —
the **operator** who runs the estate, and **customer zero**, a paying tenant like any other. They
must never share a credential or a channel. A file
`platform/otto-gateway/binding-seed.yaml` contains SQL of the form
`INSERT INTO channel_binding (tenant_id, external_id, secret_ref, outbound_secret_ref,
principal_allowlist) VALUES (...)`, one row per chat channel a bot answers on.

Write the gate. It parses the `INSERT INTO channel_binding ... VALUES` block of every `*.yaml`
under `platform/otto-gateway/` and grades three things:

1. **One secret, one tenant.** A `secret_ref` or `outbound_secret_ref` appearing under two
   different `tenant_id` values is a FAIL.
2. **No operator identity on a customer allowlist.** A row whose `tenant_id` is not `estate` may
   not carry an operator principal in `principal_allowlist`.
3. **The estate tenant owns no customer-facing channel.** A row with `tenant_id = 'estate'` must
   carry an external-id prefix from an `OPERATOR_CHANNELS` list in the gate (today: `alerts-bot:`).

Deliver: the gate, the two fixtures `tests/fixtures/tenant-split/bad.yaml` (make the bad one
violate rule 1 — the same secret under two tenants) and `tests/fixtures/tenant-split/good.yaml`,
and the `AGENTS.md` table row naming both.

### Task D — the credential ingest endpoint

The problem it removes: a credential was handed over by hand three times in one day and landed
nowhere, because the store it was being pasted into cannot accept a plaintext write (fact 2).

New file `backstage/packages/backend/src/credentialIngest.ts`, one endpoint:

```
POST /api/credential-ingest/submit
  { "entry": "cyrus-linear", "key": "api_token", "value": "<pasted>", "store": "estate-vault" }
→ 200 { "entry": "cyrus-linear", "key": "api_token", "sha256_prefix": "9f2c1a7b", "store": "estate-vault" }
→ 400  unknown entry, unknown key, empty value, store not writable
→ 403  caller not signed in, or entry not in the caller's tenant
```

Every one of these is a requirement with a test:

- The pasted value is read from the body into a local, passed to the vault writer, and dropped. It
  is **never logged, never placed in an error message, never returned, never written to disk**
  except the temporary file the vault writer already uses and removes.
- The response carries the first 8 hex characters of the SHA-256 of the value and nothing else of
  it, so the person who pasted can confirm they pasted the right thing and no reader learns it.
- `entry` and `key` are checked against an allow-list read **at request time** from the register at
  `docs/reference/policy/root-trust.md`, restricted to rows whose `Owner` column is `Customer`.
  Anything outside that list is a 400. This is what stops the endpoint being a general write
  primitive into the vault.
- The caller's tenant must own the entry. An operator identity gets **no wider** allow-list here
  than customer zero does.
- `store` must be a store the estate holds a write credential for. The list is read from a file
  `platform/vendors/stores.yaml` — never a hard-coded string. Design that file too: one row per
  store, with `write` and `sync` as **separate** booleans and a `client` field naming how a write is
  performed (`api` for a store that takes plaintext, or the client binary or sidecar for a
  zero-knowledge one, e.g. `bitwarden-sdk-server`). The picker offers every row whose `write` is
  true.
- The write goes through the existing `bin/idp-vault-put --merge <entry> <key>=<value>` so that
  another key already in the same entry is never clobbered.
- Each submission emits one telemetry span with attributes `entry`, `key`, `store`,
  `sha256_prefix`, `tenant` — and no value.

Deliver: the module, its registration line for `index.ts`, `platform/vendors/stores.yaml` with
`estate-vault` (`write: true`) and a Bitwarden row (`write: false`, `sync: true`, with the
one-sentence explanation), and the tests. The tests must actually prove the value never leaks:
capture the logger, capture the response, capture thrown errors, and assert the raw value appears
in none of them.

---

## 5. What to return, and in what order

For each task, in this order: A, B, C, D.

1. The complete files, each under a heading giving its exact repository path.
2. For each gate or test, the one command that proves it, and what its passing output looks like.
3. Anything in the brief you think is wrong, and why. That section is worth more than the code.

Do not summarise the brief back. Do not restate the architecture. Start with Task A.
