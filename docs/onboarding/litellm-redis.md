# Turning the router's answer reuse up or down

The router reuses an answer only for an identical call, and only for five minutes. Three dials, all in `platform/llm/config.base.yaml`:

1. **Life of a reused answer**: `ttl` under `cache_params`, in seconds. Keep it short — a longer life means an older answer. The guard test refuses anything over ten minutes.
2. **Turn answer reuse off estate-wide**: set `cache: false`. Leave the `redis_host` rows alone — they are the shared coordination memory the two router copies need whether or not answers are reused.
3. **One call that must be fresh**: the caller sends `"cache": {"no-cache": true}` on that request. Probes and drills do this so they always measure the live model.

After any edit, run `bin/idp-vendor-render` and commit the base file and the served copy together; the gates fail when the two drift. The cache service itself needs no hand: its password is minted in the cluster once, at creation, and nobody rotates, reads or types it.
