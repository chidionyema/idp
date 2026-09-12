# Demo: the agent that couldn't lie

A buyer's question about any agent claim is the same one: *how do I know it did what it
says?* This demo answers it with the estate's own discipline — an agent claims a change is
done, the truth-teller asks the cluster, and the claim either survives the question or the
merge is refused.

## Run it

```bash
bin/idp-truthteller-demo            # the rogue agent: claims Ready, the cluster disagrees
bin/idp-truthteller-demo --honest   # the same run with a claim that matches reality
```

## What you see

With no sandbox running, the truth-teller refuses to guess — a fail-closed BLIND, exit 2:

```
$ bin/idp-truthteller-demo
BLIND  truth-teller  sandbox vcluster not running: launch it first
       (bin/idp-sandbox action=launch, or the Demo Sandbox tile on /showcase)
$ echo $?
2
```

With the sandbox up, the rogue run ends in a refusal, and the refusal is the deliverable:

```
$ bin/idp-truthteller-demo
claim   agent-otto  demo-shop  replicas=3  status=Ready
observed            demo-shop  replicas=1  status=Progressing
FAIL   contradiction: the claim says 3 Ready, the cluster says 1 Progressing
$ echo $?
1
```

The honest run is the same machinery with a claim that agrees, and it is the only way to a 0:

```
$ bin/idp-truthteller-demo --honest
claim   agent-otto  demo-shop  replicas=1  status=Progressing
observed            demo-shop  replicas=1  status=Progressing
PASS   the claim survived the question
$ echo $?
0
```

## Why the exit code is the demo

A demo that prints "refused" and exits 0 is a demo that cannot fail, and a buyer's engineer
will find that in one sitting. Every outcome here is an exit code: `0` proved, `1` the claim
did not survive, `2` BLIND — no sandbox reachable, which is a FAIL and never a pass.

## Where it runs

Against the real `demo-sandbox` vcluster, not a mock. The kubeconfig comes from the
`vc-demo-sandbox` secret and the API is reached over
`kubectl -n demo-sandbox port-forward svc/demo-sandbox 8443:443`, the pattern in
`docs/how-to/prove-a-change-in-the-shadow.md`. 8443 is declared in `catalog/ports.yaml`, so
`bin/port-gate` passes.

## The page

`docs/demo/agent-cannot-lie.html` is the one-page version to open in front of a buyer.
