# Demo — the cross-node drill

**Door (from the UI):** Backstage → Estate → **Drills** → *verify-drill*, the row named
`cross-node`. The hourly run posts its rows there; a red `cross-node` row pages. Nothing here
needs a terminal.

## What it proves

Between 3 and 10 September 2026 the founder was served gateway timeouts every day. The cause was
not the router, not tracing and not the LLM lanes. A flannel install that had been deleted weeks
earlier had left a chain called `FLANNEL-POSTRTG` in both nodes' `nat` table, ahead of Calico's
own chain. Its catch-all rule masqueraded every packet leaving a pod for another node, so the
packet arrived wearing the *node's* physical address instead of the sending pod's address.

Every NetworkPolicy in this estate whitelists pod selectors. A packet arriving from a node
address matches none of them, so it was dropped at the tier default — with no log, no event and
no alert. The estate could not see it because every gate in the tree reads files, and every
health check that was trusted ran on one node or was synthetic.

The drill measures the two things that failed, continuously:

- **reach** — a pod on each node opens a TCP connection to the pod on the other node.
- **source** — the connection arrives wearing the sending *pod's* address, not the node's.

## Run the demo

```
bin/idp-cross-node-drill
```

A green estate prints one line per direction per check and a verdict:

```
ok    reach  10.0.148.221 -> 10.0.159.197 8/8 connects
ok    source 10.0.148.221 -> 10.0.159.197 arrived as the pod IP 10.244.117.211
ok    reach  10.0.159.197 -> 10.0.148.221 8/8 connects
ok    source 10.0.159.197 -> 10.0.148.221 arrived as the pod IP 10.244.3.63
ok    cross-node-drill                   4/4 check(s) green
```

During the outage the `reach` rows would have read `0/8 connects`, and the moment reach came
back but a masquerade rule remained the `source` row would have named the node address. Either
one is a failure; the drill never grades one without the other.

## How to make it go red on purpose

Add a rule on one node that masquerades pod traffic and the `source` rows turn red inside two
minutes without a single connection being refused — which is exactly the shape the week-long
outage had. Remove the rule and the rows go green again on the next window.

## Why it cannot be blinded

A check that cannot be measured is not a pass. If the canary pods are not both scheduled, or
their logs cannot be read, the drill exits 2 (`BLIND`) and the hourly row is `BLIND`, never `ok`.
The two canaries carry a required pod anti-affinity, so they can only ever run one per node; if
the cluster shrinks to a single node the drill says so instead of quietly grading nothing.
