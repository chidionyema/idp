# Demo: estate-request-router

`bin/estate-request-router` is slot 3 of the estate's local ops tier
(crew#929): it routes an inbound request to the estate System that owns it.
The owning taxonomy is not guessed or hardcoded — it is read from the real
`backstage/platform/catalog-info.yaml` (delivery, edge, identity,
observability, scheduling, agents, resilience, products, data, commerce), so
the router's lanes grow exactly as the estate does. Deterministic and
model-free.

Route a real request (e.g. an issue or a founder message):

```
$ bin/estate-request-router "the portal front door sign-in is returning 502"
ROUTE:identity

$ bin/estate-request-router "the postgres cluster is out of disk"
ROUTE:data

$ printf 'the LLM model router refused deepseek with a 401' | bin/estate-request-router -
REFUSED: no single estate System matched (never guess a lane); nearest: observability=2, agents=2, ...
```

A clear request resolves to one owning System. An ambiguous one — where two
Systems tie, like the model-router question sitting between the AI layer
(`agents`) and the monitoring layer (`observability`) — refuses loudly and
names the nearest candidates rather than guessing one. That refusal is the
no-op contract working: an uncertain lane is handed to a human, never invented.

List the taxonomy the router routes to:

```
$ bin/estate-request-router --systems
agents commerce data delivery edge identity observability products resilience scheduling
```

The router reads only the request's own text and returns only a route decision —
it never forwards the request body to a lane (LAW 21), so no customer or user
content leaves on the routing decision.
