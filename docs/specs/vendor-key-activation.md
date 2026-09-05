# API key lifecycle — the build spec

Governed by decision 0020, "An API key has a lifecycle, and the client chooses every road on it".
Written to be implemented without asking questions. Every file path below is real; every component
named already runs. The founder's instruction that governs it, verbatim:

> "The instruction to not limit the platform's capabilities or the choices available to our clients
> is non-negotiable ... The goal is to provide a comprehensive, flexible API Key Lifecycle
> Management solution that supports multiple secure options, from 'One-Shot Ingestion' for
> simplicity to 'Bleeding Edge Sync' for automation."

Record: `~/.claude/docs/founder/2026-09-04T1440Z-ensure-this-is-docunented-snd-never-forgotted-ticketed-b6861d5a.md`

---

## Part 0 — what already exists. Do not rebuild any of it.

Read this part before writing anything. Six of the capabilities this spec needs are already
running, and the whole shape of the work is "connect them", not "build them".

| Capability | Where it lives | What it already does |
|---|---|---|
| Machine secret store | `ClusterSecretStore/estate-vault` (OCI Vault) | Ready. Holds machine-minted values. |
| Human secret store, **read only** | `ClusterSecretStore/human-vault` (Bitwarden Secrets Manager, chart `bitwarden-sdk-server` 0.6.0) | Ready, ids populated, nothing reads it yet. Zero-knowledge: the estate can sync **from** it and can never write **to** it (decision 0020 amendment 2026-09-05, measured by `bin/idp-human-vault-probe --write`). A pasted key lands in `estate-vault`. |
| Any other store | External Secrets Operator **2.9.0** | Native providers for Azure Key Vault, AWS Secrets Manager, Google Secret Manager, HashiCorp Vault, 1Password, Doppler, Akeyless, CyberArk, Infisical and more. Each is a `ClusterSecretStore` YAML row — no code. |
| Per-entry source selection | ESO 2.9.0 `spec.data[].sourceRef.storeRef` | One Kubernetes Secret can be assembled from several stores at once; a later `data:` entry wins over an earlier `extract:`. |
| Fine-grained write scoping | `platform/oci/vault.tf:39` — `where target.secret.name != 'verdict-hmac-key'` | A grant can be scoped to exactly the entries a principal may touch. `platform/verification/verdict-key-wall.yaml` proves the refusal holds (annotated `estate/expect-ready: "false"`; Ready would be the breach). |
| Scheduler with circuit breakers | `scheduler/schedule.yml` (46 rows) rendered by `scheduler/estate_scheduler/definitions.py` into Dagster | Schedules, timezone, `dagster/max_runtime`, `dagster/priority`, a `circuit_open` breaker that trips on repeat failure, a battery gate, and `run_status_sensor` dependency sensors. **A new scheduled job is a row here — never a hand-written CronJob.** |
| Rotation road, drilled daily | `drills/catalogue.yaml`, drill `rotation-canary`, 06:17 | Proves vault write → ESO → Reloader → pod restart → pod answers with the sha of the value it is actually running, within 25 minutes. The road this spec delivers on is already under a daily drill. |
| Vendor registry | `platform/vendors/consoles.yaml` | Per-vendor rows. This is where each vendor's `verify:` block and rotation road go. |
| Key minting for the router | `bin/idp-router-key` | Mints a lane-scoped LiteLLM virtual key (`key_alias`, `models`, `max_budget`, `budget_duration`) straight into a vault entry field via `--merge`. |
| Portal | Backstage behind the one front door (ADR 0008), 29 founder-action templates | The surface. It already exists and is already behind OIDC; nothing new is needed to authenticate an operator. |
| Restart on change | Reloader | Consumers restart when their Secret changes. Already wired for the drilled road. |

Two corrections to carry, both already applied in decision 0020:

- **BitLocker is not a secret store.** It is Windows full-disk encryption. The Microsoft-managed
  store meant here is **Azure Key Vault**, backed by Entra ID; ESO has a native provider for it, so
  that road is a `ClusterSecretStore` row and no new code.
