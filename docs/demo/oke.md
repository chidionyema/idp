# Demo: Flux on OKE

```
bin/idp-oci-login                       # ok    oci     identity estate-tofu answers in uk-london-1; ...
(cd platform/oci && tofu apply)         # Plan: 60 to add ... Apply complete
bin/idp-flux-bootstrap                  # ok apiserver ready / ok sops-age secret / flux get kustomizations
bin/idp-catalog-push                    # ok      estate-catalog pushed, revision <sha>@<utc>
```

`flux get kustomizations` is the receipt: `backstage`, `chaos`, `estate-catalog` each show
`Ready True` with the applied revision. Before idp#29 merges, `backstage` shows the Deployment
waiting on an image pull; that is the expected state and is written on the onboarding page.

Render without a cluster:

```
kubectl kustomize platform/backstage/overlays/oke | grep -E '^kind:|image:'
```
