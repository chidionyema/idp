# 0001. Routing is expressed in Gateway API, and no service is given a port

- Status: PROPOSED. Only the founder moves this to accepted (ruling R16, 2026-08-24).
- Date: 2026-08-24
- Deciders: founder
- Affects: every service in the estate, the backup environment and the production cluster

## The problem, measured on 2026-08-24

Twenty-two host ports are listening on this machine and no file says who owns which one.
Five of them are hard-coded into compose files in this repo. There is no registry, and the
number each service got was whatever happened to be free when someone typed the file.

The board landed on 3300 for exactly that reason: 8080 was already held by an ssh forward.
Founder: "we need to think criticlly and solve port nnnagenent etc enterprise way", and
"we are naturing as a platforn, no anateur noves".

A port registry document is not the fix. It is a file somebody maintains and nobody reads,
which LAW 28 already rejects. The fix is to remove the allocation, not to record it.

## The decision

**Routing is expressed in Kubernetes Gateway API. Services are addressed by name. No
service publishes a host port, and no routing rule is written in a vendor's own syntax.**

Two separate choices follow, and keeping them separate is the point.

1. **The standard is Gateway API.** Core resources reached GA and the project is at v1.6.0
   (June 2026). It replaced Ingress as the traffic standard through 2025 and 2026. The
   Ingress API itself is not deprecated, but SIG Network retired the ingress-nginx
   controller on 2026-03-24, so anything built on ingress-nginx is already wrong.

2. **The implementation is replaceable, and that is the property we are buying.** Sixteen
   implementations have passed core conformance. Writing routes as HTTPRoute rather than as
   one vendor's annotations or Docker labels is what makes the implementation swappable
   (LAW 19: portability outranks detection).

**Front door: Traefik Proxy.** MIT, on the conformance list at v1.6.1, eleven years old,
64,563 stars, and it is what k3s ships by default. It runs standalone in Docker for the
backup environment and as a Gateway API controller on the cluster, reading the same
HTTPRoute resources.

**Agent-to-tool traffic: agentgateway, and it is not the same layer.** Apache-2.0, on the
conformance list at v1.6.0, and already named in `idp/docs/specs/fortress-stack.md` and
crew#180. It routes MCP, A2A and LLM calls, which is a different concern from a front door
for human-facing pages. It is deliberately not proposed as the front door: created
2025-03-18, 4,511 stars, 335 open issues, latest release v1.4.1 on 2026-07-29. That is a
young project, and a buyer's engineer will ask why the front door rests on it.

## What this rejects, and why

- **ingress-nginx.** Retired by SIG Network on 2026-03-24. No updates, no bug fixes.
- **Vendor labels as the config format.** The first attempt at this on 2026-08-24 used
  Traefik's own Docker labels. That works and it is the wrong artefact: the labels do not
  travel to the cluster, so the work would be done twice and the second copy would drift.
  This is the amateur move the founder named, and it was reverted before anything routed
  through it.
- **A port registry.** See above.
- **One gateway for both concerns.** Human pages and agent tool calls have different authz
  and different failure modes. Two gateways is not stitching; one gateway pretending to be
  both is.

## What is still open, and it is bigger than routing

The identity proxy is not chosen. Gateway API expresses authentication as a filter or an
extension, so the standard does not pick one for us. Until it is chosen, the board's login
is removed only on a loopback-bound port in the backup environment, and
`idp/board/MIGRATION.md` recorded that as the blocker (Kanboard and that file were retired on 2026-08-26, crew#282). This ADR does not pick it either,
because it is one row in `crew/docs/STANDARDS.md` chosen once for the whole estate.

## Consequences

- Every compose file loses its `ports:` block. One gateway publishes 80 and 443.
- Local names need DNS. On this machine that is one `/etc/hosts` line, added once, which
  needs the founder because it needs sudo (LAW 27: need him once, then never again).
- Nothing above has been booted. A config that has never started is not a plan, and this
  file is a decision record, not a claim that anything runs.

## Sources

- Gateway API conformant implementations: https://gateway-api.sigs.k8s.io/implementations/
- Ingress vs Gateway API, 2026: https://oneuptime.com/blog/post/2026-02-20-kubernetes-ingress-vs-gateway-api/view
- ingress-nginx retirement: https://rafay.co/ai-and-cloud-native-blog/goodbye-to-ingress-nginx---what-happens-next
- Implementation comparison: https://www.apefactory.com/en/insights/kubernetes-gateway-api-provider-comparison
- agentgateway standalone Docker: https://agentgateway.dev/docs/standalone/latest/integrations/platforms/docker/
- Repository figures read from the GitHub API on 2026-08-24.
