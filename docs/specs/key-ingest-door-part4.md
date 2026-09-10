# The key ingest door, part 4 — the writer, and the grant that must not widen

`docs/specs/key-ingest-door.md` is written and parts 1, 2, 3 and 5 are built:
`backstage/packages/backend/src/credentialIngest.ts`, `platform/vendors/stores.yaml` and
`backstage/templates/onboarding/activate-key/`. Three things are missing, and each is proved
below by a command. Until they land, the page a customer is supposed to use either does not
appear or refuses with a 502.

This spec covers the three, and nothing else. It is written so it can be implemented without
asking questions.

---

## Measurement, 2026-09-10. Every claim carries its command.

**1. The page is not loaded by the portal that runs.**

```
$ grep -nE 'templates/(onboarding|customer-onboarding)' backstage/app-config.container.yaml \
    backstage/app-config.production.yaml
$ echo $?
1
```

The deployed config loads exactly four template groups — `estate-component`,
`external-integration`, `founder-actions/*`, `enable-platform-feature`. The two onboarding
templates exist on disk and are in no catalogue location the portal reads. A signed-in person
sees founder-action buttons and nothing for setting up their own service.

**2. The backend refuses by design.**

```
$ sed -n '211,213p' backstage/packages/backend/src/credentialIngest.ts
          vaultWriter: async (_entry, _key, _value, _store) => {
            throw new Error('estate-vault in-pod writer is not wired (key-ingest-door part 4)');
          },
```

A POST returns 502. That is correct behaviour for an unwired seam — it never claims a false
success — and it is the seam this spec replaces.

**3. There is no scoped grant, and the existing one is the wrong shape.**

```
$ grep -n 'oci_identity_policy' platform/oci/vault.tf
33:resource "oci_identity_policy" "workers_read_secrets" {
```

The only policy is `Allow dynamic-group <cluster>-workers to read secret-family in compartment id
<compartment> where target.secret.name != 'verdict-hmac-key'`.

**The trap, and it is the whole reason this part is separate.** `platform/oci/vault.tf:4-6`
records that workload identity per pod needs an Enhanced cluster (billed per hour), so
**the node identity is the boundary**. A pod on a node is in the node's dynamic group. Adding the
portal to that group, or giving the portal pod an OCI credential of its own, would hand the
portal `read secret-family` on the whole compartment — including every entry the register marks
`Operator`. The spec's intent is the opposite: customer zero must get no wider allow-list than
any other customer (decision 0021 rule 2).

So the writer may not be "the portal talks to OCI". The writer is:

> **the portal calls a purpose-built in-cluster service, which holds the only write grant, and
> that grant is scoped to the entries whose register Owner is `Customer`.**

---

## Part A — the two templates the portal must load

Edit `backstage/app-config.container.yaml`, beside the four existing template blocks, adding:

```yaml
    # crew#749: the customer road. Two hand-written templates that exist in the tree and were
    # never registered, so "Activate a key" and "Onboard a customer onto messaging" appeared in
    # no portal (measured 2026-09-10: no onboarding target in this file).
    - type: file
      target: /app/templates/onboarding/*/template.yaml
      rules:
        - allow: [Template]
    - type: file
      target: /app/templates/customer-onboarding/template.yaml
      rules:
        - allow: [Template]
```

`backstage/Dockerfile:126` already does `COPY --chown=node:node templates ./templates`, so the
files are in the image. `backstage/app-config.yaml` (the compose run) gets the same two blocks
with `../../templates/...` targets.

**Acceptance:** the portal's `/create` page lists both, and
`yarn --cwd backstage test` stays green.

---

## Part B — the writer service, `platform/vault-writer`

A small in-cluster HTTP service, in namespace `backstage`, named `vault-writer`. It is the only
thing in the estate holding a vault **write** grant.

- **Endpoint.** `POST /write` `{ "entry": "...", "key": "...", "value": "..." }`.
  - `200 {"entry":..., "key":..., "sha256_prefix": "9f2c1a7b"}` — the first 8 hex of SHA-256, and
    nothing else of the value.
  - `400` unknown entry/key, empty value.
  - `403` an entry whose register Owner is not `Customer`.
  - `502` the vault itself refused.
