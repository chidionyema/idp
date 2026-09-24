# Onboarding: estate-flux-dag

What it is: the deploy-time map that cannot drift, because it is a pure function of the
`dependsOn:` edges declared in `clusters/` and `platform/` -- the same manifests Flux itself
reads before a reconcile. It answers "what does Flux wait on before it applies this" without a
person maintaining a diagram by hand.

How to use it:

- `bin/estate-flux-dag` renders `docs/architecture/flux-deploy-map.dot` from every
  Kustomization/HelmRelease under `clusters/` and `platform/`.
- `bin/estate-flux-dag --check` is the gate (rung 8b in `bin/idp-ci`): exits 1 when the `.dot` on
  disk is not what the manifests currently declare, 3 (BLIND) when neither `clusters/` nor
  `platform/` exists.
- Never edit `docs/architecture/flux-deploy-map.dot`. Change a manifest's `dependsOn:` and
  re-render.

Spec: R29 (crew#236 row 2) applied to Flux. Test: `tests/test_estate_flux_dag.py` (200-seed
property test + the R29 incident: drift refused, passes after render, BLIND with no tree).

Not automated yet: no scheduled re-render or Backstage TechDocs rendering of the `.dot` --
`bin/idp-ci` only proves the committed file matches HEAD's manifests on each run; the render
itself still happens locally before a commit, same as `bin/estate-diagram`.
