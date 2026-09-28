# Demo: ns-fence-gate

`bin/ns-fence-gate` refuses a namespace that is born without its fences: a
ResourceQuota, a LimitRange, a NetworkPolicy that denies both directions for
every pod, and a DNS exception on port 53 when egress is denied. It exists
because, measured on the `estate` cluster before any fence existed, a pod in one
namespace curled a pod in another by IP with no credential and got HTTP 200 in
4ms. That is the default state of every namespace anyone creates (crew#191).

Every rule is checked against the object itself, never a name or a label. The
fixtures prove the gate both ways:

```
$ bin/ns-fence-gate tests/fixtures/ns-fence/good.yaml
ok     ns-fence-gate: 1 namespace(s) in tests/fixtures/ns-fence/good.yaml carry a quota, a LimitRange, a both-ways default deny and a DNS exception: fixture-fenced
rc=0
$ bin/ns-fence-gate tests/fixtures/ns-fence/bad.yaml
FAIL   ns-fence-gate: 8 defect(s) across 4 namespace(s) in tests/fixtures/ns-fence/bad.yaml
       - namespace fixture-flat: no ResourceQuota. A runaway pod here takes the whole node with it.
       - namespace fixture-flat: no LimitRange, so no pod gets default requests or a ceiling.
       - namespace fixture-flat: no NetworkPolicy denies Ingress for all pods. Any pod in the cluster reaches these by IP.
       - namespace fixture-flat: no NetworkPolicy denies Egress for all pods. A compromised pod here reaches every other namespace and the internet.
       - namespace fixture-no-dns: Egress is denied and nothing allows port 53. DNS will fail in every pod, and it will look like the application is slow, not like a policy.
       - namespace fixture-quota-only: a ResourceQuota with no LimitRange. Every pod that does not declare cpu and memory will be REFUSED with 'must specify limits.cpu' -- this fence refuses correct work.
       - namespace fixture-selective-deny: no NetworkPolicy denies Ingress for all pods. Any pod in the cluster reaches these by IP.
       - namespace fixture-selective-deny: no NetworkPolicy denies Egress for all pods. A compromised pod here reaches every other namespace and the internet.
rc=1
```

`fixture-quota-only` is the rule that matters most: a quota with no LimitRange
makes every pod that declares no cpu request unschedulable, so it is a fence
that refuses correct work, which is the outage (LAW 38). `fixture-no-dns` is
the rule that gets forgotten, because its symptom is a five-second timeout on
every outbound call rather than a refusal.

Run over the estate's own manifests today it reports 76 defects across 19
namespaces, and `bin/idp-ci` carries that as report-only until crew#191 fences
them; the moment the count is 0 the same line becomes a refusal:

```
$ bin/ns-fence-gate platform
FAIL   ns-fence-gate: 76 defect(s) across 19 namespace(s) in platform
       - namespace backstage: no ResourceQuota. A runaway pod here takes the whole node with it.
       ...
```

`bin/ns-fence-gate --live` reads the cluster instead of the manifests, because
a manifest that is correct and not applied protects nothing; with no cluster
reachable it prints BLIND, never a verdict.
