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

## Amendment, 2026-09-05 — a zero-knowledge store is written through its SDK, never its REST API

Record: `~/.claude/docs/founder/2026-09-05T2025Z-ok-need-do-addrees-quicck-wwe-have-deepseek-29766295.md`

**This amendment replaces an earlier version of itself, written the same evening, which concluded
that Bitwarden could not be written to at all. That conclusion was wrong, and it was wrong in the
way LAW 15 exists to catch: it rested on one probe, from one angle, against the raw REST API.**
The second angle — the vendor's own client — was never run. It is run now and it succeeds. The
earlier text is deleted rather than struck through, because a spec DeepSeek executes from must not
contain a false fact in any form.

**Measured, estate machine account, 2026-09-05T22:08Z.** Reading is exactly as designed:

```
$ bws project list --output json
[{"id":"18e57b2f-d5c6-4c0b-9ba9-b4b900e1d792",
  "organizationId":"a9f79fcf-7059-4bad-94ab-b4b900acc259",
  "name":"estate","creationDate":"2026-09-02T13:42:15.938396Z"}]

$ bws secret list --output json
[]
```

Writing works too, through the vendor's client and only through it:

```
$ bws secret create estate-write-probe-delete-me not-a-secret 18e57b2f-...-b4b900e1d792
{"id":"7b6c411d-a695-48fc-b5f9-b4bc016cff1c",
 "projectId":"18e57b2f-d5c6-4c0b-9ba9-b4b900e1d792",
 "key":"estate-write-probe-delete-me","value":"not-a-secret",
 "creationDate":"2026-09-05T22:08:54.696383100Z"}
$ bws secret delete 7b6c411d-a695-48fc-b5f9-b4bc016cff1c
1 secret deleted successfully.
```

The same payload posted straight at `https://api.bitwarden.com/organizations/<org>/secrets` is
refused with `400 {"validationErrors":{"Key":["Key is not a valid encrypted string."], ...}}`.
Both results are correct and they are the same fact seen twice. Bitwarden is zero-knowledge, so
every field is encrypted before it reaches the API; the API therefore refuses plaintext. The
machine access token has the shape `0.<id>.<secret>:<base64 encryption key>` — the part after the
colon **is** the encryption key. A client that holds the token can encrypt, and `bws` does. Hand
the API plaintext and it correctly says no.

**What this changes.** Ingest and storage are still two choices, but the storage boundary is not
where the earlier text drew it:

| Stage | The client's choice | What the store's design permits |
|---|---|---|
| Ingest — where the key is typed | portal paste, sync from their store, programmatic | free choice, all three roads stand |
| Storage — where the pasted value lands | any store the estate holds a write credential for | **any store, provided the write goes through that store's own client** |

So road one, the one-shot paste, may write to `estate-vault` **or** to a zero-knowledge store the
client has issued a write-capable machine token for. What is refused is not the store; it is the
raw-API shortcut. This also costs nothing to build: `bitwarden-sdk-server` is already deployed in
`external-secrets` and is already doing this encryption on the read path — the write path is the
same bridge and the same credential.

**What is still refused.** Holding a *person's* master-password-derived key, or any material that
lets the estate encrypt as a human user rather than as a machine account the client created and
can revoke. The trust boundary is the machine token, and it is the client's to issue and to take
back.

**Corrected sentence.** Where this decision says provenance decides the default and not the
boundary, that stands, for ingest and for storage both. The store picker offers every store the
estate holds a write credential for, zero-knowledge stores included (see
`docs/specs/key-ingest-door.md`, part 3).