- **There is no "Decision 0021".** The highest real ADR before this work is 0019. Fine-grained vault
  authorization is not an ADR — it is live Terraform at `platform/oci/vault.tf`.

---

## The lifecycle

    ingest  ─┬─ one-shot paste (portal)      ┐
             ├─ sync from the client's store │→  PROVE  →  STORE  →  DELIVER  →  (rotate, repeats)
             └─ programmatic (vendor API)    ┘   one gate   client's  ESO
                                                fail-closed  choice

Ingest is plural. Prove is singular and has no override. Store is plural. Deliver is one mechanism
over many sources. Rotate is programmatic where the vendor allows it and assisted where it does not.

---

## Part A — Ingest: three roads, one page

### A1. One-shot paste

A Backstage template with a backend Scaffolder action. **The founder-action button road cannot carry
this**: a `workflow_dispatch` input is readable in the GitHub Actions UI, so a key pasted into one
would be a key written to a log. The template is hand-written and the value goes to a backend action
in-process.

`backstage/templates/api-key-activate/template.yaml`:

```yaml
apiVersion: scaffolder.backstage.io/v1beta3
kind: Template
metadata:
  name: api-key-activate
  title: Activate an API key
  description: Add or replace a key for a vendor. It is checked with the vendor before anything is stored.
  tags: [founder-action, estate, secrets]
spec:
  owner: group:default/platform
  type: founder-action
  parameters:
    - title: Which key
      required: [vendor]
      properties:
        vendor:
          title: Vendor
          type: string
          description: The vendor whose key you are adding or replacing.
          ui:field: EntityPicker
          ui:options: { catalogFilter: { kind: Resource, spec.type: vendor-credential } }
        store:
          title: Where to keep it
          type: string
          description: Leave as the default unless your organisation keeps its secrets somewhere else.
          default: human-vault
          enum: [human-vault, estate-vault, azure-key-vault, aws-secrets-manager, gcp-secret-manager, hashicorp-vault]
          enumNames:
            - Bitwarden (the default for a key a person created)
            - Oracle Vault (the default for a key a machine created)
            - Azure Key Vault
            - AWS Secrets Manager
            - Google Secret Manager
            - HashiCorp Vault
    - title: The key
      required: [key]
      properties:
        key:
          title: The key
          type: string
          ui:field: Secret
          description: Typed once. It is sent to the vendor to be checked, then stored. It is never written to a log, a repository, or this page's history.
  steps:
    - id: activate
      name: Check with the vendor and store
      action: estate:api-key:activate
      input:
        vendor: ${{ parameters.vendor }}
        store: ${{ parameters.store }}
        key: ${{ secrets.key }}
  output:
    text:
      - title: Result
        content: ${{ steps.activate.output.summary }}
```

The `store` enum is generated, not typed: the backend lists `ClusterSecretStore` objects carrying
the label `estate/offers-ingestion: "true"` and offers each one. Adding a store to the platform
therefore adds a road to this page with no change to this file. Ship the enum above as the initial
value and replace it with the generated list in the same pull request.

### A2. Sync from the client's own store

No paste at all. The client updates the key where they already keep it; the platform reads it from
there. This is an `ExternalSecret` with `sourceRef.storeRef` pointing at that store (Part D), plus
the same proving gate applied on every read (Part B, B3). Nothing here is new code — it is a store
row and a manifest row.

### A3. Programmatic

The vendor's own create-key API, driven by the platform. See Part F.

---

## Part B — Prove: one gate, fail-closed, no override

### B1. The vendor's own check, in the registry

Each vendor row in `platform/vendors/consoles.yaml` gains a `verify:` block:

```yaml
- name: deepseek
  verify:
    method: GET
    url: https://api.deepseek.com/user/balance
    auth: bearer            # bearer | header | query
    success: [200]
  rotation: assisted        # programmatic | assisted
  store_default: human-vault
```

`auth: header` rows add `header_name:`. `rotation: programmatic` rows add a `create:` block with
the same shape plus `revoke:`.

### B2. The gateway

