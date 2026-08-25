# Onboarding: static-secret

## What it is

`bin/static-secret-gate` counts long-lived credentials on the host it runs on and in the sops
vault, and exits 1 while the count is above 0. `STATIC_SECRET_GATE_ROOT` points it at another
home directory, `ESTATE_CODE` at the directory holding the checkouts, `ESTATE_SECRETS` at the vault
(the CI fixtures use all three; no path in the script names this machine, LAW 46).

## Why it exists

Founder, 2026-08-25: "yesterday when cluster was being built I had a lot of requests for
password ... if I did nothing moves forward, this is not sustainable." Every static credential is
a prompt waiting to happen and a thing a buyer's engineer can copy. The Kimi auth v2 spec sets
the target at zero: machines authenticate by workload identity (OCI identity propagation for
GitHub Actions, OKE workload identity in-cluster, SPIFFE between agents) and people by hardware.

## How the number goes down

Each line names the identity that replaces it. CP2 removed the need for an API key in CI
(`.github/workflows/oke-check.yml`). The laptop's `estate-tofu.pem` goes with CP5, the S3 state
key when OpenTofu's S3 backend can take a session token or the state moves to a backend that can.
