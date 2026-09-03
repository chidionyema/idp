## RESUME HERE (2026-09-02T13:3xZ, session 54539261, .wt-eye-breaker)
Thing 1 (bitwarden-machine into the OCI vault) pivoted to CLI-by-OCID on founder order
(founder doc 2026-09-02T1325Z…37dbce42.md). Write capability PROVED: canary
authz-canary-delete-me created ACTIVE then deletion-scheduled with the estate-tofu profile.
WAITING on the founder's one action (Telegram pin 21416): `! pbpaste > ~/.estate/bitwarden-machine.token`.
Background watcher bk4o20wvq fires the moment the file lands; then:
  oci vault secret create-base64 --vault-id …ervi35puaagem.abwgiljsj3naku45j7hnffej3xlqb3b3oiv6voegh5nhzekbxqofbxqxm5sa
  (compartment …ikyge5oq, key …ja3d5kfq, content = base64 of RAW token — consumer vault-bootstrap.yml
  reads it decoded via bin/idp-cloud secret get), shred the file, read ACTIVE, ping code-f9 to dispatch
  vault-bootstrap.yml. Side thread being opened now: scratch worktree wt-doc off origin/main, branch
  fix/bitwarden-cli-runbook — repoint the three console-path doc spots (bitwarden-human-vault.md §3,
  root-trust.md bitwarden-machine row, vault-bootstrap.md step 3): value is supplied once by the
  operator, the vault write is code (bin/idp-cloud secret put — RAW file, never vault-put JSON).
Incidents ledger ~/.claude/LAWS-INCIDENTS.md commit ca62f85 carries today's three findings.
