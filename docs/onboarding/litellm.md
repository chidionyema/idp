# Onboarding: litellm-up / litellm-down / litellm-status

## What it is for

LiteLLM is the one router every model call in this estate should go through:
one base URL (`http://127.0.0.1:4000/v1`), one place virtual keys and spend
are tracked, one place a provider can be swapped without touching every
caller (LAW 34, provider-agnostic from day 0). The Claude CLI and Gemini CLI
are the two deliberate exceptions — they run on a subscription, not an API
key, so there is nothing for a proxy to meter.

## Where it lives

```
llm/litellm.yml     the compose stack
llm/config.yaml      model list and routing
llm/.env             every secret, chmod 600, gitignored, per checkout
bin/litellm-up        start (safe to re-run)
bin/litellm-down      stop, keeping the spend ledger and virtual keys
bin/litellm-status    what is answering, what it serves, what it costs
```

## How it starts

`bin/litellm-up` is `bin/langfuse-up`'s shape, deliberately, so the estate has
one pattern for bringing a compose stack up: validate `config.yaml` as YAML
before anything starts (a malformed one exits the container silently, the
same class of failure ClickHouse had with its XML comment), pull every
upstream key out of the age vault into `llm/.env` at mode 600, generate the
proxy's own three secrets once and never again. `LITELLM_SALT_KEY` cannot be
regenerated once virtual keys exist — rotating it makes every stored key
unreadable, the same rule Langfuse's `ENCRYPTION_KEY` follows.

The kernel (`sovereign/`) never holds `LITELLM_MASTER_KEY`. It reads
`LITELLM_BASE_URL` and `LITELLM_API_KEY` from the estate secret store
(`estate-secrets/secrets/<env>/`, through `scripts/secret-load`), and the key
there is a LiteLLM virtual key, alias `sovereign-kernel`, capped at $5/day by the
proxy itself. `~/.config/estate/estate.env` is only the fallback for a host with
no vault. Executable spec: `features/sovereign-bus/cp2_litellm_real.feature`
(crew#284 CP2).

## How to turn it off

```
bin/litellm-down
```

Containers stop, the spend ledger and virtual keys survive.

```
bin/litellm-down --wipe
```

Deletes them as well. Cannot be undone.

## Checking it

```
bin/litellm-status
```

Exits non-zero only when the proxy is actually not answering — a running
container serving a refused config still counts as down, because `docker ps`
would say otherwise and this check exists specifically to catch that case.

## Related files

```
bin/litellm-up / litellm-down / litellm-status
llm/litellm.yml, llm/config.yaml, llm/.env
docs/specs/fortress-stack.md         defines "done" for this stack
docs/onboarding/langfuse.md          the sibling stack this one's shape follows
```
