# Demo: estate-digest-keeper

`bin/estate-digest-keeper` is the heartbeat slot of the estate's local ops tier
(crew#929): it keeps the free local model resident and proves the tier is alive.
A resident model answers a first task fast; a cold one costs the worker its job
before it starts. Measured on the Intel i7, reloading 7B ran 30.8 s cold versus
16.9 s warm (crew#284), and a warm-tier keep-alive removes that tax from every
worker that follows.

Run the one-shot liveness check on a host with Ollama serving the model:

```
$ bin/estate-digest-keeper
ALIVE:1788938377
```

The timestamp is epoch seconds at the moment the model genuinely answered a
minimal warm-up generation (reply the single word ALIVE). The keeper never
prints a guessed green: if the model is unreachable or cold it prints a FAIL
line and exits non-zero. LAW 2 — no liveness claim without a measurement.

To force the weights resident (a good hook for boot / after a model unload), or
to run the tier as a repeating heartbeat:

```
$ bin/estate-digest-keeper --load        # warm the model, no loop
$ bin/estate-digest-keeper --loop 300    # ping every 300 s until stopped
```

This is the "no-op" contract of slot 7: when there is no real work, the worker
stays warm and quiet rather than fabricating activity, so a polling call-bus
never sees a false green or pays a cold-start on the first real task.
