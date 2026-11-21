# 2026-11-17 - The estate runs without any one device

> **Decided:** the founder, 2026-11-17: *"we are not dependent on macbook at all, it is wholly
> optional, our estate must be able to run fully without one device."*

- **Status:** accepted (requirement). Implementation: BUILT and falsified, not yet operating.
  `bin/idp-passkey-enroll` + `bin/idp-passkey-seal.mjs` + `seal_verified()` in
  `bin/verify_three_proofs.py` (lane `lane/gate-and-vault-sink`, claim idp#8393): a guarded commit
  is sealed by a WebAuthn assertion from a passkey, and the gate accepts either that or the file
  key, refusing when neither verifies. Operating requires two measurements this record does not
  have yet: the founder's keyring committed at `docs/keys/founder-passkey.json`, and a real tap
  sealing a real guarded commit. See "Implementation, measured 2026-11-21" below.
- **Refines:** ADR 0048 (one node + admission list). **Supersedes:** nothing.
- **Claim:** pending (GitHub API unavailable in the session that wrote this - see "Blocker").

## The requirement, as a falsifiable claim

> With the MacBook powered off, every estate function that a human or an agent depends on still
> answers.

A claim like that is only worth writing down if it can fail. Today it fails, and this record names
exactly where.

## Measured, 2026-11-17 12:56 UTC, on the MacBook itself

```
launchd estate jobs loaded:        2  of 71 plists on disk
                                   (ai.estate.dsh-web + ai.estate.dsh-web-heal - both created today)
listening ports:                  23
estate Python services listening: ~14  (fleetview 18790/18791, surfaces 3081/3082,
                                      4090, 4300, 8002, 8766/8767/8770, inboxd 8789, nats 4222)
router:                           pennyd 127.0.0.1:4200 - a laptop process
web surface:                      dsh 127.0.0.1:3080 - a laptop process
secrets:                          ~/.config/prospector/age-key.txt  (age private key, local disk)
                                  ~/.estate/pennyd/keys.toml      (router keys, local disk)
cluster home:                     none reachable. ~/.kube/config-estate is an OKE endpoint whose
                                  `oci` exec plugin is gone; no k3s kubeconfig exists on this Mac.
```

The Mac is not merely *a* dependency. It is the only place the router, the credential, the
executor and the surfaces exist. Power it off and the estate does not degrade - it stops.

## What "no single device" actually requires

Three things are load-bearing, and each has to move to a home that outlives any one machine:

1. **The model router.** `pennyd` is a process on a laptop, addressed as `127.0.0.1:4200`. A
   device-independent estate addresses a name, not a loopback address, and the router is a workload
   with a replica count - not a launchd job.
2. **The credential.** An age private key and `keys.toml` on one disk means the estate's ability to
   think is stored in one machine's filesystem. Until the key is in a secret store the cluster can
   read, no amount of extra hardware helps.
3. **The execution surface.** The executor is a launchd daemon on the laptop. Agents that must
   survive a laptop being closed need an execution boundary that is not a login session.

## Order of work (each step provable on its own)

1. **Give the estate an address.** Bring up the declared home (ADR 0048: one Ampere A1 VM, k3s) or
   declare the CI k3s the home. Without this there is nowhere for 1-3 to move *to*; every other step
   is blocked on it.
2. **Router off the laptop.** pennyd as a cluster workload behind a stable name; the laptop becomes
   one client among several. Proof: `curl` the name from a device that is not the Mac.
3. **Secrets into the store.** age key + router keys in the cluster's secret store; the laptop keeps
   a read-only convenience copy, never the only copy. Proof: rotate a key with the Mac powered off.
4. **Executor as a workload.** Agents run where the cluster is, not where a login session is.
5. **Falsifier.** `bin/estate-device-audit` reports, on any device: which estate functions answer,
   which are loopback-only, and where secrets live. Green means every line answers from off-device.

## Blocker (honest, dated)

This record cannot land: `gh` returns `401 Requires authentication` (no token in the keyring,
`~/.config/gh/hosts.yml` has none, no `GH_TOKEN`, no GitHub credential in the vault). The commit
carrying this file exists locally on `feat/pennyd-one-name`. `gh auth login` unblocks it.

## Consequences if ignored

Every incident review that ends "the laptop was closed", "the laptop was asleep", "the laptop's disk
filled" is this ADR being violated. The estate has no redundancy to trade against those, because it
has no second home to fail over to.
