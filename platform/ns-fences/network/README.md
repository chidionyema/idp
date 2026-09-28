# These NetworkPolicies are generated, and they are applied

`platform/ns-fences/kustomization.yaml` lists `network` as a resource, so the single Flux row
`ns-fences` in `clusters/oke/platform.yaml` carries the quota, the LimitRange and the policies
together. Until 2026-09-05 it did not, and this file said the omission was deliberate.

**The reason it was deliberate has gone.** The version of this file written on 2026-09-04 said
"this cluster runs flannel", which routes pods and does not implement NetworkPolicy, so applying
the policies would have added nothing and let the estate claim a protection it did not have.
Calico merged the day after in `0c0075b0` and its Flux row (`clusters/oke/platform.yaml`, the
`calico` Kustomization) carries no `suspend` field. The sentence stayed behind, twenty lines above
a comment on the calico row saying the opposite, and on 2026-09-05 a session read the stale half
and told the founder that nothing in the estate enforced policy. That is why this file now
describes what the row does rather than why it is held back.

## The risk that has not gone

The flows in `../allowances.yaml` come from a scan of every manifest for `<service>.<namespace>.svc`
references, and that scan cannot see a flow whose address arrives through a secret, an operator's
client-go call to the API server, or Prometheus scraping a namespace it monitors. A `default-deny-all`
lands in every fenced namespace, so a flow the scan missed is a flow that stops.

One such gap was found on 2026-09-05 and is fixed in this generation: `hindsight` had an
`ingress_from` list and **no `egress` key at all**, while `estate-db`'s own `ingress_from` already
named `hindsight` -- one direction of the same conversation declared, the other missing. Under
default-deny the estate's memory service would have been cut off from `estate-rw.estate-db` at
`5432`, which is its Postgres, and from the `llm` router it calls for `HINDSIGHT_API_LLM_MODEL`.

The lesson from that one: an `ingress_from` naming a namespace is evidence the reverse `egress`
belongs somewhere, and `bin/idp-ns-fence-gen` does not derive it. Every remaining asymmetry in
`../allowances.yaml` is a candidate for the same defect.

## Reading a denial

Calico's flow logs, and the namespace's own pod logs, name what stopped. A connection timing out
to a `*.svc` address in another namespace is the shape: add that namespace to the source's
`egress:` list and the destination's `ingress_from:` list in `../allowances.yaml`, re-run
`bin/idp-ns-fence-gen`, and open a pull request. Never hand-edit a file in this directory; the
next generator run overwrites it.
