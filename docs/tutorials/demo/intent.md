# Demo: The deterministic estate compiler

What the founder sees when it runs, measured 2026-09-01 on this branch. The Diamond
Standard order is tracked in [the estate compiler issue](https://github.com/chidionyema/crew/issues/804).

## 1. An agent tries to speak vocabulary that does not exist — refused

```console
$ python3 bin/intent-compile --intents tests/fixtures/intent/bad --out /tmp/ic-bad
REFUSED aws-bucket.json: (root): Additional properties are not allowed ('dns_zone', 'provider', 'region' were unexpected)
REFUSED speaks-the-zone.json: speaks estate DNA (ESTATE_ZONE); agents are blind to those values, the compiler injects them
FAIL    intent   0 intent(s) compiled to /tmp/ic-bad (0 file(s)), 2 refused
$ echo $?
1
```

The first refusal is the schema: there is no field for a provider or a zone, so there is nowhere
to put one. The second is the blindness check: the intent was schema-valid but an env value spoke
the zone name, and the compiler read the DNA and caught it.

## 2. A valid capability request — compiled, twice, byte-identical

```console
$ python3 bin/intent-compile --intents tests/fixtures/intent/good --out "$a"
ok    intent   2 intent(s) compiled to $a (5 file(s)), 0 refused
$ python3 bin/intent-compile --intents tests/fixtures/intent/good --out "$b"
ok    intent   2 intent(s) compiled to $b (5 file(s)), 0 refused
$ diff -r "$a" "$b" && echo deterministic
deterministic
$ find "$a" -type f | sort
demo-images/storage.tf
demo-web/deployment.yaml
demo-web/httproute.yaml
demo-web/kustomization.yaml
demo-web/service.yaml
```

`demo-web` asked for "a public web workload" and got a hardened Deployment (non-root, read-only
filesystem, two replicas spread across nodes), a service and a route at
`demo.${ESTATE_ZONE}`. `demo-images` asked for "a place to store 5GB of image data" and, because
the DNA says `ESTATE_STORAGE_PROVIDER: oci`, got an OCI Object Storage bucket module. No emitted
file names the zone, the registry or the provider as a literal.

## 3. The reverse compiler hydrates the estate that already exists

```console
$ python3 bin/intent-hydrate
...
ok    hydrate  14/14 Deployments drafted to intents/drafts/; not expressible yet: 368 resources across 41 kinds (top: Kustomization x47, ExternalSecret x46, Namespace x29, HelmRelease x26, HelmRepository x23, Middleware x21)
```

Every Deployment in the platform tree became a draft intent; everything it cannot express yet is
counted by kind, never hidden. Promoting a draft is a human diff, not a claim.

## 4. CI proves it both ways on every run

```console
$ bin/idp-ci   # intent rung
ok    intent   intent-compile refuses unknown vocabulary and a spoken estate name, compiles the good intents, byte-deterministic
```
