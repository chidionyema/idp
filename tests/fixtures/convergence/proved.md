Raise the memory limit on the edge router from 128Mi to 256Mi

OOMKill fired twice overnight (crew-recorded), the pod was evicted, and traffic
re-routed around a hole. This raises the limit so the same load fits; the
request is untouched so no neighbour's quota is disturbed.

Proved in the shadow dimension before this pull request opened:

Proof-of-Convergence:
  vcluster: shadow-edge-router-20260908-a1b2c3
  run: https://github.com/chidionyema/idp/actions/runs/984312
  asserted: deployment reached Ready, 2/2 replicas, /ready 200, quota still fits
