# Estate security, end to end

Written 2026-09-02 on the founder's ask ("i need to understand end to end"). Plain English;
every claim names the file or ruling that enforces it. Four journeys, then the key inventory.

## Journey 1 — you open a page (say `metabase.mumchimp.com`)

1. Your browser asks DNS. The record was minted by the platform itself (external-dns watches
   the routing rules and writes the zone); nobody edits DNS by hand.
2. The address is the **gateway** — the only workload allowed to face the internet. A
   machine-checked rule (`bind_audit`, AGENTS.md R20) refuses anything else binding a public
   address.
3. The gateway presents a certificate that cert-manager issued from Let's Encrypt and renews
   on its own; no person handles certificate files.
4. Before serving anything it asks: signed in? If not, you are sent to `auth.mumchimp.com`
   (Oracle identity). Login is federated — we store no password for any person (decisions
   0003, 0007).
5. Signed in, the gateway stamps your identity on the request as a header and forwards it.
   Apps never run their own login (`docs/policy/auth-is-infrastructure.md`). Metabase showing
   you a password form broke this law; decision 0016 removes it.

## Journey 2 — the life of a machine secret (say Metabase's database password)

1. **Born in code**: terraform mints a random value directly into the Oracle vault
   (`platform/oci/metabase.tf`). No person ever sees it.
2. **Sealed**: every secret in the vault is encrypted by the vault's one master key
   (`platform/oci/vault.tf`, Oracle KMS, software-protected, $0).
3. **Read by identity, not by a key**: the cluster's nodes form a named group and Oracle
   policy lets that group read secret bundles — except the receipt-signing key, which is
   fenced even from them. No vault credential is stored in the cluster.
4. **Delivered**: External Secrets checks the vault every 10 minutes and writes the value as
   a Kubernetes Secret; pods mount it as a file — an admission policy refuses secrets in
   environment variables.
5. **Rotated**: change the vault entry; Reloader rolls the pod
   (`docs/policy/secrets-rotation.md`, drilled).

## Journey 3 — a secret a person holds (say the Telegram bot token)

Today: the vendor shows it to you, and you run two `gh secret set` lines so a workflow can
seed the vault. That is the gap. Decision 0017 (awaiting your word) closes it: you paste the
value into Bitwarden and the platform pulls it through the same External Secrets layer — one
machine account, free tier, no command lines for you again.

## Journey 4 — how code reaches the cluster

1. Agents push branches. Nothing lands ungraded: tests, security scan, licence scan, policy
   gates and the operating-model gate must all pass.
2. **You approve every infra merge; agents never deploy** (permanent ruling, 2026-09-01).
3. Flux, running inside the cluster, pulls from git. Git is the only way in — no laptop holds
   cluster-write credentials. Flux's own write-back identity is a GitHub App token, machine
   made (`platform/image-automation/flux-writer.yaml`).
4. On arrival every object faces admission policy (no `:latest` images, no secret in an env
   var, telemetry required — LAW 50) and lands in a namespace that denies all traffic both
   ways by default, with quotas (AGENTS.md ns_fence rule).

## The keys that exist

| Key | Where | Who can use it |
|---|---|---|
| 1 vault master key | Oracle KMS (`platform/oci/vault.tf`) | The vault itself; it seals every machine secret |
| 1 root credential per provider (R52) | Set once by you; named in `platform/vendors/consoles.yaml` | Code, to mint everything else |
| TLS certificates | cert-manager, auto-issued and renewed | The gateway |
| Receipt-signing key | The vault, fenced from worker nodes | The verdict signer only |
| Human passwords | **None stored, anywhere** | — |

## Open, honestly

- Metabase's inner door: decision 0016, awaiting GO.
- The human-secret home: decision 0017 (Bitwarden), awaiting GO.
- The two Telegram values themselves: still to be set by your hand (or by 0017 once built).
