# Demo: estate-digest-worker

`bin/estate-digest-worker` is the first piece of the estate's local ops tier
(crew#929): a self-hosted, always-on open-model agent that answers the founder's
recurrent "update / what changed / what's red / what's next" using a LOCAL free
model (qwen2.5-coder:7b through Ollama), proving the estate runs its own
low-tier operational model work on owned hardware instead of a frontier token.

Run it on a laptop that has Ollama serving `qwen2.5-coder:7b` and `kubectl`
pointed at the estate:

```
$ bin/estate-digest-worker
STATUS: RED — flux not-Ready: alerts; chaos; crossplane;
1. WHAT CHANGED:  ...
2. WHAT'S NEXT:  ...
ok estate-digest-worker answered in 145s <- qwen2.5-coder:7b (local)
```

The digest is honest by construction. The `STATUS: RED / ALL GREEN` line is
computed deterministically by the script from live Flux reconciliation and the
estate snapshot rows, and printed by the script itself — never by the model.
The local model writes only the short narrative (what changed, what's next)
from the given facts. A base 7B twice fabricated "All Green" over real RED rows
before this guard existed; it cannot greenwash a red now (LAW 2).

The tier is a batch worker, not interactive: on the Intel i7 a 7B answers in
roughly two to four minutes because local generation runs near 1 to 2 tokens a
second. That is why the worker is meant to be scheduled, not asked in a chat.

To see a FAIL path, stop Ollama (`brew services stop ollama`) and run it again;
the script reports the model did not answer and exits non-zero instead of
printing a fake digest.
