# Compile the estate — see what the charts actually render

## What it is

Every workload's real CPU and memory, rendered from git by the Helm chart that produces it — not
read from a comment, a values file, or a patch that a chart can override.

## See it

```console
$ bin/idp-compile-helm
ok    compiled-helm 33/33 release(s), 646 object(s) -> .estate/compiled-helm.json
```

One workload out of the document:

```console
$ jq '.releases[] | select(.name=="langfuse") | .objects[] | select(.kind=="Deployment")' \
    .estate/compiled-helm.json
{
  "apiVersion": "apps/v1",
  "kind": "Deployment",
  "namespace": "observability",
  "name": "langfuse-web",
  "resources": [
    {
      "name": "langfuse-web",
      "requests": { "cpu": "500m", "memory": "2Gi" },
      "limits": { "cpu": "500m", "memory": "2Gi" }
    }
  ]
}
```

That `500m` is what the cluster will run. It is not what a file claims — it is what the chart
produces.

## Why it exists

On 2026-09-12 a right-sizing that had been merged **five days earlier** was not in the cluster.
The pull request changed a comment that said "cpu 500m" and left the value at 1000m:

```yaml
      # SUPERSEDED for cpu, 2026-09-08. ... the startupProbe patch in langfuse.yaml gives boot
      # 300 seconds and sets cpu 500m on both sides.
      requests: { cpu: 1000m, memory: 2Gi }     # <- the comment says 500m; the value says 1000m
      limits: { cpu: 1000m, memory: 2Gi }
```

Every check was green, because the YAML was valid. The cluster kept running 1000m and said nothing,
because nothing asked.

`kustomize build` cannot catch this: it emits the HelmRelease *object*, never the Deployments Helm
creates from it. So the compiled document is the only place the real number exists outside the
running cluster.

## The gate

```console
$ pytest sovereign/tests/bdd/test_compiled_helm.py -q
2 passed
```

Proved both ways in one session: red with the value at 1000m, green at 500m. `bin/idp-ci` runs it on
every pull request, and a chart that does not render fails the run rather than passing as an empty
estate.

## Where you see it

The Ops page at `/ops`, in the section **"What the charts actually render"**. Every workload, its
rendered CPU, and whether request equals limit.

## Reading the output

| field | meaning |
|---|---|
| `releases[].objects[]` | every manifest the chart produced |
| `resources[].requests` | what the scheduler reserves — this is what makes a cluster "full" |
| `resources[].limits` | the ceiling the kubelet enforces |
| `releases[].error` | a chart that did not render; its numbers are **unknown**, never assumed |
| `releases[].values_sources` | the files and ConfigMaps whose values were used |