One function, called by every road: `platform/api-key-warden/warden/prove.py`, signature
`prove(vendor: str, key: str) -> Proof`. It reads the vendor's row, makes the call, and returns
either a proof carrying the HTTP status and the vendor's own response text, or raises. Rules, all
enforced by tests:

1. **A key is never written before a 2xx.** Store is called with a `Proof` object; there is no code
   path that stores without one.
2. **Failure reports the vendor's own words.** The operator sees the status and the vendor's message,
   not "something went wrong".
3. **The key value is never logged, never in an exception message, never in a Dagster event, never
   in a returned summary.** The summary names the vendor, the store, the status and the time.
4. **No override flag exists.** Not an environment variable, not a parameter, not a config key.

### B3. The gate applies to the sync road too

A key that arrives by sync is proved before it is delivered, not only when it is first written.
This is the warden's job (Part E) and is what makes A2 as safe as A1.

---

## Part C — Store: the client picks; provenance is only the default

`activate()` resolves the store in this order: the operator's choice on the form; else the vendor
row's `store_default`; else provenance — human-created keys to `human-vault`, machine-minted keys to
`estate-vault` (decision 0017).

Write scoping, one row per store, in the same shape the vault wall already proves:

- **Bitwarden**: the machine account's project permission is set to read/write. Today
  `docs/how-to/bitwarden-human-vault.md` step 2 sets **Can read**; update that document in the same
  pull request. The machine account sees exactly one project, which is the scope.
- **OCI Vault**: a second dynamic-group statement scoped with
  `where target.secret.name in ('vendor-keys')`, alongside the existing
  `!= 'verdict-hmac-key'` grant, in `platform/oci/vault.tf`.
- **Any other store**: the client's own IAM, scoped by them to the entries they choose to expose.
  The platform states the scope it needs and never asks for more.

The warden's write credential is itself an entry in `estate-vault`, delivered by ESO, mounted as a
file — never `secretKeyRef` env, which Kyverno's `secrets-not-from-env-vars` refuses.

---

## Part D — Deliver: one mechanism, many sources

One `ExternalSecret` per consumer. Per-entry `sourceRef.storeRef` lets one Kubernetes Secret draw
from several stores at once:

```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata: { name: llm-vendor-keys, namespace: llm }
spec:
  refreshInterval: 1m
  target: { name: llm-vendor-keys, creationPolicy: Owner }
  data:
    - secretKey: DEEPSEEK_API_KEY
      sourceRef: { storeRef: { name: human-vault, kind: ClusterSecretStore } }
      remoteRef: { key: vendor-deepseek }
    - secretKey: MINIMAX_API_KEY
      sourceRef: { storeRef: { name: estate-vault, kind: ClusterSecretStore } }
      remoteRef: { key: litellm-upstream, property: MINIMAX_API_KEY }
```

Reloader restarts the consumer on change. `rotation-canary` already drills this road end to end
daily, so the delivery leg needs no new drill — extend the existing row rather than adding one.

---

## Part E — Watch: the estate scheduler, not a CronJob

### E1. The warden is a row in `scheduler/schedule.yml`

```yaml
- name: api-key-warden
  description: Checks every vendor key against its vendor and reports which are dead, expiring or unproved.
  cron: "17 */4 * * *"
  runs_on: cluster
  runs_on_ref: platform/api-key-warden
  timeout_minutes: 10
  priority: 1
```

Dagster gives it the schedule, the timezone, the timeout, the priority, the `circuit_open` breaker
that trips after repeat failure and the run history — all of which a hand-rolled CronJob would have
to reinvent badly. The job pod carries `priorityClassName: platform-batch` so it is seated by
preempting a balloon pod and is not charged against the standing 6.9-core budget.

### E2. What it emits

A Prometheus gauge per vendor via the pushgateway the other scheduled jobs already use:

    estate_vendor_key_valid{vendor="deepseek",store="human-vault"} 1|0
    estate_vendor_key_checked_timestamp{vendor="deepseek"} <unix seconds>

### E3. Alert rules

