# The agent that couldn't lie: the recording

An agent says its change is done. The truth-teller asks the cluster, and the claim either
survives the question or the merge is refused.

This page is the machine-rendered recording of the real `bin/idp-truthteller-demo`. The
script is `demos/truthteller-demo.tape`; the `demo-render` workflow replays it on every
change and commits the result to `docs/demos/truthteller-demo.gif`, so this can never show
what the tool no longer does (Demo Standard, crew#805).

![The agent that couldn't lie, recorded by the machines](../demos/truthteller-demo.gif)

## The buyable moment

The claim and the cluster disagree, and that disagreement is the product:

```
claim     Ready 3
observed  CrashLoopBackOff 1
match     False
signature edd19abdb80f647b9e93a1d37ca506ba…
impact    Loss of checkout functionality for 5,000+ active sessions.
```

`3 Ready` was fabricated. The cluster said `1 CrashLoopBackOff`. The merge is refused, the
refusal is signed, and the signature is over the claim and the observed state together — so
the receipt cannot be re-cut to say something else.

## Run it

```bash
bin/idp-truthteller-demo            # the rogue claim, refused
bin/idp-truthteller-demo --honest   # a claim that matches, proved
bin/idp-truthteller-demo shadow --all
```

With no sandbox reachable it does not guess: `BLIND`, exit 2, fail-closed.

## The one-page version

For a buyer at a screen, open `agent-cannot-lie.html` beside this page — the same story told
as a single visual page.

## Where it lives

| | |
|---|---|
| the CLI | `bin/idp-truthteller-demo` |
| the recording script | `demos/truthteller-demo.tape` |
| the recording | `docs/demos/truthteller-demo.gif` |
| the buyer page | `docs/demo/agent-cannot-lie.html` |
| the tests | `tests/test_truthteller_demo.py` |

The port it forwards is 8443, declared in `catalog/ports.yaml`.
