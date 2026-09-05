# 0020 — An API key has a lifecycle, and the client chooses every road on it

- Status: DECIDED 2026-09-04 on the founder's instruction, recorded verbatim at
  `~/.claude/docs/founder/2026-09-04T1440Z-ensure-this-is-docunented-snd-never-forgotted-ticketed-b6861d5a.md`
- Deciders: founder
- Supersedes: nothing. Extends 0017 (two secret stores, split by provenance) and 0019
  (credentials federate; a human pastes at most one seed).
- Affects: every vendor credential the estate or a customer holds, and the portal surface that
  manages them.

## The instruction

> "The instruction to not limit the platform's capabilities or the choices available to our
> clients is non-negotiable. I have captured that rule and will not propose a design that funnels
> everything into a single solution again."

He said it about a spec written earlier the same day that standardised on Bitwarden Secrets
Manager as the one place a vendor key may live, and wrote the alternatives up as rejected. That
spec was wrong in a specific way worth naming, because it is a mistake with a shape: it took a
component chosen for being provider-plural and spent that plurality on a single default.

## The decision

**A key has a lifecycle with four stages — ingest, prove, store, deliver — and a fifth that
repeats, rotate. At every stage the platform offers every road its built capabilities already
support, and the client chooses. One stage has no choice at all, and that is proving.**

### Ingest — the client's workflow, not ours

Three roads, all live on the same portal page:

1. **One-shot** — paste the key once into the portal, click Activate. The simplest thing that can
   work, and the right answer for a person whose key has just expired at 9pm.
2. **Sync from the client's own store** — the client updates the key where they already keep it,
   and the platform reads it from there. No paste, nothing typed into a surface of ours.
3. **Programmatic** — the vendor's own create-key API, driven by the platform (see rotate).

### Prove — the one stage with no choice

Every road ends at the same gate: a direct call to the vendor, using that vendor's own `verify:`
block in `platform/vendors/consoles.yaml`. A 2xx stores the key. Anything else discards it and
reports the vendor's own status and message, immediately to the operator on the one-shot road and
into the run's failure on the sync road. There is no path that stores an unproved key, and there
is no override. This is R52 and it is the reason the rest can be flexible.

### Store — provenance decides the default, the client decides the answer

External Secrets Operator 2.9.0 is already running and already speaks to Bitwarden Secrets
Manager, Azure Key Vault, AWS Secrets Manager, Google Secret Manager, HashiCorp Vault, 1Password,
Doppler, CyberArk, Akeyless, Infisical and Oracle's own vault, among others, and each one is a
`ClusterSecretStore` row — a YAML file, not a line of code. The estate therefore supports a
customer's existing secret store by adding a row, and any design that names one store is throwing
that away.

Decision 0017's provenance split remains the **default**, not the boundary: machine-minted values
default to the OCI vault, human-created values default to Bitwarden. A client who keeps their
secrets in Azure Key Vault gets a store row and keeps their secrets in Azure Key Vault.

The blast-radius objection to the portal holding write access is answered by a capability the
estate has already built and proved: `platform/oci/vault.tf` scopes a grant with
`where target.secret.name != 'verdict-hmac-key'`, and `platform/verification/verdict-key-wall.yaml`
proves daily that the refusal holds. Write access is scoped to exactly the entries a surface may
touch, in the same shape.

### Deliver — one mechanism, many sources

One `ExternalSecret` per consumer, with a per-entry `sourceRef.storeRef`, so a single Kubernetes
Secret can be assembled from several stores at once and a later `data:` entry wins over an earlier
`extract:`. Reloader restarts the consumer when the value changes. This is the road
`drills/catalogue.yaml`'s `rotation-canary` drill already proves every morning at 06:17: a vault
write reaches the cluster, the pod restarts, and the restarted pod answers with the sha of the
value it is actually running.

### Rotate — programmatic where the vendor allows it, assisted where it does not

Where a vendor publishes a create-key API, the platform mints, proves, writes and only then
revokes — in that order, so a failure never leaves the estate with no working key. Where it does
not, the warden detects the dead key, alerts, and the operator takes the one-shot road. DeepSeek
is the second case today. A vendor's rotation road is written into its registry row only after
that vendor's own documentation has been read, and the row cites the page and the date.

## What this rules out

