# Onboarding: estate-twin-runtime

How to ask the estate what it actually is, rather than what it declares.

## Before you write anything, ask the graph

Every session starts by asking whether the capability already exists. The estate has 1,523
unmerged branches carrying 722 files that exist on no commit of main; a question answered
from the graph costs a second, and a question answered by rebuilding costs a day.

```
bin/estate-twin-runtime --once --code --domains   # refresh, ~5s
bin/estate-twin-runtime --state                   # is each domain current, and what is broken
bin/estate-twin-runtime --dead                    # what is not serving, workloads first
```

An agent session asks the same thing over the estate MCP server:

```
get_estate_state(domain="code")           # what is built and unmerged
get_estate_state(query="lago")            # anything whose id carries that word
```

## If it is not in-cluster

The graph is built in CI by `.github/workflows/catalog-render.yml`, which runs the sweep and
then ships `estate.db` as the OCI artifact the `estate-mcp` pod pulls. The runtime half can
also be swept from a laptop, which is how it is proved:

```
bin/idp-cloud object get --bucket estate-drill-receipts --name state/cluster | head -1
bin/estate-twin-runtime --once --code --domains
```

The bus needs a port-forward to be read from here, and publishes back through the same door:

```
kubectl port-forward -n event-bus svc/nats 4222:4222 &
NATS_URL=nats://127.0.0.1:4222 bin/estate-twin-runtime --once --code --publish
```

`--publish` is off unless asked for: a dry sweep never touches the bus.

## Adding a domain

A domain is one function in `bin/estate-twin-runtime` following the shape of `sweep_code`:
make the schema, write one node per thing with `_put`, write a freshness row, return a
counts dict. Two rules are not optional.

**A domain that cannot be read writes ONE node saying why**, never nothing:

```
_blind(con, "bus", "stream", "no JetStream stream could be read; the bus is unreachable")

```

An empty domain renders exactly like a healthy one, which is the failure this whole system
exists to end. When a later sweep succeeds, `_clear_blind` removes the marker so the graph
cannot hold yesterday's blindness next to today's reading.

**Every domain writes a freshness row.** A domain with nodes and no freshness row reads
`UNKNOWN` for ever, and a reader that cannot tell a five-minute answer from a five-day one
is a lie with a timestamp on it.

## The rules

Three rules in `rules.yaml` hold this, and all three are green in `bin/idp-ci`:

```
bin/idp-rules run --only estate-twin         # the graph equals the catalogue; no second store
bin/idp-rules run --only estate-graph-view   # the view never flatters a stale read
bin/idp-rules run --only bdd-proof           # no PR opens without proof on its own head
```

## Proof

Every claim about this feature carries the command that proves it:
`docs/evidence/estate-twin/PROOF-OF-WORK.md`, raw capture in `PROOFS.txt`. The acceptance
suites are:

```
python3 tests/test_estate_twin_domains.py                      # all 12 domains
python3 -m pytest sovereign/tests/bdd/test_estate_twin.py -q   # 8 scenarios
./bin/idp-estate-graph-prove                                   # 13 proofs of the view
```
