# Onboarding: the truth-teller demo

## What it is for

It answers one question, the one a buyer asks about every agent: *how do I know it did what
it says it did?* An agent claims a change is done; this asks the cluster and refuses the
claim if the two disagree. It is a demonstration of the estate's proof discipline, not a
gate — nothing in CI depends on it.

## What it costs

Nothing. It runs locally, it is a Python script, and it has no cloud spend. The only thing it
needs is the `demo-sandbox` vcluster, which the sandbox tile already provides and which costs
what the sandbox costs when it is up.

## Where it lives

| | |
|---|---|
| the CLI | `bin/idp-truthteller-demo` |
| the buyer page | `docs/demo/agent-cannot-lie.html` |
| the demo doc | `docs/tutorials/demo/truthteller-demo.md` |
| the tests | `tests/test_truthteller_demo.py` |
| the port | 8443, declared in `catalog/ports.yaml` |

## How to run it

```bash
bin/idp-sandbox action=launch    # once; the demo is BLIND without it
bin/idp-truthteller-demo         # the rogue claim, refused
bin/idp-truthteller-demo --honest
bin/idp-truthteller-demo shadow demo-shop   # just read the observed state
```

Exit codes are the result: `0` proved, `1` the claim did not survive the question,
`2` BLIND. Never read the prose — read the exit code.

## How to stop it

It stops when it returns. The only lasting thing it creates is a port-forward, which it
cleans up itself; if a run was killed mid-flight,
`pkill -f "port-forward.*demo-sandbox"` clears it. Nothing is deployed and nothing is left
running.

## What it is not

It is not a gate. It grades nothing in CI and blocks no merge. The estate's gates live in
`rules.yaml`; this is the demonstration that those gates mean something.
