# Estate Stewardship — P0 integration candidate

A bounded, evidence-backed improvement lifecycle. No external Python dependencies. This is a **tested integration candidate**, not a live production deployment.

## Run

```sh
python -m unittest discover -s tests -v
python -m stewardship.cli --db output/stewardship.sqlite3 record issue-123 observed --actor agent-1 --payload '{"summary":"Repeated auth fallback","evidence_refs":["trace:123"],"verified":false}'
python -m stewardship.cli --db output/stewardship.sqlite3 cases
python -m stewardship.cli --db output/stewardship.sqlite3 verify
python -m stewardship.cli authorize examples/change.json examples/policy.json
```

## Design

- Append-only event log with SHA-256 hash chaining and tamper detection. **Not** cryptographic non-repudiation: a privileged DB writer can rewrite the chain. Anchor heads to the existing estate receipt system before production use.
- Classified event records; nested forbidden sensitive keys are rejected. **Not** comprehensive DLP: sensitive values inside arbitrary strings are not automatically detected.
- Autonomous authority is deny-by-default for shared changes, high risk, irreversible changes, new infrastructure and security-boundary changes. Approval claims are **caller assertions** until the shipping adapter validates them against estate gates.
- Paired measurements compare correctness, latency and cost descriptively; statistical confidence and representative workload selection remain integration tasks.
- No automatic code changes or network writes. Execution remains delegated to the estate's existing claimed work executor.

## Production requirements

Wire to GitHub claim-gate, estate-execute, Oracle, AEI, /fleet, evidence receipt chain and existing ticketing; add authentication, multi-tenant clearance, retention, backup and load tests. Validate real operational outcomes rather than claiming deployment from unit tests.
