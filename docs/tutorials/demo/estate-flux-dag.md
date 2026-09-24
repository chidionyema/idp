# Demo: estate-flux-dag

R29 (founder, 2026-08-25) applied to Flux: the deploy-time map is generated from what Flux
itself will honour, never hand-drawn. `bin/estate-flux-dag` parses every Kustomization/HelmRelease
under `clusters/` and `platform/` -- the same manifests Flux applies -- and writes
`docs/architecture/flux-deploy-map.dot`.

```
$ bin/estate-flux-dag
estate-flux-dag: 118 nodes, 153 edges -> .../docs/architecture/flux-deploy-map.dot
$ bin/estate-flux-dag --check
ok    estate-flux-dag: .../flux-deploy-map.dot matches clusters/ + platform/
$ echo "hand drawn" >> docs/architecture/flux-deploy-map.dot && bin/estate-flux-dag --check; echo rc=$?
FAIL  estate-flux-dag: .../flux-deploy-map.dot is not what clusters/ + platform/ declare; run bin/estate-flux-dag
rc=1
```

The `.dot` is a Graphviz file: `dot -Tsvg docs/architecture/flux-deploy-map.dot -o flux-deploy-map.svg`
renders it. Every declared Kustomization/HelmRelease is a node (`flux:{kind}:{namespace}/{name}`,
the same id `bin/estate-twin-runtime` uses for the live-receipt graph); a `dependsOn` target with
no manifest of its own is drawn dashed, so a broken reference is visible on the map rather than
silently absent from it.

Door (from the UI): not wired into a Backstage portal page yet -- open it from the repository's
file browser at `docs/architecture/flux-deploy-map.dot`, same as any other generated file, until
a TechDocs Graphviz plugin lands (tracked as "not automated yet" in the onboarding doc).
