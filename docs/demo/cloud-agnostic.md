# Demo: the platform names no cloud

Run the gate on the repository and on the fixture that contains an Oracle load-balancer annotation.

```
$ bin/cloud-agnostic-gate
cloud-agnostic-gate: 0 provider-specific line(s) outside the provisioner
$ CLOUD_AGNOSTIC_ROOT=tests/fixtures/cloud-agnostic/bad bin/cloud-agnostic-gate
platform/edge/svc.yaml:6: service.beta.kubernetes.io/oci-load-balancer-shape: flexible
cloud-agnostic-gate: 1 provider-specific line(s) outside the provisioner
```

The first run is the state of `platform/` today: zero lines name Oracle, AWS or Google outside the three places allowed to (the compute provisioner `platform/oci`, the one ClusterSecretStore `platform/secret-store`, and the per-cluster rows under `clusters/`). The second run shows the gate refusing a Service that carries a provider annotation, and printing the file and line so the author can move it to the cluster row. The same gate runs inside `bin/idp-ci` on every pull request, so the count cannot drift back up without a red check.
