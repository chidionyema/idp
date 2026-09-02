# 0017 — Bitwarden is the human door for secrets; the estate vault stays the machine store

Date: 2026-09-02. Status: proposed, awaiting the founder's word (permission-before-building,
2026-08-31). Fires on: the founder, 2026-09-02: "i think we need to think about bitwarden
integration."

## The gap it closes

Machine-born secrets already have one home: code mints them into the OCI vault
(`platform/oci/*.tf`, R52) and External Secrets pulls them through the one
`ClusterSecretStore/estate-vault` (`platform/secret-store/store.yaml`). But **human-born**
secrets have no home at all. A token the founder gets from a vendor (BotFather, a registrar, a
partner portal) travels through his hands as a `gh secret set` command, and his own logins live
wherever his browser put them. Chat is banned as a carrier (R49); nothing else was named.

## The decision

1. **Bitwarden holds every human-born secret.** The founder's own logins, and any credential a
   vendor hands to a person. One organisation, one collection for estate secrets.
2. **The bridge is the platform layer we already run.** External Secrets Operator has a native
   [Bitwarden Secrets Manager provider](https://external-secrets.io/latest/provider/bitwarden-secrets-manager/)
   (plus the vendor's small [sdk-server](https://github.com/external-secrets/bitwarden-sdk-server),
   TLS from our cert-manager). A second `ClusterSecretStore/human-vault` points at it, read by
   one machine account. No script, no new layer — the same ESO rows every workload already uses.
3. **One home per secret, decided by who created it.** Machine-minted → estate vault, as today.
   Human-supplied → Bitwarden. A secret never lives in both; this is a role split, not a second
   copy of a layer, so the one-platform rule holds.
4. **First use: the Telegram alert roots.** Instead of two `gh secret set` lines, the founder
   pastes the BotFather token and chat id into Bitwarden and the platform pulls them. Every
   future FOUNDER ACTION involving a secret becomes "paste it into Bitwarden".

## Cost

$0: the free Secrets Manager tier carries unlimited secrets, 2 users, 3 projects and 3 machine
accounts ([vendor FAQ](https://bitwarden.com/help/secrets-manager-faqs/), checked 2026-09-02);
the estate needs 1 user and 1 machine account. Inside the $0–150 contract.

## The risk, in a sentence

The sdk-server is one more pod on the cluster and Bitwarden's cloud is a new availability
dependency for *human-born* secret refresh — accepted because ESO caches delivered Secrets, so
an outage delays rotation, never sign-in or boot.

## Rejected

- **Migrating machine secrets to Bitwarden too** — the terraform-minted OCI flow already works,
  is code-owned end to end, and free-tier machine-account limits would bite; moving it buys
  nothing a buyer's engineer would credit.
- **Bitwarden password manager without Secrets Manager** — gives the founder a wallet but no
  machine bridge; the `gh secret set` hands survive.
- **Writing our own Bitwarden sync script** — LAW 43; the mature bridge exists inside ESO.
