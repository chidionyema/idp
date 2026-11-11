# Legion integration contract

Legion is the umbrella product. Its planes have one responsibility each:

| Plane | Responsibility | Must not do |
|---|---|---|
| Intercloud | Select, provision through provider adapters, fence and reclaim lanes | Hold model keys or execute formations |
| Muster | Turn a RunSpec into a receipt-gated execution | Claim that a placement is ready without an observed readiness receipt |
| Pennyd | Authenticate model calls, enforce budgets, route and record usage | Provision infrastructure or decide formations |
| Receipt layer | Join placement, execution and model evidence into one verifiable run record | Trust a component's self-report |

## On-demand placement

```text
RunSpec
  -> Muster requests placement
  -> Intercloud evaluates free-first lanes and declared paid options
  -> provider controller converges capacity
  -> observed readiness receipt
  -> Muster engages the formation
  -> every model call through Pennyd
  -> step receipt references placement + Pennyd request IDs
  -> next step allowed only when the receipt verifies
  -> work drains, lane is measured and reclaimed
```

Intercloud is therefore a resilience layer over operational options. It can
move work between failure domains on demand, but it depends on a substrate and
provider adapters to make capacity real.

## Minimum receipt fields

```text
run_id
step_id
formation
placement_id
provider
lane
observed_ready
pennyd_req_ids[]
input_tokens
output_tokens
cost_usd
started_at
finished_at
evidence_sha256
previous_receipt_sha256
```

A run may fail over to another eligible lane, but it must create a new
placement receipt. It may not silently rewrite the provider or lane on the
existing receipt.

## Data ownership

- Formation definitions, doctrine packs and rank policy are governed data.
- Lane capability, cost and failure-domain declarations are governed data.
- Model aliases, fallbacks and budgets are governed Pennyd data.
- The receipt chain is append-only evidence.

No component may infer another component's contract from a URL or a model
name.
