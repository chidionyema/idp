# How to put a contract on a tool call

The gate grades one declared contract (pre-condition, post-condition, observations) and exits 0
(both conditions held), 1 (a condition failed), or 2 (BLIND — unreadable, or a subject with no
observation at all). It takes no configuration and needs no model.

## Check a contract

```bash
python3 bin/idp-contract --pre "pod uptime > 0s" --post "readiness probe passes within 30s" \
    --tool restart_pod --observe <observations.json>
```

`<observations.json>` is `{"<subject>": [[t0, v0], [t1, v1], ...]}` — the readings a caller (a
live probe upstream, or a recorded transcript) declares. This script never invents a value.

Real output, post-condition failing at its deadline:

```
$ python3 bin/idp-contract --run tests/fixtures/contract/bad/contract.json
FAIL  contract refused (post_condition_failed): post-condition 'readiness probe passes within 30s' never held within 30s (last observed False at t=20.0)
```

Real output, post-condition holding inside its deadline:

```
$ python3 bin/idp-contract --run tests/fixtures/contract/good/contract.json
ok    contract restart_pod held: pre and post both held; post confirmed at t=20.0
```

## The condition grammar

`<subject> <op> <value>` where `<op>` is one of `>` `>=` `<` `<=` `==` `!=`, or `<subject>
passes` / `<subject> fails` for a boolean reading — with an optional trailing `within <N>s`
deadline on the post-condition. `<subject>` is matched case-insensitively against the
observation keys.

## Name the cause without acting on it

```bash
python3 bin/idp-contract --explain <contract.json>
```

Always exits `0`; prints whether the contract held, and if not, which condition and why.

## Exit codes

| code | meaning |
|------|---------|
| 0 | pre-condition held, and post-condition held by its deadline |
| 1 | pre-condition or post-condition failed (both observed, neither held) |
| 2 | BLIND — the contract file could not be read, or a named subject has no observation at all |

## Prove the script itself runs

```bash
bin/idp-contract --self-test
```

Runs the real contract path against the bad/good fixtures under `tests/fixtures/contract/` and
exits 0 only if the bad one refuses and the good one holds (LAW 45).

## What it will and will not catch

**Catches** the founder essay's named failure mode: a trajectory that claims a tool call
succeeded ("I assume the database is up") when the post-condition was never actually observed
to hold.

**Does not catch** a bad pre/post-condition declaration itself — a contract that names the wrong
subject, or a deadline too generous for the real SLA, still grades clean if the observations
satisfy what was literally written. This gate proves the declared contract, not that the
contract is the right one to declare.

**Does not reach a live cluster.** There is no bespoke k8s/HTTP prober here — wiring one would
duplicate what the estate MCP server (`mcp/plugins/estate_simulate.py`, `workload_state.py`)
already exists to do (R43, THE HEADLINE). Feed this script observations from that layer, or from
a recorded session, not a new client.

## Adding a rule

The gate is registered in `rules.yaml` as `id: contract` with a fixture pair, so `bin/idp-ci`
runs it and `docs/policy/rules-table.md` is generated from it. Change the rule by editing
`rules.yaml`, then regenerate:

```bash
bin/idp-rules render-agents-md
bin/idp-rules run --only contract
```
