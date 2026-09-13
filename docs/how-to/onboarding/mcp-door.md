# Onboarding: the MCP door

## What it is for

Every agent tool call in this estate passes through one gateway (decision 0006). `bin/idp-mcp-door`
makes one real call to it and reports whether the door is open. It exists because a door that only
ever answers 401 is indistinguishable from a door that is down, and nothing here could tell the two
apart — measured 2026-09-13, the gateway's logs held three requests in 24 hours and all three were
401.

## Use it

```bash
# the key is the vault entry mcp-gateway; the value is never in git
export MCP_GATEWAY_KEY="$(kubectl -n mcp get secret mcp-gateway -o jsonpath='{.data.MCP_GATEWAY_KEY}' | base64 -d)"
python3 bin/idp-mcp-door --route estate      # or --route github
```

From outside the cluster, or against another address:

```bash
python3 bin/idp-mcp-door --url http://127.0.0.1:3310/estate/mcp
```

Exit codes: `0` the door served a call, `1` the door refused or answered unexpectedly, `2` BLIND —
`MCP_GATEWAY_KEY` is unset, so nothing was tested and that is not a pass.

## The header, which is the point

The gateway's `apiKey` policy reads **`Authorization: Bearer <key>`**. `x-api-key` — what most MCP
clients and the estate's own docs send — returns:

```
HTTP 401  error="api key authentication failure: no API Key found"  reason=APIKeyAuth
```

The message names neither the header nor the key, so a caller cannot tell which is wrong. If you
are wiring a client and get a 401, send `Authorization` before you touch the credential.

## What it costs

One `tools/list` call per invocation. Nothing is written: the probe does not call a tool, and
`tools/list` is a read. No new credential, no new route, no new fence — it uses the Service and the
policies that already exist.

## How to stop it

It is a script; stop running it. Nothing stays resident, no Job and no CronJob was added, and the
gateway is unchanged by its use.

## What to watch

- **A 401 after a key rotation.** The config carries `keyHash: sha256:...`, not the key. When the
  vault entry rotates, the hash must be regenerated in the same commit or every caller is refused —
  and the refusal reads as an auth failure, not as a stale hash.
- **A 200 with zero tools.** The door answered but the backend behind it is empty; check
  `estate-mcp` before blaming the gateway.
- **Where a person goes next:** `docs/tutorials/demo/mcp-door.md` shows a real call.
