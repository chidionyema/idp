# The secret bridge's certificate deadlock

Owner: @chidionyema. Record for decision 0017; found live on 2026-09-02 by [the cluster's own state check](https://github.com/chidionyema/idp/actions/runs/33619832091).

## What broke

The human door for secrets (decision 0017) shipped with a flaw that stopped the whole secrets
layer from ever reporting ready. The bridge to Bitwarden runs as a small server inside the
external-secrets release. That server needs a certificate before it can start. The certificate
was created by the human-vault layer — and the human-vault layer waits for external-secrets to
be ready before it applies anything.

So the layer waited for a pod, the pod waited for a certificate, and the certificate waited for
the layer. Nothing moved. The cluster showed `external-secrets: Reconciliation in progress`
forever, and every layer behind it stayed red.

## Why it happened

The certificate files were grouped with the rest of the human-vault work because they belong to
the same feature. But grouping by feature ignored the order things start in. The rule that
matters is: anything a layer's own pods need at start must be created by that same layer, or by
one it depends on — never by a layer that depends on it.

## The repair

The certificate chain moved into the external-secrets layer itself
(`platform/secrets/certs.yaml`). That layer now also names `edge` as a dependency, because edge
installs cert-manager, the service that signs the certificate. The order is now a straight
line: edge brings the signer, external-secrets brings the certificate and the bridge, and
human-vault brings only the store and the token wiring on top.

## The guard

`tests/test_incident_sdk_server_certs_ride_their_own_row.py` fails any change that recreates
the loop: if the bridge is switched on, its certificate must live in the external-secrets
layer, that layer must depend on edge, and no dependent layer may carry the certificate.
