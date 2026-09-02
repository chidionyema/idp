# 0019 — Credentials federate; a human pastes at most one seed

Date: 2026-09-02. Status: accepted.
Founder record: `~/.claude/docs/founder/2026-09-02T1155Z-in-on-loptop-at-see-i-idn-tthikn-9ddeac68.md`
(his laptop, 11:55Z): pinned terminal commands for a person are rejected — a person acting as a
machine's keyboard is a defect (LAW 31). Credentials rotate themselves; after the one Bitwarden
seed he never touches one again.

## Decision

1. **Workload identity over pasted secrets, everywhere a provider supports it.**
   GitHub Actions authenticates to OCI by exchanging its own OIDC token — no stored cloud key.
   This is already live: `.github/workflows/vault-bootstrap.yml` uses the pinned
   `oci-token-exchange-action`; every new workflow that touches OCI uses the same road.
2. **The Bitwarden seam is one machine-account token, and that is the whole manual surface.**
   Verified from the vendor's own pages (2026-09-02, not memory): the External Secrets Operator
   Bitwarden Secrets Manager provider authenticates with a machine-account access token only —
   no OIDC, no Kubernetes service-account federation
   (external-secrets.io/latest/provider/bitwarden-secrets-manager). So the founder's one paste
   of `bitwarden-machine` into the estate vault is the single root credential for that provider
   (R52), and the record says so honestly rather than promising federation the vendor does not sell.
3. **No new pasted credential, ever.** A new provider is admitted only if (a) it federates via
   OIDC/workload identity, or (b) its root is minted by code from a root we already hold. A pinned
   message asking a person to run a seeding command is the rejected shape; agents seed repo and
   cluster secrets themselves from where the value already lives, without printing it.
4. **Rotation is a follow-up, designed against the vendor API.** Automating reissue of the
   Bitwarden machine-account token is tracked separately and will be specified from Bitwarden's
   API documentation before any build (memory rule: console steps come from the vendor page).

## Consequences

- The three one-time founder moves (subscribe, machine account + token, one paste) are the entire
  human credential ceremony for the estate; everything downstream is code.
- Telegram alert repo secrets (`SEED_TELEGRAM_ALERTS_*`) are seeded by an agent from the hermes
  gateway's existing store, replacing the rejected pinned commands.
- Any design that adds a second pasted credential fails review against this record.

Related: 0003 (identity is OIDC at the gateway), 0007 (federated login, no held passwords).