Not options — stitching. A second identity layer, a second scheduler, a second collector, or a
hand-rolled script for something a running component already does. A configuration a component
already supports is never a "rejected alternative": keeping it costs nothing and removing it costs
a customer their choice.

## Note on one name in the instruction

The instruction names "Microsoft BitLocker Sync" for the Microsoft road. BitLocker is Windows
full-disk encryption and holds no API keys; the Microsoft-managed store this design means is Azure
Key Vault, backed by Entra ID. External Secrets Operator has a native Azure Key Vault provider, so
that road is a `ClusterSecretStore` row and no new code — it is on the list above and needs
nothing built to be offered.

---

## Amendment, 2026-09-05 — a zero-knowledge store can be read from and never written to

Record: `~/.claude/docs/founder/2026-09-05T2025Z-ok-need-do-addrees-quicck-wwe-have-deepseek-29766295.md`

This decision named three ingest roads and let the client pick the store on each. Building road
one turned up a constraint that decides where a pasted key can land, and it is a property of the
store rather than of our code, so it belongs in the decision rather than the spec.

**Measured, with the estate's own Bitwarden machine account, 2026-09-05.** Reading works exactly
as designed:

```
auth: ok, scope=api.secrets
secrets the machine account can list: 0
projects visible: [('18e57b2f-d5c6-4c0b-9ba9-b4b900e1d792', '2.QKtQmaAK7Ns0k9LuR0qmyw==|...')]
```

Writing does not, and the refusal is the whole point:

```
POST https://api.bitwarden.com/organizations/<org>/secrets
{"key": "...", "value": "...", "note": "...", "projectIds": ["18e57b2f-..."]}

400 {"object":"error","message":"The model state is invalid.","validationErrors":{
  "Key":["Key is not a valid encrypted string."],
  "Value":["Value is not a valid encrypted string."],
  "Note":["Note is not a valid encrypted string."]}}
```

Bitwarden is zero-knowledge: every field is encrypted on the client with a key derived from the
access token before it reaches the API, which is why the project's own *name* comes back as
`2.QKtQ…|…|…` rather than a word. There is no plaintext write path and there is not meant to be.
The two probes are `bin/idp-human-vault-probe` (this PR), so the finding is re-measurable rather
than remembered.

**What this changes.** Ingest and storage were being treated as one choice, and they are two:

| Stage | The client's choice | What the store's design permits |
|---|---|---|
| Ingest — where the key is typed | portal paste, sync from their store, programmatic | free choice, all three roads stand |
| Storage — where the pasted value lands | any store the estate can write | **only a store with a plaintext write path** |

So road one, the one-shot paste, writes to `estate-vault` and no other store. This is not a
narrowing of the client's choice; it is the honest shape of it. A client who keeps keys in
Bitwarden, 1Password or any other zero-knowledge vault does not want us writing into it — that
would mean handing us the ability to encrypt as them. They want road two: they put the key in
their own vault with their own client, and the estate reads it. That road already runs, and
`human-vault` has been Valid for four days waiting for its first consumer.

The only way to make road one write into such a store is to ship the vendor's client-side
encryption SDK inside the portal and hold a credential able to encrypt as the customer. That is
refused: it is a second secret store in the portal's process (the HEADLINE), it is a per-vendor
SDK for every vendor a client might use, and it puts customer-encrypting material in a web
front end. `bitwarden-sdk-server` stays what the chart ships it as — a read bridge for ESO.

**Corrected sentence.** Where this decision says provenance decides the default and not the
boundary, that remains true of *ingest*. For *storage* the boundary is real and the store draws
it: a zero-knowledge store is a source the estate syncs from, never a destination the estate
writes to. A UI that offers a customer "save this into my Bitwarden" is offering something no
correct implementation can deliver, so the store picker does not offer it (see
`docs/specs/key-ingest-door.md`, part 3).

**Consequence for the register.** The `cyrus-linear-api-token` row stays Customer-owned and keeps
its `human-vault` read, because that key genuinely is born in a browser and the founder genuinely
holds it. What changes is that the *hand-over* stops being "type the exact name into Bitwarden's
web interface and pick the right project", which failed three times on 2026-09-05, and becomes
one paste into the portal that lands in `estate-vault`. The client may later move the key onto
the human road with their own client, and the ExternalSecret follows with a one-line store swap.