`platform/monitoring/rules/api-key-warden.yaml`, three rules:

- `VendorKeyInvalid` — `estate_vendor_key_valid == 0` for 10m. The message names the vendor and the
  portal URL that fixes it.
- `VendorKeyUnchecked` — `time() - estate_vendor_key_checked_timestamp > 6*3600`. The warden itself
  has stopped; this is the instrument that watches the instrument (LAW 28).
- `VendorKeyWardenJobFailed` — `kube_job_failed{job_name=~"api-key-warden.*"} > 0`.

Every workload emits to the central collector (LAW 50); coverage is proved by querying the backend,
never by scanning files.

---

## Part F — Rotate

### F1. Programmatic — mint, prove, write, then revoke, in that order

For a vendor with `rotation: programmatic`. The order matters: the old key stays valid until the new
one has been proved and delivered, so a failure at any step leaves the estate with a working key.

1. Call the vendor's `create:` endpoint. 2. Prove the new key (Part B). 3. Write it to the resolved
store. 4. Wait for the consumer to restart and answer. 5. Call `revoke:` on the old key. A failure
before step 5 leaves the old key live and raises; a failure at step 5 raises and names the orphan
key so it can be revoked by hand.

The router's own lanes already have this: `bin/idp-router-key` with `ROUTER_ROTATE=1` mints a
lane-scoped virtual key with its own daily budget and merges it into the vault entry. Programmatic
rotation for a LiteLLM lane calls that, it does not reimplement it.

### F2. Assisted — where the vendor has no API

DeepSeek today. The warden detects the dead key, `VendorKeyInvalid` fires, the message names the
vendor and links the portal page, and the operator takes the one-shot road. That is the whole
fallback, and it is why Part A1 exists.

### F3. A vendor's road is written from that vendor's own documentation

A `rotation: programmatic` row is added only after that vendor's API documentation has been read,
and the row cites the page and the date it was read. No vendor's capability is assumed.

---

## Acceptance

Each line is a command or an observable state, and each is a checkpoint on the ticket.

1. `bin/idp-ci` green on the branch.
2. A key that the vendor rejects is not stored: unit test on `prove()` plus an integration test that
   calls `activate()` with a bad key and asserts the store was not written.
3. No code path stores without a `Proof`: a test that greps the module for a store call not guarded
   by one, or a type-level guarantee that makes it unrepresentable. Prefer the type.
4. The key value appears in no log, event, exception or summary: a test that runs `activate()` with
   a sentinel value and asserts the sentinel is absent from captured logs and from the returned
   summary.
5. The portal page offers every `ClusterSecretStore` labelled `estate/offers-ingestion: "true"`,
   proved by adding a fake store row in the test fixture and asserting it appears.
6. An `ExternalSecret` with two different `sourceRef.storeRef` entries renders one Secret with both
   keys, proved against the running cluster.
7. `estate_vendor_key_valid` is queryable in Prometheus for every vendor in
   `platform/vendors/consoles.yaml`.
8. The three alert rules load: `promtool check rules platform/monitoring/rules/api-key-warden.yaml`.
9. The warden row renders: `python -c "from estate_scheduler.definitions import defs"` and the job
   appears in the Dagster UI with its description.
10. `bin/idp-kyverno-render platform/api-key-warden` passes — the warden must not take a secret from
    an env var and must carry a catalogue entity and a priority class.

## Order of work

Each step is shippable on its own and leaves the estate better than it found it.

1. `verify:`, `rotation:` and `store_default:` rows for every vendor in `platform/vendors/consoles.yaml`.
2. `prove()` and its tests. Nothing else can be built honestly before this.
3. The warden: the scheduler row, the job image, the gauges, the three alert rules.
4. `activate()`: store resolution, the write drivers for Bitwarden and OCI Vault, the write scoping.
5. The Backstage template and the `estate:api-key:activate` backend action, with the generated store list.
6. Per-entry `sourceRef` delivery for the LLM consumer, and the `rotation-canary` drill extended to cover it.
7. Programmatic rotation, one vendor at a time, each from that vendor's own documentation.
