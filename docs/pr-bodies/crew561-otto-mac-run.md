No-Issue: crew#561 (Otto fully enabled, parity list) and crew#562 (founder setup) are the tracked items on the crew board; this repo has no issue for them.

The architect-doctor run 33272111128 (2026-08-29 19:40Z) read Otto's state out of the pod: 58 restarts, `PermissionError: Permission denied: '/data/bin/hermes'` on every cron-lane install (fixed in hermes-v2, exec bit dropped by `cp --no-preserve=mode`), and a Mac transport that could never work as designed: `tailscale up --ssh` on the founder's Mac answers "The Tailscale SSH server does not run in sandboxed Tailscale GUI builds" (kb/1193). Nobody replaces the founder's Tailscale client. The Mac already carries `tag:founder-mac` (`tailscale status --self --json` on it, 2026-08-29), so every rule names the tag; a rule on his login or `autogroup:self` never matches a tagged device (kb/1068) and would lock the cluster and his phone out.

Port 22 is macOS Remote Login; Otto's identity to it is an ed25519 key minted on the apply runner (`bin/idp-bootstrap-macrun`, vault `hermes-mac-run`, private half base64 in one line), mounted into the pod (`mac-run-key.yaml`), used by `mac-run`, and authorised on the Mac by `bin/idp-mac-adopt-otto`, which reads the public half from the apply run's log. The tailnet policy is two rules: `tag:k8s` to `tag:founder-mac` on 22 and 5900 (Guacamole), `group:founder` to `tag:founder-mac:*` and `autogroup:self:*`; tagOwners for both tags are admins only. The from-scratch proof is break-glass playbook `otto-parity`: gateway ready and not restarting, key mounted, tailnet up, `mac-run hostname`, memory service, cron lanes, model lane — from inside the pod.

## Options considered
- Replace the founder's App Store Tailscale with the open-source `tailscaled` so Tailscale SSH runs: a hand on his machine at every reinstall and a client he did not choose; rejected (LAW 31, R52).
- Write the rules on the founder's login and `autogroup:self` (the first shape of this branch): the Mac is tagged, so neither matches it (kb/1068); rejected on measurement.
- Chosen: rules name `tag:founder-mac`; sshd on 22; a CI-minted key; `group:founder` is the only source that reaches every port.

## Architecture laws
- LAW 1 zero-gravity: `bin/idp-bootstrap-macrun` -> vault `hermes-mac-run` -> ExternalSecret -> `mac-run`; `bin/idp-mac-adopt-otto` -> the Mac's authorised keys
- LAW 2 fractal: `python3 -m pytest -q tests/test_incident_crew516_otto_hands_on_the_mac.py tests/test_incident_crew562_the_tailnet_acl_must_not_lock_the_founder_out_of_his_mac.py`
- LAW 3 nervous system: `tests/test_incident_crew562_the_tailnet_acl_must_not_lock_the_founder_out_of_his_mac.py` (no ssh section, both tags owned by admins only, cluster gets 22 and 5900 only, founder gets the Mac and autogroup:self only, one placeholder) and `tests/test_incident_crew516_otto_hands_on_the_mac.py` (key mounted from the vault entry, decoded, 0440 optional; no key material in git)
- LAW 4 calibration: `n/a: port set is exact (22, 5900)`
Cost-delta-usd-month: 0
Drill: oke-check

## Definition of done
1. Tracked item — crew#561, crew#562
2. Code or config — `platform/tailscale/policy.hujson`, `platform/hermes-agent/{mac-run,mac-run-key,gateway,kustomization}.yaml`, `bin/idp-bootstrap-macrun`, `bin/idp-mac-adopt-otto`, `bin/idp-oke-break-glass` (otto-parity), `.github/workflows/oke-check.yml`
3. Gate proved both ways — the tests above refuse an ssh section, a missing tagOwner, a third port, an open source; the policy applier still refuses a surviving placeholder
4. Reference doc — `platform/hermes-agent/README.md`, `docs/founder/mac-remote-desk/README.md` (every ticked item carries its measurement from the Mac on 2026-08-29; what is left for the founder's hands is listed at the top; Brewfile drops the standalone `tailscale` cask that would fight the App Store client), `docs/founder/otto-on-the-mac.md`
5. How-to and demo — merge; `gh workflow run oke-check.yml -f mode=apply` (mints the key, applies the policy); `bin/idp-mac-adopt-otto` in a session on the Mac; `gh workflow run oke-check.yml -f mode=break-glass -f playbook=otto-parity`; expect `ok mac-run-hostname` with the Mac's name
6. Catalog entity — existing hermes-agent component
7. Operational proof — the otto-parity run, all steps ok
8. Scheduled re-grade — the daily oke-check apply keeps the key; otto-parity on demand
9. Standard row — identity; no provider name added outside clusters/
10. Evidence block — below, attached by pr-evidence
Standard: Identity
Lifecycle: `hermes-mac-run` row on docs/reference/policy/credential-lifecycle.md
Optimised: 6 -> 3 steps, 4 -> 2 round trips; cut: a separate parity workflow (the break-glass job already holds the cluster) and a second apply before review; memoised: the key is minted once and kept, the adopt reads the log instead of a paste

Author-session: 80471694

## Verify

Verify: `python3 -m pytest -q -p no:cacheprovider tests/test_incident_crew516_otto_hands_on_the_mac.py tests/test_incident_crew562_the_tailnet_acl_must_not_lock_the_founder_out_of_his_mac.py tests/test_incident_crew562_mac_remote_desk_brewfile.py`
Verify: `python3 -m pytest -q -p no:cacheprovider tests/test_incident_crew284_flux_envsubst_strict_variable.py tests/test_incident_crew66_root_trust_register.py`
