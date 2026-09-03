# LATEST — session a0d64ea4 (crew#66 founder lane)

## RESUME HERE

Branch `feat/crew66-root-trust` (from crew459-portal-polish worktree): root-trust gate PR
for crew#66 ruling 5453747447 / crew#580. Files: bin/idp-root-trust (+ test
tests/test_incident_crew66_root_trust_register.py, 5 passed), docs/reference/policy/root-trust.md
(register, 33 entries, MEETS 11 / PARTIAL 1 / MISS 19), bin/idp-bootstrap-tailscale (written,
not run end to end), security-policy row, idp-ci + verify-drill rows, stale comments fixed,
vault-seed tailscale entry refused. Next: commit, push, bin/pr-report, PR (Tracked: crew#66,
Drill: root-trust), then tell the founder `bin/idp-bootstrap-tailscale` is ready to run.
Then the bootstrappers PR (#575–#579): bin/idp-estate-seed, router keys, github-app tokens,
bin/idp-bootstrap-cloudflare, bin/idp-bootstrap-vendors, umbrella bin/idp-bootstrap-estate.
Founder plan recorded crew#66 5453918598 (one-shot, "just you").

## RESUME HERE (2026-09-02T19:2xZ, lane .wt-dagster-port)
Founder instruction: user-deployment probe timeouts to 30s. Measured in-pod: exec health-check healthy path = 5s wall at 250m CPU, so the handler moves to the kubelet-native gRPC probe (server answers grpc.health.v1 SERVING, measured). Branch fix/dagster-probe-grpc-30s off origin/main: platform/dagster/dagster.yaml probe block + tests/test_incident_dagster_user_deployment_probe_defaults.py. Next: push, PR, green, founder merges.

## RESUME HERE (54539261, 2026-09-02T21:05Z)
Silent-green: notify+otto-staging kustomizations True, all pods CrashLoopBackOff.
Two measured roots, two fixes in flight:
1. idp branch fix/notify-apprise-boots — apprise manifest exported secret file `founder-telegram`
   (dash = invalid shell identifier, set -eu fatal, and bash printed the token value into the pod
   log — rotation queued for the founder). Fix: ES template key founder-telegram.cfg,
   APPRISE_STATEFUL_MODE=simple + APPRISE_CONFIG_DIR=/run/secrets/notify, image default CMD.
2. hermes-v2 worktree ~/dev/code/.wt-otto-image-deps branch fix/otto-image-deps — image never
   installs otto/requirements.txt (jsonschema ModuleNotFoundError in otto-staging). Fix: uv pip
   install runtime section into the venv + otto rows in deploy/k8s/boot-contract.txt.
Watcher b9c14c543 follows apply run 33681830297 (new deepseek key verdict).