- **The allow-list is read at request time** from `docs/reference/policy/root-trust.md`, rows
  whose Owner is `Customer` — the same file and the same rule `credentialIngest.ts` uses, so the
  two cannot drift.
- **The write goes through `bin/idp-vault-put --merge <entry> <key>=<value>`**, so a vendor key
  already in the same entry is never clobbered, exactly as `bin/idp-estate-seed` does it. The
  value is passed on stdin, never argv: argv is visible to any process on the node.
- **The value is never logged, never echoed, never in an error string, never on disk** beyond the
  temp file `bin/idp-vault-put` already creates and removes.
- **One span per submission** to the central collector (LAW 50) with `entry`, `key`, `store`,
  `sha256_prefix`, `tenant` and no value.
- **Reached only in-cluster.** A `ClusterIP` Service, no Ingress, no route. `bin/idp-ci` renders
  the directory and fails on a non-ClusterIP Service, which is the existing wall (R20).

**Tests, failing first, at `tests/test_vault_writer_part4.py`:**

1. An entry whose register Owner is `Operator` is refused `403`. This is the tenant plane failing
   to reach the control plane, which decision 0021 exists to catch.
2. An unknown entry is refused `400`.
3. A successful write returns a `sha256_prefix` equal to the first 8 hex of the value's digest,
   and the response body contains no substring of the value longer than 4 characters.
4. The value is absent from the service's log output after a successful write.
5. A non-ClusterIP Service in `platform/vault-writer/` fails the render check.

**Acceptance:** `python3 -m pytest tests/test_vault_writer_part4.py -q` passes, and
`bin/idp-ci` is green.

---

## Part C — the grant, scoped, and the wall that proves the refusal

New policy in `platform/oci/vault.tf`, its statement list **generated from the register** by a
small function so the entry names cannot drift:

```hcl
resource "oci_identity_policy" "vault_writer_customer_entries" {
  provider       = oci.home
  compartment_id = var.compartment_ocid
  name           = "${var.cluster_name}-vault-writer-customer-entries"
  description    = "the vault writer may use exactly the entries whose register Owner is Customer (decision 0021)"
  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.workers.name} to use secret-family in compartment id ${var.compartment_ocid} where target.secret.name in (${join(", ", local.customer_owned_entries)})",
  ]
}
```

`use` rather than `manage`, and the `in (...)` list rather than a compartment-wide grant: the
narrowest statement OCI offers that lets the writer create a new version of a named secret.

`platform/verification/` gains a wall proving the refusal, annotated
`estate/expect-ready: "false"` exactly as `verdict-key-wall.yaml` does: a write attempt by the
writer against an `Operator`-owned entry must fail.

**Acceptance:** `bin/idp-root-trust` still passes and prints the same onboarding number; the new
wall's expectation is proved by the render check.

---

## Part D — required-bring-up, and the empirical proof

The end-to-end, which is the only proof that counts. Each step's output is quoted:

1. Sign in to the portal. Open **Create** → **Activate a key**. Choose the Linear entry, paste a
   key, submit.
2. The page shows the sha prefix. No terminal was opened and no repository secret was created.
3. Within one refresh interval:
   ```
   bin/idp-kube get externalsecret cyrus-webhook -n cyrus -o jsonpath='{.status.conditions[0].reason}'
   → SecretSynced
   ```
4. A real line from the consuming workload's log showing the key in use.
5. `bin/idp-root-trust` prints a **lower** customer count than the 6 it prints today
   (`commerce-payment-provider`, `otto-staging-telegram`, `cyrus-linear`,
   `cyrus-linear-api-token`, `DEEPSEEK_API_KEY`, `TELEGRAM_ALERTS_BOT_TOKEN`).

Until step 4 quotes a live line, the door is not working (THE EMPIRICAL PROOF RULE).

---

## Out of scope

- No new portal, no second login. The portal is `https://catalogue.mumchimp.com` behind the
  estate's existing OIDC (ADR 0008).
- No per-pod OCI workload identity: it needs an Enhanced cluster, and the node boundary is the
  recorded decision (`platform/oci/vault.tf:4-6`).
- No change to `bin/idp-portal-buttons`. It already skips the `activate-key` template by its
  marker, and part 3 proved that both ways.
