# The model router's shared memory

The estate's model router runs as two copies so it survives losing a machine. Until now each copy kept its own memory: which vendor was cooling down, how much had been spent, how many calls were in the window — and no answer was ever reused. This feature gives both copies one shared memory (a small cache service next to the router) and bounded answer reuse: an identical call inside five minutes is answered from the cache instead of spending vendor money twice.

## See it work

Ask the router the same question twice within five minutes, with a router key:

    curl -s https://llm.mumchimp.com/v1/chat/completions \
      -H "Authorization: Bearer $ROUTER_KEY" -H 'content-type: application/json' \
      -d '{"model":"minimax","messages":[{"role":"user","content":"say ok"}]}'

The second answer comes back faster, and its trace in Langfuse is marked as a cache hit — a reused answer is visible, never silent. A call that must be fresh sends `"cache": {"no-cache": true}` and always reaches the live model; the drills do this.

## Where the pieces live

- Cache service: `platform/llm/redis.yaml` — its password is minted inside the cluster; no person ever sees or types it.
- Wiring: `platform/llm/config.base.yaml` — the shared-state rows and the five-minute answer cache; `bin/idp-vendor-render` writes the served copy.
- Guard: `tests/test_incident_litellm_redis_shared_state_and_bounded_cache.py` holds all of it in place.
